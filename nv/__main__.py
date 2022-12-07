#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Commandline tools for nv.

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

import json
import time
import uuid
from gettext import ngettext
from importlib import metadata

import click

import nv

node = nv.node.Node(
    f"nv_cli #{uuid.uuid4()}",
    skip_registration=True,
    log_level=nv.logger.ERROR,
)


def print_version(ctx, param, value):
    """
    Custom version printer which destroys the node after completion.
    """
    if not value or ctx.resilient_parsing:
        return
    node.destroy_node()
    click.echo(f"nv framework v{metadata.version('nv-framework')}")
    ctx.exit()


class CustomGroup(click.Group):
    def format_help(self, ctx, formatter) -> None:
        """
        Custom help formatter which destroys the node after completion.
        """
        node.destroy_node()
        return super().format_help(ctx, formatter)


class CustomChoice(click.Choice):
    """
    Custom implementation of `click.Choice` which can allow any value, but
    displays a warning if the value is not in the list of choices.
    """

    def __init__(
        self, choices, case_sensitive: bool = True, allow_others: bool = True
    ) -> None:
        self.choices = choices
        self.case_sensitive = case_sensitive
        self.allow_others = allow_others

    def convert(
        self,
        value,
        param,
        ctx,
    ):
        # Match through normalization and case sensitivity
        # first do token_normalize_func, then lowercase
        # preserve original `value` to produce an accurate message in
        # `self.fail`
        normed_value = value
        normed_choices = {choice: choice for choice in self.choices}

        if ctx is not None and ctx.token_normalize_func is not None:
            normed_value = ctx.token_normalize_func(value)
            normed_choices = {
                ctx.token_normalize_func(normed_choice): original
                for normed_choice, original in normed_choices.items()
            }

        if not self.case_sensitive:
            normed_value = normed_value.casefold()
            normed_choices = {
                normed_choice.casefold(): original
                for normed_choice, original in normed_choices.items()
            }

        if normed_value in normed_choices:
            return normed_choices[normed_value]

        choices_str = ", ".join(map(repr, self.choices))

        if self.allow_others:
            click.echo(
                click.style(
                    f"Warning: {value} has not yet been published to.",
                    fg="yellow",
                )
            )
            return value
        else:
            self.fail(
                ngettext(
                    "{value!r} is not {choice}.",
                    "{value!r} is not one of {choices}.",
                    len(self.choices),
                ).format(value=value, choice=choices_str, choices=choices_str),
                param,
                ctx,
            )


@click.group(cls=CustomGroup)
@click.option(
    "--version", is_flag=True, callback=print_version, expose_value=False, is_eager=True
)
@click.pass_context
def main(ctx):
    """
    nv  Copyright (C) 2022  UNMND Ltd.

    This program comes with ABSOLUTELY NO WARRANTY. This is free software, and
    you are welcome to redistribute it under certain conditions.

    ---

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
@click.argument("topic", type=CustomChoice(node.get_topics().keys()))
def topic_echo(topic):
    """
    Subscribes to a topic and prints all messages received.
    """
    click.echo(f"Echoing from topic: {topic}")

    def echo_callback(message):
        click.echo(str(message))

    node.create_subscription(topic, echo_callback)
    node.spin()


@topic.command("list")
def topic_list():
    """
    List all topics, and how recently they were last published to.
    """

    # Get topics
    topics = node.get_topics()

    # Format their timestamps nicely
    for topic in topics:
        duration, prefix, suffix = nv.utils.format_duration(time.time(), topics[topic])
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

    try:
        msg = json.loads(msg)
    except json.JSONDecodeError:
        pass

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
@click.argument("topic", type=CustomChoice(node.get_topics().keys()))
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

    node.spin()


@topic.command("subs")
@click.argument("topic", type=click.Choice(node.get_topics().keys()))
def topic_subs(topic):
    """
    List all subscribers to a topic.
    """
    click.echo(f"Subscribers to topic: {topic}")

    subscribers = node.get_topic_subscribers(topic)
    click.echo(json.dumps(subscribers, indent=4))


@main.group("node")
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


@nodes.command("ps")
def nodes_ps():
    """
    Get system information about each running node.
    """
    nodes_list = node.get_nodes_list()

    nodes_ps = {}

    for key in nodes_list:
        nodes_ps[key] = node.get_node_ps(key)

    # Tabulate the data
    tabulated_nodes_ps = nv.utils.tabulate_dict(
        nodes_ps, ["node_name"] + list(nodes_ps[nodes_list[0]].keys()), stringify=True
    )

    click.echo(tabulated_nodes_ps)


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
        + json.dumps(node.get_parameter(node_name=node_name, name=param_name), indent=4)
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
            node.get_parameter_description(node_name=node_name, name=param_name),
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
@click.option("--verbose", "-v", is_flag=True, help="Print the full service info.")
def service_list(verbose):
    """
    List all services.
    """
    if verbose:
        services = {key: str(value) for key, value in node.get_services().items()}
        click.echo(f"Listing services:\n" + json.dumps(services, indent=4))
    else:
        click.echo(
            f"Listing services:\n"
            + json.dumps(list(node.get_services().keys()), indent=4)
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
    click.echo(f"Service result: {node.call_service(service_name, *args, **kwargs)}")


# @main.group("tree")
# def tree():
#     """
#     Functions related to behaviour trees.
#     """
#     ...


# @tree.command("blackboard")
# def tree_blackboard():
#     """
#     Monitor the py_trees blackboard.
#     """

#     class Blackboard:
#         blackboard_state = (
#             node.call_service("get_blackboard_state").wait().get_response()
#         )

#     def echo_callback(message):

#         # Update the blackboard state
#         Blackboard.blackboard_state[message["key"]] = message["current_value"]

#         click.echo(json.dumps(Blackboard.blackboard_state, indent=4))

#     node.create_subscription("blackboard_activity", echo_callback)
#     node.spin()


if __name__ == "__main__":
    main()
