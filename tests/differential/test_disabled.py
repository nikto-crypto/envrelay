"""Differential tests for PYTHON_DOTENV_DISABLED (channels 2, 3, 7, 8).

The environment variable disables ``load_dotenv`` and the IPython magic for a
specific set of trigger values, and is ignored by ``dotenv_values``, ``get_key``,
and the command line (including ``run``). This gap was not exercised anywhere
else in the suite. Each case compares envrelay against the oracle: the return
value, the ``os.environ`` effect, and the emitted log records for loading; the
parsed result for the ignorers; and stdout/stderr/exit/env for the CLI and magic.
"""

from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import tempfile

import cli_modes
import diff_helpers
import oracle_iface
import pytest

import envrelay

_OK, _REASON = oracle_iface.availability()
pytestmark = pytest.mark.skipif(not _OK, reason=_REASON)

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
PY = os.path.join(REPO, ".venv", "bin", "python")
MAGIC_RUNNER = os.path.join(REPO, "scripts", "magic_runner.py")

# Documented triggers: 1, t, true, y, yes in any case. Everything else is a
# non-trigger (on, " 1", 0, false, empty, x, ...). We compare both sides so a
# wrong classification in either direction is caught regardless of the oracle's
# exact rule.
TRIGGERS = ["1", "t", "true", "y", "yes", "TRUE", "Yes", "T", "YES", "TrUe"]
NON_TRIGGERS = ["on", " 1", "1 ", "0", "false", "", "x", "2", "no", "off", "yep", "ja"]
ALL_VALUES = TRIGGERS + NON_TRIGGERS


@pytest.mark.parametrize("value", ALL_VALUES)
def test_load_dotenv_disabled_flag(value):
    # base_env carries PYTHON_DOTENV_DISABLED so it is present during the call.
    for override in (False, True):
        for verbose in (False, True):
            ok, detail = diff_helpers.compare_load_dotenv(
                "QQ=1\nRR=2\n",
                override=override,
                interpolate=True,
                verbose=verbose,
                base_env={"PYTHON_DOTENV_DISABLED": value},
            )
            assert ok, (
                "load_dotenv disabled=%r override=%s verbose=%s: %r"
                % (value, override, verbose, detail)
            )


@pytest.mark.parametrize("value", ["1", "true", "YES", "on", "0", ""])
def test_dotenv_values_ignores_disabled(value):
    saved = dict(os.environ)
    os.environ["PYTHON_DOTENV_DISABLED"] = value
    try:
        ok, detail = diff_helpers.compare_dotenv_values(
            "QQ=1\nRR=${QQ}\n", interpolate=True, via_file=False
        )
    finally:
        os.environ.clear()
        os.environ.update(saved)
    assert ok, "dotenv_values should ignore disabled=%r: %r" % (value, detail)


@pytest.mark.parametrize("value", ["1", "true", "on", ""])
def test_get_key_ignores_disabled(oracle, value):
    d = tempfile.mkdtemp()
    path = os.path.join(d, ".env")
    with open(path, "w") as fh:
        fh.write("QQ=hello\n")
    saved = dict(os.environ)
    os.environ["PYTHON_DOTENV_DISABLED"] = value
    try:
        mine = repr(envrelay.get_key(path, "QQ"))
        ora = repr(oracle.get_key(path, "QQ"))
    finally:
        os.environ.clear()
        os.environ.update(saved)
        shutil.rmtree(d)
    assert mine == ora, "get_key disabled=%r: mine=%s ora=%s" % (value, mine, ora)


@pytest.mark.parametrize("value", ["1", "true", "on", ""])
def test_cli_run_ignores_disabled(value):
    """`run` loads the file and executes the command regardless of the flag."""
    results = {}
    for which in ("oracle", "mine"):
        d = tempfile.mkdtemp()
        with open(os.path.join(d, ".env"), "w") as fh:
            fh.write("GREETING=hi\n")
        code, out, err = cli_modes.run_subprocess(
            which,
            "module",
            ["run", "printenv", "GREETING"],
            d,
            80,
            extra_env={"PYTHON_DOTENV_DISABLED": value},
        )
        results[which] = (code, out, err)
        shutil.rmtree(d)
    assert results["oracle"] == results["mine"], "run disabled=%r: %r" % (
        value,
        results,
    )


def _run_magic(ext, cwd, commands, disabled):
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env["MAGIC_BASE"] = cwd
    if disabled is not None:
        env["PYTHON_DOTENV_DISABLED"] = disabled
    proc = subprocess.run(
        [PY, MAGIC_RUNNER, ext],
        cwd=cwd,
        env=env,
        input=json.dumps(commands),
        capture_output=True,
        text=True,
    )
    out = {}
    for line in proc.stdout.splitlines():
        if line.startswith("{"):
            data = json.loads(line)
            out[data["cmd"]] = data
    assert out, "magic_runner (%s) no output: %s" % (ext, proc.stderr[-500:])
    return out


@pytest.mark.parametrize("value", ["1", "on", "true"])
def test_magic_honors_disabled(value):
    commands = ["", "-v", "-o"]
    d = tempfile.mkdtemp()
    try:
        with open(os.path.join(d, ".env"), "w") as fh:
            fh.write("A=1\nB=${A}\n")
        oracle = _run_magic("dotenv", d, commands, value)
        mine = _run_magic("envrelay", d, commands, value)
    finally:
        shutil.rmtree(d)
    for cmd in commands:
        assert oracle.get(cmd) == mine.get(cmd), (
            "magic disabled=%r cmd=%r: oracle=%r mine=%r"
            % (value, cmd, oracle.get(cmd), mine.get(cmd))
        )
