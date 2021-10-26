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
import threading
import time

import requests
import socketio

from nv import logger, utils, exceptions

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

        Parameters:
            name (str): The name of the node.
        """

        # SocketIO client
        self.sio = socketio.Client()

        # Initialise parameters
        self.name = name
        self.host = None
        self.node_registered = False

        # Assign sio callback functions
        self.sio.on("connect", self.on_connect)
        self.sio.on("disconnect", self.on_disconnect)

        # Initialise logger
        self.log = logger.generate_log(self.name, log_level=logger.DEBUG)

        self.log.debug(
            f"Initialising '{self.name}' using framework version nv {utils.VERSION}"
        )

        # Attempt to find the host IP address
        self.host = self.discover_host(**kwargs)
        self.log.debug(f"Found host: {self.host}")

        # Check if another node with this name already exists
        if self.node_exists(node_name=self.name):
            raise exceptions.DuplicateNodeName(
                "A node with the name " + self.name + " already exists on this network."
            )

        # Connect socket-io client
        self.sio.connect(self.host)

    def on_connect(self):
        """
        Callback for socket-io connect event.
        """
        self.log.debug("Connected to server.")
        self.log.debug(f"Attempting to register node '{self.name}'.")
        self.register_node()

    def on_disconnect(self):
        """
        Callback for socket-io disconnect event.
        """
        self.log.debug("Disconnected from server.")

    def register_node(self):
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

    def discover_host(self, timeout: float = -1, port: int = 5000, subnet: int = 24):
        """
        Attempt to automatically find the host of the nv network, by trying
        common IPs. The host must be on the same subnet as the node, unless
        overwritten in the `subnet` parameter.

        If the host is found, the IP is stored in a file called `.hostcache`,
        which will be tried first next time the function is called.

        It attempts to find the host by sending GET requests to all IPs on the

        Parameters:
            timeout (float): How long to wait for a response from the server.
                [Default: -1 (No timeout)]
            port (int): The port the host is listening for web requests on.
                [Default: 5000]
            subnet (int): The subnet mask of the host.
                [Default: 24 (i.e. X.X.X.0 - X.X.X.255)]

        Returns:
            The host of the nv network if found, otherwise None.
        """

        def _test_ip(ip, port):
            """
            Check if nv_host is running on the given IP.

            Parameters:
                ip (str): The IP to test.

            Returns:
                True, version if the host is running on the given IP, False otherwise.
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

                    if response_json.get("status") != "ok":
                        self.log.error(
                            f"Status not ok. Got: {response_json.get('status')}"
                        )
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

    def node_exists(self, node_id=None, node_name=None, node_ip=None):
        """
        Check if a node exists in the network. If the node exists, information
        about the node is returned, otherwise None.
        """

        # Ensure only one node identifier is provided
        assert (
            bool(node_id) ^ bool(node_name) ^ bool(node_ip)
        ), "You must specify exactly one of `node_id`, `node_name`, or `node_ip`."

        params = {
            "node_id": node_id,
            "node_name": node_name,
            "node_ip": node_ip,
        }

        r = requests.get(self.host + "/get_node_info", params=params)

        if r.status_code == 200:
            return r.json() or None

    # def subscribe(self, topic: str, callback) -> None:
    #     """
    #     Creates a subscription to a topic using socketio.
    #     """
    #     self.sio.on("_topic" + topic, callback)

    # def publish(self, topic: str, data) -> None:
    #     """
    #     Publishes a message to a topic using socketio.
    #     """
    #     print("publishing to topic: " + topic)
    #     self.sio.emit("new_message", {"topic": topic, "data": data})

    # def create_timer(self, interval, callback, **kwargs):
    #     """
    #     Create a timer which calls the callback function every `time` seconds
    #     """
    #     timer = threading.Thread(
    #         target=self._timer_thread, args=(interval, callback), kwargs=kwargs
    #     )
    #     timer.start()
    #     return timer

    # def _timer_thread(self, interval, callback, **kwargs):
    #     while True:
    #         callback(**kwargs)
    #         time.sleep(interval)

    # def destroy_timer(self, timer):
    #     """
    #     Destroy a timer
    #     """
    #     timer.cancel()
