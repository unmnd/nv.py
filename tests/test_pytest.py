#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Testing suite for the nv framework.

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
import pathlib
import random
import time

from nv import utils
from nv import Node


class Subscriber(Node):
    def __init__(self):
        super().__init__("subscriber_node", skip_registration=True)

        self.message = None
        self.create_subscription("pytest_test_topic", self.subscriber_callback)

    def subscriber_callback(self, msg):
        self.message = msg


class ServiceServer(Node):
    def __init__(self):
        # You can't skip registration on service servers
        super().__init__()
        self.create_service("example_service", self.example_service)
        self.create_service("list_service", self.list_service)
        self.create_service(
            "nonconcurrent_service",
            self.nonconcurrent_service,
            allow_parallel_calls=False,
        )

    def example_service(self, arg: str, kwarg: str = None):
        return arg + kwarg

    def list_service(self):
        return [1, 2, 3]

    def nonconcurrent_service(self, call_number: int):
        time.sleep(random.random())
        return call_number


class ConditionalNode(Node):
    def __init__(self):

        self.counter = 0

        super().__init__(skip_registration=True)

    def node_condition(self):
        self.counter += 1
        return self.counter > 2


def test_messaging():
    subscriber_node = Subscriber()
    publisher_node = Node(skip_registration=True)

    test_data = {
        "string": "Hello World",
        "int": 123,
        "float": 123.456,
        "list": [1, 2, 3],
        "dict": {"key": "value"},
        "binary": b"Hello World",
        "large_data": ["Hello World" for _ in range(100000)],
    }

    for key, value in test_data.items():
        publisher_node.publish("pytest_test_topic", value)

        while subscriber_node.message is None:
            time.sleep(0.001)

        assert subscriber_node.message == value
        subscriber_node.message = None

    subscriber_node.destroy_node()
    publisher_node.destroy_node()


def test_compression():
    data = {
        "string": "Hello World",
        "int": 123,
        "object": {"key": "value"},
        "binary": b"Hello World",
        "large_data": ["Hello World" for _ in range(100000)],
        "array": [1 if i % 2 == 0 else i for i in range(10000)],
    }

    for key, value in data.items():
        compressed_data, compression_ratio = utils.compress_message(
            value, size_comparison=True, stringify=False
        )

        assert utils.decompress_message(compressed_data) == value


def test_parameters():
    parameter_node = Node("parameter_node", skip_registration=True)

    # Remove any preexisting parameters (this is not done automatically because
    # skip_registration is True)
    parameter_node.delete_parameters()

    # Getting and setting parameters
    assert parameter_node.get_parameter("test_param") is None
    parameter_node.set_parameter("test_param", "test_value")
    assert parameter_node.get_parameter("test_param") == "test_value"

    # Set multiple parameters at once
    parameter_node.set_parameters(
        [
            {
                "name": "test_param_1",
                "value": "test_value_1",
            },
            {
                "name": "test_param_2",
                "value": "test_value_2",
            },
        ]
    )
    assert parameter_node.get_parameter("test_param_1") == "test_value_1"

    # Getting and setting parameters on a different node
    parameter_node.set_parameter("test_param", "test_value", node_name="node2")
    assert parameter_node.get_parameter("test_param", node_name="node2") == "test_value"

    # Setting parameters from a file
    parameters_file = str(pathlib.Path(__file__).parent / "config.yml")
    os.environ["NV_EXAMPLE_ENV_CONDITIONAL"] = ""
    parameter_node.set_parameters_from_file(parameters_file)
    assert parameter_node.get_parameter("test_param_3") == "test_value_3"

    # Check conditionals in file loading
    assert parameter_node.get_parameter("test_param_4") is None
    os.environ["NV_EXAMPLE_ENV_CONDITIONAL"] = "123"
    parameter_node.set_parameters_from_file(parameters_file)
    assert parameter_node.get_parameter("test_param_4") == "test_value_4"

    # Getting all parameters from a node
    parameters = parameter_node.get_parameters()
    assert parameters["test_param_1"] == "test_value_1"

    # Deleting parameters
    parameter_node.delete_parameter("test_param_1")
    assert parameter_node.get_parameter("test_param_1") is None

    # Deleting all parameters from a node
    parameter_node.delete_parameters(node_name="node2")
    assert parameter_node.get_parameter("test_param", node_name="node2") is None

    parameter_node.destroy_node()


def test_services():
    service_server = ServiceServer()
    service_client = Node(skip_registration=True)

    # Wait for the services to be active
    assert service_client.wait_for_service_ready("example_service")
    assert service_client.wait_for_service_ready("list_service")
    assert service_client.wait_for_service_ready("nonconcurrent_service")

    # Calling a service
    assert (
        service_client.call_service("example_service", "test", kwarg="test")
        == "testtest"
    )

    # Calling a service with a list
    assert service_client.call_service("list_service") == [1, 2, 3]

    # Check non-concurrent service
    responses = []
    for i in range(3):
        responses.append(service_client.call_service("nonconcurrent_service", i))

    assert responses == [0, 1, 2]

    service_server.destroy_node()
    service_client.destroy_node()
