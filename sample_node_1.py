import nv


class SampleNode1(nv.Node):
    def __init__(self):
        super().__init__(name="test_node_1")
        # self.create_timer(interval=1, callback=publish_on_timer, node=self)

        self.create_subscription("test_topic", self.test_callback)

        print(self.get_parameter("test_parameter"))
        self.set_parameter("test_parameter", "EYOOYY")
        print(self.get_parameter("test_parameter"))

        self.set_parameters(
            [
                {"name": "test_parameter_1", "value": "test_value_1"},
                {"name": "test_parameter_2", "value": "test_value_2"},
            ]
        )

        print(self.get_parameter("test_parameter_1"))
        print(self.get_parameter("test_parameter_2"))

    def test_callback(self, msg):
        self.log.warning("test_callback: {}".format(msg))


def main():
    node = SampleNode1()
    # timer = node.create_timer(interval=1, callback=publish_on_timer, node=node)

    # print(timer)


if __name__ == "__main__":
    main()
