#
# ------------------------------------------------------------------------------
#                                NV DOCKERFILE
# ------------------------------------------------------------------------------
#
# The base Docker image for the nv framework, which contains a minimal Alpine
# linux installation, Python, and the latest nv framework.
#
# The nv framework is used as an alternative for ROS2, as a robotics framework
# which facilitates communication and interaction between different 'nodes'. It
# has been designed primarily for the Navvy robot.
#
# Callum Morrison, 2021
# UNMND, Ltd. 2021
# <callum@unmnd.com>
#
# All Rights Reserved

# Currently, this uses Python 3.10 but there should be no issues with automatic
# updates to later Python 3 versions.
FROM python:3-alpine

WORKDIR /opt/nv

# Copy files needed to install requirements only
COPY setup.py setup.py
COPY nv/version.py nv/version.py

# Install requirements for the nv framework by first separating dependencies
# from the setup.py file, then installing them.
RUN python3 setup.py egg_info && \
    pip3 install -r *.egg-info/requires.txt && \
    rm -rf *.egg-info

# Then copy the rest of the nv framework and install
COPY . .
RUN pip3 install .