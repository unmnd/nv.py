import pickle
import time
from pathlib import Path

from nv.node import Node


class PerformanceTester(Node):
    def __init__(self):
        super().__init__("performance_tester_node")

        # Load the test_data as bytes
        test_data_10mb = open(Path(__file__).parent / "10mb_data.pickle", "rb").read()
        test_data_1mb = open(Path(__file__).parent / "1mb_data.pickle", "rb").read()
        test_data_small = "this is a small text message"

        self.test_data = [test_data_small, test_data_1mb, test_data_10mb]

        # Set up the subscriber
        self.subscriber = self.create_subscription(
            "performance_test_topic",
            self.subscriber_callback,
        )

        self.start_times = [0] * 3

        # For each data size, send a message and wait for a response
        for i, data in enumerate(self.test_data):
            self.start_times[i] = time.time()
            self.log.info("Publishing test data...")
            self.publish("performance_test_topic", data)
            time.sleep(1)

    def subscriber_callback(self, msg):
        finish_time = time.time()

        self.log.info("Got message")

        # Get index of test data
        index = self.test_data.index(msg)

        if index == 0:
            self.log.info("Small message:")
        elif index == 1:
            self.log.info("1MB message:")
        else:
            self.log.info("10MB message:")

        self.log.info(
            f"Time taken to send & receive message: {(finish_time - self.start_times[index]) * 1000:.5}ms"
        )


def main():
    node = PerformanceTester()


if __name__ == "__main__":
    main()
