#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Commandline tools for nv.

Callum Morrison, 2021
UNMND, Ltd. 2021
<callum@unmnd.com>

All Rights Reserved
"""

import json
import time
import uuid

import click

import nv.logger
import nv.node
import nv.utils
import nv.version


class NodeClass:
    def set_node(self, node: nv.node.Node):
        self.node = node


node = NodeClass()


@click.group()
@click.version_option(
    version=nv.version.__version__,
    prog_name="nv",
    message="%(prog)s framework v%(version)s",
)
@click.pass_context
def main(ctx):
    """
    Main nv commandline interface.

    Provides a means to access nodes, echo and publish on topics, edit
    parameters, and more.
    """

    node.set_node(
        nv.node.Node(
            f"nv_cli #{uuid.uuid4()}",
            log_level=nv.logger.ERROR,
            skip_registration=True,
        )
    )

    # Create a callback which terminates the node when the command is complete
    ctx.call_on_close(node.node.destroy_node)


@main.group()
def topic():
    """
    Functions related to topics.
    """
    ...


@topic.command("echo")
@click.argument("topic")
def topic_echo(topic):
    """
    Subscribes to a topic and prints all messages received.
    """
    click.echo(f"Echoing from topic: {topic}")

    def echo_callback(message):
        print(str(message))

    node.node.create_subscription(topic, echo_callback)
    spin_until_keyboard_interrupt()


@topic.command("list")
def topic_list():
    """
    List all topics, and how recently they were last published to.
    """

    # Get topics
    topics = node.node.get_topics()

    # Format their timestamps nicely
    for topic in topics:
        duration, prefix, suffix = node.node.format_duration(time.time(), topics[topic])
        topics[topic] = f"Last message {prefix} {duration} {suffix}"

    click.echo(json.dumps(topics, indent=4))


@topic.command("pub")
@click.argument("topic")
@click.argument("msg")
@click.option(
    "--rate", default=0, help="Continuously publish the data at a specified rate in hz."
)
def topic_pub(topic, msg, rate):
    """
    Publish a message to a topic.
    """
    click.echo(f"Publishing to topic: {topic}")

    if rate > 0:
        try:
            while True:
                node.node.publish(topic, msg)
                click.echo(f"Published: {msg}")
                time.sleep(1 / rate)
        except KeyboardInterrupt:
            node.node.destroy_node()
    else:
        node.node.publish(topic, msg)


@main.group()
def nodes():
    """
    Functions related to nodes.
    """
    ...


@nodes.command("list")
def nodes_list():
    """
    List all nodes.
    """
    returned_list_of_nodes = node.node.get_nodes_list()

    click.echo(
        f"Listing nodes [{len(returned_list_of_nodes)}]:\n"
        + "\n".join(returned_list_of_nodes)
    )


@nodes.command("info")
@click.argument("node_name")
def nodes_info(node_name):
    """
    Get information about a node.
    """
    node_info = node.node.get_node_information(node_name=node_name)

    click.echo(
        f"Node info for {node_name}:\n{json.dumps(node_info, indent=4, sort_keys=True)}"
    )


@main.group("param")
def param():
    """
    Functions related to parameters
    """
    ...


@param.command("list")
@click.argument("node_name")
def param_list(node_name):
    """
    List all parameters, and their values, for a node.
    """
    click.echo(
        f"Listing parameters for node {node_name}:\n"
        + json.dumps(node.node.get_parameters(node_name=node_name), indent=4)
    )


def spin_until_keyboard_interrupt():
    """
    Spin until keyboard interrupt.
    """
    try:
        node.node.spin()
    except KeyboardInterrupt:
        node.node.destroy_node()


if __name__ == "__main__":
    main()
