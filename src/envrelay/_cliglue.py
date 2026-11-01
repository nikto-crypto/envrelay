"""Mechanics behind the command line that need the OS or process control.

This module holds no user-facing prose (those strings live in
``_commandline``). It opens files with the locale's default encoding, parses
their text, and replaces the current process for ``run``. It may use click only
for control flow; the core library never imports it.
"""

from __future__ import annotations

import os
from collections import OrderedDict

from . import _interpolate
from ._core import load_into_environ, logger
from ._parsing import parse


def read_values(path: str, interpolate: bool = True) -> OrderedDict:
    """Open ``path`` with the locale's default encoding and parse it.

    Raises the underlying ``OSError`` (missing file, directory, ...) or
    ``UnicodeDecodeError`` to the caller; both are surfaced by the command line.
    Text-mode reading folds all line endings to LF before parsing.
    """
    with open(path) as handle:  # locale default encoding, universal newlines
        text = handle.read()
    result = parse(text)
    for line in result.error_lines:
        logger.warning(
            "python-dotenv could not parse statement starting at line %s", line
        )
    if interpolate:
        return _interpolate.resolve(result.entries, os.environ)
    return _interpolate.resolve_plain(result.entries)


def load_for_run(path: str, override: bool) -> None:
    """Apply the env file to ``os.environ`` for ``run`` (ignores the disable flag)."""
    load_into_environ(path, override=override, encoding="utf-8")


def replace_process(commandline) -> None:
    """Replace the current process image with ``commandline``.

    Returns only on failure; ``FileNotFoundError`` means the command was not
    found, other OS errors propagate.
    """
    os.execvpe(commandline[0], list(commandline), os.environ)
