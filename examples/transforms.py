#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Part of the included nv examples. This file demonstrates the use of tranforms
(not yet implemented).

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

# import numpy as np
# from nv import Node


# class Transforms(Node):
#     def __init__(self):
#         super().__init__("transforms_node")

#         # A transform contains two parts:
#         #  - a translation (x, y, z)       [np.array]
#         #  - a rotation (qx, qy, qz, qw)   [np.quaternion]

#         # Transforms can be set using the `node.set_transform` method
#         self.set_transform(
#             "source_frame",
#             "target_frame",
#             np.array([0, 0, 0], dtype=float),
#             np.quaternion(1, 0, 0, 0),
#         )

#         # Setting multiple transforms creates a transform tree
#         self.set_transform(
#             "A",
#             "B",
#             np.array([0, 1, 0], dtype=float),
#             np.quaternion(0.707, 0.707, 0, 0),
#         )
#         self.set_transform(
#             "B",
#             "C",
#             np.array([0, 0, 3], dtype=float),
#             np.quaternion(0.707, 0, 0.707, 0),
#         )
#         self.set_transform("C", "D", np.array([1, 0, 0], dtype=float), np.quaternion())

#         # A frame may have multiple children, but only one parent
#         self.set_transform(
#             "C", "E", np.array([1.2, 0, 0], dtype=float), np.quaternion()
#         )

#         # You can check if a transform exists using `node.transform_exists`
#         self.log.info(self.transform_exists("A", "B"))

#         # It works even if there are multiple jumps required to connect the
#         # frames
#         self.log.info(self.transform_exists("A", "D"))

#         # If the transform does not exist, `node.get_transform` will return
#         # `None`
#         self.set_transform("X", "Y", np.array([0, 0, 0], dtype=float), np.quaternion())
#         self.log.info(self.get_transform("A", "X"))

#         # Transforms are directional
#         self.log.info(self.get_transform("A", "C"))  # Exists
#         self.log.info(self.get_transform("C", "A"))  # Does not exist

#         # You are not allowed to set a transform which already exists in
#         # reverse, or through a longer path
#         try:
#             self.set_transform(
#                 "B", "A", np.array([0, 0, 0], dtype=float), np.quaternion()
#             )
#         except:
#             self.log.info("Cannot set transform B -> A")

#         try:
#             self.set_transform(
#                 "A", "C", np.array([0, 0, 0], dtype=float), np.quaternion()
#             )
#         except:
#             self.log.info("Cannot set transform A -> C")


# def main():
#     node = Transforms()
#     node.spin()


# if __name__ == "__main__":
#     main()
