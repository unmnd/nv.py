#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Part of the included nv examples. This file shows a minimal service server.

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


class OddEvenCheckServer(Node):
    def __init__(self):
        super().__init__("odd_even_check_server_node")

        # The `create_service` method creates a service server.
        # The first argument is the name of the service.
        # The second argument is the callback function that will be called when a client calls the service.
        self.create_service("odd_even_check", self.determine_odd_even)

    def determine_odd_even(self, number: int):
        # The arguments supplied can be any number of positional or keyword
        # arguments. Just make sure the node calling the service has the same arguments!

        self.log.info(f"Request received: {number}")

        # If the number is not an integer, raise an exception
        if not isinstance(number, int):
            raise ValueError(f"Number is not an integer: {number}")

        # The response can be any Python data type, and is sent using the return keyword.
        return "even" if number % 2 == 0 else "odd"


def main():
    node = OddEvenCheckServer()
    node.log.debug("Odd Even Check server running")
    node.spin()


if __name__ == "__main__":
    main()
