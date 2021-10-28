from nv.node import Node
from nv.timer import LoopTimer


class Publisher(Node):
    def __init__(self):
        super().__init__("publisher_node")

        # To continuously publish at a defined rate, we can use the timer
        # provided by nv.timer.LoopTimer.
        self.timer = LoopTimer(interval=1.0, function=self.publish_hello_world)

        # Alternatively, we can just publish on any topic, at any time.
        # No limitations!
        self.publish("another_topic", ["Python", "objects", "work", "as", "well!"])

        self.counter = 0

    def publish_hello_world(self):
        # The `publish` method is used to publish a message to a topic.
        # It takes two arguments:
        #   - topic_name: the name of the topic to publish to
        #   - message: the message to publish
        self.publish("hello_world", "Hello World! " + str(self.counter))
        self.counter += 1


def main():
    node = Publisher()
    node.log.debug("Publisher node is now running")


if __name__ == "__main__":
    main()
