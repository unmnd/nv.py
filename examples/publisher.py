#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Part of the included nv examples. This file shows an example publisher node.

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


class Publisher(Node):
    def __init__(self):
        super().__init__("publisher_node")

        # To continuously publish at a defined rate, we can use a loop timer.
        self.counter = 0
        self.timer = self.create_loop_timer(
            interval=1.0, function=self.publish_hello_world
        )

        # Alternatively, we can just publish on any topic, at any time.
        # No limitations!
        self.publish("another_topic", ["Python", "objects", "work", "as", "well!"])

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
    node.spin()


if __name__ == "__main__":
    main()
