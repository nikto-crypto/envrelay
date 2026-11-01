"""Differential tests for the command line in three run modes (channel 7).

Every hand-written case runs through a real subprocess, a forked CliRunner, and a
pseudo-terminal, as both ``python -m`` and the console script where applicable;
generated documents are read by ``list`` in each mode. Exit code, stdout, stderr,
and the resulting ``.env`` bytes are compared after normalizing the program name,
version, temp dir, and temp-file randomness and reducing tracebacks. Help text is
checked at COLUMNS 80/100/120/unset.
"""

from __future__ import annotations

import os
import shutil
import tempfile

import cli_modes
import grammar
import normalizer
import oracle_iface
import pytest
from hypothesis import HealthCheck, given, settings

_OK, _REASON = oracle_iface.availability()
pytestmark = pytest.mark.skipif(not _OK, reason=_REASON)

_SCALE = int(os.environ.get("ENVRELAY_SCALE", "300"))


def _prog_version(which, mode, invocation):
    if mode == "clirunner":
        prog = "cli"
    elif invocation == "module":
        prog = "python -m dotenv" if which == "oracle" else "python -m envrelay"
    else:
        prog = "dotenv" if which == "oracle" else "envrelay"
    version = "1.2.4" if which == "oracle" else "0.1.0"
    return prog, version


def _run(which, mode, invocation, args, cwd, columns, input_text=None):
    if mode == "subprocess":
        return cli_modes.run_subprocess(
            which, invocation, args, cwd, columns, input_text
        )
    if mode == "pty":
        return cli_modes.run_pty(which, invocation, args, cwd, columns, input_text)
    return cli_modes.run_clirunner(which, args, cwd, columns, input_text)


def _compare(initial, args, mode, invocation="module", columns=80, input_text=None):
    results = {}
    for which in ("oracle", "mine"):
        d = tempfile.mkdtemp()
        env_path = os.path.join(d, ".env")
        if initial is not None:
            with open(env_path, "wb") as fh:
                fh.write(initial)
        code, out, err = _run(which, mode, invocation, args, d, columns, input_text)
        prog, version = _prog_version(which, mode, invocation)
        after = None
        if os.path.exists(env_path):
            with open(env_path, "rb") as fh:
                after = fh.read()
        results[which] = (
            code,
            normalizer.normalize(out, prog, version, d),
            normalizer.normalize(err, prog, version, d),
            after,
        )
        shutil.rmtree(d)
    return results["oracle"] == results["mine"], results


ENV1 = b"A=1\nB=two words\nD=\nC=\xc3\xa9\nE\n"
CASES = [
    ("version", None, ["--version"]),
    ("list simple", ENV1, ["list"]),
    ("list json", ENV1, ["list", "--format=json"]),
    ("list shell", ENV1, ["list", "--format=shell"]),
    ("list export", ENV1, ["list", "--format=export"]),
    ("get A", ENV1, ["get", "A"]),
    ("get empty", ENV1, ["get", "D"]),
    ("get none", ENV1, ["get", "E"]),
    ("get missing", ENV1, ["get", "NOPE"]),
    ("get noarg", ENV1, ["get"]),
    ("list missing file", None, ["-f", "nope.env", "list"]),
    ("set spaces", b"A=1\n", ["set", "K", "a b"]),
    ("set quote never", b"A=1\n", ["-q", "never", "set", "K", "x y"]),
    ("set export", b"A=1\n", ["-e", "true", "set", "G", "1"]),
    ("set e-bad", b"A=1\n", ["-e", "nope", "set", "G", "1"]),
    ("unset present", ENV1, ["unset", "A"]),
    ("unset missing", b"A=1\n", ["unset", "ZZZ"]),
    ("bad command", None, ["badcmd"]),
    ("bad option", None, ["--badopt", "list"]),
    ("set missing value", b"A=1\n", ["set", "K"]),
    ("run no command", b"A=1\n", ["run"]),
    ("run missing file", None, ["-f", "missing.env", "run", "echo", "hi"]),
    ("run cmd not found", b"A=1\n", ["run", "nosuchcmd"]),
    ("run unknown opt", b"A=1\n", ["run", "-x", "echo", "hi"]),
    ("run printenv", b"GREETING=hi\n", ["run", "printenv", "GREETING"]),
    ("run exit7", b"A=1\n", ["run", "sh", "-c", "exit 7"]),
    ("run no-override", b"A=1\n", ["run", "--no-override", "printenv", "A"]),
    ("set dir", None, ["-f", ".", "set", "A", "1"]),
    ("list dir", None, ["-f", ".", "list"]),
    ("dash file list", b"", ["-f", "-", "list"]),
]

HELP_CASES = [
    ["--help"],
    ["get", "--help"],
    ["list", "--help"],
    ["set", "--help"],
    ["unset", "--help"],
    ["run", "--help"],
]


@pytest.mark.parametrize("mode", ["subprocess", "clirunner", "pty"])
@pytest.mark.parametrize("label,initial,args", CASES, ids=[c[0] for c in CASES])
def test_cli_cases(mode, label, initial, args):
    invocations = ["module"] if mode == "clirunner" else ["module", "console"]
    for invocation in invocations:
        ok, results = _compare(initial, args, mode, invocation)
        assert ok, "%s/%s/%s: oracle=%r mine=%r" % (
            mode,
            invocation,
            label,
            results["oracle"],
            results["mine"],
        )


@pytest.mark.parametrize("columns", [80, 100, 120, None])
@pytest.mark.parametrize("args", HELP_CASES, ids=["+".join(a) for a in HELP_CASES])
def test_cli_help(columns, args):
    # Help text wrapping below 80 cols is exempt; 80 and up are compared.
    for mode in ("subprocess", "clirunner"):
        invocations = ["module"] if mode == "clirunner" else ["module", "console"]
        for invocation in invocations:
            cols = columns if columns is not None else 80
            ok, results = _compare(None, args, mode, invocation, columns=cols)
            assert ok, "help %s/%s/%s cols=%s: oracle=%r mine=%r" % (
                mode,
                invocation,
                args,
                columns,
                results["oracle"],
                results["mine"],
            )


@settings(
    max_examples=_SCALE,
    deadline=None,
    suppress_health_check=[
        HealthCheck.too_slow,
        HealthCheck.data_too_large,
        HealthCheck.function_scoped_fixture,
    ],
)
@given(text=grammar.env_documents())
@pytest.mark.parametrize("mode", ["subprocess", "clirunner", "pty"])
def test_cli_list_generated(mode, text):
    initial = text.encode("utf-8", "surrogatepass")
    ok, results = _compare(initial, ["list"], mode)
    assert ok, "%s list on %r: oracle=%r mine=%r" % (
        mode,
        text,
        results["oracle"],
        results["mine"],
    )
