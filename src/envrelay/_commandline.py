"""The ``envrelay`` command line (click).

This module is the single home for the command-line declarations and every
string the CLI prints: help text, command and option descriptions, and error
messages. It is reproduced from the reference's actual ``--help`` and error
output, and is listed in PROVENANCE.md so a similarity check can treat it
separately. Mechanics (reading files, replacing the process) live in
``_cliglue``; the parsing/editing logic lives in the core library.
"""

from __future__ import annotations

import json
import os
import shlex

import click

from . import _cliglue
from ._editing import set_key, unset_key
from ._version import VERSION

# Fixed when this module is imported, so the default reflects the working
# directory at import time (matching the reference).
_DEFAULT_FILE = os.path.join(os.getcwd(), ".env")


@click.group()
@click.option(
    "-f",
    "--file",
    default=_DEFAULT_FILE,
    type=click.Path(file_okay=True),
    help="Location of the .env file, defaults to .env file in current working "
    "directory.",
)
@click.option(
    "-q",
    "--quote",
    default="always",
    type=click.Choice(["always", "never", "auto"]),
    help="Whether to quote or not the variable values. Default mode is always. "
    "This does not affect parsing.",
)
@click.option(
    "-e",
    "--export",
    default=False,
    type=click.BOOL,
    help="Whether to write the dot file as an executable bash script.",
)
@click.version_option(version=VERSION)
@click.pass_context
def cli(ctx, file, quote, export):
    """This script is used to set, get or unset values from a .env file."""
    ctx.obj = {"FILE": file, "QUOTE": quote, "EXPORT": export}


@cli.command("list")
@click.option(
    "--format",
    "output_format",
    default="simple",
    type=click.Choice(["simple", "json", "shell", "export"]),
    help="The format in which to display the list. Default format is simple, "
    "which displays name=value without quotes.",
)
@click.pass_context
def list_command(ctx, output_format):
    """Display all the stored key/value."""
    file = ctx.obj["FILE"]
    try:
        values = _cliglue.read_values(file)
    except OSError as exc:
        click.echo("Error opening env file: %s" % exc, err=True)
        ctx.exit(2)
    if output_format == "json":
        click.echo(json.dumps(values, indent=2, sort_keys=True))
        return
    for key in sorted(values):
        value = values[key]
        if value is None:
            continue
        if output_format == "shell":
            click.echo("%s=%s" % (key, shlex.quote(value)))
        elif output_format == "export":
            click.echo("export %s=%s" % (key, shlex.quote(value)))
        else:
            # "simple" and any other value (e.g. None passed via CliRunner).
            click.echo("%s=%s" % (key, value))


@cli.command("get")
@click.argument("key", required=True)
@click.pass_context
def get_command(ctx, key):
    """Retrieve the value for the given key."""
    file = ctx.obj["FILE"]
    try:
        values = _cliglue.read_values(file)
    except OSError as exc:
        click.echo("Error opening env file: %s" % exc, err=True)
        ctx.exit(2)
    if key in values and values[key] is not None:
        click.echo(values[key])
    else:
        ctx.exit(1)


@cli.command("set")
@click.argument("key", required=True)
@click.argument("value", required=True)
@click.pass_context
def set_command(ctx, key, value):
    """Store the given key/value.

    This doesn't follow symlinks, to avoid accidentally modifying a file at a
    potentially untrusted path.
    """
    file = ctx.obj["FILE"]
    quote = ctx.obj["QUOTE"]
    export = ctx.obj["EXPORT"]
    success, set_key_name, set_value = set_key(
        file, key, value, quote_mode=quote, export=export, encoding="utf-8"
    )
    if success:
        click.echo("%s=%s" % (set_key_name, set_value))


@cli.command("unset")
@click.argument("key", required=True)
@click.pass_context
def unset_command(ctx, key):
    """Removes the given key.

    This doesn't follow symlinks, to avoid accidentally modifying a file at a
    potentially untrusted path.
    """
    file = ctx.obj["FILE"]
    quote = ctx.obj["QUOTE"]
    success, unset_key_name = unset_key(file, key, quote_mode=quote, encoding="utf-8")
    if success:
        click.echo("Successfully removed %s" % unset_key_name)
    else:
        ctx.exit(1)


@cli.command(
    "run",
    # Stop option parsing at the first token of the command, so every option
    # after the command name (including --help) is passed to the command, while
    # "run --help" with no command still shows run's own help.
    context_settings={
        "ignore_unknown_options": True,
        "allow_interspersed_args": False,
    },
)
@click.option(
    "--override/--no-override",
    default=True,
    help="Override variables from the environment file with those from the .env file.",
)
@click.argument("commandline", nargs=-1, type=click.UNPROCESSED)
@click.pass_context
def run_command(ctx, override, commandline):
    """Run command with environment variables present."""
    file = ctx.obj["FILE"]
    if not os.path.isfile(file):
        raise click.UsageError(
            "Invalid value: Invalid value for '-f' \"%s\" does not exist." % file
        )
    _cliglue.load_for_run(file, override)
    if not commandline:
        click.echo("No command given.")
        ctx.exit(1)
    try:
        _cliglue.replace_process(commandline)
    except FileNotFoundError:
        click.echo("Command not found: %s" % commandline[0], err=True)
        ctx.exit(1)
