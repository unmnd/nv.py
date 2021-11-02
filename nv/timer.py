#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Timer related helpers for use in the nv framework.

Callum Morrison, 2021
UNMND, Ltd. 2021
<callum@unmnd.com>

All Rights Reserved
"""

import typing
from threading import Timer

OneShotTimer = Timer


class LoopTimer:
    def __init__(
        self,
        interval: int,
        function: typing.Callable,
        autostart: bool = True,
        immediate: bool = False,
        *args,
        **kwargs
    ):
        """
        Call a function repeatedly every 'interval' seconds.

        Parameters:
            interval (int): The interval in seconds to call the function.
            function (callable): The function to call.
            autostart (bool): Whether to start the timer automatically.
            immediate (bool): Whether to call the function immediately after start.
            args: The arguments to pass to the function.
            kwargs: The keyword arguments to pass to the function.
        """
        self._timer = None
        self.interval = interval
        self.function = function
        self.immediate = immediate
        self.args = args
        self.kwargs = kwargs
        self.is_running = False

        if autostart:
            self.start()

    def _run(self):
        self.is_running = False
        self.start()
        self.function(*self.args, **self.kwargs)

    def start(self):
        """
        Manually start the timer.
        """
        if self.immediate:
            self.function(*self.args, **self.kwargs)

        if not self.is_running:
            self._timer = Timer(self.interval, self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        """
        Manually stop the timer.
        """
        self._timer.cancel()
        self.is_running = False
