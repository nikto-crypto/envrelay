"""Helpers to run the same input through envrelay and the oracle and compare.

Comparisons cover return values (by repr), log records (level + message, in
order), and -- for loading -- the exact effect on ``os.environ``.
"""

from __future__ import annotations

import io
import logging
import os
import shutil
import tempfile

import oracle_iface

import envrelay

_dotenv = None


def dotenv():
    global _dotenv
    if _dotenv is None:
        _dotenv = oracle_iface.load()
    return _dotenv


class _Capture(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append((record.levelname, record.getMessage()))


def _attach(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    cap = _Capture()
    logger.addHandler(cap)
    logger.propagate = False
    return logger, cap


_MINE_LOG, _MINE_CAP = _attach("envrelay")
_ORA_LOG, _ORA_CAP = _attach("dotenv")


def _run_capturing(cap, fn):
    cap.records.clear()
    try:
        value = ("ok", repr(fn()))
    except BaseException as exc:  # noqa: BLE001
        value = ("exc", "%s: %s" % (type(exc).__name__, exc))
    return value, list(cap.records)


def _write_temp(text, encoding="utf-8"):
    fd, path = tempfile.mkstemp()
    with os.fdopen(fd, "wb") as handle:
        handle.write(text.encode(encoding, "surrogatepass"))
    return path


def compare_dotenv_values(text, interpolate, via_file, encoding="utf-8"):
    """Return (ok, detail) comparing dotenv_values via stream or file."""
    if via_file:
        path = _write_temp(text, encoding)
        try:
            mine = _run_capturing(
                _MINE_CAP,
                lambda: envrelay.dotenv_values(
                    path, interpolate=interpolate, encoding=encoding
                ),
            )
            ora = _run_capturing(
                _ORA_CAP,
                lambda: dotenv().dotenv_values(
                    path, interpolate=interpolate, encoding=encoding
                ),
            )
        finally:
            os.unlink(path)
    else:
        mine = _run_capturing(
            _MINE_CAP,
            lambda: envrelay.dotenv_values(
                stream=io.StringIO(text), interpolate=interpolate
            ),
        )
        ora = _run_capturing(
            _ORA_CAP,
            lambda: dotenv().dotenv_values(
                stream=io.StringIO(text), interpolate=interpolate
            ),
        )
    ok = mine == ora
    return ok, (mine, ora)


def compare_load_dotenv(text, override, interpolate, verbose, base_env):
    """Compare load_dotenv's return, logs, and os.environ effect via a stream."""
    saved = dict(os.environ)

    def reset():
        os.environ.clear()
        os.environ.update(base_env)

    reset()
    mine_ret = _run_capturing(
        _MINE_CAP,
        lambda: envrelay.load_dotenv(
            stream=io.StringIO(text),
            override=override,
            interpolate=interpolate,
            verbose=verbose,
        ),
    )
    mine_env = {k: os.environ.get(k) for k in _interesting_keys(base_env, text)}

    reset()
    ora_ret = _run_capturing(
        _ORA_CAP,
        lambda: dotenv().load_dotenv(
            stream=io.StringIO(text),
            override=override,
            interpolate=interpolate,
            verbose=verbose,
        ),
    )
    ora_env = {k: os.environ.get(k) for k in _interesting_keys(base_env, text)}

    os.environ.clear()
    os.environ.update(saved)

    ok = (mine_ret == ora_ret) and (mine_env == ora_env)
    return ok, (mine_ret, mine_env, ora_ret, ora_env)


def _dir_listing(directory, normalize_tmp=True):
    """A comparable snapshot of a directory: name -> attributes."""
    import re as _re

    out = {}
    for name in sorted(os.listdir(directory)):
        path = os.path.join(directory, name)
        disp = (
            _re.sub(r"\.tmp_[A-Za-z0-9_]+", ".tmp_<RAND>", name)
            if normalize_tmp
            else name
        )
        if os.path.islink(path):
            out[disp] = ("link", os.readlink(path).replace(directory, "<DIR>"))
        elif os.path.isdir(path):
            out[disp] = ("dir",)
        else:
            mode = os.stat(path).st_mode & 0o777
            with open(path, "rb") as fh:
                content = fh.read()
            out[disp] = ("file", oct(mode), content)
    return out


def _apply_op(module, path, op):
    name = op[0]
    fn = getattr(module, name)
    return fn(path, *op[1:])


def compare_edit_sequence(initial, ops, make_symlink=False):
    """Compare a sequence of editing ops (return, logs, final dir state).

    ``ops`` is a list of tuples like ("set_key", key, value, quote_mode, export,
    encoding, follow_symlinks). ``initial`` is bytes for the .env file, or None
    for no file. Paths in log messages and the inode-changed flag are normalized
    so two separate temp dirs compare equal.
    """
    summaries = {}
    for who, module, cap in (
        ("mine", envrelay, _MINE_CAP),
        ("ora", dotenv(), _ORA_CAP),
    ):
        directory = tempfile.mkdtemp()
        path = os.path.join(directory, ".env")
        if make_symlink:
            target = os.path.join(directory, "target.env")
            with open(target, "wb") as fh:
                fh.write(initial if initial is not None else b"")
            os.symlink(target, path)
        elif initial is not None:
            with open(path, "wb") as fh:
                fh.write(initial)
        before_inode = os.stat(path).st_ino if os.path.exists(path) else None
        before_is_link = os.path.islink(path)
        results = []
        for op in ops:
            cap.records.clear()
            try:
                value = ("ok", repr(_apply_op(module, path, op)))
            except BaseException as exc:  # noqa: BLE001
                value = ("exc", "%s: %s" % (type(exc).__name__, exc))
            logs = [
                (lvl, msg.replace(directory, "<DIR>")) for (lvl, msg) in cap.records
            ]
            results.append((value, logs))
        after_inode = os.stat(path).st_ino if os.path.exists(path) else None
        inode_changed = before_inode != after_inode
        still_link = os.path.islink(path)
        listing = _dir_listing(directory)
        summaries[who] = (results, inode_changed, before_is_link, still_link, listing)
        shutil.rmtree(directory)
    ok = summaries["mine"] == summaries["ora"]
    return ok, summaries


def _interesting_keys(base_env, text):
    keys = set(base_env)
    for line in text.replace("\r", "\n").split("\n"):
        token = line.strip()
        if token and "=" in token:
            keys.add(token.split("=", 1)[0].strip().lstrip("export ").strip("'\""))
    # a conservative fixed set too
    keys.update({"A", "B", "C", "D", "E", "X", "Y", "Z"})
    return keys
