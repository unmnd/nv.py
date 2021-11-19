import os
import time

from nv.node import Node


test_data = {
    "Small String": "This is a small text message",
    "Medium String": "This is a medium text message. It contains more characters than the previous small string, but in the grand scheme of data transfer it's still pretty small. Following this message is a short poem to further pad this data. According to all known laws of aviation, there is no way a bee should be able to fly. Its wings are too small to get its fat little body off the ground. The bee, of course, flies anyway because bees don't care what humans think is impossible. Yellow, black. Yellow, black. Yellow, black. Yellow, black. Ooh, black and yellow! Let's shake it up a little. Barry! Breakfast is ready! Ooming! Hang on a second. Hello?",
    "Float": 1.23456789,
    "Integer": 123456789,
    "Dictionary": {
        "key1": "value1",
        "key2": "value2",
        "key3": 11223344,
        "key4": True,
        "key5": False,
    },
    "List": [
        "value1",
        "value2",
        "value3",
        "value4",
        "value5",
        "value6",
        "value7",
        "value8",
        "value9",
        "value10",
    ],
    "1MB of random bytes": os.urandom(1024 * 1024),
    "10MB of random bytes": os.urandom(10 * 1024 * 1024),
}


class PerformanceTester(Node):
    def __init__(self):
        super().__init__("performance_tester_node", skip_registration=True)

        # Set up the subscriber
        self.subscriber = self.create_subscription(
            "performance_test_topic",
            self.subscriber_callback,
        )

        self.start_times = {}
        self.durations = {}

        self.waiting_on_message = False

        # For each data size, send a message and wait for a response
        for key, value in test_data.items():
            self.start_times[key] = time.perf_counter()
            self.log.debug("Publishing test data...")

            self.waiting_on_message = True
            self.publish("performance_test_topic", value)

            while self.waiting_on_message:
                time.sleep(0.1)

        self.log.info("\n\n---\n\nDurations:")
        for key, value in self.durations.items():
            self.log.info(f"{key}: {value:.5}ms")

    def subscriber_callback(self, msg):
        finish_time = time.perf_counter()

        self.log.debug("Got message")

        # Get key of test data
        data_key = [key for key, value in test_data.items() if value == msg][0]

        self.durations[data_key] = (finish_time - self.start_times[data_key]) * 1000

        self.waiting_on_message = False


def main():
    node = PerformanceTester()
    node.spin()


if __name__ == "__main__":
    main()
