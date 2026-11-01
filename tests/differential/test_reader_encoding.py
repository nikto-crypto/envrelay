"""Differential tests for reading files in non-UTF-8 encodings (channels 1-3).

The existing reader tests always read UTF-8. Here we write raw bytes and read
them back through ``dotenv_values``/``load_dotenv`` with a range of ``encoding``
values -- matching and mismatching the bytes -- comparing the parsed result, the
log records, and any raised exception (class + message) against the oracle.
"""

from __future__ import annotations

import logging
import os
import shutil
import tempfile

import oracle_iface
import pytest

import envrelay

_OK, _REASON = oracle_iface.availability()
pytestmark = pytest.mark.skipif(not _OK, reason=_REASON)


class _Cap(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append((record.levelname, record.getMessage()))


def _attach(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    cap = _Cap()
    logger.addHandler(cap)
    logger.propagate = False
    return cap


_MINE = _attach("envrelay")
_ORA = _attach("dotenv")


def _capture(cap, fn):
    cap.records.clear()
    try:
        value = ("ok", repr(fn()))
    except BaseException as exc:  # noqa: BLE001
        value = ("exc", "%s: %s" % (type(exc).__name__, exc))
    return value, list(cap.records)


# (label, raw bytes, encoding to read with)
CASES = [
    ("latin1 match", "A=café\nB=2\n".encode("latin-1"), "latin-1"),
    ("latin1 as utf8", "A=café\n".encode("latin-1"), "utf-8"),
    ("utf16 match", "A=café\nB=hi\n".encode("utf-16"), "utf-16"),
    ("utf16 as utf8", "A=café\n".encode("utf-16"), "utf-8"),
    ("cp1252 match", "A=“quoted”\n".encode("cp1252"), "cp1252"),
    ("cp1252 as latin1", "A=“quoted”\n".encode("cp1252"), "latin-1"),
    ("utf8 bom as utf8", "﻿A=1\n".encode(), "utf-8"),
    ("utf8 bom as utf8-sig", "﻿A=1\n".encode(), "utf-8-sig"),
    ("utf16le interp", "A=1\nB=${A}\n".encode("utf-16-le"), "utf-16-le"),
    ("raw highbytes as utf8", b"A=1\nB=\xff\xfe\nC=3\n", "utf-8"),
    ("raw highbytes as latin1", b"A=1\nB=\xff\xfe\nC=3\n", "latin-1"),
    ("ascii strict", b"A=1\nB=xy\n", "ascii"),
    ("nonascii as ascii", "A=é\n".encode(), "ascii"),
]


@pytest.mark.parametrize("label,raw,encoding", CASES, ids=[c[0] for c in CASES])
def test_dotenv_values_encoding(oracle, label, raw, encoding):
    d = tempfile.mkdtemp()
    path = os.path.join(d, ".env")
    with open(path, "wb") as fh:
        fh.write(raw)
    try:
        mine = _capture(_MINE, lambda: envrelay.dotenv_values(path, encoding=encoding))
        ora = _capture(_ORA, lambda: oracle.dotenv_values(path, encoding=encoding))
    finally:
        shutil.rmtree(d)
    # Normalize any path appearing in messages/exceptions.
    mine = _strip(mine, d)
    ora = _strip(ora, d)
    assert mine == ora, "%s: mine=%r ora=%r" % (label, mine, ora)


@pytest.mark.parametrize("label,raw,encoding", CASES, ids=[c[0] for c in CASES])
def test_load_dotenv_encoding(oracle, label, raw, encoding):
    d = tempfile.mkdtemp()
    path = os.path.join(d, ".env")
    with open(path, "wb") as fh:
        fh.write(raw)
    probe = ("A", "B", "C")
    results = {}
    for name, module, cap in (("mine", envrelay, _MINE), ("ora", oracle, _ORA)):
        saved = dict(os.environ)
        for k in probe:
            os.environ.pop(k, None)
        outcome = _capture(cap, lambda m=module: m.load_dotenv(path, encoding=encoding))
        env = {k: os.environ.get(k) for k in probe}
        os.environ.clear()
        os.environ.update(saved)
        results[name] = (_strip(outcome, d), env)
    shutil.rmtree(d)
    assert results["mine"] == results["ora"], "%s: %r" % (label, results)


def _strip(captured, directory):
    value, logs = captured
    value = tuple(
        v.replace(directory, "<DIR>") if isinstance(v, str) else v for v in value
    )
    logs = [(lvl, msg.replace(directory, "<DIR>")) for (lvl, msg) in logs]
    return value, logs
