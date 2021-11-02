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

import threading
import typing
import uuid

import socketio


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
