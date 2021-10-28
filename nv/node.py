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
import typing

import requests
import socketio
import yaml

from nv import exceptions, logger, services, udp_server, utils

HOSTCACHE = os.path.join(utils.CONFIG_PATH, "hostcache.json")


class Node:
    def __init__(self, name: str, **kwargs):
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
        """

        # SocketIO client
        self.sio = socketio.Client()

        # Initialise parameters
        self.name = name
        self.host = None
        self.node_registered = False

        # Assign sio callback functions
        self.sio.on("connect", self._on_connect)
        self.sio.on("disconnect", self._on_disconnect)

        # Initialise logger
        self.log = logger.generate_log(self.name, log_level=logger.DEBUG)

        self.log.debug(
            f"Initialising '{self.name}' using framework version nv {utils.VERSION}"
        )

        # Attempt to find the host IP address
        self.host = self._discover_host(**kwargs)
        self.log.debug(f"Found host: {self.host}")

        # Check if another node with this name already exists
        if utils.node_exists(host=self.host, node_name=self.name):
            raise exceptions.DuplicateNodeName(
                "A node with the name " + self.name + " already exists on this network."
            )

        # Connect socket-io client
        self.sio.connect(self.host)

    def _on_connect(self):
        """
        Callback for socket-io connect event.
        """
        self.log.debug("Connected to server.")
        self.log.debug(f"Attempting to register node '{self.name}'.")
        self._register_node()

    def _on_disconnect(self):
        """
        Callback for socket-io disconnect event.
        """
        self.log.warning("Disconnected from server.")

    def _register_node(self):
        """
        Register the node with the server.
        """

        def _callback(data):
            """
            Handles response from the server after a registration request.
            """
            if data["status"] == "success":
                self.node_registered = True
                self.log.info("Node successfully registered with server.")
            else:
                self.log.error(
                    "Failed to register node with server: " + data["message"]
                )

        self.sio.emit(
            "register_node",
            {
                "magic": utils.MAGIC,
                "version": utils.VERSION,
                "node_name": self.name,
            },
            callback=_callback,
        )

    def _discover_host(self, timeout: float = -1, port: int = 5000, subnet: int = 24):
        """
        Attempt to automatically find the host of the nv network, by trying
        common IPs. The host must be on the same subnet as the node, unless
        overwritten in the `subnet` parameter.

        If the host is found, the IP is stored in a file called `.hostcache`,
        which will be tried first next time the function is called.

        It attempts to find the host by sending GET requests to all IPs on the

        ---

        ### Parameters:
            - `timeout` (float): How long to wait for a response from the server.
                [Default: `-1` (No timeout)]
            - `port` (int): The port the host is listening for web requests on.
                [Default: `5000`]
            - `subnet` (int): The subnet mask of the host.
                [Default: `24` (i.e. `X.X.X.0` - `X.X.X.255`)]

        ---

        ### Returns:
            The host of the nv network if found, otherwise `None`.
        """

        def _test_ip(ip, port):
            """
            ### Check if nv_host is running on the given IP.

            ---

            ### Parameters:
                - `ip` (str): The IP to test.

            ---

            ### Returns:
                `True`, version if the host is running on the given IP, `False` otherwise.
            """
            try:
                # Attempt to connect to the host
                response = requests.get(
                    "http://" + ip + ":" + str(port) + "/ping",
                )
                if response.status_code == 200:

                    # Check the response JSON to ensure it is part of the nv
                    # network, and is running the correct version.
                    response_json = response.json()

                    if response_json.get("magic") != utils.MAGIC:
                        self.log.error(
                            f"Magic number mismatch. Got: {response_json.get('magic')}, expected: {utils.MAGIC}"
                        )
                        return False

                    if response_json.get("status") != "success":
                        self.log.error(response_json.get("message"))
                        return False

                    if response_json.get("version") != utils.VERSION:
                        self.log.error(
                            f"Version mismatch. Got: {response_json.get('version')}, expected: {utils.VERSION}"
                        )
                        return False

                    else:
                        return True

            except requests.exceptions.ConnectionError:
                return False

        def _get_lan_ip():
            """
            Gets the LAN IP address, even if /etc/hosts contains localhost or if there is no internet connection.
            """
            import socket

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                # Does not need to be reachable
                sock.connect(("10.255.255.255", 1))
                ip = sock.getsockname()[0]
            except Exception:
                ip = "127.0.0.1"
            finally:
                sock.close()
            return ip

        def _autodiscover_host():
            """
            Scan a subnet range to in an attempt to find the host, using nmap
            for service discovery.
            """
            import nmap

            def _callback_result(host, scan_result):
                """
                Callback function for the nmap scan.
                """
                self.log.debug(f"Found host: {host}")
                self.log.debug(f"Scan result: {scan_result}")

            # Get the LAN IP address
            # ip = _get_lan_ip()
            ip = "192.168.1.0/24"
            scan_ip = ".".join(ip.split(".")[:-1]) + ".0/" + str(subnet)

            # Scan the subnet
            self.log.info(f"Scanning subnet: {scan_ip}")
            nma = nmap.PortScannerAsync()
            nma.scan(scan_ip, str(port), callback=_callback_result, arguments="-sP")

            # Wait for the scan to finish
            while nma.still_scanning():
                self.log.debug(f"Scanning...")
                nma.wait(1)

        # The environment variable overrides all if it exists
        if host := os.environ.get("NV_HOST"):

            # Remove protocol
            host = host.split("://")[-1]

            # Split port
            host_ip, host_port = host.rsplit(":", 1)

            # Check if the host is running the correct version
            if _test_ip(ip=host_ip, port=host_port):

                # Save the host to the cache
                hostcache = {"ip": host_ip, "port": host_port}
                json.dump(hostcache, open(HOSTCACHE, "w"))

                return f"http://{host_ip}:{host_port}"
            else:
                raise Exception(
                    f"The host at {host} is invalid, make sure it is accessible and running the correct framework version ({utils.VERSION})"
                )

        # First try to find the host in the cache
        if os.path.exists(HOSTCACHE):
            hostcache = json.load(open(HOSTCACHE, "r"))

            if _test_ip(ip=hostcache["ip"], port=hostcache["port"]):
                return f"http://{hostcache['ip']}:{hostcache['port']}"

        # If the host wasn't found, try a named host (if running in Docker bridge)
        if _test_ip("nv_host", port):

            # Save the host to the cache
            hostcache = {"ip": "nv_host", "port": port}
            json.dump(hostcache, open(HOSTCACHE, "w"))

            return f"http://nv_host:{port}"

        # If the host wasn't found, scan LAN for a host
        raise NotImplementedError(
            "Scanning LAN for host is not yet implemented, please manually specify a host instead"
        )
        return _autodiscover_host()

    def _check_api_response(self, r):
        """
        ### Check a response from the nv API for errors.

        ---

        ### Parameters:
            - `r` (requests.Response): The response to check.

        ---

        ### Returns:
            `True` if the response was successful, `False` otherwise.
        """
        if r.status_code == 200:
            if r.json().get("status") == "success":
                return True
            else:
                self.log.error(r.json().get("message"))

        return False

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
            def callback_function(message):
                print(message)

            create_subscription("test", callback_function)
        """
        self.sio.on("_topic" + topic_name, callback_function)

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

        def _callback(data):
            """
            Handles response from the server after a publish request.
            """
            if data["status"] != "success":
                self.log.error("Failed to publish message: " + data["message"])

        self.sio.emit(
            "publish_on_topic",
            data={"topic": topic_name, "message": message},
            callback=_callback,
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
            name=service_name, callback=callback_function, sio=self.sio
        )

        server.create_service()

    def create_udp_service(self, service_name: str, callback_function):
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

        raise NotImplementedError(
            "UDP services are unreliable with large data (> 100,000 bytes), \
            as there is no error checking or correction. The standard socketio \
            backend is fast enough for this data anyway. Instead, TCP servers \
            should be implemented."
        )

        # Initialise the server
        server = services.UDPServiceServer(
            name=service_name, callback=callback_function, sio=self.sio
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
        client = services.ServiceClient(name=service_name, sio=self.sio)

        client.call_service(*args, **kwargs)
        return client

    def call_udp_service(self, service_name: str, *args, **kwargs):
        """
        ### Call a UDP service.
        UDP services are used for particularly fast data transfer from the
        service server back to the client. It should only be used if required,
        as it provides no error correction for lost packets.

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
            future = call_udp_service("test", "Hello", "World")

            # Wait for the response
            future.wait()

            # Get the response
            response = future.get_response()
        """

        raise NotImplementedError(
            "UDP services are unreliable with large data (> 100,000 bytes), \
            as there is no error checking or correction. The standard socketio \
            backend is fast enough for this data anyway. Instead, TCP servers \
            should be implemented."
        )

        # Initialise the server
        client = services.UDPServiceClient(name=service_name, sio=self.sio)

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
            The parameter value.

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

        params = {
            "name": parameter,
            "node_name": node_name,
        }

        # Send the request to the parameter server
        r = requests.get(self.host + "/api/get_parameter", params=params)

        # Check if the request was successful
        if self._check_api_response(r):
            return r.json().get("parameter_value")

        # If the parameter wasn't found, None or raise an exception
        if fail_if_not_found:
            raise Exception(
                f"Failed to get parameter: {parameter}. Maybe it doesn't exist?"
            )
        else:
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
            `True` if all parameters were set successfully.

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

        data = {
            "node_name": node_name,
            "name": name,
            "value": value,
            "description": description,
        }

        # Send the request to the parameter server
        r = requests.post(self.host + "/api/set_parameter", data=data)

        # Check if the request was successful
        if self._check_api_response(r):
            return True

        raise Exception(f"Failed to set parameter: {name} to value: {value}")

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

        # Ensure all parameters have a specified node name, adding the current
        # node for any without
        for parameter in parameters:
            if "node_name" not in parameter:
                parameter["node_name"] = self.name

            if "description" not in parameter:
                parameter["description"] = None

        # Send the request to the parameter server
        r = requests.post(
            self.host + "/api/set_parameters", json={"parameters": parameters}
        )

        # Check if the request was successful
        if self._check_api_response(r):
            return True

        raise Exception(f"Failed to set parameters: {parameters}.")

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

    def create_udp_server(
        self,
        callback: typing.Callable,
        port: int = 0,
        host: str = "localhost",
        buffer_size: int = 1024,
    ):
        """
        ### Create a UDP server to listen for UDP dataframes.
        This allows much faster client-client communication, as opposed to the
        standard socket-io client-server-client method (approx 10x improvement).
        All data transferred must be in bytes.

        #### Important notes:
        - Any message sent must be smaller than the buffer size.
        - Any message larger than the buffer size will be truncated.
        - There is no special handling of message size, sending large messages
            must be handled by the user.
        - There is no guarantee that the message will be received by the
            destination. Any error correction must be handled by the user.


        ---

        ### Parameters:
            - `callback` (function): A function to call when a dataframe is received.
                The function should take a single argument, which is the dataframe.
            - `port` (int): The port to listen on. If 0, a random port will be
                chosen.
            - `host` (str): The host to listen on. Defaults to "localhost".
            - `buffer_size` (int): The size of the buffer to use for receiving data.

        ---

        ### Returns:
            `udp_server` if the server was created successfully.
                Methods:
                    - `udp_server.start()`: Starts the server
                    - `udp_server.stop()`: Stops the server
                    - `udp_server.wait_until_ready()`: Waits until the server is ready to receive data.
                    - `udp_server.get_host()`: Returns the host the server is listening on.
                    - `udp_server.get_port()`: Returns the port the server is listening on.
        """

        return udp_server.UDP_Server(
            port=port, host=host, callback=callback, buffer_size=buffer_size
        )

    def create_udp_client(
        self,
        port: int,
        host: str = "localhost",
    ):
        """
        ### Create a UDP client to send UDP dataframes.
        This allows much faster client-client communication, as opposed to the
        standard socket-io client-server-client method. All data transferred
        must be in bytes.

        ---

        ### Parameters:
            - `port` (int): The port to send data to.
            - `host` (str): The host to send data to. Defaults to "localhost".

        ---

        ### Returns:
            `udp_client` if the client was created successfully.
                Methods:
                    - `udp_client.send(dataframe)`: Sends a dataframe to the server
        """

        return udp_server.UDP_Client(port=port, host=host)
