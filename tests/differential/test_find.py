"""Differential tests for find_dotenv across run modes and layouts (channel 5).

Each case builds a directory tree, then runs find_dotenv on both envrelay and the
oracle from the same frame (a subprocess invoked as a script, module, ``-m``,
``-c``, or via stdin), comparing the returned path or the error. Covers depth,
custom filenames, usecwd, raise_error_if_not_found, an active tracer, and
sys.frozen.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile

import oracle_iface
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
PY = os.path.join(REPO, ".venv", "bin", "python")
PROBE = os.path.join(REPO, "scripts", "find_probe.py")

_OK, _REASON = oracle_iface.availability()
pytestmark = pytest.mark.skipif(not _OK, reason=_REASON)


def _run(mode, cwd, base, args, settrace=False, frozen=False):
    env = dict(os.environ)
    env["FIND_BASE"] = base
    env.pop("PYTHONPATH", None)
    probe_src = open(PROBE).read()
    prelude = ""
    if settrace:
        prelude += "import sys\nsys.settrace(lambda *a: None)\n"
    if frozen:
        prelude += "import sys\nsys.frozen=True\n"
    if mode == "script":
        proc = subprocess.run(
            [PY, PROBE, *args], cwd=cwd, env=env, capture_output=True, text=True
        )
    elif mode in ("module", "minusm"):
        modpath = os.path.join(cwd, "finder_mod.py")
        with open(modpath, "w") as fh:
            fh.write(prelude + probe_src)
        argv = (
            [PY, "finder_mod.py", *args]
            if mode == "module"
            else [PY, "-m", "finder_mod", *args]
        )
        proc = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True)
    elif mode in ("minusc", "stdin"):
        code = prelude + "import runpy,sys; sys.argv=['x',%s]; runpy.run_path(%r)" % (
            ",".join(repr(a) for a in args),
            PROBE,
        )
        if mode == "minusc":
            proc = subprocess.run(
                [PY, "-c", code], cwd=cwd, env=env, capture_output=True, text=True
            )
        else:
            proc = subprocess.run(
                [PY], input=code, cwd=cwd, env=env, capture_output=True, text=True
            )
    else:
        raise ValueError(mode)
    for ln in proc.stdout.splitlines():
        if ln.startswith("{"):
            return json.loads(ln)
    raise AssertionError("no probe output: %s / %s" % (proc.stdout, proc.stderr[-300:]))


def _build_tree(scenario, depth):
    base = tempfile.mkdtemp()
    parts = [base] + ["d%d" % i for i in range(depth)]
    leaf = os.path.join(*parts)
    os.makedirs(leaf, exist_ok=True)
    if scenario == "env_at_base":
        open(os.path.join(base, ".env"), "w").write("X=1\n")
    elif scenario == "env_midway" and depth >= 1:
        open(os.path.join(base, "d0", ".env"), "w").write("X=1\n")
    elif scenario == "cfg_at_base":
        open(os.path.join(base, "cfg.ini"), "w").write("X=1\n")
    # "no_env": nothing
    return base, leaf


def test_find_dotenv_matrix():
    cases = 0
    scenarios = ["env_at_base", "env_midway", "no_env", "cfg_at_base"]
    modes = ["script", "module", "minusm", "minusc", "stdin"]
    try:
        for scenario in scenarios:
            for depth in (0, 1, 2, 3, 4):
                base, leaf = _build_tree(scenario, depth)
                try:
                    for mode in modes:
                        for args in (
                            [".env", "0", "0"],
                            [".env", "1", "0"],
                            [".env", "0", "1"],
                            ["cfg.ini", "0", "0"],
                            ["cfg.ini", "1", "1"],
                        ):
                            data = _run(mode, leaf, base, args)
                            assert data["oracle"] == data["mine"], (
                                scenario,
                                depth,
                                mode,
                                args,
                                data,
                            )
                            cases += 1
                    # tracer + frozen variants
                    for extra in ("tracer", "frozen"):
                        data = _run(
                            "module",
                            leaf,
                            base,
                            [".env", "0", "0"],
                            settrace=(extra == "tracer"),
                            frozen=(extra == "frozen"),
                        )
                        assert data["oracle"] == data["mine"], (
                            scenario,
                            depth,
                            extra,
                            data,
                        )
                        cases += 1
                finally:
                    shutil.rmtree(base)
    finally:
        pass
    assert cases >= 500, "only %d find_dotenv cases" % cases
