#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Add support for services. Services work in a similar manner to topic publishers
and subscribers, except the publisher expects a response from the service.

Callum Morrison, 2021
UNMND, Ltd. 2021
<callum@unmnd.com>

All Rights Reserved
"""

import json
import threading
import typing
import uuid

import socketio

from .udp_server import UDP_Client, UDP_Server


class ServiceServer:
    def __init__(self, name: str, callback: typing.Callable, sio: socketio.Client):
        """
        ### Create a service server.

        ---

        ### Parameters
        - `name`: The name of the service. This is what other nodes can call to
            request this service.
        - `callback`: The callback function to be called when a request is
          received.
        - `sio`: The socket.io client to use. This is needed to allow internal
          message sending and receiving.
        """
        self.name = name
        self.callback = callback
        self.sio = sio

    def _handle_service_request(self, msg):
        """
        Handle the request to call a service, and respond with the result.
        """
        args = msg.get("args")
        kwargs = msg.get("kwargs")
        request_uuid = msg.get("request_uuid")

        response = self.callback(*args, **kwargs)

        self.sio.emit(
            "_service_response",
            {"service": self.name, "request_uuid": request_uuid, "response": response},
        )

    def create_service(self):
        """
        Create the service server.
        """
        self.sio.on("_service" + self.name, self._handle_service_request)


class ServiceClient:
    def __init__(self, name: str, sio: socketio.Client):
        """
        ### Create a service client.

        ---

        ### Parameters
        - `name`: The name of the service. This is what other nodes can call to
            request this service.
        - `sio`: The socket.io client to use. This is needed to allow internal
            message sending and receiving.
        """

        self.name = name
        self.sio = sio
        self.request_uuid = str(uuid.uuid4())
        self._response_received = threading.Event()
        self.response = None

    def call_service(self, *args, **kwargs):
        """
        Call a service.
        A UUID is generated for the request, which ensures that the server only
        responds to this exact request.

        ---

        ### Parameters
        - `args`: The arguments to pass to the service.
        - `kwargs`: The keyword arguments to pass to the service.
        """
        self.sio.on(
            "_service_response_" + self.request_uuid, self._service_response_callback
        )

        self.sio.emit(
            "service_request",
            {
                "service": self.name,
                "request_uuid": self.request_uuid,
                "args": args,
                "kwargs": kwargs,
            },
        )

    def _service_response_callback(self, response):
        """
        Handle the response from a service.
        """
        self._response_received.set()
        self.response = response

    def wait(self, timeout: float = None):
        """
        Wait for a response from a service.

        ---

        ### Parameters
        - `timeout`: The maximum amount of time to wait for a response.
        """
        self._response_received.wait(timeout)
        self._response_received.clear()

    def get_response(self):
        """
        Get the response from a service. If no response has been received,
        this will return None.
        """
        return self.response


class UDPServiceServer(ServiceServer):
    def _handle_service_request(self, msg):
        """
        Handle the request to call a service, and respond with the result.

        This is a UDP service, so the response is sent back to the client over
        UDP, instead of the socket.io client used in the normal case.
        """
        args = msg.get("args")
        kwargs = msg.get("kwargs")
        request_uuid = msg.get("request_uuid")
        host = msg.get("host")
        port = msg.get("port")

        # Get the response
        response = self.callback(*args, **kwargs)

        # Ensure the response is in bytes
        if not isinstance(response, bytes):
            raise TypeError("Response must be bytes")

        # Connect the UDP client
        udp_client = UDP_Client(host, port)

        # Send the initial data information packet
        udp_client.send(
            json.dumps(
                {
                    "service": self.name,
                    "request_uuid": request_uuid,
                    "response_length": len(response),
                }
            ).encode("utf-8")
        )

        CHUNK_SIZE = 1024 * 32

        # Send the response in chunks
        for i in range(0, len(response), CHUNK_SIZE):
            udp_client.send(response[i : i + CHUNK_SIZE])

        # Finally send the terminating packet
        udp_client.send(b"\x00" * 1024)


class UDPServiceClient(ServiceClient):
    def __init__(self, name: str, sio: socketio.Client):
        """
        ### Create a UDP service client.
        This client is used when the service responds over UDP. This is useful
        for fast data transfer, but is unecessary for most services.

        ---

        ### Parameters
        - `name`: The name of the service. This is what other nodes can call to
            request this service.
        - `sio`: The socket.io client to use. This is needed to allow internal
            message sending and receiving.
        """

        super().__init__(name, sio)

        self._data_buffer = b""
        self._data_info = None

    def call_service(self, *args, **kwargs):
        """
        Call a service.
        A UUID is generated for the request, which ensures that the server only
        responds to this exact request.

        ---

        ### Parameters
        - `args`: The arguments to pass to the service.
        - `kwargs`: The keyword arguments to pass to the service.
        """

        CHUNK_SIZE = 1024 * 32

        # Generate the UDP listener. Use port 0 to get a random port
        udp_server = UDP_Server(
            callback=self._udp_service_response_callback, buffer_size=CHUNK_SIZE
        )
        self.host = udp_server.get_host()
        self.port = udp_server.get_port()

        # Start the UDP listener
        udp_server.start()
        udp_server.wait_until_ready()

        self.sio.emit(
            "service_request",
            {
                "service": self.name,
                "request_uuid": self.request_uuid,
                "host": self.host,
                "port": self.port,
                "args": args,
                "kwargs": kwargs,
            },
        )

    def _udp_service_response_callback(self, data):
        """
        Handle the response from a service.
        """

        # The first packet should be serialised information about the data
        if self._data_info is None:
            self._data_info = json.loads(data.decode("utf-8"))
            return

        # The last packet should contain a terminating sequence
        elif data == b"\x00" * 1024:

            # Check the length of the data matches the original handshake packet
            if len(self._data_buffer) != self._data_info["response_length"]:
                raise ValueError("Response length does not match handshake packet")

            # Send the data to the callback
            self._service_response_callback(self._data_buffer)

            # Reset the buffer
            self._data_buffer = b""
            self._data_info = None

        else:
            self._data_buffer += data
