"""Extra differential tests for file editing (channel 4).

Covers gaps not reached by the generated editing sequences:

* ``set_key`` with an ``encoding`` that cannot represent the value -- the raised
  exception (class + message, including the byte position) must match, and no
  temporary file may be left behind (checked via the directory listing);
* ``get_key`` / ``unset_key`` on a key written with no ``=`` (value ``None``);
* editing a read-only existing file -- the file is still rewritten (new inode),
  its mode is preserved, and the result matches the oracle.
"""

from __future__ import annotations

import os
import shutil
import tempfile

import diff_helpers
import oracle_iface
import pytest

import envrelay

_OK, _REASON = oracle_iface.availability()
pytestmark = pytest.mark.skipif(not _OK, reason=_REASON)


# --- unencodable values: error + no leftover temp file -----------------------

_UNENC = [
    ("ascii nonascii", "é1", "ascii"),
    ("ascii emoji", "smile\U0001f642", "ascii"),
    ("latin1 cjk", "中", "latin-1"),
    ("ascii in key ok value bad", "ÿ", "ascii"),
]


@pytest.mark.parametrize("label,value,encoding", _UNENC, ids=[c[0] for c in _UNENC])
def test_set_key_unencodable_value_new_file(label, value, encoding):
    # On a new (empty) file the only line is the one being written, so the
    # UnicodeEncodeError's position matches on both sides, and no temp file is
    # left behind.
    op = ("set_key", "K", value, "always", False, encoding, False)
    ok, summaries = diff_helpers.compare_edit_sequence(None, [op])
    assert ok, "%s new file: mine=%r ora=%r" % (
        label,
        summaries["mine"],
        summaries["ora"],
    )


@pytest.mark.parametrize("label,value,encoding", _UNENC, ids=[c[0] for c in _UNENC])
def test_set_key_unencodable_value_existing_file(label, value, encoding):
    # set_key writes each rendered binding/preserved span separately, so when the
    # encoding cannot represent a value the UnicodeEncodeError's reported position
    # is relative to the offending piece (matching the reference), not the whole
    # file -- including when the bad value spans a newline.
    op = ("set_key", "K", value, "always", False, encoding, False)
    ok, summaries = diff_helpers.compare_edit_sequence(b"FIRST=longvalue\n", [op])
    assert ok, "%s existing file: mine=%r ora=%r" % (
        label,
        summaries["mine"],
        summaries["ora"],
    )


# --- get_key / unset_key on a key with value None (no '=') -------------------

_NO_EQ_INITIALS = [
    b"A\nB=2\n",
    b"export A\nB=2\n",
    b"A\n",
    b"A \nB=2\n",
]


@pytest.mark.parametrize(
    "initial", _NO_EQ_INITIALS, ids=[repr(i) for i in _NO_EQ_INITIALS]
)
def test_get_key_on_valueless_key(initial):
    ok, summaries = diff_helpers.compare_edit_sequence(initial, [("get_key", "A")])
    assert ok, "get_key none initial=%r: mine=%r ora=%r" % (
        initial,
        summaries["mine"],
        summaries["ora"],
    )


@pytest.mark.parametrize(
    "initial", _NO_EQ_INITIALS, ids=[repr(i) for i in _NO_EQ_INITIALS]
)
def test_unset_key_on_valueless_key(initial):
    op = ("unset_key", "A", "always", "utf-8", False)
    ok, summaries = diff_helpers.compare_edit_sequence(initial, [op])
    assert ok, "unset none initial=%r: mine=%r ora=%r" % (
        initial,
        summaries["mine"],
        summaries["ora"],
    )


# --- read-only existing file -------------------------------------------------


def _edit_readonly(module, initial, op, perms):
    d = tempfile.mkdtemp()
    path = os.path.join(d, ".env")
    with open(path, "wb") as fh:
        fh.write(initial)
    os.chmod(path, perms)
    before_ino = os.stat(path).st_ino
    try:
        try:
            ret = ("ok", repr(getattr(module, op[0])(path, *op[1:])))
        except BaseException as exc:  # noqa: BLE001
            ret = ("exc", "%s: %s" % (type(exc).__name__, exc))
        after = None
        after_mode = None
        after_ino = None
        if os.path.exists(path):
            st = os.stat(path)
            after_mode = oct(st.st_mode & 0o777)
            after_ino = st.st_ino
            with open(path, "rb") as fh:
                after = fh.read()
        leftovers = sorted(n for n in os.listdir(d) if n != ".env")
        inode_changed = before_ino != after_ino
        return (ret, after, after_mode, inode_changed, leftovers)
    finally:
        os.chmod(path, 0o700) if os.path.exists(path) else None
        shutil.rmtree(d, ignore_errors=True)


@pytest.mark.parametrize("perms", [0o400, 0o444, 0o600, 0o640])
def test_set_key_readonly_existing(oracle, perms):
    initial = b"A=1\nB=2\n"
    op = ("set_key", "C", "hi", "always", False, "utf-8", False)
    mine = _edit_readonly(envrelay, initial, op, perms)
    ora = _edit_readonly(oracle, initial, op, perms)
    assert mine == ora, "perms=%s: mine=%r ora=%r" % (oct(perms), mine, ora)
