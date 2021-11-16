#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
The `Node` class is the base class for all nodes in the network. It provides
methods for communicating between different nodes and the server, as well as
logging, parameter handling, and other things.

Callum Morrison, 2021
UNMND, Ltd. 2021
<callum@unmnd.com>

All Rights Reserved
"""

import json
import os
import pickle
import re
import signal
import sys
import threading
import time
import typing
import uuid

import numpy as np
import quaternion  # This need to be imported to extend np
import redis
import yaml

from nv import exceptions, logger, timer, version


class Node:
    def __init__(
        self, name: str, skip_registration: bool = False, log_level: int = None
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
        """

        # Bind callbacks to gracefully exit the node on signal
        signal.signal(signal.SIGINT, self._sigterm_handler)
        signal.signal(signal.SIGTERM, self._sigterm_handler)

        # Initialise logger
        self.log = logger.generate_log(
            name, log_level=log_level or os.environ.get("NV_LOG_LEVEL") or logger.DEBUG
        )

        self.log.debug(
            f"Initialising '{name}' using framework version nv {version.__version__}"
        )

        # Initialise parameters
        self.name = name
        self.node_registered = False
        self.skip_registration = skip_registration
        self.stopped = threading.Event()
        self._start_time = time.time()

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

        # Connect redis clients
        # The topics database stores messages for communication between nodes.
        # The key is always the topic.
        redis_host = os.environ.get("NV_REDIS_HOST")
        redis_port = os.environ.get("NV_REDIS_PORT") or 6379

        self._redis_topics = self._connect_redis(
            redis_host=redis_host,
            port=redis_port,
            db=0,
        )

        # The parameters database stores key-value parameters to be used for
        # each node. The key is the node_name.parameter_name.
        self._redis_parameters = self._connect_redis(
            redis_host=redis_host,
            port=redis_port,
            db=1,
        )

        # The transforms database stores transformations between frames. The key
        # is in the form <source_frame>:<target_frame>.
        self._redis_transforms = self._connect_redis(
            redis_host=redis_host,
            port=redis_port,
            db=2,
        )

        # The nodes database stores up-to-date information about which nodes are
        # active on the network. Each node is responsible for storing and
        # keeping it's own information active.
        self._redis_nodes = self._connect_redis(
            redis_host=redis_host,
            port=redis_port,
            db=3,
        )

        if self.skip_registration:
            self.log.warning("Skipping node registration...")
        else:

            # Check if another node with this name already exists
            if self.check_node_exists(self.name):
                raise exceptions.DuplicateNodeNameException(
                    "A node with the name "
                    + self.name
                    + " already exists on this network."
                )

            # Register the node with the server
            self._register_node()

        # Start the pubsub loop for topics in a separate thread.
        Node._pubsub = self._redis_topics.pubsub()
        Node._pubsub_thread = threading.Thread(target=self._pubsub_loop)

    def _register_node(self):
        """
        Register the node with the server.
        """

        def _renew_node_information():
            """
            Renew the node information, by overwriting the node information and
            resetting a 10 second expiry timer.
            """

            # Update the node information
            self._redis_nodes.set(
                self.name,
                pickle.dumps(self.get_node_information()),
                ex=10,
            )

        # Create a timer which renews the node information every 5 seconds
        self._renew_node_information_timer = self.create_loop_timer(
            interval=5,
            function=_renew_node_information,
            immediate=True,
        )

        # Set the node as registered
        self.node_registered = True

        self.log.info(f"Node successfully registered!")

    def _deregister_node(self):
        """
        Deregister the node with the server.
        """

        # Delete the node information from the nodes database
        self._redis_nodes.delete(self.name)

        # Set the node as deregistered
        self.node_registered = False

        self.log.info(f"Node successfully deregistered!")

    def _connect_redis(self, redis_host: str = None, port: int = 6379, db: int = 0):
        """
        Connect the Redis client to the database to allow messaging. It attempts
        to find the host automatically on either localhost, or connecting to a
        container named 'redis'.

        Optionally, the host can be specified using the parameter `redis_host`,
        to overwrite autodetection.

        ---

        ### Parameters:
            - `redis_host` (str): The host of the redis database.
            - `port` (int): The port of the redis database.
            - `db` (int): The database hosting messaging data.

        ---

        ### Returns:
            The redis client.
        """

        def _test_connection(r: redis.Redis):
            """
            ### Check if the redis client is connected.

            ---

            ### Parameters:
                - `r` (redis.Redis): The redis client.

            ---

            ### Returns:
                `True` if the client is connected, `False` otherwise.
            """
            try:
                r.ping()
                return True
            except redis.exceptions.ConnectionError:
                return False

        if redis_host:
            r = redis.Redis(host=redis_host, port=port, db=db)

            # Don't catch for errors; if a host is supplied it should override
            # any other auto-detection.
            r.ping()
            return r
        else:
            for host in ["redis", "localhost"]:
                r = redis.Redis(host=host, port=port, db=db)

                if _test_connection(r):
                    return r

        raise ConnectionError(
            "Could not connect to Redis. Check it's running and accessible!"
        )

    def _pubsub_loop(self):
        """
        Continously monitors the Redis server for updated messages, enabling
        subscription callbacks to trigger.
        """
        while not self.stopped.is_set():
            try:
                # The timeout changes the way this function works.
                # Normally, the function will not block. Adding a timeout will
                # block for up to that time. If no messages are received, the
                # function will return None. A larger timeout is less CPU
                # intensive, but means node termination will be delayed.
                Node._pubsub.get_message(ignore_subscribe_messages=True, timeout=1)
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
        return pickle.loads(message)

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
        return pickle.dumps(message)

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
        for callback in self._subscriptions[topic]:
            callback(message)

    def _sigterm_handler(self, _signo, _stack_frame):
        """
        Handle termination signals to gracefully stop the node.
        """
        self.log.info("Received program termination signal; exiting...")
        self.destroy_node()
        sys.exit(0)

    def spin(self):
        """
        ### Blocking function while the node is active.

        It's not necessary to call this function to run the node! This is just
        used as a blocker if there is no other code to run.
        """
        self.stopped.wait()

    def get_logger(self, name=None, log_level=logger.INFO):
        """
        ### Get a logger for the nv framework.
        Note, the logger for the current node is always available as `self.log`.

        ---

        ### Parameters:
            - `name` (str): The name of the logger.
                [Default: <node name>]
            - `log_level` (int): The log level.
                [Default: `logger.INFO`]

        ---

        ### Returns:
            A logger for the nv framework.
        """
        return logger.generate_log(name or self.name, log_level)

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
                "version": version.__version__,
                "subscriptions": list(self._subscriptions.keys()),
                "publishers": self._publishers,
                "services": self._services,
            }
        else:
            return pickle.loads(self._redis_nodes.get(node_name))

    def get_nodes(self) -> typing.Dict[str, dict]:
        """
        ### Get all nodes present in the network.

        ---

        ### Returns:
            A dictionary containing all nodes on the network.
        """
        return {
            node.decode(): pickle.loads(self._redis_nodes.get(node))
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

    def get_topic_subscriptions(self, topic: str) -> typing.List[str]:
        """
        ### Get a list of nodes which are subscribed to a specific topic.

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

    def create_subscription(self, topic_name: str, callback_function):
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

            create_subscription("test", callback_function)
        """

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
        Node._pubsub.subscribe(**{topic_name: self._handle_subscription_callback})

        # Add the subscription to the list of subscriptions for this topic
        if topic_name in self._subscriptions:
            self._subscriptions[topic_name].append(callback_function)
        else:
            self._subscriptions[topic_name] = [callback_function]

    def get_latest_message(self, topic_name: str):
        """
        ### Get the latest message received on a topic.

        Using this method is an alternative to subscribing to the topic, as it
        allows for a node to fetch data only when it is required, and without
        needing to rate limit messages received in a callback.

        A limit with using this method is that there is no indication of how old
        the data is; which might cause issues with time-critical applications.

        ---

        ### Parameters:
            - `topic_name` (str): The name of the topic to get the latest message
                from.

        ---

        ### Returns:
            The latest message received on the topic, or `None` if no messages
            have been received.
        """
        return self._redis_topics.get(topic_name)

    def destroy_subscription(self, topic_name: str):
        """
        ### Destroy a subscription to a topic.

        ---

        ### Parameters:
            - `topic_name` (str): The name of the topic to unsubscribe from.
        """

        # Unsubscribe from Redis
        Node._pubsub.unsubscribe(topic_name)

        # Remove any callbacks for this subscription
        if topic_name in self._subscriptions:
            del self._subscriptions[topic_name]

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

        Differs from using `nv.timer.LoopTimer` directly as it automatically
        terminates the timer when the node is destroyed.

        Additional args and kwargs are passed to the function.

        ---

        ### Parameters:
            - `interval` (int): The interval in seconds between calls to the
                function.
            - `function` (function): The function to call.
            - `autostart` (bool): Whether to start the timer automatically.
            - `immediate` (bool): Whether to call the function immediately after start.

        """

        loop_timer = timer.LoopTimer(
            interval=interval,
            function=function,
            autostart=autostart,
            immediate=immediate,
            termination_event=self.stopped,
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

    def create_service(self, service_name: str, callback_function: typing.Callable):
        """
        ### Create a service.

        A service is a function which can be called by other nodes. It can
        accept any number of args and kwargs, and can return any Python
        datatype.

        If there is an exception during the execution of the service, the caller
        will receive `None` as the result. Be careful if your service returns
        `None` under normal operation.

        ---

        ### Parameters:
            - `service_name` (str): The name of the service to create.
            - `callback_function` (function): The function to call when a message
                is received on the service.

        ---

        ### Example::

            # Create a service called "test"
            def callback_function(message):
                print(message)

            create_service("test", callback_function)
        """

        def handle_service_callback(message):
            """
            Used to handle requests to call a service, and respond by publishing
            any data on the requested topic.
            """

            # Get the response topic from the message
            response_topic = message.get("response_topic")

            # Get args and kwargs from the message
            args = message.get("args", [])
            kwargs = message.get("kwargs", {})

            # Call the service
            try:
                result = callback_function(*args, **kwargs)
            except Exception as e:
                self.log.error(f"Error calling service '{service_name}'", exc_info=e)
                self.publish(response_topic, None)
                return

            # Publish the result on the response topic
            self.publish(response_topic, result)

        # Generate a unique ID for the service
        service_id = "srv://" + str(uuid.uuid4())

        # Register a message handler for the service
        self.create_subscription(service_id, handle_service_callback)

        # Save the service name and ID
        self._services[service_name] = service_id

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
            A client which can be used to wait for the response.

            Methods:
                - `client.wait()`: Wait for the response.
                - `client.get_response()`: Get the response.
        ---

        ### Raises:
            - `nv.exceptions.ServiceNotFoundException`: If the service is not registered.

        ---

        ### Example::

            # Call the service "test"
            future = call_service("test", "Hello", "World")

            # Wait for the response
            future.wait()

            # Get the response
            response = future.get_response()
        """

        class ServiceClient:
            def __init__(self):
                self._response = None
                self._response_received = threading.Event()

            def wait(self, timeout: float = None):
                """
                Wait for the response.
                """

                self._response_received.wait(timeout)
                self._response_received.clear()

            def get_response(self):
                """
                Get the response.
                """
                return self._response

            def _response_callback(self, message):
                """
                Used to handle the response to a service call.
                """
                self._response = message
                self._response_received.set()

        # Get all the services currently registered
        services = self.get_services()

        # Check the service exists
        if service_name not in services:
            raise exceptions.ServiceNotFoundException(
                f"Service '{service_name}' does not exist"
            )

        # Get the service ID
        service_id = services[service_name]

        # Generate a unique ID for the response topic
        response_topic = "srv://" + str(uuid.uuid4())

        # Create a message to send to the service
        message = {
            "response_topic": response_topic,
            "args": args,
            "kwargs": kwargs,
        }

        # Create a client to wait for the response
        client = ServiceClient()

        # Subscribe to the response topic
        self.create_subscription(response_topic, client._response_callback)

        # Publish the message to the service
        self.publish(service_id, message)

        # Return the client
        return client

    def get_parameter(
        self, name: str, node_name: str = None, fail_if_not_found: bool = False
    ):
        """
        ### Get a parameter value from the parameter server.

        ---

        ### Parameters:
            - `parameter` (str): The parameter name to get.
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
            return pickle.loads(parameter).get("value")

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
            return pickle.loads(parameter).get("description")

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
            pickle.dumps(
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
                pickle.dumps(
                    {
                        "value": parameter["value"],
                        "description": parameter["description"],
                    }
                ),
            )

        # Set the parameters on the parameter server, only returning True if all
        # parameters were set successfully
        return pipe.execute()

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

        def convert_to_parameter_dict(parameter_dict, _node_name=None, _subparams=[]):
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

                    # Check if the name contains an env variable conditional
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

                    # Recurse all parameters
                    parameter_list.extend(
                        convert_to_parameter_dict(value, _node_name=key)
                    )

                elif isinstance(value, dict):
                    # Recurse into subparameters
                    parameter_list.extend(
                        convert_to_parameter_dict(
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

        # Read the file
        with open(filepath, "r") as f:

            # Determine the type of file
            if filepath.endswith(".json"):
                parameters_dict = json.load(f)

            elif filepath.endswith(".yml") or filepath.endswith(".yaml"):
                parameters_dict = yaml.safe_load(f)

        parameters = convert_to_parameter_dict(parameters_dict)

        if self.set_parameters(parameters):
            self.log.info("Parameters set successfully.")
            return True

    def format_duration(
        self, time_1: float, time_2: float
    ) -> typing.Tuple[str, str, str]:
        """
        ### Format a duration between two unix timestamps into a human-readable string.

        It works in the form `time_1` to `time_2`; meaning if `time_2` <
        `time_1`, the duration is "in the past". Likewise, if `time_1` <
        `time_2` the duration is "in the future".

        Formats to seconds, hours, and days as long as they are > 0.

        ---

        ### Parameters:
            - `time_1` (float): The first timestamp.
            - `time_2` (float): The second timestamp.

        ---

        ### Returns:
            - A human-readable string representing the duration.
            - The prefix, "was" or "is" if required.
            - The suffix, "ago" or "from now".

        ---

        ### Example::

            # Get the duration between two timestamps
            duration, prefix, suffix = format_duration(time.time(), example_timestamp)

            # Display how long ago an event was
            print(f"This event {prefix} {duration} {suffix}")

        """

        # Get the duration
        duration = time_2 - time_1

        # If the duration is negative, the second time is in the past
        if duration < 0:
            prefix = "was"
            suffix = "ago"
            duration = -duration

        # If the duration is positive, the second time is in the future
        else:
            prefix = "is"
            suffix = "from now"

        # Format the duration as a human-readable string
        if duration < 1:
            duration = f"{duration * 1000:.0f}ms"
        elif duration < 60:
            duration = f"{duration:.0f}s"
        elif duration < 3600:
            duration = f"{duration / 60:.0f}m"
        elif duration < 86400:
            duration = f"{duration / 3600:.0f}h"
        else:
            duration = f"{duration / 86400:.0f}d"

        return duration, prefix, suffix

    """
    --- TRANSFORMS ---
        Transforms work in a similar way to the ROS transform tree.

        The system works by storing transformations (as a translation and rotation vector)
        from one coordinate system (frame) to another.

        The vectors are stored in the following order:
            - Translation [x, y, z]
            - Rotation    [qw, qx, qy, qz]

        It is possible to convert between quaternion and euler angles, however it is
        advised to do everything in quaternions where possible.

        The transform tree is relatively strict to prevent errors. The following
        rules must be adhered to:

            1. There can only be one transform between frames, regardless of direction.
                - The first published transform may be `A:B`, or `B:A`, but future transforms must be the same direction.
            2. Every frame can only have one parent.
                - It is advised each frame eventually leads back to the root `odom` or `map` frame.
            3. Root frames (`map`, `odom`, `base_link`, etc) should only have one child each.
            4. Transforms can not be deleted once they have been set.

        n.b. The colon as a separator between frames; A:B means A to B.
             A:B:C:D or A::D means A to D, via B and C.

        As a result of these rules, there should be no cyclic transforms, and there
        should only be one possible route between frames.
    """

    def set_transform(
        self,
        frame_source: str,
        frame_target: str,
        translation: np.array,
        rotation: np.quaternion,
    ):
        """
        ### Set a transform between two frames.
        This works in the form `frame_source` to `frame_target`. If any route
        already exists between the frames (either directly or via other frames),
        an exception is raised.

        ---

        ### Parameters:
            - `frame_source` (str): The source frame.
            - `frame_target` (str): The target frame.
            - `translation` (np.ndarray): The translation in the form [x, y, z].
            - `rotation` (np.quaternion): The rotation in the form [qw, qx, qy, qz].

        ---

        ### Returns:
            `True` if the transform was set successfully.

        ---

        ### Raises:
            `nv.exceptions.TransformExistsException`: If the transform could not be set because it already exists.
        """

        # The ':' character is not allowed in frame names
        if ":" in frame_source or ":" in frame_target:
            raise Exception(
                "The ':' character is not allowed in frame names. "
                "Please use a different frame name."
            )

        # Ensure the translation has three elements
        assert translation.shape == (3,), "The translation must have shape (3,)"

        # Ensure the rotation is a quaternion
        assert isinstance(
            rotation, np.quaternion
        ), "The rotation must be of type `np.quaternion`"

        # The transform is only allowed if it either doesn't already exist, or
        # exists as a direct transform. Pre-existing inverse or aliased
        # transforms cannot be overwritten.
        if self.transform_exists(
            frame_source, frame_target
        ) == "alias" or self.transform_exists(frame_target, frame_source):
            raise exceptions.TransformExistsException(
                f"Transform already exists between {frame_source} and {frame_target}. "
                "You are not allowed to have multiple transformations between frames."
            )

        # Set the transform
        return self._redis_transforms.set(
            f"{frame_source}:{frame_target}",
            pickle.dumps(
                {
                    "translation": translation,
                    "rotation": rotation,
                    "timestamp": time.time(),
                }
            ),
        )

    def get_transform(self, frame_source: str, frame_target: str):
        """
        ### Get a transform between two frames.
        This works in the form `frame_source` to `frame_target`. This method
        will account for any intermediary frames, i.e. get_transform(A, C) will
        return A:B:C if there is a transform from A to B, and B to C.

        ---

        ### Parameters:
            - `frame_source` (str): The source frame.
            - `frame_target` (str): The target frame.

        ---

        ### Returns:
            The transform between the two frames, or `None` if no transform
            exists.

        ---

        ### Example::

            # Get the transform between two frames
            transform = get_transform(frame_source, frame_target)

            # Display the transform
            print(f"Transform from {frame_source} to {frame_target}: {transform}")
        """

        # Check if the transform exists
        transform_path = self.transform_exists(frame_source, frame_target)

        if not transform_path:
            return None

        # If the transform is direct, decode and return
        if transform_path == "direct":
            # Otherwise, decode the transform
            return pickle.loads(
                self._redis_transforms.get(f"{frame_source}:{frame_target}")
            )

        # If the transform is an alias, get the transform from the alias
        if transform_path == "alias":
            path = pickle.loads(
                self._redis_transforms.get(f"{frame_source}::{frame_target}")
            )

            # Convert the path in the form ["A", "B", "C"] to the form [("A",
            # "B"), ("B", "C")]
            path = [(path[i], path[i + 1]) for i in range(0, len(path) - 1)]

            # Get the individual transforms between each frame
            transforms = np.array(
                [self.get_transform(source, target) for source, target in path]
            )

            # Combine the translations by adding
            translation = np.sum(
                [transform["translation"] for transform in transforms], axis=0
            )

            # Combine the quaternions by multiplying
            quaternions = [transform["rotation"] for transform in transforms]
            output_quaternion = np.quaternion(1, 0, 0, 0)

            for quaternion in quaternions:
                output_quaternion *= quaternion

            # Use the oldest timestamp
            timestamp = np.min([transform["timestamp"] for transform in transforms])

            # Return the combined transform
            return {
                "translation": translation,
                "rotation": output_quaternion,
                "timestamp": timestamp,
            }

    def transform_exists(self, frame_source: str, frame_target: str) -> str:
        """
        ### Check if a transform exists between two frames.
        This works in the form `frame_source` to `frame_target`.

        This method will account for any intermediary frames, i.e.
        transform_exists(A, C) will return True if there is a transform from A
        to B, and B to C. It will set an alias for the transform if required
        (see `set_transform_alias`).

        ---

        ### Parameters:
            - `frame_source` (str): The source frame.
            - `frame_target` (str): The target frame.

        ---

        ### Returns:
            - "direct" if the transform exists directly between frames.
            - "alias" if the transform exists as an alias.
            - False if no transform exists.
        """

        def find_path(frame_source: str, frame_target: str, path=[]):
            """
            Find any path between the source and target frame.
            It may not be the shortest.
            """

            path = path + [frame_source]

            if frame_source == frame_target:
                return path

            if frame_source not in _graph:
                return None

            for node in _graph[frame_source]:
                if node not in path:
                    new_path = find_path(node, frame_target, path)

                    if new_path:
                        return new_path

        # Make sure the source and target are different
        assert (
            frame_source != frame_target
        ), "The source and target frames must be different!"

        # Alias the function to improve readability
        tf = self._redis_transforms.exists

        # Check if a transform exists
        if tf(f"{frame_source}:{frame_target}"):
            return "direct"

        # TODO:
        # Test if adding aliases to the database, as opposed to just calculating
        # them each time, is actually faster.
        elif tf(f"{frame_source}::{frame_target}"):
            return "alias"

        # No direct or aliased transform exists, but there may be a route which
        # has not been aliased yet. We can check this by traversing up the tree
        # from each frame, and checking if the branches overlap at any points.

        # Get all transforms in the database
        transforms = self._redis_transforms.scan_iter(match=f"*")

        _graph = {}

        # Add all the transforms to the graph
        for key in transforms:

            # Decode the key
            key = key.decode("utf-8")

            # If there is more than one colon, this is an aliased transform
            if key.count(":") != 1:
                continue

            # Split the transform into source and target
            source, target = key.split(":")

            # If the source is not in the graph, add it
            if source not in _graph:
                _graph[source] = set()

            # Add the target to the source's branch
            _graph[source].add(target)

        # Get the path between the source and target
        path = find_path(frame_source, frame_target)

        # If the path is not found, return False
        if path is None:
            return False

        # Otherwise, create an alias and return True
        self.log.debug(f"New route found from {frame_source} to {frame_target}: {path}")

        self.set_transform_alias(path)

        return "alias"

    def set_transform_alias(self, alias: list):
        """
        ### Set an alias for a transform.

        An alias is a way to speed up lookup of indirect transforms (transforms
        which must go through an intermediary frame, i.e. A:B:C).

        They are automatically set when discovered for the first time, as it
        allows a route between frames to be calculates once, and never again.

        In the database, aliases are distinguished from direct transforms by
        using two colons to separate frames, i.e. A::C.

        ---

        ### Parameters:
            - `alias` (list): The alias to set. This is a list of frame strings in the form ["A", "B", "C"], where:
                - A is the source frame
                - C is the target frame
                - B is any number of intermediary frames required to connect the source and target.

        ---

        ### Returns:
            `True` if the alias was set successfully.

        ---

        ### Raises:
            `nv.exceptions.TransformAliasException`: If the alias could not be set. This may be because it already exists.
        """

        # Check that the alias has at least 3 parts
        if len(alias) < 3:
            raise exceptions.TransformAliasException(
                "The alias must be in the form A:B:C, where A is the source frame, "
                "B is any number of intermediary frames, and C is the target frame."
            )

        # Check that the source and target frames are not the same
        if alias[0] == alias[-1]:
            raise exceptions.TransformAliasException(
                "The source and target frames cannot be the same. Please use a different alias."
            )

        # Check that the alias does not already exist
        if self._redis_transforms.exists(alias[0] + "::" + alias[-1]):
            raise exceptions.TransformAliasException("The alias already exists.")

        # Set the alias
        return self._redis_transforms.set(
            alias[0] + "::" + alias[-1], pickle.dumps(alias)
        )
