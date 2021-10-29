#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Callum Morrison, 2021
UNMND, Ltd. 2021
<callum@unmnd.com>

All Rights Reserved
"""

import os
import pkg_resources

import requests

VERSION = pkg_resources.require("nv")[0].version
MAGIC = "n4vvy"
CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".nv")

# Generate the config path if it doesn't exist
if not os.path.exists(CONFIG_PATH):
    os.makedirs(CONFIG_PATH)


def node_exists(host, node_id=None, node_name=None, node_ip=None):
    """
    Check if a node exists in the network. If the node exists, information
    about the node is returned, otherwise None.
    """

    # Ensure only one node identifier is provided
    assert (
        bool(node_id) ^ bool(node_name) ^ bool(node_ip)
    ), "You must specify exactly one of `node_id`, `node_name`, or `node_ip`."

    params = {
        "node_id": node_id,
        "node_name": node_name,
        "node_ip": node_ip,
    }

    r = requests.get(host + "/api/get_node_info", params=params)

    if r.status_code == 200:
        if r.json().get("status") == "success":
            return r.json().get("node")
        else:
            return None

    raise Exception(
        f"Unable to check if the node exists. Got status code: {r.status_code}"
    )
