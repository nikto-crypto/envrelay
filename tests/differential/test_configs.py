"""Differential tests over realistic hand-written configuration files.

Each file (web app, data pipeline, container, CI) is read through dotenv_values
(path and stream, interpolate on/off) and load_dotenv, and listed through the CLI
in every format and all three run modes, compared with the oracle.
"""

from __future__ import annotations

import os
import shutil
import tempfile

import cli_modes
import diff_helpers
import normalizer
import oracle_iface
import pytest

CONFIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "configs")
CONFIGS = sorted(f for f in os.listdir(CONFIG_DIR) if f.endswith(".env"))

_OK, _REASON = oracle_iface.availability()
pytestmark = pytest.mark.skipif(not _OK, reason=_REASON)


@pytest.mark.parametrize("name", CONFIGS)
def test_config_readers(name):
    text = open(os.path.join(CONFIG_DIR, name)).read()
    for interpolate in (True, False):
        for via_file in (False, True):
            ok, detail = diff_helpers.compare_dotenv_values(text, interpolate, via_file)
            assert ok, "%s interp=%s file=%s: %r" % (
                name,
                interpolate,
                via_file,
                detail,
            )
    for override in (False, True):
        ok, detail = diff_helpers.compare_load_dotenv(text, override, True, True, {})
        assert ok, "%s load override=%s: %r" % (name, override, detail)


@pytest.mark.parametrize("name", CONFIGS)
@pytest.mark.parametrize("fmt", ["simple", "json", "shell", "export"])
def test_config_cli_list(name, fmt):
    initial = open(os.path.join(CONFIG_DIR, name), "rb").read()
    for mode in ("subprocess", "clirunner", "pty"):
        results = {}
        for which in ("oracle", "mine"):
            d = tempfile.mkdtemp()
            with open(os.path.join(d, ".env"), "wb") as fh:
                fh.write(initial)
            args = ["list", "--format=%s" % fmt]
            if mode == "subprocess":
                code, out, err = cli_modes.run_subprocess(which, "module", args, d, 80)
                prog = "python -m dotenv" if which == "oracle" else "python -m envrelay"
            elif mode == "pty":
                code, out, err = cli_modes.run_pty(which, "module", args, d, 80)
                prog = "python -m dotenv" if which == "oracle" else "python -m envrelay"
            else:
                code, out, err = cli_modes.run_clirunner(which, args, d, 80)
                prog = "cli"
            ver = "1.2.4" if which == "oracle" else "0.1.0"
            results[which] = (
                code,
                normalizer.normalize(out, prog, ver, d),
                normalizer.normalize(err, prog, ver, d),
            )
            shutil.rmtree(d)
        assert results["oracle"] == results["mine"], "%s %s %s: %r" % (
            name,
            fmt,
            mode,
            results,
        )
