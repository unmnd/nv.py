#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Part of the included nv examples. This file shows an minimal service client.

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


class OddEvenCheckClient(Node):
    def __init__(self):
        super().__init__("odd_even_check_client_node")

        # You can wait for a service to be ready using the
        # `wait_for_service_ready` method.
        self.wait_for_service_ready("odd_even_check")

        self.log.debug("Odd Even Check client making a request")

        # Call any service using the `call_service` method
        # The service name is the first argument, and any number of args or
        # kwargs can be passed afterwards. Ensure the arguments match what is
        # expected by the service server!
        result = self.call_service("odd_even_check", number=5)

        # Get the response
        self.log.info(f"Result: The number was {result}!")


def main():
    node = OddEvenCheckClient()

    node.spin()


if __name__ == "__main__":
    main()
