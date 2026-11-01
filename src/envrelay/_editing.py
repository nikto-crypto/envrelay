"""Read and edit individual keys in an env file.

Writes are atomic: a sibling temporary file (named ``.tmp_<random>``) is created
in the destination directory, written, given the destination's permissions, and
renamed into place, so a crash can never leave a half-written file. A symlink is
replaced by a regular file unless ``follow_symlinks`` is set, in which case the
link's target is edited in place.
"""

from __future__ import annotations

import logging
import os
import re
import tempfile

from ._core import dotenv_values
from ._parsing import normalize_newlines, scan

logger = logging.getLogger("envrelay.main")

_VALID_QUOTE_MODES = ("always", "auto", "never")
# In "auto" mode a value is left unquoted only when it is a non-empty run of
# alphanumerics (Unicode letters/digits allowed, but not "_").
_BARE_OK = re.compile(r"\A[^\W_]+\Z")


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _format_value(value, quote_mode: str) -> str:
    if quote_mode == "never":
        return value
    if quote_mode == "always":
        return "'" + _escape(value) + "'"
    if quote_mode == "auto":
        if _BARE_OK.match(value):
            return value
        return "'" + _escape(value) + "'"
    raise ValueError("Unknown quote_mode: %s" % quote_mode)


def _log_parse_warnings(error_lines) -> None:
    for line in error_lines:
        logger.warning(
            "python-dotenv could not parse statement starting at line %s", line
        )


def _read_existing(path: str, encoding: str | None) -> str | None:
    # A path that exists is opened directly, so a directory raises
    # IsADirectoryError (as the reference does) rather than being treated as
    # empty. A missing path means "start from nothing".
    if not os.path.exists(path):
        return None
    with open(path, encoding=encoding) as handle:
        return normalize_newlines(handle.read())


def _atomic_write(
    link_path: str, write_path: str, pieces, encoding: str | None
) -> None:
    directory = os.path.dirname(write_path) or os.curdir
    # Keep the mode of an existing regular file; a brand-new file -- including one
    # that replaces a symlink -- gets 0o600.
    if os.path.exists(write_path) and not os.path.islink(write_path):
        mode = os.stat(write_path).st_mode & 0o777
    else:
        mode = 0o600
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".tmp_")
    try:
        with os.fdopen(fd, "w", encoding=encoding, newline="") as handle:
            # Each piece (one rendered binding or one preserved span) is written
            # separately, so an encoding error's reported position is relative to
            # the offending piece rather than the whole file.
            for piece in pieces:
                handle.write(piece)
        os.chmod(tmp, mode)
        os.replace(tmp, write_path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _rewrite_pieces(segments, key, replacement):
    """Build the output pieces for editing ``key``.

    Each binding of ``key`` is replaced by ``replacement`` (a rendered line), or
    dropped when ``replacement`` is None (unset). In both cases the contiguous run
    of blank / whitespace-only lines *directly* above that binding is also
    removed, matching the reference (comment lines are kept and break the run).
    Returns ``(pieces, replaced)``.
    """
    pieces = []
    replaced = False
    for seg in segments:
        if seg.kind == "bind" and seg.key == key:
            while pieces and pieces[-1].strip() == "":
                pieces.pop()
            if replacement is not None:
                pieces.append(replacement)
            replaced = True
        else:
            pieces.append(seg.text)
    return pieces, replaced


def set_key(
    dotenv_path,
    key_to_set,
    value_to_set,
    quote_mode="always",
    export=False,
    encoding="utf-8",
    follow_symlinks=False,
):
    """Set ``key_to_set`` to ``value_to_set`` in the file, returning a 3-tuple.

    Every existing line for the key is rewritten; if the key is absent a new
    line is appended. The whole file is rewritten with LF endings.
    """
    formatted = _format_value(value_to_set, quote_mode)
    new_line = ("export " if export else "") + key_to_set + "=" + formatted + "\n"

    write_path = os.path.realpath(dotenv_path) if follow_symlinks else dotenv_path
    content = _read_existing(dotenv_path, encoding)
    scanned = scan(content if content is not None else "")
    _log_parse_warnings(scanned.error_lines)

    pieces, replaced = _rewrite_pieces(scanned.segments, key_to_set, new_line)
    if not replaced:
        joined = "".join(pieces)
        if joined and not joined.endswith("\n"):
            pieces.append("\n")
        pieces.append(new_line)

    _atomic_write(dotenv_path, write_path, pieces, encoding)
    return True, key_to_set, value_to_set


def unset_key(
    dotenv_path,
    key_to_unset,
    quote_mode="always",
    encoding="utf-8",
    follow_symlinks=False,
):
    """Remove every line for ``key_to_unset`` from the file.

    Returns ``(True, key)`` on removal, ``(None, key)`` if the key or file is
    absent. ``quote_mode`` is accepted but ignored.
    """
    if not os.path.exists(dotenv_path):
        logger.warning("Can't delete from %s - it doesn't exist.", dotenv_path)
        return None, key_to_unset

    write_path = os.path.realpath(dotenv_path) if follow_symlinks else dotenv_path
    content = _read_existing(dotenv_path, encoding)
    scanned = scan(content if content is not None else "")
    _log_parse_warnings(scanned.error_lines)

    # The file is rewritten whether or not the key was present (so an absent-key
    # unset still produces a fresh file / replaces a symlink), matching the
    # reference. Removing a key also removes the blank lines directly above it.
    pieces, present = _rewrite_pieces(scanned.segments, key_to_unset, None)
    _atomic_write(dotenv_path, write_path, pieces, encoding)
    if present:
        return True, key_to_unset
    logger.warning(
        "Key %s not removed from %s - key doesn't exist.",
        key_to_unset,
        dotenv_path,
    )
    return None, key_to_unset


def get_key(dotenv_path, key_to_get, encoding="utf-8"):
    """Return the (interpolated) value of ``key_to_get`` or ``None``."""
    values = dotenv_values(dotenv_path, verbose=True, encoding=encoding)
    if key_to_get in values:
        return values[key_to_get]
    logger.warning("Key %s not found in %s.", key_to_get, dotenv_path)
    return None
