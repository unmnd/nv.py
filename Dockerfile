# This Dockerfile is used as a base image for the Python version of the nv
# framework, running on an NVIDIA Jetson device.
#
# Callum Morrison, 2021
# UNMND, Ltd.
# <callum@unmnd.com>
#
# All Rights Reserved

FROM nvcr.io/nvidia/l4t-base:r32.6.1

ARG DEBIAN_FRONTEND="noninteractive"
ENV TZ="Europe/London"

ARG PYTHON_VERSION="3.8"

# Install Python and pip
RUN apt-get update && \
    apt-get install -y --no-install-recommends software-properties-common && \
    add-apt-repository -y ppa:deadsnakes && \
    apt-get install -y --no-install-recommends python${PYTHON_VERSION} python${PYTHON_VERSION}-dev python${PYTHON_VERSION}-venv gcc g++ && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN python${PYTHON_VERSION} -m venv /venv
ENV PATH=/venv/bin:$PATH

WORKDIR /opt/nv

# Copy examples
COPY examples examples

# Copy files needed to install requirements only
COPY requirements.txt requirements.txt

# Install requirements for the nv framework first
RUN python3 -m pip install --upgrade pip && \
    pip3 install -r requirements.txt

# Then copy the rest of the nv framework and install
COPY setup.py setup.py
COPY nv nv
RUN pip3 install . && rm -rf nv setup.py