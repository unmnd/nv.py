import nv


class SampleNode2(nv.Node):
    def __init__(self):
        super().__init__(name="test_node_2")
        # self.create_timer(interval=1, callback=publish_on_timer, node=self)

        self.publish("test_topic", {"test_key": "test_value"})

    # def test_callback(self, msg):
    #     self.log.warning("test_callback: {}".format(msg))


def main():
    node = SampleNode2()
    # timer = node.create_timer(interval=1, callback=publish_on_timer, node=node)

    # print(timer)


if __name__ == "__main__":
    main()
