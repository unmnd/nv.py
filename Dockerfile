# NV Dockerfile
# This Dockerfile is used as a base image for the Python version of the
# nv framework.
#
# Callum Morrison
# UNMND, Ltd. 2022
# <callum@unmnd.com>
#
# This file is part of nv.
#
# nv is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# nv is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# nv. If not, see <https://www.gnu.org/licenses/>.

FROM python:3.10-slim

ARG DEBIAN_FRONTEND="noninteractive"
ENV TZ="Europe/London"

WORKDIR /opt/nv

# Copy examples
COPY examples examples

# Copy the nv framework and install
COPY setup.py setup.py
COPY nv nv
RUN pip3 install . && \
    rm -rf nv setup.py && rm -rf nv/__pycache__