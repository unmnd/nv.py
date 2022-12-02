#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Part of the included nv examples. This file shows an example subscriber node.

Callum Morrison
UNMND, Ltd. 2022
<callum@unmnd.com>

This file is part of nv.

nv is free software: you can redistribute it and/or modify it under the
terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

nv is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
nv. If not, see <https://www.gnu.org/licenses/>.
"""

from nv import Node


class Subscriber(Node):
    def __init__(self):
        super().__init__("subscriber_node")

        # The `create_subscription` function takes two parameters:
        # - topic_name: The name of the topic to subscribe to.
        # - callback_function: The function to call when a message is received.
        self.sub = self.create_subscription("hello_world", self.subscriber_callback)

        # You can unsubscribe from a topic by calling Subscriber.unsubscribe()
        # self.sub.unsubscribe()

    def subscriber_callback(self, msg):
        self.log.info(f"Received: {msg}")


def main():
    node = Subscriber()
    node.log.debug("Waiting for data to be published over topic")
    node.spin()


if __name__ == "__main__":
    main()
