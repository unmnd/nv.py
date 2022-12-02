# This Dockerfile is used as a base image for the Python version of the nv
# framework.
#
# Callum Morrison, 2022
# UNMND, Ltd.
# <callum@unmnd.com>
#
# All Rights Reserved

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