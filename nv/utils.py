#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Extra utilities and helper functions.

Callum Morrison, 2021
UNMND, Ltd. 2021
<callum@unmnd.com>

All Rights Reserved
"""

import os

import requests

MAGIC = "n4vvy"
CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".nv")

# Generate the config path if it doesn't exist
if not os.path.exists(CONFIG_PATH):
    os.makedirs(CONFIG_PATH)
