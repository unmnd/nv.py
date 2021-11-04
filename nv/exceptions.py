#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Custom exceptions for the nv package.

Callum Morrison, 2021
UNMND, Ltd. 2021
<callum@unmnd.com>

All Rights Reserved
"""


class HostNotFoundException(Exception):
    ...


class DuplicateNodeNameException(Exception):
    ...

class ServiceNotFoundException(Exception):
    ...