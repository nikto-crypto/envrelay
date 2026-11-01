"""Extra command-line differential cases (channel 7).

Fills CLI gaps not covered by test_cli.py:

* every boolean spelling of ``-e`` (1/yes/true/off/no/t/f/on/0/bad);
* ``--format`` in unusual casing (the Choice is case-sensitive);
* the ``run --`` separator;
* stdin piped through to the ``run`` child;
* ``-f -`` for ``get`` and ``list`` with content supplied on stdin;
* ``list`` on a file with an undecodable byte (UnicodeDecodeError traceback).

Each case is compared after normalizing program name, version, temp dir and
temp-file randomness, and reducing tracebacks -- in the same three run modes used
elsewhere where applicable.
"""

from __future__ import annotations

import os
import shutil
import tempfile

import cli_modes
import normalizer
import oracle_iface
import pytest

_OK, _REASON = oracle_iface.availability()
pytestmark = pytest.mark.skipif(not _OK, reason=_REASON)


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


# --- -e boolean spellings ----------------------------------------------------

_E_VALUES = [
    "1", "0", "true", "false", "t", "f", "yes", "no", "y", "n",
    "on", "off", "TRUE", "False", "Yes", "OFF", "2", "nope", "",
]


@pytest.mark.parametrize("mode", ["subprocess", "clirunner", "pty"])
@pytest.mark.parametrize("value", _E_VALUES, ids=[repr(v) for v in _E_VALUES])
def test_cli_export_spellings(mode, value):
    invocations = ["module"] if mode == "clirunner" else ["module", "console"]
    for invocation in invocations:
        ok, results = _compare(
            b"A=1\n", ["-e", value, "set", "G", "1"], mode, invocation
        )
        assert ok, "-e %r/%s/%s: oracle=%r mine=%r" % (
            value, mode, invocation, results["oracle"], results["mine"],
        )


# --- --format casing (case-sensitive Choice) ---------------------------------

_FORMATS = ["simple", "SIMPLE", "Json", "JSON", "Shell", "EXPORT", "export", "bogus"]
_ENV = b"A=1\nB=two words\nD=\nC=\xc3\xa9\nE\n"


@pytest.mark.parametrize("mode", ["subprocess", "clirunner", "pty"])
@pytest.mark.parametrize("fmt", _FORMATS)
def test_cli_format_casing(mode, fmt):
    invocations = ["module"] if mode == "clirunner" else ["module", "console"]
    for invocation in invocations:
        ok, results = _compare(_ENV, ["list", "--format=%s" % fmt], mode, invocation)
        assert ok, "--format=%s/%s/%s: oracle=%r mine=%r" % (
            fmt, mode, invocation, results["oracle"], results["mine"],
        )


# --- run -- separator and stdin passthrough ----------------------------------


@pytest.mark.parametrize("mode", ["subprocess", "pty"])
def test_cli_run_double_dash(mode):
    for invocation in ["module", "console"]:
        ok, results = _compare(
            b"GREETING=hi\n", ["run", "--", "printenv", "GREETING"], mode, invocation
        )
        assert ok, "run -- /%s/%s: oracle=%r mine=%r" % (
            mode, invocation, results["oracle"], results["mine"],
        )


@pytest.mark.parametrize("mode", ["subprocess"])
def test_cli_run_stdin_passthrough(mode):
    # `run` execs the child, which should inherit the parent's stdin.
    for invocation in ["module", "console"]:
        ok, results = _compare(
            b"A=1\n", ["run", "cat"], mode, invocation, input_text="piped-in-data\n"
        )
        assert ok, "run cat stdin/%s/%s: oracle=%r mine=%r" % (
            mode, invocation, results["oracle"], results["mine"],
        )


# --- -f - (dash as the env file) ---------------------------------------------


@pytest.mark.parametrize("mode", ["subprocess", "clirunner"])
@pytest.mark.parametrize(
    "args", [["-f", "-", "get", "A"], ["-f", "-", "list"], ["-f", "-", "get", "NOPE"]]
)
def test_cli_dash_file_with_stdin(mode, args):
    invocations = ["module"] if mode == "clirunner" else ["module", "console"]
    for invocation in invocations:
        ok, results = _compare(
            None, args, mode, invocation, input_text="A=1\nB=two\n"
        )
        assert ok, "%s/%s/%s: oracle=%r mine=%r" % (
            args, mode, invocation, results["oracle"], results["mine"],
        )


# --- undecodable byte for list (UnicodeDecodeError traceback) -----------------

_UNDECODABLE = [
    b"A=1\nB=\xff\xfe\nC=3\n",
    b"\xff\xfe\x00A=1\n",
    b"GOOD=1\nBAD=\x80\x81\n",
]


@pytest.mark.parametrize("mode", ["subprocess", "clirunner", "pty"])
@pytest.mark.parametrize(
    "initial", _UNDECODABLE, ids=[repr(i) for i in _UNDECODABLE]
)
def test_cli_list_undecodable(mode, initial):
    invocations = ["module"] if mode == "clirunner" else ["module", "console"]
    for invocation in invocations:
        ok, results = _compare(initial, ["list"], mode, invocation)
        assert ok, "undecodable %r/%s/%s: oracle=%r mine=%r" % (
            initial, mode, invocation, results["oracle"], results["mine"],
        )
