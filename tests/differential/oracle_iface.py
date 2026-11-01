"""Black-box access to the python-dotenv 1.2.4 oracle for differential tests.

Puts the oracle (and its bundled click) on ``sys.path`` and imports ``dotenv``.
Exposes availability/version checks so the suite can skip cleanly when the oracle
is absent or the interpreter does not match what the oracle was built for, and
turn those skips into failures under ``ENVRELAY_REQUIRE_ORACLE=1``.

Only the public API and (for CliRunner) ``dotenv.cli.cli`` are touched. No
inspection of oracle objects, and no import of any other ``dotenv.`` submodule.
"""

from __future__ import annotations

import importlib.util
import os
import sys

ORACLE_DIR = os.environ.get(
    "ENVRELAY_ORACLE_DIR", os.path.expanduser("~/envrelay-oracle")
)


def _recorded_python():
    path = os.path.join(ORACLE_DIR, "ORACLE_PYTHON.txt")
    with open(path) as handle:
        first = handle.readline().split()
    # "<major> <minor> <magic-hex>"
    return int(first[0]), int(first[1]), first[2]


def availability():
    """Return (ok, reason). ok is False with a reason when unusable."""
    if not os.path.isdir(ORACLE_DIR):
        return False, "oracle directory %s not found" % ORACLE_DIR
    try:
        major, minor, magic = _recorded_python()
    except OSError as exc:
        return False, "cannot read ORACLE_PYTHON.txt: %s" % exc
    if sys.version_info[:2] != (major, minor):
        return False, "interpreter %s != oracle %d.%d" % (
            ".".join(map(str, sys.version_info[:2])),
            major,
            minor,
        )
    if importlib.util.MAGIC_NUMBER.hex() != magic:
        return False, "bytecode magic %s != oracle %s" % (
            importlib.util.MAGIC_NUMBER.hex(),
            magic,
        )
    return True, ""


def _ensure_path():
    for part in (ORACLE_DIR, os.path.join(ORACLE_DIR, "deps")):
        if part not in sys.path:
            sys.path.insert(0, part)


def load():
    """Import and return the oracle ``dotenv`` module, asserting its location."""
    _ensure_path()
    import dotenv

    assert dotenv.__file__.startswith(ORACLE_DIR), (
        "oracle dotenv.__file__ is not under the oracle dir: %s" % dotenv.__file__
    )
    return dotenv


def load_cli_group():
    """Return the oracle's click group, only for use as a CliRunner target."""
    _ensure_path()
    from dotenv.cli import cli  # noqa: WPS433  (allowlisted single import)

    return cli
