#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Commandline tools for nv.

Callum Morrison, 2021
UNMND, Ltd. 2021
<callum@unmnd.com>

All Rights Reserved
"""

import uuid

import click

import nv.logger
import nv.node


class NodeClass:
    def set_node(self, node):
        self.node = node


node = NodeClass()


@click.group()
@click.option(
    "--nv_host", help="Override the host to connect to", default=None, type=str
)
def main(nv_host):
    """
    Main nv commandline interface.

    Provides a means to access nodes, echo and publish on topics, edit
    parameters, and more.
    """

    node.set_node(
        nv.node.Node(
            f"nv_cli #{uuid.uuid4()}", nv_host=nv_host, log_level=nv.logger.ERROR
        )
    )


@main.group()
# @click.argument("command", type=click.Choice(["echo", "list", "pub"]))
def topic():
    ...


@topic.command("echo")
@click.argument("topic")
def topic_echo(topic):
    click.echo(f"Echoing from topic: {topic}")

    def echo_callback(message):
        print(str(message))

    node.node.create_subscription(topic, echo_callback)


@main.command("param")
def main_param(self):
    raise NotImplementedError


if __name__ == "__main__":
    main()
