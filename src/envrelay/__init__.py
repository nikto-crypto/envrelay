"""envrelay -- read, load, and edit ``.env`` files.

A small, dependency-free library for working with environment files. The public
surface mirrors a well-known contract: parse an env file into a mapping, push it
into ``os.environ``, read and edit individual keys, and locate the nearest file.
"""

from __future__ import annotations

from ._core import (
    dotenv_values,
    find_dotenv,
    get_cli_string,
    load_dotenv,
)
from ._editing import get_key, set_key, unset_key
from ._magic import load_ipython_extension

__all__ = [
    "dotenv_values",
    "find_dotenv",
    "get_cli_string",
    "get_key",
    "load_dotenv",
    "load_ipython_extension",
    "set_key",
    "unset_key",
]
