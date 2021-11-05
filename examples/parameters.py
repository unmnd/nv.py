import os
from pathlib import Path

from nv.node import Node


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
        self.set_parameters_from_file(
            os.path.join(Path(__file__).parent, "config.json")
        )
        self.log.info(
            f"Parameter from `config.json`: {self.get_parameter('param1', node_name='node1')}"
        )

        # You can get all parameters for a node with `get_parameters`
        self.log.info(f"All parameters for this node: {self.get_parameters()}")


def main():
    node = ParameterExamples()
    node.spin()


if __name__ == "__main__":
    main()
