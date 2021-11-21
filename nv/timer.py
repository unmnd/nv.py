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
from threading import Thread, Event


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
        ### Call a function repeatedly every `interval` seconds.

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
        self.interval = interval
        self.function = function
        self.immediate = immediate
        self.args = args
        self.kwargs = kwargs

        if autostart:
            self.start()

    def _run(self):
        while not self.stopped.wait(self.interval):
            self.function(*self.args, **self.kwargs)

    def start(self):
        """
        Manually start the timer.
        """
        if self.immediate:
            self.function(*self.args, **self.kwargs)

        self._run_thread = Thread(target=self._run, daemon=True)
        self._run_thread.start()

    def stop(self):
        """
        Manually stop the timer.
        """
        self.stopped.set()


# def ratelimit(limit: int, every: float = 1.0, droppy: bool = False):
#     """
#     ### Function decorator which limits function calls to a specified rate.

#     ---

#     ### Parameters:
#         - limit (int): The maximum number of calls to allow.
#         - every (float): The time in seconds to allow between calls.
#         - droppy (bool): Whether to drop calls if the rate limit is reached.

#     ### Returns:
#         - The wrapped function.

#     ### Example::

#         @ratelimit(5, 1.0)
#         def spam():
#             print("Spam!")

#         spam()
#     """

#     def limitdecorator(fn):
#         if droppy:
#             semaphore = Semaphore(limit + 1)
#         else:
#             semaphore = Semaphore(limit)

#         @wraps(fn)
#         def wrapper(*args, **kwargs):
#             if droppy:
#                 if not semaphore.acquire(blocking=False):
#                     return
#             else:
#                 semaphore.acquire()
#             try:
#                 return fn(*args, **kwargs)
#             finally:  # don't catch but ensure semaphore release
#                 timer = Timer(every, semaphore.release)
#                 timer.setDaemon(True)  # allows the timer to be canceled on exit
#                 timer.start()

#         return wrapper

#     return limitdecorator
