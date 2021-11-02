#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
One of the primary benefits of the nv framework is that data transfer can be
done with any standard Python variable type.

However, occasionally it's useful to transfer data in a more structured way.
For example, 'twist' messages allow you to specify a throttle and yaw velocity,
which is useful throughout various nodes.

At the end of the day, use of these are completely optional, but it might be
useful to create more intercompatible nodes.

An additional note, if you use this module you add a function call into each
message generation, which typically adds about 70ns to execution time. If you
need ultimate performance, make each message manually in your code!

Callum Morrison, 2021
UNMND, Ltd. 2021
<callum@unmnd.com>

All Rights Reserved
"""


def twist(throttle: float = 0.0, yaw: float = 0.0) -> dict:
    """
    A twist message for specifying throttle and yaw velocities.

    Throttle should always be in m/s (forward is positive), and yaw should
    always be in rad/s (clockwise is positive).
    """
    return {"throttle": throttle, "yaw": yaw}


def twist_6dof(
    linear_x: float = 0.0,
    linear_y: float = 0.0,
    linear_z: float = 0.0,
    angular_x: float = 0.0,
    angular_y: float = 0.0,
    angular_z: float = 0.0,
) -> dict:
    """
    A twist message for specifying linear and angular velocities in
    6 degrees of freedom.

    The direction convention is as follows:

        +z
        ^   +x
        |  7
        | /
        |/
        +---------> +y

    """
    return {
        "linear_x": linear_x,
        "linear_y": linear_y,
        "linear_z": linear_z,
        "angular_x": angular_x,
        "angular_y": angular_y,
        "angular_z": angular_z,
    }
