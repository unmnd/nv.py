#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Add support for UDP client-client communication, as an alternative to the
standard socketio client-server-client communication.

It is much faster (~1ms) than socketio (~10ms), but a limitation is that all
data must be sent and received in bytes.

UNMND, Ltd. 2021
<callum@unmnd.com>

All Rights Reserved
"""

import socket
import threading


class UDP_Server:
    def __init__(self, port, host, callback, buffer_size):
        """
        ### Initialise the UDP server.
        """
        self.active = False
        self.ready = False
        self.host = host
        self.port = port
        self.callback = callback
        self.buffer_size = buffer_size

    def _run_udp_server(self):
        """
        ### Bind a UDP server to the specified host and port.
        Active while self.active is True.

        ---

        ### Parameters:
            - host (str): The host to bind to.
            - port (int): The port to bind to.

        ### Returns:
            (socket.socket): The bound socket.
        """

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1024)

        sock.bind((self.host, self.port))

        self.ready = True
        while self.active:
            data, addr = sock.recvfrom(self.buffer_size)
            self.callback(data)

    def start(self):
        """
        ### Start the UDP server.
        """
        self.active = True
        thread = threading.Thread(target=self._run_udp_server)
        thread.start()

    def stop(self):
        """
        ### Stop the UDP server.
        """
        self.active = False
        self.ready = False

    def wait_until_ready(self):
        """
        ### Wait until the server is ready.
        """
        while not self.ready:
            pass


class UDP_Client:
    def __init__(self, host, port):
        """
        ### Initialise the UDP client.
        """
        self.active = False
        self.host = host
        self.port = port

    def send(self, data: bytes):
        """
        ### Send data to the UDP server.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(data, (self.host, self.port))
