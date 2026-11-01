"""Differential tests for the IPython %dotenv magic (channel 8).

Runs ``%load_ext envrelay`` / ``%load_ext dotenv`` in separate IPython shells and
compares, for each magic invocation, the printed output, os.environ effect, and
errors. Help text and error strings must match.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile

import pytest

import oracle_iface

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
PY = os.path.join(REPO, ".venv", "bin", "python")
RUNNER = os.path.join(REPO, "scripts", "magic_runner.py")

_OK, _REASON = oracle_iface.availability()
pytestmark = pytest.mark.skipif(not _OK, reason=_REASON)

COMMANDS = [
    "",
    "-v",
    "-o",
    "-o -v",
    "--override",
    "--verbose",
    "-h",
    "--help",
    "custom.env",
    "-v custom.env",
    "-o custom.env",
    "nope.env",
    "-v nope.env",
    "-x",
    "--bogus",
    "a b",
]


def _run(ext, cwd):
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env["MAGIC_BASE"] = cwd
    proc = subprocess.run(
        [PY, RUNNER, ext], cwd=cwd, env=env, input=json.dumps(COMMANDS),
        capture_output=True, text=True,
    )
    results = {}
    for line in proc.stdout.splitlines():
        if line.startswith("{"):
            data = json.loads(line)
            results[data["cmd"]] = data
    assert results, "magic_runner (%s) produced no output: %s" % (ext, proc.stderr[-500:])
    return results


def test_magic_differential():
    d = tempfile.mkdtemp()
    try:
        with open(os.path.join(d, ".env"), "w") as fh:
            fh.write("A=1\nB=${A}\n")
        with open(os.path.join(d, "custom.env"), "w") as fh:
            fh.write("C=custom\n")
        oracle = _run("dotenv", d)
        mine = _run("envrelay", d)
    finally:
        shutil.rmtree(d)
    for cmd in COMMANDS:
        o = oracle.get(cmd)
        m = mine.get(cmd)
        assert o == m, "magic %r: oracle=%r mine=%r" % (cmd, o, m)
