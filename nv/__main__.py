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
from typing import Optional
import uuid

import click

import nv.logger
import nv.node
import nv.utils
import nv.version

node = nv.node.Node(
    f"nv_cli #{uuid.uuid4()}",
    log_level=nv.logger.ERROR,
    skip_registration=True,
)


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

    # Create a callback which terminates the node when the command is complete
    ctx.call_on_close(node.destroy_node)


@main.group()
def topic():
    """
    Functions related to topics.
    """
    ...


@topic.command("echo")
@click.argument("topic", type=click.Choice(node.get_topics().keys()))
def topic_echo(topic):
    """
    Subscribes to a topic and prints all messages received.
    """
    click.echo(f"Echoing from topic: {topic}")

    def echo_callback(message):
        print(str(message))

    node.create_subscription(topic, echo_callback)
    spin_until_keyboard_interrupt()


@topic.command("list")
def topic_list():
    """
    List all topics, and how recently they were last published to.
    """

    # Get topics
    topics = node.get_topics()

    # Format their timestamps nicely
    for topic in topics:
        duration, prefix, suffix = node.format_duration(time.time(), topics[topic])
        topics[topic] = f"Last message {prefix} {duration} {suffix}"

    click.echo(json.dumps(topics, indent=4))


@topic.command("pub")
@click.argument("topic", type=str)
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
                node.publish(topic, msg)
                click.echo(f"Published: {msg}")
                time.sleep(1 / rate)
        except KeyboardInterrupt:
            node.destroy_node()
    else:
        node.publish(topic, msg)


@topic.command("hz")
@click.argument("topic", type=click.Choice(node.get_topics().keys()))
def topic_hz(topic):
    """
    Measure the rate at which a topic is published.
    """
    click.echo(f"Measuring rate of: {topic}")

    class Rate:
        def __init__(self):
            self.count = 0
            self.start = None

        def __call__(self, message):
            # If this is the first message, set the start time
            if self.start is None:
                self.start = time.time()
                return

            self.count += 1

            current_rate = self.count / (time.time() - self.start)
            click.echo(
                f"{round(current_rate, 1)} hz ({self.count} {'messages' if self.count > 1 else 'message'})\r",
                nl=False,
            )

    rate_callback = Rate()
    node.create_subscription(topic, rate_callback)

    spin_until_keyboard_interrupt()


@topic.command("subs")
@click.argument("topic", type=click.Choice(node.get_topics().keys()))
def topic_subs(topic):
    """
    List all subscribers to a topic.
    """
    click.echo(f"Subscribers to topic: {topic}")

    subscribers = node.get_topic_subscriptions(topic)
    click.echo(json.dumps(subscribers, indent=4))


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
    returned_list_of_nodes = node.get_nodes_list()

    click.echo(
        f"Listing nodes [{len(returned_list_of_nodes)}]:\n"
        + "\n".join(returned_list_of_nodes)
    )


@nodes.command("info")
@click.argument("node_name", type=click.Choice(node.get_nodes_list()))
def nodes_info(node_name):
    """
    Get information about a node.
    """
    node_info = node.get_node_information(node_name=node_name)

    click.echo(
        f"Node info for {node_name}:\n{json.dumps(node_info, indent=4, sort_keys=True)}"
    )


@main.group("param")
def param():
    """
    Functions related to parameters.
    """
    ...


@param.command("list")
@click.argument("node_name", type=click.Choice(node.get_nodes_list()))
def param_list(node_name):
    """
    List all parameters, and their values, for a node.
    """
    click.echo(
        f"Listing parameters for node {node_name}:\n"
        + json.dumps(node.get_parameters(node_name=node_name), indent=4)
    )


@param.command("set")
@click.argument("node_name", type=str)
@click.argument("param_name", type=str)
@click.argument("param_value", type=str)
@click.option("--description", type=str)
def param_set(node_name, param_name, param_value, description):
    """
    Set a parameter for a node.
    """
    if node.set_parameter(
        node_name=node_name, name=param_name, value=param_value, description=description
    ):
        click.echo(f"Set parameter {param_name} to '{param_value}'")
    else:
        click.echo(f"Failed to set parameter {param_name} to {param_value}")


@param.command("get")
@click.argument("node_name", type=str)
@click.argument("param_name", type=str)
def param_get(node_name, param_name):
    """
    Get a parameter value.
    """
    click.echo(
        f"Getting parameter {param_name} for node {node_name}:\n"
        + json.dumps(
            node.get_parameter(node_name=node_name, parameter=param_name), indent=4
        )
    )


@param.command("describe")
@click.argument("node_name", type=str)
@click.argument("param_name", type=str)
def param_describe(node_name, param_name):
    """
    Get a parameter description.
    """
    click.echo(
        f"Getting description for parameter {param_name} for node {node_name}:\n"
        + json.dumps(
            node.get_parameter_description(node_name=node_name, parameter=param_name),
            indent=4,
        )
    )


@param.command("dump")
@click.argument("node_name", type=str)
def param_dump(node_name):
    """
    Dump all parameters for a node in `json` format.
    """
    click.echo(
        json.dumps({node_name: node.get_parameters(node_name=node_name)}, indent=4)
    )


@main.group("service")
def service():
    """
    Functions related to services.
    """
    ...


@service.command("list")
def service_list():
    """
    List all services.
    """
    click.echo(
        f"Listing services:\n" + json.dumps(list(node.get_services().keys()), indent=4)
    )


@service.command("call")
@click.argument("service_name", type=click.Choice(node.get_services().keys()))
@click.option(
    "--arg",
    "-a",
    multiple=True,
    type=click.UNPROCESSED,
    required=False,
)
@click.option(
    "--kwarg",
    "-k",
    multiple=True,
    type=(str, click.UNPROCESSED),
    required=False,
)
def service_call(service_name, arg, kwarg):
    """
    Call a service.
    """

    if kwarg is None:
        kwarg = {}
    else:
        kwarg = {k: v for k, v in kwarg}

    # Convert to Python datatypes
    kwargs = {}
    for k, v in kwarg.items():
        try:
            kwargs[k] = eval(v)
        except (SyntaxError, NameError):
            kwargs[k] = v

    args = []
    for a in arg:
        try:
            args.append(eval(a))
        except (SyntaxError, NameError):
            args.append(a)

    click.echo(f"Calling service {service_name} with args: {args} and kwargs: {kwargs}")
    service_result = node.call_service(service_name, *args, **kwargs)

    click.echo("Waiting for response...")

    service_result.wait()

    click.echo(f"Service result: {service_result.get_response()}")


def spin_until_keyboard_interrupt():
    """
    Spin until keyboard interrupt.
    """
    try:
        node.spin()
    except KeyboardInterrupt:
        node.destroy_node()


if __name__ == "__main__":
    main()
