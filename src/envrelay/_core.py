"""Public reading, loading, locating, and helper functions.

This module never imports click or anything about the oracle. It depends only on
the standard library and the sibling parsing/interpolation modules.
"""

from __future__ import annotations

import logging
import os
import sys
from collections import OrderedDict
from collections.abc import Iterator

from . import _interpolate
from ._parsing import normalize_newlines, parse

logger = logging.getLogger("envrelay.main")

# Values of PYTHON_DOTENV_DISABLED (compared case-insensitively) that turn off
# loading. Note that surrounding spaces, "on", and "0" do NOT count.
_DISABLED_VALUES = frozenset({"1", "t", "true", "y", "yes"})


def _disabled() -> bool:
    raw = os.environ.get("PYTHON_DOTENV_DISABLED")
    if raw is None:
        return False
    return raw.lower() in _DISABLED_VALUES


def _read_text_from_path(path: str, encoding: str | None) -> str:
    with open(path, encoding=encoding) as handle:
        return normalize_newlines(handle.read())


def _collect(
    dotenv_path, stream, verbose: bool, encoding: str | None
) -> tuple[list, list] | None:
    """Return (entries, error_lines) or None when no source could be read.

    A stream, when supplied, is used only if the path is not a real file; text
    from a stream keeps its original line endings, while text from a file has
    CR/CRLF folded to LF.
    """
    if dotenv_path and os.path.isfile(dotenv_path):
        text = _read_text_from_path(dotenv_path, encoding)
    elif stream is not None:
        text = stream.read()
    else:
        if verbose:
            name = dotenv_path if dotenv_path else ".env"
            logger.info("python-dotenv could not find configuration file %s.", name)
        return None
    result = parse(text)
    for line in result.error_lines:
        logger.warning(
            "python-dotenv could not parse statement starting at line %s", line
        )
    return result.entries, result.error_lines


def dotenv_values(
    dotenv_path=None,
    stream=None,
    verbose=False,
    interpolate=True,
    encoding="utf-8",
):
    """Parse an env source and return an ``OrderedDict`` of its values.

    Nothing is written to ``os.environ``. A key given with no ``=`` maps to
    ``None``. With ``interpolate`` on, ``${...}`` references are expanded against
    earlier values and then ``os.environ``.
    """
    if not dotenv_path and stream is None:
        dotenv_path = find_dotenv()
    collected = _collect(dotenv_path, stream, verbose, encoding)
    if collected is None:
        return OrderedDict()
    entries, _ = collected
    if interpolate:
        return _interpolate.resolve(entries, os.environ)
    return _interpolate.resolve_plain(entries)


def load_dotenv(
    dotenv_path=None,
    stream=None,
    verbose=False,
    override=False,
    interpolate=True,
    encoding="utf-8",
):
    """Parse an env source and set the results into ``os.environ``.

    Returns ``True`` when a source was read, ``False`` otherwise. Existing
    variables are preserved unless ``override`` is true. Keys whose value is
    ``None`` are skipped.
    """
    if _disabled():
        logger.debug(
            "python-dotenv: .env loading disabled by "
            "PYTHON_DOTENV_DISABLED environment variable"
        )
        return False
    return load_into_environ(
        dotenv_path, stream, verbose, override, interpolate, encoding
    )


def load_into_environ(
    dotenv_path=None,
    stream=None,
    verbose=False,
    override=False,
    interpolate=True,
    encoding="utf-8",
):
    """Read a source and apply it to ``os.environ`` (no disabled-flag check).

    Shared by ``load_dotenv`` and the command line's ``run``, which ignores
    ``PYTHON_DOTENV_DISABLED``.
    """
    if not dotenv_path and stream is None:
        dotenv_path = find_dotenv()
    collected = _collect(dotenv_path, stream, verbose, encoding)
    if collected is None:
        return False
    entries, _ = collected
    _apply_to_environ(entries, override, interpolate)
    # True when the source yielded at least one key (even a value-less one),
    # False for an empty / comment-only / unparsable source.
    return bool(entries)


def _apply_to_environ(entries, override: bool, interpolate: bool) -> None:
    # Resolve every entry into a last-wins mapping first (interpolation reads the
    # current os.environ, with precedence depending on override), then write it
    # out. Writing can raise part-way (e.g. an embedded NUL), leaving the keys
    # resolved before it already set.
    resolved = _resolve_for_load(entries, override, interpolate)
    for key, value in resolved.items():
        if value is None:
            continue
        if override or key not in os.environ:
            os.environ[key] = value


def _resolve_for_load(entries, override: bool, interpolate: bool) -> OrderedDict:
    out: OrderedDict = OrderedDict()
    for name, value in entries:
        if value is None or not interpolate:
            out[name] = value
            continue

        def lookup(ref: str):
            env_has = ref in os.environ
            local = out.get(ref)
            local_has = ref in out  # present even when the value is None
            if override:
                if local_has:
                    return True, local
                if env_has:
                    return True, os.environ[ref]
            else:
                if env_has:
                    return True, os.environ[ref]
                if local_has:
                    return True, local
            return False, None

        out[name] = _interpolate.expand(value, lookup)
    return out


# --- locating ----------------------------------------------------------------


def _ascend(start: str) -> Iterator[str]:
    """Yield ``start`` and each parent directory up to the filesystem root."""
    current = os.path.abspath(start)
    while True:
        yield current
        parent = os.path.dirname(current)
        if parent == current:
            return
        current = parent


def _running_interactively() -> bool:
    main = sys.modules.get("__main__")
    return not hasattr(main, "__file__")


def find_dotenv(filename=".env", raise_error_if_not_found=False, usecwd=False):
    """Search upward for ``filename`` and return its absolute path or ``''``.

    The search begins at the caller's directory (walking the call stack past this
    package), or at the working directory when ``usecwd`` is set, when the
    program is frozen, or when running interactively.
    """
    if usecwd or getattr(sys, "frozen", False) or _running_interactively():
        start = os.getcwd()
    else:
        frame = sys._getframe()
        here = __file__
        while frame is not None and (
            frame.f_code.co_filename == here
            or not os.path.exists(frame.f_code.co_filename)
        ):
            frame = frame.f_back
        assert frame is not None
        start = os.path.dirname(os.path.abspath(frame.f_code.co_filename))

    for directory in _ascend(start):
        candidate = os.path.join(directory, filename)
        if os.path.isfile(candidate):
            return candidate

    if raise_error_if_not_found:
        raise OSError("File not found")
    return ""


# --- CLI string helper -------------------------------------------------------


def get_cli_string(path=None, action=None, key=None, value=None, quote=None):
    """Build the command-line string equivalent to the given operation."""
    parts = ["dotenv"]
    if quote:
        parts.append("-q %s" % quote)
    if path:
        parts.append("-f %s" % path)
    if action:
        parts.append(action)
        if key:
            parts.append(key)
            if value:
                if " " in value:
                    parts.append('"%s"' % value)
                else:
                    parts.append(value)
    return " ".join(parts).strip()
