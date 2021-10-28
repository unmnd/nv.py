import time

from nv.node import Node


class PerformanceTester(Node):
    def __init__(self):
        super().__init__("performance_tester_node")

        # Set up the subscriber
        self.subscriber = self.create_subscription(
            "performance_test_topic",
            self.subscriber_callback,
        )

        # Start the node by saving the current time and immediately publishing
        # to a topic
        self.start_time = time.time()
        self.publish("performance_test_topic", "This data doesn't matter")

    def subscriber_callback(self, msg):
        self.log.info(
            f"Time taken to send & receive message: {(time.time() - self.start_time) * 1000:.2}ms"
        )


def main():
    node = PerformanceTester()


if __name__ == "__main__":
    main()
