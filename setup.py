#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Setup script to allow installation of nv. This allows the nv module to be
imported within the current environment, and allows the nv cli to be used.

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

from setuptools import setup

setup(
    name="nv-framework",
    version="1.25.0",
    description="A Python-based robot-focused framework.",
    long_description="For more information, please visit https://github.com/unmnd/nv.py.",
    license="GPL-3.0-or-later",
    url="https://github.com/unmnd",
    author="UNMND, Ltd.",
    author_email="callum@unmnd.com",
    packages=["nv"],
    install_requires=[
        "pyyaml==6.0",
        "click==8.0.3",
        "redis==3.5.3",
        # "numpy==1.20.3",
        # "numpy-quaternion==2021.11.4.15.26.3",
        "orjson==3.6.8",
        "psutil==5.9.1",
    ],
    python_requires=">=3.8",
    entry_points={"console_scripts": ["nv=nv.__main__:main"]},
)
