#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Custom logger module for Navvy. Includes custom formatting and the ability to
attach to a centralised log store.

Callum Morrison, 2021
UNMND, Ltd. 2021
<callum@unmnd.com>

All Rights Reserved
"""

import logging

# Set log levels in the same order as the logging module.
CRITICAL = 50
FATAL = CRITICAL
ERROR = 40
WARNING = 30
WARN = WARNING
INFO = 20
DEBUG = 10
NOTSET = 0


class LoggingFormatter(logging.Formatter):
    """
    Logging formatter to add colours and improve readability of logs.
    """

    grey = "\x1b[38m"
    blue = "\x1b[96m"
    yellow = "\x1b[33m"
    red = "\x1b[31m"
    bold_red = "\x1b[31;7mm"
    reset = "\x1b[0m"
    format = (
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"
    )

    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: blue + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


def generate_log(name: str, log_level: int = logging.DEBUG):
    """
    Automatically generate the log with formatting for a given name.

    Parameters:
        name (str): Name of the log.
        log_level (int): Log level to use.

    Returns:
        logging.Logger: Logger object.
    """
    handler = logging.StreamHandler()
    handler.setFormatter(LoggingFormatter())
    log = logging.getLogger(name)
    log.addHandler(handler)
    log.setLevel(log_level)

    return log


def get_logger(name: str):
    """
    Get the logger for a given name.

    Parameters:
        name (str): Name of the log.

    Returns:
        logging.Logger: Logger object.
    """
    return logging.getLogger(name)
