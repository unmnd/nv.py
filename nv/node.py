#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
The `Node` class is the base class for all nodes in the network. It provides
methods for communicating between different nodes and the server, as well as
logging, parameter handling, and other things.

Callum Morrison
UNMND, Ltd. 2022
<callum@unmnd.com>

This file is part of nv.

nv is free software: you can redistribute it and/or modify it under the
terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

nv is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
nv. If not, see <https://www.gnu.org/licenses/>.
"""

import os
import platform
import re
import signal
import sys
import threading
import time
import typing
import uuid
from importlib import metadata

# import numpy as np
import orjson as json
import psutil

# import quaternion  # This need to be imported to extend np
import redis
import yaml

# Optional imports
try:
    import cysimdjson

    lazy_parser = cysimdjson.JSONParser()
except ImportError:
    lazy_parser = None


from nv import exceptions, logger, utils

PLATFORM = platform.system() + " " + platform.release() + " " + platform.machine()


class Node:
    def __init__(
        self,
        name: str = None,
        skip_registration: bool = False,
        log_level: int = None,
        keep_old_parameters: bool = False,
        use_lazy_parser: bool = False,
        workspace: str = None,
        redis_host: str = None,
        redis_port: int = 6379,
        redis_unix_socket: str = None,
    ):
        """
        The Node class is the main class of the nv framework. It is used to
        handle all interaction with the framework, including initialisation of
        nodes, subscribing to topics, publishing to topics, and creating timers.

        It is designed to be relatively compatible with the ROS framework,
        although some simplifications and improvements have been made where
        applicable.

        Initialise a new node by inheriting this class. Ensure you call
        `super().__init__(name)` in your new node.

        ---

        ### Parameters:
            - `name` (str): The name of the node.
            - `skip_registration` (bool): Whether to skip registering the node.
                This should not be used for normal nodes, but is useful for
                commandline access.
            - `log_level` (int): The log level to use. If not specified, the
                default is used.
            - `keep_old_parameters` (bool): Whether to keep old parameters from
                previous instances of this node.
            - `use_lazy_parser` (bool): Whether to use the lazy parser
              (cysimdjson) when decoding messages for improved performance on
              large data.
            - `workspace` (str): An optional workspace to use for topics.
            - `redis_host` (str): Force the Redis host to use.
            - `redis_port` (int): Force the Redis port to use.
            - `redis_unix_socket` (str): Force the Redis unix socket to use.

        """

        # Bind callbacks to gracefully exit the node on signal
        signal.signal(signal.SIGINT, self._sigterm_handler)
        signal.signal(signal.SIGTERM, self._sigterm_handler)

        # Generate a random name if one is not specified
        if name is None:
            name = utils.generate_name()

        # Initialise logger
        self.log = logger.generate_log(
            name, log_level=log_level or os.environ.get("NV_LOG_LEVEL") or logger.DEBUG
        )

        # Check if the node should be started by calling self.node_condition().
        while not self.node_condition():
            self.log.info(f"Node condition not met, waiting...")
            time.sleep(10)

        self.log.debug(
            f"Initialising '{name}' using framework version nv {metadata.version('nv-framework')}"
        )

        # Initialise parameters
        self.name = name
        self.node_registered = False
        self.skip_registration = skip_registration
        self.stopped = threading.Event()
        self._start_time = time.time()

        # Only allow lazy parsing if the module is available
        if use_lazy_parser and lazy_parser is not None:
            self.log.debug("Using lazy parser")
            self.use_lazy_parser = True
        else:
            if use_lazy_parser and lazy_parser is None:
                self.log.warning("Lazy parser not available, using standard parser")
            else:
                self.log.debug("Using standard parser")

            self.use_lazy_parser = False

        # Workspace used for topic names
        self.workspace = workspace or os.environ.get("NV_WORKSPACE")

        if workspace:
            self.log.info(f"Using workspace '{workspace}'")
        else:
            self.log.info("No workspace specified")

        # The subscriptions dictionary is in the form of:
        # {
        #   topic1: [callback1],
        #   topic2: [callback2, callback3],
        #   ...
        # }
        self._subscriptions = {}

        # The publishers dict tracks each topic which has been published on
        # in the past, and the unix timestamp of the last publish.
        self._publishers = {}

        # The services dictionary is used to keep track of exposed services, and
        # their unique topic names for calling.
        self._services = {}
        self._service_locks = {}

        # Connect redis clients
        self.redis_host = redis_host or os.environ.get("NV_REDIS_HOST")
        self.redis_port = redis_port or os.environ.get("NV_REDIS_PORT")
        self.redis_unix_socket = redis_unix_socket or os.environ.get(
            "NV_REDIS_UNIX_SOCKET"
        )

        # The topics database stores messages for communication between nodes.
        # The key is always the topic.
        self._redis_topics = self._connect_redis(db=0)

        # The parameters database stores key-value parameters to be used for
        # each node. The key is the node_name.parameter_name.
        self._redis_parameters = self._connect_redis(db=1)

        # The transforms database stores transformations between frames. The key
        # is in the form <source_frame>:<target_frame>.
        self._redis_transforms = self._connect_redis(db=2)

        # The nodes database stores up-to-date information about which nodes are
        # active on the network. Each node is responsible for storing and
        # keeping it's own information active.
        self._redis_nodes = self._connect_redis(db=3)

        # Get the current Python process for resource monitoring
        self.process = psutil.Process()

        if self.skip_registration:
            self.log.warning("Skipping node registration...")
        else:

            # Check if another node with this name already exists
            if self.check_node_exists(self.name):
                # It may have been recently terminated, wait up to
                # 10 seconds and try again

                self.log.warning(
                    f"Node '{self.name}' already exists, waiting to see if it disappears..."
                )

                start_time = time.time()

                while self.check_node_exists(self.name):
                    time.sleep(1)

                    if time.time() - start_time > 10:
                        raise exceptions.DuplicateNodeNameException(
                            f"Node '{self.name}' already exists on this network!"
                        )

                self.log.info(f"Node '{self.name}' no longer exists, continuing...")

            # Register the node with the server
            self._register_node()

            # Remove residual parameters if required
            if not keep_old_parameters:
                self.delete_parameters()

        # Pubsub is done globally, this allows topics to be subscribed to
        # without restarting the pubsub thread. The issue with this is that
        # multiple nodes initialised by the same file will conflict. We get
        # around this by only creating variables if they don't already exist.

        # Start the pubsub loop for topics in a separate thread.
        try:
            Node._pubsub
        except AttributeError:
            Node._pubsub = self._redis_topics.pubsub()

        # Create the pubsub thread if required
        try:
            Node._pubsub_thread
        except AttributeError:
            Node._pubsub_thread = threading.Thread(
                target=self._pubsub_loop, daemon=True, name="Pubsub Loop"
            )

        # The service requests dict improves efficiency by allowing all service
        # requests to respond to the same topic (meaning only one subscription).
        # The queue keys are a unique request id, and the values contain a dict:
        # {
        #     "result": "success"/"error"
        #     "data": <response data>/<error message>,
        #     "event": Event()
        # }
        self._service_requests = {}

        # Generate a random id for the service response channel for this node
        self.service_response_channel = "srv://" + str(uuid.uuid4())
        self.create_subscription(
            self.service_response_channel, self._handle_service_callback
        )

        # Used to terminate the node remotely
        self.create_subscription("nv_terminate", self._handle_terminate_callback)

    def _register_node(self):
        """
        Register the node with the server.
        """

        # Create a timer which renews the node information every 5 seconds
        self._renew_node_information_timer = self.create_loop_timer(
            interval=5,
            function=self._renew_node_information,
            immediate=True,
        )

        # Set the node as registered
        self.node_registered = True

        self.log.info(f"Node successfully registered!")

    def _renew_node_information(self):
        """
        Renew the node information, by overwriting the node information and
        resetting a 10 second expiry timer.
        """

        # Update the node information
        self._redis_nodes.set(
            self.name,
            json.dumps(self.get_node_information()),
            ex=10,
        )

    def _deregister_node(self):
        """
        Deregister the node with the server.
        """

        if not self.node_registered:
            self.log.warning(
                f"Node '{self.name}' is not registered, cannot deregister!"
            )
            return

        # Stop the node information renewal timer
        self._renew_node_information_timer.stop()

        # Delete the node information from the nodes database
        self._redis_nodes.delete(self.name)

        # Set the node as deregistered
        self.node_registered = False

        self.log.info(f"Node successfully deregistered!")

    def _connect_redis(
        self,
        db: int = 0,
    ):
        """
        Connect the Redis client to the database to allow messaging. It uses a
        unix sock if available, otherwise it attempts to find the host
        automatically on either localhost, or connecting to a container named
        'redis'.

        Optionally, the host can be specified using the parameter `redis_host`,
        to overwrite autodetection.

        ---

        ### Parameters:
            - `redis_unix_socket` (str): The path to the unix socket.
            - `redis_host` (str): The host of the redis database.
            - `redis_port` (int): The port of the redis database.
            - `db` (int): The database hosting messaging data.

        ---

        ### Returns:
            The redis client.
        """

        def _create_redis(connection_params: dict):
            self.log.debug(f"Connecting to Redis using parameters: {connection_params}")

            r = redis.Redis(**connection_params)
            r.ping()

            return r

        # If a unix socket is specified, use it
        if self.redis_unix_socket:
            self.log.info(
                f"Connecting to Redis using unix socket: {self.redis_unix_socket}"
            )

            redis_connection_params = {
                "unix_socket_path": self.redis_unix_socket,
                "db": db,
            }

            return _create_redis(redis_connection_params)

        # If a host is specified, use it
        elif self.redis_host:

            self.log.info(
                f"Connecting to Redis using host/port: {self.redis_host}:{self.redis_port}"
            )

            redis_connection_params = {
                "host": self.redis_host,
                "port": self.redis_port,
                "db": db,
            }

            return _create_redis(redis_connection_params)

        # Otherwise, try to find a redis host automatically
        else:
            self.log.info("Attempting to autodetect Redis host...")

            hosts = ["localhost", "redis", "127.0.0.1"]

            for host in hosts:
                redis_connection_params = {
                    "host": host,
                    "port": self.redis_port,
                    "db": db,
                }

                try:
                    r = _create_redis(redis_connection_params)
                    self.redis_host = host
                    return r

                except redis.exceptions.ConnectionError:
                    pass

            raise exceptions.RedisConnectionException("Could not connect to Redis!")

    def _pubsub_loop(self):
        """
        Continously monitors the Redis server for updated messages, enabling
        subscription callbacks to trigger.
        """
        while True:
            try:
                # The timeout changes the way this function works.
                # Normally, the function will not block. Adding a timeout will
                # block for up to that time. If no messages are received, the
                # function will return None. A larger timeout is less CPU
                # intensive, but means node termination will be delayed.
                Node._pubsub.get_message(ignore_subscribe_messages=True, timeout=100)
            except RuntimeError:
                # If there are no subscriptions, an error is thrown. This is
                # fine; when a subscription is added the errors will stop.
                continue

    def _decode_pubsub_message(self, message):
        """
        ### Decode a message received by a callback to the Redis pubsub.

        ---

        ### Parameters:
            - `message` (str): The message to decode.

        ---

        ### Returns:
            The decoded message.
        """

        try:
            # Select the parser to use
            if self.use_lazy_parser:
                return lazy_parser.loads(str(message))
            else:
                return json.loads(message)
        except (json.JSONDecodeError, ValueError):
            return message

    def _encode_pubsub_message(self, message):
        """
        ### Encode a message to be sent to the Redis pubsub.

        ---

        ### Parameters:
            - `message` (str): The message to encode.

        ---

        ### Returns:
            The encoded message.
        """

        try:
            return json.dumps(message, option=json.OPT_SERIALIZE_NUMPY)
        except TypeError:
            return message

    def _handle_subscription_callback(self, message):
        """
        Handle messages received as a callback from Redis subscriptions. This is
        required because Redis callbacks contain a dictionary of data (as
        opposed to just the value from key changed).

        The dictionary is as follows:
            {
                "type": "message",
                "pattern": None,
                "channel": <topic name: bytes>,
                "data": <message: bytes>
            }

        The data is decoded and send to the callback function supplied in the
        original subscription request.

        ---

        ### Parameters:
            - `message` (dict): The message to handle.

        ---

        ### Returns:
            `None`
        """

        # Decode the message
        topic = message.get("channel").decode("utf-8")
        message = self._decode_pubsub_message(message.get("data"))

        # Call the corresponding callback(s)
        for i, callback in enumerate(self._subscriptions[topic]):

            # Handle callback in its own thread. This is done because
            # _handle_subscription_callback locks the PubSub Loop thread,
            # meaning that no other data can be received while the callback
            # below is running. This causes issues e.g. when a service is called
            # inside a message callback.
            thread = threading.Thread(
                target=callback,
                args=(message,),
                name=f"Callback thread {i} for topic {topic}",
            )
            thread.start()

    def _handle_service_callback(self, message):
        """
        Handle responses from server requests. This works similarly to
        `_handle_subscription_callback`, but is specific to messages received as
        a response to a service request.

        Any response contains the following dict:
        ```
        {
            "result": "success"/"error",
            "data": <the returned data>/<the error stacktrace>,
            "request_id": <the id of the request>,
        }
        ```

        ---

        ### Parameters:
            - `message` (dict): The message to handle.

        ---

        ### Returns:
            `None`
        """

        self._service_requests[message["request_id"]]["result"] = message["result"]

        # If the data starts with "NV_BYTES:" we need to fetch the binary data
        # directly from redis
        if isinstance(message["data"], str) and message["data"].startswith("NV_BYTES:"):
            self._service_requests[message["request_id"]][
                "data"
            ] = self._redis_topics.get(message["data"])
        else:
            self._service_requests[message["request_id"]]["data"] = message["data"]

        self._service_requests[message["request_id"]]["timings"] = message["timings"]

        # Set the event to indicate the response has been received
        self._service_requests[message["request_id"]]["event"].set()

    def _handle_terminate_callback(self, message):
        """
        ### Handle node termination requests

        ---

        ### Parameters:
            - `message` (dict): The message to handle.
                - `message["node"]` (str): The node to terminate.
                - `message["reason"]` (str): The reason for termination.
        """

        if message.get("node") == self.name:
            self.log.info(
                f"Node terminated remotely with reason: {message.get('reason')}"
            )
            self.destroy_node()

    def _sigterm_handler(self, _signo, _stack_frame):
        """
        Handle termination signals to gracefully stop the node.
        """
        self.log.info("Received program termination signal; exiting...")
        self.destroy_node()
        sys.exit(0)

    def node_condition(self) -> bool:
        """
        This function is called before any further node setup. It is used to
        determine whether the node should be started or not.

        It can be used to stop node creation until a desired condition is met,
        for example that a device is connected.

        When overwriting this function in a node, it should not depend on any
        other node functions, as they will not be initialised yet.

        ---

        ### Returns:
            `True` if the node should be started, `False` otherwise.
        """
        return True

    def spin(self):
        """
        ### Blocking function while the node is active.

        It's not necessary to call this function to run the node! This is just
        used as a blocker if there is no other code to run.
        """
        self.stopped.wait()

    def get_logger(self, name=None):
        """
        ### Get a logger for the nv framework.
        Note, the logger for the current node is always available as `self.log`.

        ---

        ### Parameters:
            - `name` (str): The name of the logger.
                [Default: <node name>]

        ---

        ### Returns:
            A logger for the nv framework.
        """
        return logger.get_logger(name or self.name)

    def get_name(self) -> str:
        """
        ### Get the name of the node.

        ---

        ### Returns:
            The name of the node.
        """
        return self.name

    def destroy_node(self):
        """
        ### Destroy the node cleanly.

        Terminating a node without calling this function is not a major issue,
        however the node information will remain in the network for several
        seconds, which might cause issues with service calls, or if you want to
        re-start the node immediately.
        """

        self.log.debug("Node termination requested...")

        # Remove the node from the list of nodes
        self._deregister_node()

        # Stop any timers or services currently running
        self.stopped.set()

    def get_node_ps(self, node_name: str = None) -> dict:
        """
        ### Get process information about the node.

        If a node name is provided, the information for that node is returned.
        If no node name is provided, the information for the current node is returned.

        ---

        ### Returns:
            A dictionary containing information about the node's process.
        """

        if node_name is None:
            return {
                "pid": self.process.pid,
                # "environ": self.process.environ(),
                "cpu": round(self.process.cpu_percent(interval=None), 2),
                "memory": round(self.process.memory_info().rss, 2),
                "platform": PLATFORM,
                "lang": "Python " + platform.python_version(),
            }
        else:
            return json.loads(self._redis_nodes.get(node_name))["ps"]

    def get_node_information(self, node_name: str = None) -> dict:
        """
        ### Return the node information dictionary.

        If a node name is provided, the information for that node is returned.
        If no node name is provided, the information for the current node is returned.

        ---

        ### Returns:
            The node information dictionary.
        """
        if node_name is None:
            return {
                "time_registered": self._start_time,
                "time_modified": time.time(),
                "version": metadata.version("nv-framework"),
                "subscriptions": list(self._subscriptions.keys()),
                "publishers": self._publishers,
                "services": self._services,
                "ps": self.get_node_ps(),
            }
        else:
            return json.loads(self._redis_nodes.get(node_name))

    def get_nodes(self) -> typing.Dict[str, dict]:
        """
        ### Get all nodes present in the network.

        ---

        ### Returns:
            A dictionary containing all nodes on the network.
        """
        return {
            node.decode(): json.loads(self._redis_nodes.get(node))
            for node in self._redis_nodes.keys()
        }

    def get_nodes_list(self) -> typing.List[str]:
        """
        ### Get a list of names of all nodes present in the network.

        ---

        ### Returns:
            A list containing all nodes on the network.
        """
        return [node.decode() for node in self._redis_nodes.keys()]

    def check_node_exists(self, node_name: str) -> bool:
        """
        ### Check if a node exists.
        Check if a node exists on the network.

        ---

        ### Parameters:
            - `node_name` (str): The name of the node to check.

        ### Returns:
            - `True` if the node exists, `False` otherwise.
        """
        return self._redis_nodes.exists(node_name)

    def get_topics(self) -> typing.Dict[str, float]:
        """
        ### Get all topics present in the network.

        ---

        ### Returns:
            A dictionary containing all topics on the network,
            and the time of their most recent message.
        """

        topics = {}

        nodes = self.get_nodes()

        # Loop over each node and add their publishers to the list. If the topic
        # already exists, the most recent publish time is used.
        for node in nodes.values():
            for topic, last_published in node.get("publishers").items():

                # Remove service topics
                if topic.startswith("srv://"):
                    continue

                if topic not in topics:
                    topics[topic] = last_published
                else:
                    topics[topic] = max(topics[topic], last_published)

        return topics

    def get_topic_subscribers(self, topic: str) -> typing.List[str]:
        """
        ### Get a list of nodes which are subscribed to a specific topic.

        Note: This will not count nodes which have not been registered (such as
        the nv cli)! If you want to include these subscribers, use
        `get_num_topic_subscriptions` instead.

        ---

        ### Parameters:
            - `topic` (str): The topic to get the subscriptions for.

        ---

        ### Returns:
            A list of nodes which are subscribed to the topic.
        """

        # First, get all registered nodes
        nodes = self.get_nodes()

        # Then, filter out the nodes which are subscribed to the topic
        return [
            node
            for node, info in nodes.items()
            if topic in info.get("subscriptions", {})
        ]

    def get_num_topic_subscriptions(self, topic: str) -> int:
        """
        ### Get the number of topic subscriptions.

        Although this method could call `get_topic_subscribers`, this will
        ignore any nodes which are not currently registered (such as the nv
        cli). Instead, it uses the built-in redis clients list, which only keeps
        a list of topics with at least one subscription.

        ---

        ### Parameters:
            - `topic` (str): The topic to check.

        ---

        ### Returns:
            The number of subscribers to the topic.
        """

        return self._redis_topics.pubsub_numsub(topic)[0][1]

    def has_subscribers(self, topic: str) -> bool:
        """
        ### Check if a topic has any subscribers (including unregistered ones).

        ---

        ### Parameters:
            - `topic` (str): The topic to check.

        ---

        ### Returns:
            `True` if the topic has any subscribers, `False` otherwise.
        """
        return self.get_num_topic_subscriptions(topic) > 0

    def create_subscription(Node, topic_name: str, callback_function) -> object:
        """
        ### Create a subscription to a topic.

        ---

        ### Parameters:
            - `topic_name` (str): The name of the topic to subscribe to.
            - `callback_function` (function): The function to call when a message
                is received on the topic.

        ---

        ### Example::

            # Create a subscription to the topic "test"
            def callback_function(msg):
                print(msg)

            sub = create_subscription("test", callback_function)

            # Unsubscribe from the topic
            sub.unsubscribe()
        """

        class Subscription:
            def __init__(self, topic_name, callback_function):
                self.topic_name = topic_name
                self.callback_function = callback_function
                self.subscribed = True

            def unsubscribe(self):
                if self.subscribed:
                    Node._subscriptions[topic_name].remove(self.callback_function)
                    self.subscribed = False
                    return True

                return False

        # Start the pubsub loop if it hasn't already been started
        if not Node._pubsub_thread.is_alive():
            Node._pubsub_thread.start()

        # The `Node` object is used rather than `self` when accessing the pubsub
        # object, which allows the separate thread running the pubsub loop
        # (`_pubsub_loop`) to access subscriptions created at any point, after
        # the loop has already started.

        # The alternative is to stop and re-create the loop whenever a new
        # subscription is added, however this could result in missed messages for
        # a short period of time, and so it's avoided.

        # Create the subscription to Redis
        Node._pubsub.subscribe(**{topic_name: Node._handle_subscription_callback})

        # Add the subscription to the list of subscriptions for this topic
        if topic_name in Node._subscriptions:
            Node._subscriptions[topic_name].append(callback_function)
        else:
            Node._subscriptions[topic_name] = [callback_function]

        return Subscription(topic_name, callback_function)

    def destroy_subscription(self, topic_name: str):
        """
        ### Destroy a subscription to a topic.

        Note: This will remove *all* subscription callbacks for a particular
        topic. It's recommended to instead use the `unsubscribe` method in the
        `Subscription` object.

        ---

        ### Parameters:
            - `topic_name` (str): The name of the topic to unsubscribe from.
        """

        # Unsubscribe from Redis
        Node._pubsub.unsubscribe(topic_name)

        # Remove any callbacks for this subscription
        if topic_name in self._subscriptions:
            del self._subscriptions[topic_name]

    def get_absolute_topic(self, topic_name: str):
        """
        ### Convert a topic name to an absolute topic name.

        nv topics default to the global workspace, but this can be overridden by
        proceeding the topic with a ".", which will automatically add the node
        name.

        A custom workspace can be added in the node setup or using an
        environment variable.

        ---

        ### Parameters:
            - `topic_name` (str): The name of the topic to convert.

        ---

        ### Returns:
            The absolute topic name.
        """

        if topic_name.startswith("."):
            topic_name = f"{self.name}{topic_name}"

        if (not self.workspace is None) and (not topic_name.startswith(self.workspace)):
            topic_name = f"{self.workspace}.{topic_name}"

        return topic_name

    def publish(self, topic_name: str, message):
        """
        ### Publish a message to a topic.

        ---

        ### Parameters:
            `topic_name` (str): The name of the topic to publish to.
            `message`: The message to publish.

        ---

        ### Returns:
            bool: `True` if the message was successfully published, `False` otherwise.
        """

        # Convert the topic name to an absolute topic name
        topic_name = self.get_absolute_topic(topic_name)

        # Update the publishers dict
        self._publishers[topic_name] = time.time()

        # Send the message to the Redis pubsub
        return self._redis_topics.publish(
            topic_name, self._encode_pubsub_message(message)
        )

    def create_loop_timer(
        self,
        interval: int,
        function: typing.Callable,
        autostart: bool = True,
        immediate: bool = False,
        *args,
        **kwargs,
    ):
        """
        ### Create a looping timer in a new thread.

        This is equivalent to using `nv.utils.LoopTimer` directly.

        Additional args and kwargs are passed to the function.

        ---

        ### Parameters:
            - `interval` (int): The interval in seconds between calls to the
                function.
            - `function` (function): The function to call.
            - `autostart` (bool): Whether to start the timer automatically.
            - `immediate` (bool): Whether to call the function immediately after start.

        """

        loop_timer = utils.LoopTimer(
            interval=interval,
            function=function,
            autostart=autostart,
            immediate=immediate,
            *args,
            **kwargs,
        )

        return loop_timer

    def get_services(self):
        """
        Get all the services currently registered, and their topic ID used when
        calling them.

        ---

        ### Returns:
            A dictionary containing the service information.
        """

        # Get all nodes currently registered
        nodes = self.get_nodes()

        # Extract the service information from the nodes
        services = {}

        for node, info in nodes.items():
            if registered_services := info.get("services"):
                for service_name, service_id in registered_services.items():
                    services[service_name] = service_id

        return services

    def wait_for_service_ready(self, service_name: str, timeout: int = 10):
        """
        ### Wait for a service to be ready.

        This method is used to wait for a service to be ready before calling it.
        This is useful when a service is created in the same thread as the node,
        and the node needs to wait for the service to be ready before calling it.

        ---

        ### Parameters:
            - `service_name` (str): The name of the service to wait for.
            - `timeout` (int): The timeout in seconds to wait for the service to
                be ready.

        ---

        ### Returns:
            bool: `True` if the service is ready, `False` otherwise.
        """

        self.log.debug(f"Waiting for service {service_name} to be ready...")

        while service_name not in self.get_services():
            if timeout <= 0:
                raise exceptions.ServiceNotFoundException(
                    f"Service {service_name} not found"
                )

            time.sleep(0.1)
            timeout -= 0.1

        self.log.debug(f"Service {service_name} is ready.")
        return True

    def create_service(
        self,
        service_name: str,
        callback_function: typing.Callable,
        allow_parallel_calls: bool = True,
    ):
        """
        ### Create a service.

        A service is a function which can be called by other nodes. It can
        accept any number of args and kwargs, and can return any Python
        datatype.

        ---

        ### Parameters:
            - `service_name` (str): The name of the service to create.
            - `callback_function` (function): The function to call when a message
                is received on the service.
            - `allow_parallel_calls` (bool): Whether to allow multiple calls to
                the service at the same time.

        ---

        ### Example::

            # Create a service called "test"
            def callback_function(message):
                print(message)

            create_service("test", callback_function)
        """

        def handle_service_call(message):
            """
            Used to handle requests to call a service, and respond by publishing
            any data on the requested topic.
            """

            # Acquire lock
            if not allow_parallel_calls:

                # Check if the service is already being called
                if self._service_locks[service_name].locked():
                    self.log.debug(
                        f"Service {service_name} is already being called. If you see this message frequently the service cannot keep up with requests!"
                    )

                self._service_locks[service_name].acquire()

            # Get the response topic from the message
            response_topic = message["response_topic"]

            # Extract and update timings dict
            timings = message["timings"]
            timings["request_received"] = time.time()

            # Get args and kwargs from the message
            args = message.get("args", [])
            kwargs = message.get("kwargs", {})

            # Call the service
            try:
                data = callback_function(*args, **kwargs)
                timings["request_completed"] = time.time()
            except Exception as e:
                self.log.error(
                    f"Error handling service call: '{service_name}'", exc_info=e
                )
                self.publish(
                    response_topic,
                    {
                        "result": "error",
                        "data": str(e),
                        "request_id": message["request_id"],
                        "timings": timings,
                    },
                )
                return

            # If the data is bytes, we can't JSON serialise it. Instead, we push
            # it straight to Redis, and send the key in the service response.
            if isinstance(data, bytes):
                key = "NV_BYTES:" + uuid.uuid4().hex
                self._redis_topics.set(key, data, ex=60)
                data = key

            # Publish the result on the response topic
            self.publish(
                response_topic,
                {
                    "result": "success",
                    "data": data,
                    "request_id": message["request_id"],
                    "timings": timings,
                },
            )

            if not allow_parallel_calls:
                self._service_locks[service_name].release()

        # Generate a unique ID for the service
        service_id = "srv://" + str(uuid.uuid4())

        # Register a message handler for the service
        self.create_subscription(service_id, handle_service_call)

        # Save the service name and ID
        self._services[service_name] = service_id

        # Renew node info immediately
        self._renew_node_information()

        self._service_locks[service_name] = threading.Lock()

    def call_service(self, service_name: str, *args, **kwargs):
        """
        ### Call a service.

        ---

        ### Parameters:
            - `service_name` (str): The name of the service to call.
            - `*args`: Arguments to pass to the service.
            - `**kwargs`: Keyword arguments to pass to the service.

        ---

        ### Returns:
            The result of the service.

        ---

        ### Raises:
            - `nv.exceptions.ServiceNotFoundException`: If the service is not registered.

        ---

        ### Example::

            # Call the service "test"
            response = call_service("test", "Hello", "World")
        """

        # Get all the services currently registered
        services = self.get_services()

        # Check the service exists
        if service_name not in services:
            raise exceptions.ServiceNotFoundException(
                f"Service '{service_name}' does not exist"
            )

        # Get the service ID
        service_id = services[service_name]

        # Generate a request id
        request_id = str(uuid.uuid4())

        # Create the entry in the service requests dict
        self._service_requests[request_id] = {
            "event": threading.Event(),
        }

        # Create a message to send to the service
        message = {
            "timings": {
                "start": time.time(),
            },
            "response_topic": self.service_response_channel,
            "request_id": request_id,
            "args": args,
            "kwargs": kwargs,
        }

        # Call the service
        self.publish(service_id, message)

        # Wait for the response
        self._service_requests[request_id]["event"].wait(timeout=10)

        # Handle a timeout
        if not self._service_requests[request_id]["event"].is_set():
            raise exceptions.ServiceTimeoutException(
                f"Service '{service_name}' timed out"
            )

        # Check for errors
        if self._service_requests[request_id]["result"] == "error":
            raise exceptions.ServiceErrorException(
                f"Service '{service_name}' returned an error: {self._service_requests[request_id]['data']}"
            )

        # Extract the data
        data = self._service_requests[request_id]["data"]
        timings = self._service_requests[request_id]["timings"]

        # Complete timings
        timings["end"] = time.time()

        # Normalise timings to the time the request was sent
        timings = {
            key: (value - timings["start"]) * 1000 for key, value in timings.items()
        }

        # Print and format the cumulative timings
        self.log.debug(
            f"Service ({service_name}) timings: {' -> '.join([f'{value:.0f}ms ({key})' for key, value in timings.items()])}"
        )

        # Delete the request
        del self._service_requests[request_id]

        # Return the response
        return data

    def get_parameter(
        self, name: str, node_name: str = None, fail_if_not_found: bool = False
    ):
        """
        ### Get a parameter value from the parameter server.

        ---

        ### Parameters:
            - `name` (str): The parameter name to get.
            - `node_name` (str): Optionally get parameters from a different node.
                If not specified, uses the current node.
            - `fail_if_not_found` (bool): If `True`, raise an exception if the
                parameter is not found. If `False`, return `None`.

        ---

        ### Returns:
            The parameter value if it exists, or `None` if it doesn't.

        ---

        ### Raises:
            ParameterNotFoundException: If the parameter is not found and fail_if_not_found is `True`.

        ---

        ### Example::

            # Get the parameter 'foo' from the current node
            foo = get_parameter('foo')

            # Get the parameter 'foo' from the node 'node1'
            foo = get_parameter('foo', node_name='node1')
        """

        # If the node name is not specified, use the current node
        if not node_name:
            node_name = self.name

        # Get the parameter from the parameter server
        parameter = self._redis_parameters.get(f"{node_name}.{name}")

        # Raise an exception if the parameter is not found and fail_if_not_found is True
        if parameter is None and fail_if_not_found:
            raise exceptions.ParameterNotFoundException(
                f"Parameter {parameter} not found"
            )

        # Extract the value from the parameter if it exists
        if parameter is not None:
            return json.loads(parameter).get("value")

        # Otherwise return None
        return None

    def get_parameters(
        self, node_name: str = None, match: str = "*"
    ) -> typing.Dict[str, typing.Any]:
        """
        ### Get all parameters for a specific node, matching a pattern.

        ---

        ### Parameters:
            - `node_name` (str): Optionally get parameters from a different node.
                If not specified, uses the current node.
            - `match` (str): The pattern to match. Defaults to '*', which returns
                every parameter for that node.

        ---

        ### Returns:
            A dictionary of parameters.

        ---

        ### Example::

            # Get all parameters for the current node
            parameters = get_parameters()

            # Get all parameters for the node 'node1'
            parameters = get_parameters(node_name='node1')

            # Get all parameters for the node 'node1' matching 'foo*'
            parameters = get_parameters(node_name='node1', match='foo*')
        """

        # If the node name is not specified, use the current node
        if not node_name:
            node_name = self.name

        parameters = {}

        # Get all keys which start with the node name
        keys = self._redis_parameters.scan_iter(match=f"{node_name}.{match}")

        # Extract the parameter name from each key
        for key in keys:
            parameter = key.decode().split(".", 1)[1]
            parameters[parameter] = self.get_parameter(parameter, node_name)

        # Return the parameters
        return parameters

    def get_parameter_description(self, name: str, node_name: str = None):
        """
        ### Get a parameter description from the parameter server.

        ---

        ### Parameters:
            - `parameter` (str): The parameter name to get.
            - `node_name` (str): Optionally get parameters from a different node.
                If not specified, uses the current node.

        ---

        ### Returns:
            The parameter description if it exists, or `None` if it doesn't.

        ---

        ### Example::

            # Get the parameter 'foo' from the current node
            foo = get_parameter_description('foo')

            # Get the parameter 'foo' from the node 'node1'
            foo = get_parameter_description('foo', node_name='node1')
        """

        # If the node name is not specified, use the current node
        if not node_name:
            node_name = self.name

        # Get the parameter from the parameter server
        parameter = self._redis_parameters.get(f"{node_name}.{name}")

        # Extract the value from the parameter if it exists
        if parameter is not None:
            return json.loads(parameter).get("description")

        # Otherwise return None
        return None

    def set_parameter(
        self, name: str, value, node_name: str = None, description: str = None
    ):
        """
        ### Set a parameter value on the parameter server.

        ---

        ### Parameters:
            - `name` (str): The parameter name to set.
            - `value`: The value to set the parameter to.
            - `node_name` (str): Optionally set parameters on a different node.
                If not specified, uses the current node.
            - `description` (str): An optional description of the parameter.

        ---

        ### Returns:
            `True` if the parameter was set correctly.

        ---

        ### Raises:
            Exception: If the parameter server returns an error.

        ---

        ### Example::

            # Set the parameter "foo" to "bar" on the current node
            set_parameter("foo", "bar")

            # Set the parameter "foo" to "bar" on the node "node1"
            set_parameter(
                name="foo",
                value="bar",
                node_name="node1",
                description="This is a test parameter"
            )
        """

        # If the node name is not specified, use the current node
        if not node_name:
            node_name = self.name

        # Set the parameter on the parameter server
        return self._redis_parameters.set(
            f"{node_name}.{name}",
            json.dumps(
                {
                    "value": value,
                    "description": description,
                }
            ),
        )

    def set_parameters(self, parameters: typing.List[dict]):
        """
        ### Set multiple parameter values on the parameter server at once.

        ---

        ### Parameters:
            - `parameters` (list): A list of parameter dictionaries. Each dictionary should have the following keys:
                - `name` (str): The parameter name to set.
                - `value`: The value to set the parameter to.
                - `node_name` (str): Optionally set parameters on a different node.
                    If not specified, uses the current node.
                - `description` (str): An optional description of the parameter.

        ---

        ### Returns:
            `True` if all parameters were set successfully.

        ---

        ### Raises:
            Exception: If the parameter server returns an error.

        ---

        ### Example::

            # Set the parameters "param1" and "param2" on the current node
            set_parameters([
                {"name": "param1", "value": "value1"},
                {"name": "param2", "value": "value2", "description": "This is a test parameter"}},
            ])

            # Set the parameters "param1" and "param2" on the node "node1"
            set_parameters([
                {"name": "param1", "value": "value1", "node_name": "node1"},
                {"name": "param2", "value": "value2", "node_name": "node1"},
            ])
        """

        # Ensure all parameters have the required keys
        for parameter in parameters:
            if "node_name" not in parameter:
                parameter["node_name"] = self.name

            if "description" not in parameter:
                parameter["description"] = None

        # Create a pipe to send all updates at once
        pipe = self._redis_parameters.pipeline()

        # Set each parameter
        for parameter in parameters:
            pipe.set(
                f"{parameter['node_name']}.{parameter['name']}",
                json.dumps(
                    {
                        "value": parameter["value"],
                        "description": parameter["description"],
                    }
                ),
            )

        # Set the parameters on the parameter server, only returning True if all
        # parameters were set successfully
        return pipe.execute()

    def delete_parameter(self, name: str, node_name: str = None):
        """
        ### Delete a parameter value on the parameter server.

        ---

        ### Parameters:
            - `name` (str): The parameter name to delete.
            - `node_name` (str): Optionally delete parameters on a different node.
                If not specified, uses the current node.

        ---

        ### Returns:
            `True` if the parameter was deleted correctly.

        """

        # If the node name is not specified, use the current node
        if not node_name:
            node_name = self.name

        # Delete the parameter on the parameter server
        return self._redis_parameters.delete(f"{node_name}.{name}")

    def delete_parameters(self, names: typing.List[str] = None, node_name: str = None):
        """
        ### Delete multiple parameter values on the parameter server at once.

        Supplying no arguments will delete all parameters on the current node.
        Supplying only parameter names will use the current node.

        ---

        ### Parameters:
            - `names` (list): A list of parameter names to delete. If not specified,
                all parameters on the specified node will be deleted.
            - `node_name` (str): Optionally delete parameters on a different node.
                If not specified, uses the current node.

        ---

        ### Returns:
            `True` if all parameters were deleted successfully.

        """

        # If the node name is not specified, use the current node
        if not node_name:
            node_name = self.name

        # Create a pipe to send all updates at once
        pipe = self._redis_parameters.pipeline()

        # If no names are specified, delete all parameters on the node
        if names is None:
            # Get all parameters on the node
            names = self._redis_parameters.scan_iter(f"{node_name}.*")
        else:
            # Append the node name to each parameter name
            names = [f"{node_name}.{name}" for name in names]

        # Delete each parameter
        for name in names:
            pipe.delete(name)

        # Delete the parameters on the parameter server, only returning True if all
        # parameters were deleted successfully
        return pipe.execute()

    def load_parameters_from_file(self, filepath) -> dict:
        """
        ### Load a dictionary of parameters, but don't set them on the parameter server.

        To automatically load and set parameters in the parameter server, use
        `node.set_parameters_from_file`.

        ---

        ### Parameters:
            - `filepath` (str): The path to the file to load.

        ---

        ### Returns:
            A dictionary of parameters.

        ---

        ### Raises:
            Exception: If the file cannot be loaded.

        ---

        ### Example::

            # Load the parameters from a file
            parameters = node.load_parameters_from_file("/path/to/parameters.json")
        """

        # Read the file
        with open(filepath, "r") as f:

            # Determine the type of file
            if filepath.endswith(".json"):
                parameters_dict = json.load(f)

            elif filepath.endswith(".yml") or filepath.endswith(".yaml"):
                parameters_dict = yaml.safe_load(f)

            parameters = {}

            # Evaluate any conditionals in the file
            for key, value in parameters_dict.items():
                if "(" in key:

                    # Get the condition
                    condition_original = re.search(r"\((.*)\)", key).group(1)

                    # Replace all env names with os.environ.get(name)
                    condition = re.sub(
                        r"\$\{(.*?)\}",
                        lambda x: f"os.environ.get('{x.group(1)}')",
                        condition_original,
                    )

                    # Replace any logic operators with their Python equivalents
                    condition = re.sub(r"\|\|", "or", condition)
                    condition = re.sub(r"&&", "and", condition)

                    # Evaluate the condition
                    if not eval(condition):
                        continue
                    else:
                        key = key.replace(f"({condition_original})", "")

                parameters[key] = value

        return parameters

    def set_parameters_from_file(self, filepath):
        """
        ### Set multiple parameter values on the parameter server from a file.

        Conditional statements are supported in the file. They are used to check
        the value of environment variables, and set parameters accordingly. See
        the examples for information on how this works.

        ---

        ### Parameters:
            - `filepath` (str): The path to the file containing the parameters.
                The file should be a JSON or YAML file following one of the
                example styles below.

        ---

        ### Returns:
            `True` if all parameters were set successfully.

        ---

        ### Raises:
            Exception: If the parameter server returns an error.

        ---

        ### Example::

            # Set the parameters from the file "parameters.json"
            set_parameters_from_file("parameters.json")

        ### config.yml::

            node1:
                param1: value1
                param2: value2

                subparam:
                    subparam1: value1
                    subparam2: value2

            node2:
                param3: value3
                param4: value4

        ### config.json::

            {
                "node1": {
                    "param1": "value1",
                    "param2": "value2",
                    "subparam": {
                        "subparam1": "value1",
                        "subparam2": "value2"
                    }
                },
                "node2": {
                    "param3": "value3",
                    "param4": "value4"
                }
            }
        """

        def convert_to_parameter_list(parameter_dict, _node_name=None, _subparams=[]):
            """
            Convert a parameter dictionary read from a file, to a list of
            parameters suitable for sending to the parameter server.

            Supports subparameters, by recursively setting the parameter name as:
                `subparam.param = value1`
                `subparam1.subparam2.param = value2`

            ---

            ### Parameters:
                - `parameter_dict` (dict): A dictionary containing the parameters to convert.

            ---

            ### Returns:
                A list of parameter dictionaries.
            """

            parameter_list = []

            for key, value in parameter_dict.items():

                # If this is the first level of the parameter, set the node name
                if _node_name is None:

                    # Recurse all parameters
                    parameter_list.extend(
                        convert_to_parameter_list(value, _node_name=key)
                    )

                elif isinstance(value, dict):
                    # Recurse into subparameters
                    parameter_list.extend(
                        convert_to_parameter_list(
                            value,
                            _subparams=[*_subparams, key],
                            _node_name=_node_name,
                        )
                    )
                else:
                    # Set the parameter
                    parameter_list.append(
                        {
                            "node_name": _node_name,
                            "name": f"{'.'.join([*_subparams, ''])}{key}",
                            "value": value,
                        }
                    )

            return parameter_list

        self.log.info(f"Setting parameters from file: {filepath}")

        # Load the parameters from the file
        parameters = self.load_parameters_from_file(filepath)

        # Convert the parameters to a list of parameters
        parameters = convert_to_parameter_list(parameters)

        if self.set_parameters(parameters):
            self.log.info("Parameters set successfully.")
            return True

    # """
    # --- TRANSFORMS ---
    #     Transforms work in a similar way to the ROS transform tree.

    #     The system works by storing transformations (as a translation and rotation vector)
    #     from one coordinate system (frame) to another.

    #     The vectors are stored in the following order:
    #         - Translation [x, y, z]
    #         - Rotation    [qw, qx, qy, qz]

    #     It is possible to convert between quaternion and euler angles, however it is
    #     advised to do everything in quaternions where possible.

    #     The transform tree is relatively strict to prevent errors. The following
    #     rules must be adhered to:

    #         1. There can only be one transform between frames, regardless of direction.
    #             - The first published transform may be `A:B`, or `B:A`, but future transforms must be the same direction.
    #         2. Every frame can only have one parent.
    #             - It is advised each frame eventually leads back to the root `odom` or `map` frame.
    #         3. Root frames (`map`, `odom`, `base_link`, etc) should only have one child each.
    #         4. Transforms can not be deleted once they have been set.

    #     n.b. The colon as a separator between frames; A:B means A to B.
    #          A:B:C:D or A::D means A to D, via B and C.

    #     As a result of these rules, there should be no cyclic transforms, and there
    #     should only be one possible route between frames.
    # """

    # def set_transform(
    #     self,
    #     frame_source: str,
    #     frame_target: str,
    #     translation: np.array,
    #     rotation: np.quaternion,
    # ):
    #     """
    #     ### Set a transform between two frames.
    #     This works in the form `frame_source` to `frame_target`. If any route
    #     already exists between the frames (either directly or via other frames),
    #     an exception is raised.

    #     ---

    #     ### Parameters:
    #         - `frame_source` (str): The source frame.
    #         - `frame_target` (str): The target frame.
    #         - `translation` (np.ndarray): The translation in the form [x, y, z].
    #         - `rotation` (np.quaternion): The rotation in the form [qw, qx, qy, qz].

    #     ---

    #     ### Returns:
    #         `True` if the transform was set successfully.

    #     ---

    #     ### Raises:
    #         `nv.exceptions.TransformExistsException`: If the transform could not be set because it already exists.
    #     """

    #     # The ':' character is not allowed in frame names
    #     if ":" in frame_source or ":" in frame_target:
    #         raise Exception(
    #             "The ':' character is not allowed in frame names. "
    #             "Please use a different frame name."
    #         )

    #     # Ensure the translation has three elements
    #     assert translation.shape == (3,), "The translation must have shape (3,)"

    #     # Ensure the rotation is a quaternion
    #     assert isinstance(
    #         rotation, np.quaternion
    #     ), "The rotation must be of type `np.quaternion`"

    #     # The transform is only allowed if it either doesn't already exist, or
    #     # exists as a direct transform. Pre-existing inverse or aliased
    #     # transforms cannot be overwritten.
    #     if self.transform_exists(
    #         frame_source, frame_target
    #     ) == "alias" or self.transform_exists(frame_target, frame_source):
    #         raise exceptions.TransformExistsException(
    #             f"Transform already exists between {frame_source} and {frame_target}. "
    #             "You are not allowed to have multiple transformations between frames."
    #         )

    #     # Set the transform
    #     return self._redis_transforms.set(
    #         f"{frame_source}:{frame_target}",
    #         pickle.dumps(
    #             {
    #                 "translation": translation,
    #                 "rotation": rotation,
    #                 "timestamp": time.time(),
    #             }
    #         ),
    #     )

    # def get_transform(self, frame_source: str, frame_target: str):
    #     """
    #     ### Get a transform between two frames.
    #     This works in the form `frame_source` to `frame_target`. This method
    #     will account for any intermediary frames, i.e. get_transform(A, C) will
    #     return A:B:C if there is a transform from A to B, and B to C.

    #     ---

    #     ### Parameters:
    #         - `frame_source` (str): The source frame.
    #         - `frame_target` (str): The target frame.

    #     ---

    #     ### Returns:
    #         The transform between the two frames, or `None` if no transform
    #         exists.

    #     ---

    #     ### Example::

    #         # Get the transform between two frames
    #         transform = get_transform(frame_source, frame_target)

    #         # Display the transform
    #         print(f"Transform from {frame_source} to {frame_target}: {transform}")
    #     """

    #     # Check if the transform exists
    #     transform_path = self.transform_exists(frame_source, frame_target)

    #     if not transform_path:
    #         return None

    #     # If the transform is direct, decode and return
    #     if transform_path == "direct":
    #         # Otherwise, decode the transform
    #         return pickle.loads(
    #             self._redis_transforms.get(f"{frame_source}:{frame_target}")
    #         )

    #     # If the transform is an alias, get the transform from the alias
    #     if transform_path == "alias":
    #         path = pickle.loads(
    #             self._redis_transforms.get(f"{frame_source}::{frame_target}")
    #         )

    #         # Convert the path in the form ["A", "B", "C"] to the form [("A",
    #         # "B"), ("B", "C")]
    #         path = [(path[i], path[i + 1]) for i in range(0, len(path) - 1)]

    #         # Get the individual transforms between each frame
    #         transforms = np.array(
    #             [self.get_transform(source, target) for source, target in path]
    #         )

    #         # Combine the translations by adding
    #         translation = np.sum(
    #             [transform["translation"] for transform in transforms], axis=0
    #         )

    #         # Combine the quaternions by multiplying
    #         quaternions = [transform["rotation"] for transform in transforms]
    #         output_quaternion = np.quaternion(1, 0, 0, 0)

    #         for quaternion in quaternions:
    #             output_quaternion *= quaternion

    #         # Use the oldest timestamp
    #         timestamp = np.min([transform["timestamp"] for transform in transforms])

    #         # Return the combined transform
    #         return {
    #             "translation": translation,
    #             "rotation": output_quaternion,
    #             "timestamp": timestamp,
    #         }

    # def transform_exists(self, frame_source: str, frame_target: str) -> str:
    #     """
    #     ### Check if a transform exists between two frames.
    #     This works in the form `frame_source` to `frame_target`.

    #     This method will account for any intermediary frames, i.e.
    #     transform_exists(A, C) will return True if there is a transform from A
    #     to B, and B to C. It will set an alias for the transform if required
    #     (see `set_transform_alias`).

    #     ---

    #     ### Parameters:
    #         - `frame_source` (str): The source frame.
    #         - `frame_target` (str): The target frame.

    #     ---

    #     ### Returns:
    #         - "direct" if the transform exists directly between frames.
    #         - "alias" if the transform exists as an alias.
    #         - False if no transform exists.
    #     """

    #     def find_path(frame_source: str, frame_target: str, path=[]):
    #         """
    #         Find any path between the source and target frame.
    #         It may not be the shortest.
    #         """

    #         path = path + [frame_source]

    #         if frame_source == frame_target:
    #             return path

    #         if frame_source not in _graph:
    #             return None

    #         for node in _graph[frame_source]:
    #             if node not in path:
    #                 new_path = find_path(node, frame_target, path)

    #                 if new_path:
    #                     return new_path

    #     # Make sure the source and target are different
    #     assert (
    #         frame_source != frame_target
    #     ), "The source and target frames must be different!"

    #     # Alias the function to improve readability
    #     tf = self._redis_transforms.exists

    #     # Check if a transform exists
    #     if tf(f"{frame_source}:{frame_target}"):
    #         return "direct"

    #     # TODO:
    #     # Test if adding aliases to the database, as opposed to just calculating
    #     # them each time, is actually faster.
    #     elif tf(f"{frame_source}::{frame_target}"):
    #         return "alias"

    #     # No direct or aliased transform exists, but there may be a route which
    #     # has not been aliased yet. We can check this by traversing up the tree
    #     # from each frame, and checking if the branches overlap at any points.

    #     # Get all transforms in the database
    #     transforms = self._redis_transforms.scan_iter(match=f"*")

    #     _graph = {}

    #     # Add all the transforms to the graph
    #     for key in transforms:

    #         # Decode the key
    #         key = key.decode("utf-8")

    #         # If there is more than one colon, this is an aliased transform
    #         if key.count(":") != 1:
    #             continue

    #         # Split the transform into source and target
    #         source, target = key.split(":")

    #         # If the source is not in the graph, add it
    #         if source not in _graph:
    #             _graph[source] = set()

    #         # Add the target to the source's branch
    #         _graph[source].add(target)

    #     # Get the path between the source and target
    #     path = find_path(frame_source, frame_target)

    #     # If the path is not found, return False
    #     if path is None:
    #         return False

    #     # Otherwise, create an alias and return True
    #     self.log.debug(f"New route found from {frame_source} to {frame_target}: {path}")

    #     self.set_transform_alias(path)

    #     return "alias"

    # def set_transform_alias(self, alias: list):
    #     """
    #     ### Set an alias for a transform.

    #     An alias is a way to speed up lookup of indirect transforms (transforms
    #     which must go through an intermediary frame, i.e. A:B:C).

    #     They are automatically set when discovered for the first time, as it
    #     allows a route between frames to be calculates once, and never again.

    #     In the database, aliases are distinguished from direct transforms by
    #     using two colons to separate frames, i.e. A::C.

    #     ---

    #     ### Parameters:
    #         - `alias` (list): The alias to set. This is a list of frame strings in the form ["A", "B", "C"], where:
    #             - A is the source frame
    #             - C is the target frame
    #             - B is any number of intermediary frames required to connect the source and target.

    #     ---

    #     ### Returns:
    #         `True` if the alias was set successfully.

    #     ---

    #     ### Raises:
    #         `nv.exceptions.TransformAliasException`: If the alias could not be set. This may be because it already exists.
    #     """

    #     # Check that the alias has at least 3 parts
    #     if len(alias) < 3:
    #         raise exceptions.TransformAliasException(
    #             "The alias must be in the form A:B:C, where A is the source frame, "
    #             "B is any number of intermediary frames, and C is the target frame."
    #         )

    #     # Check that the source and target frames are not the same
    #     if alias[0] == alias[-1]:
    #         raise exceptions.TransformAliasException(
    #             "The source and target frames cannot be the same. Please use a different alias."
    #         )

    #     # Check that the alias does not already exist
    #     if self._redis_transforms.exists(alias[0] + "::" + alias[-1]):
    #         raise exceptions.TransformAliasException("The alias already exists.")

    #     # Set the alias
    #     return self._redis_transforms.set(
    #         alias[0] + "::" + alias[-1], pickle.dumps(alias)
    #     )
