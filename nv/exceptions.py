#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Custom exceptions for the nv package.

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


class RedisConnectionException(Exception):
    ...


class HostNotFoundException(Exception):
    ...


class DuplicateNodeNameException(Exception):
    ...


class ServiceNotFoundException(Exception):
    ...


class ServiceTimeoutException(Exception):
    ...


class ServiceErrorException(Exception):
    ...


class TransformExistsException(Exception):
    ...


class TransformAliasException(Exception):
    ...


class ParameterNotFoundException(Exception):
    ...
