import nv


class SampleNode1(nv.Node):
    def __init__(self):
        super().__init__(name="test_node_1")
        # self.create_timer(interval=1, callback=publish_on_timer, node=self)

        self.discover_host()


def main():
    node = SampleNode1()
    # timer = node.create_timer(interval=1, callback=publish_on_timer, node=node)

    # print(timer)


if __name__ == "__main__":
    main()
