#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Part of the included nv examples. This file shows demonstrates the use of
parameters (getting and setting persistent state) in nv.

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
from pathlib import Path

from nv import Node


class ParameterExamples(Node):
    def __init__(self):
        super().__init__("parameter_examples_node")

        # Getting and setting single parameters is easy
        self.set_parameter(
            "example_parameter",
            "Hello World",
            description="This is an example parameter",
        )
        self.log.info(f"Example parameter: {self.get_parameter('example_parameter')}")

        # You can also set multiple parameters at once
        self.set_parameters(
            [
                {
                    "name": "example_parameter_2",
                    "value": "Hello World 2",
                    "description": "This is an example parameter 2",
                },
                {
                    "name": "example_parameter_3",
                    "value": "Hello World 3",
                    "description": "This is an example parameter 3",
                },
            ]
        )
        self.log.info(
            f"One of two parameters set together: {self.get_parameter('example_parameter_2')}"
        )
        self.log.info(
            f"Two of two parameters set together: {self.get_parameter('example_parameter_3')}"
        )

        # If you try to get a parameter which doesn't exist, you'll get None
        self.log.info(
            f"This parameter doesn't exist: {self.get_parameter('example_parameter_4')}"
        )

        # You can set and get subparameters with dot notation
        self.set_parameter("subparameter.example_parameter", "dlroW olleH")
        self.log.info(
            f"Subparameter: {self.get_parameter('subparameter.example_parameter')}"
        )

        # By default, parameters are specific to each node, but it's easy to get
        # or set parameters from different nodes
        self.set_parameter(
            "example_parameter", "Hello from another node!", node_name="node2"
        )
        self.log.info(self.get_parameter("example_parameter", node_name="node2"))

        # If you want to set loads of parameters, you can do this from a .json
        # or .yaml file accessible from the node
        self.set_parameters_from_file(os.path.join(Path(__file__).parent, "config.yml"))
        self.log.info(
            f"Parameter from `config.yml`: {self.get_parameter('param1', node_name='node1')}"
        )

        # If you only want to load the parameters but not set them on the
        # parameter server, you can use `load_parameters_from_file`
        parameters = self.load_parameters_from_file(
            os.path.join(Path(__file__).parent, "config.yml")
        )
        self.log.info(f"Parameter from `config.yml`: {parameters['node1']['param1']}")

        # An environment variable condition can be applied to any top-level
        # assignment. In the config files, `node1(ENV_VARIABLE==somevalue)` will
        # assign the parameters to node1 only if ENV_VARIABLE==somevalue.

        # Should be "value1"
        self.log.info(self.get_parameter("param1", node_name="node1"))
        os.environ["ENV_VARIABLE"] = "somevalue"
        self.set_parameters_from_file(os.path.join(Path(__file__).parent, "config.yml"))

        # Should be "value1_override"
        self.log.info(self.get_parameter("param1", node_name="node1"))

        # You can get all parameters for a node with `get_parameters`
        self.log.info(f"All parameters for this node: {self.get_parameters()}")

        # Finally you can remove parameters from the parameter server
        self.delete_parameter("example_parameter")
        self.log.info(f"Removed parameter: {self.get_parameter('example_parameter')}")

        # You can remove all parameters from a node at once
        self.delete_parameters(node_name="node1")


def main():
    node = ParameterExamples()
    node.spin()


if __name__ == "__main__":
    main()
