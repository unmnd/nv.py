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
import warnings


class UDP_Server:
    def __init__(self, callback, port=0, host="localhost", buffer_size=1024):
        """
        ### Initialise the UDP server.
        """
        self._active = False
        self._ready = threading.Event()
        self.host = host
        self.port = port
        self.callback = callback
        self.buffer_size = buffer_size

        if buffer_size > 1024:
            warnings.warn(
                "Buffer size is greater than 1024 bytes. This is not recommended.",
                BytesWarning,
            )

        if buffer_size > 65507:
            raise BufferError(
                "Buffer size is larger than the maximum packet size allowed for UDP. Please use no more than 65507 bytes"
            )

        # Binding will allow the host and port to be fetched before the server
        # is started.
        self._bind()

    def _run_udp_server(self):
        """
        ### Bind a UDP server to the specified host and port.
        Active while self.active is True.
        """
        self._ready.set()

        while self._active:
            data, addr = self.sock.recvfrom(self.buffer_size)
            self.callback(data)

    def _bind(self):
        """
        ### Bind the UDP server to the specified host and port.
        """
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1024)
        self.sock.bind((self.host, self.port))

    def get_host(self):
        """
        ### Get the host of the UDP server.
        """
        return self.sock.getsockname()[0]

    def get_port(self):
        """
        ### Get the port of the UDP server.
        """
        return self.sock.getsockname()[1]

    def start(self):
        """
        ### Start the UDP server.
        """
        self._active = True
        thread = threading.Thread(target=self._run_udp_server)
        thread.start()

    def stop(self):
        """
        ### Stop the UDP server.
        """
        self._active = False
        self._ready.clear()

    def wait_until_ready(self):
        """
        ### Wait until the server is ready.
        """
        self._ready.wait()


class UDP_Client:
    def __init__(self, host, port):
        """
        ### Initialise the UDP client.
        """
        self.active = False
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send(self, data: bytes):
        """
        ### Send data to the UDP server.
        """
        self.sock.sendto(data, (self.host, self.port))
