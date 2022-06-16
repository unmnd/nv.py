import os
import random
import time
from pathlib import Path
from threading import Event

# import cv2
import numpy as np
from nv import Node

NUM_TESTS = 20


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
    "1D Floats Array": [random.random() for _ in range(64 * 64)],
    "1D Integers Array": [random.randint(-32768, 32767) for _ in range(64 * 64)],
    "2D Floats Array": [[random.random() for _ in range(64)] for _ in range(64)],
    "Image Array": np.load(Path(__file__).parent / "image_array.npy"),
}

# _, jpg = cv2.imencode(".jpg", test_data["Image Array"])
# test_data["Image JPG"] = jpg.tobytes()

# _, png = cv2.imencode(".png", test_data["Image Array"])
# test_data["Image PNG"] = png.tobytes()


class PerformanceTester(Node):
    def __init__(self):
        super().__init__(
            "performance_tester_node", skip_registration=True, use_lazy_parser=False
        )

        # Set up the subscriber
        self.subscriber = self.create_subscription(
            "performance_test_topic",
            self.subscriber_callback,
        )

        self.start_times = {key: [] for key in test_data.keys()}
        self.durations = {key: [] for key in test_data.keys()}
        self.key = None

        self.waiting_on_message = Event()

        for i in range(NUM_TESTS):

            # Print the current test without newline
            print(f"\rRunning test {i + 1}/{NUM_TESTS}...", end="")

            # For each data size, send a message and wait for a response
            for key, value in test_data.items():
                self.key = key

                self.start_times[key].append(time.perf_counter())

                self.waiting_on_message.clear()
                self.publish("performance_test_topic", value)

                self.waiting_on_message.wait()

        self.log.info("\n\n---\n\n")
        self.log.info("Test results (mean, median, std):")
        for key, value in self.durations.items():
            mean = sum(value) / len(value)
            median = sorted(value)[len(value) // 2]
            std_dev = sum([(x - sum(value) / len(value)) ** 2 for x in value]) / len(
                value
            )

            # Log the mean, median, and standard deviation
            self.log.info(f"{key}: {mean:.5}ms, {median:.5}ms, {std_dev:.5}ms")

        self.destroy_node()

    def subscriber_callback(self, msg):
        finish_time = time.perf_counter()

        self.durations[self.key].append(
            (finish_time - self.start_times[self.key][-1]) * 1000
        )

        self.waiting_on_message.set()


def main():
    node = PerformanceTester()
    node.spin()


if __name__ == "__main__":
    main()
