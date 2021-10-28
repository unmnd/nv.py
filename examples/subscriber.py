from nv.node import Node


class Subscriber(Node):
    def __init__(self):
        super().__init__("subscriber_node")

        # The `create_subscription` function takes two parameters:
        # - topic_name: The name of the topic to subscribe to.
        # - callback_function: The function to call when a message is received.
        self.sub = self.create_subscription("hello_world", self.subscriber_callback)

    def subscriber_callback(self, msg):
        self.log.info(f"Received: {msg}")


def main():
    node = Subscriber()
    node.log.debug("Waiting for data to be published over topic")


if __name__ == "__main__":
    main()
