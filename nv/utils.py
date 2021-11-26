#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Extra utilities and helper functions.

Callum Morrison, 2021
UNMND, Ltd. 2021
<callum@unmnd.com>

All Rights Reserved
"""

import cProfile
import pstats
import time
import typing
from threading import Event, Thread

# MAGIC = "n4vvy"
# CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".nv")

# # Generate the config path if it doesn't exist
# if not os.path.exists(CONFIG_PATH):
#     os.makedirs(CONFIG_PATH)


class LoopTimer:
    def __init__(
        self,
        interval: int,
        function: typing.Callable,
        autostart: bool = True,
        immediate: bool = False,
        *args,
        **kwargs,
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

        self._run_thread = Thread(
            target=self._run,
            daemon=True,
            name=f"LoopTimer for `{self.function.__name__}`",
        )
        self._run_thread.start()

    def stop(self):
        """
        Manually stop the timer.
        """
        self.stopped.set()


def time_func(
    func: typing.Callable, print_function: typing.Callable = print, *args, **kwargs
):
    """
    ### Time execution time of a function.

    ---

    ### Parameters:
        - `func` (callable): The function to time.
        - `print_function` (callable): Replace `print` with a custom function.
        - `args`: The arguments to pass to the function.
        - `kwargs`: The keyword arguments to pass to the function.
    """

    start = time.time()
    result = func(*args, **kwargs)
    end = time.time()

    # Convert duration to human readable
    duration, prefix, suffix = format_duration(start, end)

    print_function(f"{func.__name__} took {duration}")

    return result


def profile_func(
    func: typing.Callable,
    *args,
    print_function: typing.Callable = print,
    **kwargs,
):
    """
    ### Profile execution time of a function.

    ---

    ### Parameters:
        - `func` (callable): The function to time.
        - `print_function` (callable): Replace `print` with a custom function.
        - `args`: The arguments to pass to the function.
        - `kwargs`: The keyword arguments to pass to the function.
    """

    pr = cProfile.Profile()
    pr.enable()

    result = func(*args, **kwargs)

    pr.disable()
    sortby = pstats.SortKey.CUMULATIVE
    ps = pstats.Stats(pr).sort_stats(sortby)

    # Override print function
    pstats.print = print_function

    ps.print_stats()

    return result


def format_duration(time_1: float, time_2: float) -> typing.Tuple[str, str, str]:
    """
    ### Format a duration between two unix timestamps into a human-readable string.

    It works in the form `time_1` to `time_2`; meaning if `time_2` <
    `time_1`, the duration is "in the past". Likewise, if `time_1` <
    `time_2` the duration is "in the future".

    Formats to seconds, hours, and days as long as they are > 0.

    ---

    ### Parameters:
        - `time_1` (float): The first timestamp.
        - `time_2` (float): The second timestamp.

    ---

    ### Returns:
        - A human-readable string representing the duration.
        - The prefix, "was" or "is" if required.
        - The suffix, "ago" or "from now".

    ---

    ### Example::

        # Get the duration between two timestamps
        duration, prefix, suffix = format_duration(time.time(), example_timestamp)

        # Display how long ago an event was
        print(f"This event {prefix} {duration} {suffix}")

    """

    # Get the duration
    duration = time_2 - time_1

    # If the duration is negative, the second time is in the past
    if duration < 0:
        prefix = "was"
        suffix = "ago"
        duration = -duration

    # If the duration is positive, the second time is in the future
    else:
        prefix = "is"
        suffix = "from now"

    # Format the duration as a human-readable string
    if duration < 1:
        duration = f"{duration * 1000:.0f}ms"
    elif duration < 60:
        duration = f"{duration:.0f}s"
    elif duration < 3600:
        duration = f"{duration / 60:.0f}m"
    elif duration < 86400:
        duration = f"{duration / 3600:.0f}h"
    else:
        duration = f"{duration / 86400:.0f}d"

    return duration, prefix, suffix


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
