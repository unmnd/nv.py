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
from threading import Timer, Event, Thread

OneShotTimer = Timer


class LoopTimer:
    def __init__(
        self,
        interval: int,
        function: typing.Callable,
        autostart: bool = True,
        immediate: bool = False,
        termination_event: Event = None,
        *args,
        **kwargs
    ):
        """
        ### Call a function repeatedly every 'interval' seconds.

        ---

        ### Parameters:
            - interval (int): The interval in seconds to call the function.
            - function (callable): The function to call.
            - autostart (bool): Whether to start the timer automatically.
            - immediate (bool): Whether to call the function immediately after start.
            - termination_event (Event): An event to watch for to stop the timer.
            - args: The arguments to pass to the function.
            - kwargs: The keyword arguments to pass to the function.
        """

        self.stopped = Event()
        self._termination_event = termination_event
        self.interval = interval
        self.function = function
        self.immediate = immediate
        self.args = args
        self.kwargs = kwargs

        # If the termination event exists, we want to 'attach' it to the
        # self.stopped event. This is so that a termination event will
        # immediately trigger the self.stopped event, and terminate the timer.
        if termination_event:
            self._termination_thread = Thread(target=self._termination_event_checker)
            self._termination_thread.start()

        if autostart:
            self.start()

    def _run(self):
        while not self.stopped.wait(self.interval):
            self.function(*self.args, **self.kwargs)

    def _termination_event_checker(self):
        """
        Couple the termination event to the stop method, so that as soon as the
        termination event is set, the timer is stopped.
        """
        self._termination_event.wait()
        self.stop()

    def start(self):
        """
        Manually start the timer.
        """
        if self.immediate:
            self.function(*self.args, **self.kwargs)

        self._run_thread = Thread(target=self._run)
        self._run_thread.start()

    def stop(self):
        """
        Manually stop the timer.
        """
        self.stopped.set()
