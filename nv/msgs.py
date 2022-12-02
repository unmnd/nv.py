#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Helpful example messages and related functions.

One of the primary benefits of the nv framework is that data transfer can be
done with nearly any standard data structure.

However, occasionally it's useful to transfer data in a more structured way.
For example, 'twist' messages allow you to specify a throttle and yaw velocity,
which is useful throughout various nodes.

At the end of the day, use of these are completely optional, but it might be
useful to create more intercompatible nodes.

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

import time


def stamp_message(message, timestamp: float = time.time(), frame: str = ""):
    """
    ### Stamp a message with a timestamp and frame.

    ---

    ### Parameters:
        - message (dict): A message to stamp.
        - timestamp (float): The timestamp to stamp the message with.
            [Default: time.time()]
        - frame (str): The frame to stamp the message with.
            [Default: ""]

    ---

    ### Returns:
        dict: The message with the timestamp and frame.
    """
    return {"msg": message, "header": Msg.header(timestamp, frame)}


class Msg:
    @staticmethod
    def header(timestamp: float = time.time(), frame: str = "") -> dict:
        """
        A header message, which provide a timestamp and transform frame parameter
        for messages. May be used to ensure messages received are not too old, or in
        the correct order.

        This message should not be sent on its own, but used in conjunction with
        other messages in the following manner:

        message_with_header = {
            "header": header(),
            "msg": message,
        }
        """
        return {"timestamp": timestamp, "frame": frame}

    @staticmethod
    def twist(throttle: float = 0.0, yaw: float = 0.0) -> dict:
        """
        A twist message for specifying throttle and yaw velocities.

        Throttle should always be in m/s (forward is positive), and yaw should
        always be in rad/s (clockwise is positive).
        """
        return {"throttle": throttle, "yaw": yaw}

    @staticmethod
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

    @staticmethod
    def joy(**kwargs) -> dict:
        """
        A joystick message.

        Note: This method is for docstring reference only, and should not be used.

        Axes should be a dict of floats, and buttons should be a dict of ints. Not
        all the fields need to be populated, but fields should not be populated for
        axes or buttons which don't exist on the gamepad.

        The axes are defined as follows:
            - "axis_left_x": left stick x-axis
            - "axis_left_y": left stick y-axis
            - "axis_left_trigger": left trigger or L2

            - "axis_right_x": right stick x-axis
            - "axis_right_y": right stick y-axis
            - "axis_right_trigger": right trigger or R2

            - "axis_dpad_x": dpad x-axis
            - "axis_dpad_y": dpad y-axis

        The buttons are defined as follows:
            - "button_a": A or ❌ button
            - "button_b": B or ⭕ button
            - "button_x": X or 🟧 button
            - "button_y": Y or 🔺 button

            - "button_left_bumper": left bumper or L1
            - "button_right_bumper": right bumper or R1

            - "button_select": select button
            - "button_start": start button
            - "button_home": xbox or ps button

            - "button_left_stick": left stick button
            - "button_right_stick": right stick button

            - "button_dpad_up": dpad up button
            - "button_dpad_down": dpad down button
            - "button_dpad_left": dpad left button
            - "button_dpad_right": dpad right button
        """

        raise NotImplementedError(
            "There is no reason to use this method directly, instead reference the docstring and construct your joy message manually."
        )
