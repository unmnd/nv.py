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
import marshal
import os
import threading
import time
import typing

import redis
import requests
import serpent
import yaml

from nv import exceptions, logger, services, utils, timer


class Node:
    def __init__(self, name: str, skip_registration: bool = False, **kwargs):
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

        # Initialise logger
        self.log = logger.generate_log(
            name, log_level=kwargs.get("log_level") or logger.DEBUG
        )

        self.log.debug(
            f"Initialising '{name}' using framework version nv {utils.VERSION}"
        )

        # Initialise parameters
        self.name = name
        self.node_registered = False
        self.skip_registration = skip_registration
        self.stopped = False
        self._start_time = time.time()

        # The subscriptions dictionary is in the form of:
        # {
        #   topic1: [callback1],
        #   topic2: [callback2, callback3],
        #   ...
        # }
        self._subscriptions = {}

        # The services dictionary is used to keep track of exposed services,
        # which other nodes can access using pyro5.
        self._services = {}

        # Connect redis clients
        # The topics database stores messages for communication between nodes.
        # The key is always the topic.
        self._redis_topics = self._connect_redis(
            redis_host=kwargs.get("redis_host"),
            port=kwargs.get("redis_port") or 6379,
            db=0,
        )

        # The parameters database stores key-value parameters to be used for
        # each node. The key is the node_name.parameter_name.
        self._redis_parameters = self._connect_redis(
            redis_host=kwargs.get("redis_host"),
            port=kwargs.get("redis_port") or 6379,
            db=1,
        )

        # The nodes database stores up-to-date information about which nodes are
        # active on the network. Each node is responsible for storing and
        # keeping it's own information active.
        self._redis_nodes = self._connect_redis(
            redis_host=kwargs.get("redis_host"),
            port=kwargs.get("redis_port") or 6379,
            db=2,
        )

        if self.skip_registration:
            self.log.warning("Skipping node registration...")
        else:
            # Check if another node with this name already exists
            if self.node_exists(self.name):
                raise exceptions.DuplicateNodeName(
                    "A node with the name "
                    + self.name
                    + " already exists on this network."
                )

            # Register the node with the server
            self._register_node()

        # Start the pubsub loop for topics in a separate thread.
        Node._pubsub = self._redis_topics.pubsub()
        Node._pubsub_thread = threading.Thread(target=self._pubsub_loop)
        Node._pubsub_thread.start()

    def _register_node(self):
        """
        Register the node with the server.
        """

        def _renew_node_information():
            """
            Renew the node information, by overwriting the node information and
            resetting a 10 second expiry timer.
            """

            # Check if the node has been stopped, if so, stop the timer
            if self.stopped:
                self._renew_node_information_timer.stop()
                return

            # Update the node information
            self._redis_nodes.set(
                self.name,
                marshal.dumps(self.get_node_information()),
                ex=10,
            )

        # Create a timer which renews the node information every 5 seconds
        self._renew_node_information_timer = timer.LoopTimer(
            interval=5,
            function=_renew_node_information,
        )

        # Set the node as registered
        self.node_registered = True

        self.log.info(f"Node successfully registered!")

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
        while True:
            try:
                Node._pubsub.get_message()
            except RuntimeError:
                # If there are no subscriptions, an error is thrown. This is
                # fine; when a subscription is added the errors will stop.
                continue

            time.sleep(0.001)

    def _decode_pubsub_message(self, message):
        """
        # Decode a message received by a callback to the Redis pubsub.

        By default it uses `marshal` for speed, but if this fails it will fall
        back to `serpent`, which supports more data types, including initialised
        classes!

        ---

        ### Parameters:
            - `message` (str): The message to decode.

        ---

        ### Returns:
            The decoded message.
        """
        try:
            return marshal.loads(message)
        except (EOFError, TypeError, ValueError):
            self.log.debug("Falling back to serpent for data serialisation...")
            return serpent.loads(message)

    def _encode_pubsub_message(self, message):
        """
        # Encode a message to be sent to the Redis pubsub.

        By default it uses `marshal` for speed, but if this fails it will fall
        back to `serpent`, which supports more data types, including initialised
        classes!

        ---

        ### Parameters:
            - `message` (str): The message to encode.

        ---

        ### Returns:
            The encoded message.
        """
        try:
            return marshal.dumps(message)
        except (EOFError, TypeError, ValueError):
            self.log.debug("Falling back to serpent for data serialisation...")
            return serpent.dumps(message)

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
                "version": utils.VERSION,
                "subscriptions": list(self._subscriptions.keys()),
                "services": self._services,
            }
        else:
            return marshal.loads(self._redis_nodes.get(node_name))

    def get_nodes(self) -> typing.Dict[str, dict]:
        """
        ### Get all nodes present in the network.

        ---

        ### Returns:
            A dictionary containing all nodes on the network.
        """
        return {
            node: marshal.loads(self._redis_nodes.get(node))
            for node in self._redis_nodes.keys()
        }

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

    def node_exists(self, node_name: str) -> bool:
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

        # Send the message to the Redis pubsub
        return self._redis_topics.publish(
            topic_name, self._encode_pubsub_message(message)
        )

    def destroy_node(self):
        """
        ### Destroy the node.
        """
        raise NotImplementedError("Destroy node is not yet implemented")

    def create_service(self, service_name: str, callback_function):
        """
        ### Create a service.

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

        # Initialise the server
        server = services.ServiceServer(
            name=service_name, callback=callback_function, sio=self._sio
        )

        server.create_service()

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

        ### Example::

            # Call the service "test"
            future = call_service("test", "Hello", "World")

            # Wait for the response
            future.wait()

            # Get the response
            response = future.get_response()
        """

        # Initialise the server
        client = services.ServiceClient(name=service_name, sio=self._sio)

        client.call_service(*args, **kwargs)
        return client

    def get_parameter(
        self, parameter: str, node_name: str = None, fail_if_not_found: bool = False
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
            Exception: If the parameter is not found and fail_if_not_found is `True`.

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
        parameter = self._redis_parameters.get(f"{node_name}.{parameter}")

        # Raise an exception if the parameter is not found and fail_if_not_found is True
        if parameter is None and fail_if_not_found:
            raise Exception(f"Parameter {parameter} not found")

        # Extract the value from the parameter if it exists
        if parameter is not None:
            return marshal.loads(parameter).get("value")

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
            marshal.dumps(
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
                marshal.dumps(
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
