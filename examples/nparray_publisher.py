"""
This publisher node is an example of publishing numpy data to the network. It is
converted to a generic format (effectively JSON) so that it can be understood by
different languages on the network. This is advised, but not strictly required.

Callum Morrison, 2022
UNMND, Ltd. 2022
<callum@unmnd.com>

All Rights Reserved
"""

import numpy as np
from nv.node import Node


class Publisher(Node):
    def __init__(self):
        super().__init__("nparray_publisher_node")

        self.timer = self.create_loop_timer(
            interval=1.0, function=self.publish_hello_world
        )

    def publish_hello_world(self):

        # Generate random numpy arrays
        arr_small = np.random.rand(10, 10)
        arr_large = np.random.rand(100, 100)
        arr_uint8 = np.random.randint(0, 255, size=(20, 20), dtype=np.uint8)
        arr_bool = np.random.randint(0, 2, size=(20, 20), dtype=bool)
        arr_uneven = np.random.randint(0, 255, size=(20, 12), dtype=np.uint8)

        self.publish("numpy_small", arr_small.tolist())
        self.publish("numpy_large", arr_large.tolist())
        self.publish("numpy_uint8", arr_uint8.tolist())
        self.publish("numpy_bool", arr_bool.tolist())
        self.publish("numpy_uneven", arr_uneven.tolist())


def main():
    node = Publisher()
    node.log.debug("Numpy array publisher node is now running")
    node.spin()


if __name__ == "__main__":
    main()
