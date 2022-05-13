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
import random
import sys
import time
import typing
from threading import Event, Thread

import orjson as json

try:
    import lz4framed
except ImportError:
    lz4framed = None


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


def generate_name() -> str:
    """
    ### Generate a random human-readable name.

    ---

    ### Returns:
        - A random name.
    """

    # fmt: off
    adjectives = ["defiant", "homeless", "adorable", "delightful", "homely", "quaint", "adventurous", "depressed", "horrible", "aggressive", "determined", "hungry", "real", "agreeable", "different", "hurt", "relieved", "alert", "difficult", "repulsive", "alive", "disgusted", "ill", "rich", "amused", "distinct", "important", "angry", "disturbed", "impossible", "scary", "annoyed", "dizzy", "inexpensive", "selfish", "annoying", "doubtful", "innocent", "shiny", "anxious", "drab", "inquisitive", "shy", "arrogant", "dull", "itchy", "silly", "ashamed", "sleepy", "attractive", "eager", "jealous", "smiling", "average", "easy", "jittery", "smoggy", "awful", "elated", "jolly", "sore", "elegant", "joyous", "sparkling", "bad", "embarrassed", "splendid", "beautiful", "enchanting", "kind", "spotless", "better", "encouraging", "stormy", "bewildered", "energetic", "lazy", "strange", "black", "enthusiastic", "light", "stupid", "bloody", "envious", "lively", "successful", "blue", "evil", "lonely", "super", "blue", "eyed", "excited", "long", "blushing", "expensive", "lovely", "talented", "bored", "exuberant", "lucky", "tame", "brainy", "tender", "brave", "fair", "magnificent", "tense", "breakable", "faithful", "misty", "terrible", "bright", "famous", "modern",
                  "tasty", "busy", "fancy", "motionless", "thankful", "fantastic", "muddy", "thoughtful", "calm", "fierce", "mushy", "thoughtless", "careful", "filthy", "mysterious", "tired", "cautious", "fine", "tough", "charming", "foolish", "nasty", "troubled", "cheerful", "fragile", "naughty", "clean", "frail", "nervous", "ugliest", "clear", "frantic", "nice", "ugly", "clever", "friendly", "nutty", "uninterested", "cloudy", "frightened", "unsightly", "clumsy", "funny", "obedient", "unusual", "colorful", "obnoxious", "upset", "combative", "gentle", "odd", "uptight", "comfortable", "gifted", "old", "fashioned", "concerned", "glamorous", "open", "vast", "condemned", "gleaming", "outrageous", "victorious", "confused", "glorious", "outstanding", "vivacious", "cooperative", "good", "courageous", "gorgeous", "panicky", "wandering", "crazy", "graceful", "perfect", "weary", "creepy", "grieving", "plain", "wicked", "crowded", "grotesque", "pleasant", "wide", "eyed", "cruel", "grumpy", "poised", "wild", "curious", "poor", "witty", "cute", "handsome", "powerful", "worrisome", "happy", "precious", "worried", "dangerous", "healthy", "prickly", "wrong", "dark", "helpful", "proud", "dead", "helpless", "putrid", "zany", "defeated", "hilarious", "puzzled", "zealous"]
    nouns = ["actor", "gold", "painting", "advertisement", "grass", "parrot", "afternoon", "greece", "pencil", "airport", "guitar", "piano", "ambulance", "hair", "pillow", "animal", "hamburger", "pizza", "answer", "helicopter", "planet", "apple", "helmet", "plastic", "army", "holiday",  "honey", "potato", "balloon", "horse", "queen", "banana", "hospital", "quill", "battery", "house", "rain", "beach", "hydrogen", "rainbow", "beard", "ice", "raincoat", "bed", "insect", "refrigerator", "insurance", "restaurant", "boy", "iron", "river", "branch", "island", "rocket", "breakfast", "jackal", "room", "brother", "jelly", "rose", "camera", "jewellery", "candle", "sandwich", "car", "juice", "school", "caravan", "kangaroo", "scooter", "carpet", "king", "shampoo", "cartoon", "kitchen", "shoe", "kite", "soccer", "church", "knife", "spoon", "crayon", "lamp",
             "stone", "crowd", "lawyer", "sugar", "daughter", "leather", "death", "library", "teacher", "lighter", "telephone", "diamond", "lion", "television", "dinner", "lizard", "tent", "disease", "lock", "doctor", "tomato", "dog", "lunch", "toothbrush", "dream", "machine", "traffic", "dress", "magazine", "train", "easter", "magician", "truck", "egg", "eggplant", "market", "umbrella", "match", "van", "elephant", "microphone", "vase", "energy", "monkey", "vegetable", "engine", "morning", "vulture", "motorcycle", "wall", "evening", "nail", "whale", "eye", "napkin", "window", "family", "needle", "wire", "nest", "xylophone", "fish", "yacht", "flag", "night", "yak", "flower", "notebook", "zebra", "football", "ocean", "zoo", "forest", "oil", "garden", "fountain", "orange", "gas", "oxygen", "girl", "furniture", "oyster", "glass", "garage", "ghost"]
    # fmt: on

    return random.choice(adjectives) + "_" + random.choice(nouns)


def compress_message(message: typing.Any, size_comparison=False) -> bytes:
    """
    ### Compress a message before sending it over the network.

    Uses lz4 frames for maximum performance. It works best using large data with
    lots of repeating values, such as arrays where a lot of values are '0' or
    'NaN'.

    If size_comparison is True, it will check if the compressed message is
    actually smaller than the original, and will return whichever is smaller, as
    well as the compression ratio.
    """

    if lz4framed is None:
        raise ImportError(
            "lz4framed is not installed. Please install `py-lz4framed` with pip."
        )

    # Try to serialise the message as JSON.
    try:
        message = json.dumps(message, option=json.OPT_SERIALIZE_NUMPY)
    except TypeError:
        pass

    compressed = lz4framed.compress(message)

    if size_comparison:
        original_size = sys.getsizeof(message)
        compressed_size = sys.getsizeof(compressed)
        ratio = original_size / compressed_size

        print(f"Original size: {original_size}")
        print(f"Compressed size: {compressed_size}")
        print(f"Compression ratio: {ratio}")

        return compressed if compressed_size < original_size else message, ratio

    else:
        return compressed


def decompress_message(message: bytes) -> typing.Union[str, bytes]:
    """
    ### Decompress a message after receiving it over the network.
    """

    # First try to decompress the message
    try:
        message = lz4framed.decompress(message)
    except lz4framed.Lz4FramedError:
        pass

    # Then try to deserialise the message as JSON
    try:
        message = json.loads(message)
    except json.JSONDecodeError:
        pass

    return message


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
