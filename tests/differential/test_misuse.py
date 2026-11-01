"""Differential tests for API misuse (channel 10).

Wrong argument types, missing files, directories where files are expected,
invalid quote_mode, unknown keyword arguments, binary streams, and embedded NULs
must raise the same exception class and message as the oracle (or return the same
value). Oracle exceptions are caught in-process and compared as (class, message);
no traceback is printed.
"""

from __future__ import annotations

import io
import os
import pathlib
import shutil
import tempfile

import envrelay


def _outcome(fn):
    try:
        return ("ok", repr(fn()))
    except BaseException as exc:  # noqa: BLE001
        return ("exc", type(exc).__name__, str(exc))


def _both(oracle, make):
    """make(module) performs the call; compare outcome on envrelay vs oracle."""
    return _outcome(lambda: make(envrelay)), _outcome(lambda: make(oracle))


def _norm(outcome, directory):
    if outcome[0] == "exc":
        return (outcome[0], outcome[1], outcome[2].replace(directory, "<DIR>"))
    return outcome


def test_misuse_readers(oracle):
    d = tempfile.mkdtemp()
    adir = os.path.join(d, "adir")
    os.mkdir(adir)
    afile = os.path.join(d, "f.env")
    with open(afile, "w") as fh:
        fh.write("A=1\n")
    try:
        cases = [
            ("int path", lambda m: m.dotenv_values(123)),
            ("bytes path", lambda m: m.dotenv_values(b"nope")),
            ("Path ok", lambda m: m.dotenv_values(pathlib.Path(afile))),
            ("Path missing", lambda m: m.dotenv_values(pathlib.Path(d) / "no.env")),
            ("binary stream", lambda m: m.dotenv_values(stream=io.BytesIO(b"A=1"))),
            ("dir as file", lambda m: m.dotenv_values(adir)),
            ("unknown kwarg", lambda m: m.dotenv_values(bogus=1)),
            ("load int", lambda m: m.load_dotenv(123)),
            ("load binary stream", lambda m: m.load_dotenv(stream=io.BytesIO(b"A=1"))),
            ("load Path", lambda m: m.load_dotenv(pathlib.Path(afile))),
            ("get_key dir", lambda m: m.get_key(adir, "A")),
            ("get_key int key", lambda m: m.get_key(afile, 123)),
        ]
        for label, make in cases:
            mine, ora = _both(oracle, make)
            assert _norm(mine, d) == _norm(ora, d), "%s: mine=%r ora=%r" % (
                label,
                mine,
                ora,
            )
    finally:
        shutil.rmtree(d)


def test_misuse_editing(oracle):
    for label, make in [
        ("set None value", lambda m: _set(m, "K", None)),
        ("set bogus quote", lambda m: _set(m, "K", "v", quote_mode="bogus")),
        ("set int value", lambda m: _set(m, "K", 123)),
        ("set unknown kwarg", lambda m: _set(m, "K", "v", bogus=1)),
        ("unset bogus quote", lambda m: _unset(m, "A", quote_mode="bogus")),
        ("set missing dir", lambda m: m.set_key("/nonexistent/dir/.env", "A", "x")),
    ]:
        # Each needs its own temp file; run per module inside the lambda via _set.
        mine = _outcome(lambda: make(envrelay))
        ora = _outcome(lambda: make(oracle))
        assert _strip_paths(mine) == _strip_paths(ora), "%s: mine=%r ora=%r" % (
            label,
            mine,
            ora,
        )


def _set(module, key, value, **kw):
    d = tempfile.mkdtemp()
    try:
        return module.set_key(os.path.join(d, ".env"), key, value, **kw)
    finally:
        shutil.rmtree(d)


def _unset(module, key, **kw):
    d = tempfile.mkdtemp()
    try:
        with open(os.path.join(d, ".env"), "w") as fh:
            fh.write("A=1\n")
        return module.unset_key(os.path.join(d, ".env"), key, **kw)
    finally:
        shutil.rmtree(d)


def _strip_paths(outcome):
    if outcome[0] == "exc":
        import re

        msg = re.sub(r"/[^ ']*\.tmp_[A-Za-z0-9_]+", "<TMP>", outcome[2])
        return (outcome[0], outcome[1], msg)
    return outcome


def test_embedded_nul_partial(oracle):
    text = "A=1\nB=x\x00y\nC=3\n"
    results = {}
    for name, module in (("mine", envrelay), ("ora", oracle)):
        saved = dict(os.environ)
        for k in ("A", "B", "C"):
            os.environ.pop(k, None)
        outcome = _outcome(lambda: module.load_dotenv(stream=io.StringIO(text)))
        env = {k: os.environ.get(k) for k in ("A", "B", "C")}
        os.environ.clear()
        os.environ.update(saved)
        results[name] = (outcome, env)
    assert results["mine"] == results["ora"], results
