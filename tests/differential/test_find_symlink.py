"""Differential tests for find_dotenv across symlinked directories (channel 5).

find_dotenv walks upward from the calling script's directory. When that directory
is reached through a symlink, whether the symlink is resolved (realpath) or kept
(abspath) changes the returned path. We build a tree where the two differ and run
the same probe through the symlinked path on both envrelay and the oracle.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile

import oracle_iface
import pytest

_OK, _REASON = oracle_iface.availability()
pytestmark = pytest.mark.skipif(not _OK, reason=_REASON)

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
PY = os.path.join(REPO, ".venv", "bin", "python")
ORACLE_DIR = oracle_iface.ORACLE_DIR

_PROBE = r"""
import json, os, sys
import dotenv as oracle
import envrelay
base = os.environ.get("FIND_BASE", "")

def norm(v):
    if not isinstance(v, str) or not base:
        return v
    for b in (base, ("/private" + base) if not base.startswith("/private") else base):
        if b in v:
            return v.replace(b, "<B>")
    return v

fn = sys.argv[1] if len(sys.argv) > 1 else ".env"
usecwd = len(sys.argv) > 2 and sys.argv[2] == "1"

def call(mod):
    try:
        return mod.find_dotenv(fn, usecwd=usecwd)
    except BaseException as exc:
        return "%s: %s" % (type(exc).__name__, exc)

print(json.dumps({"oracle": norm(call(oracle)), "mine": norm(call(envrelay))}))
"""


def _env(base):
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", "/tmp"),
        "LANG": "en_US.UTF-8",
        "LC_ALL": "en_US.UTF-8",
        "FIND_BASE": base,
        "PYTHONPATH": os.pathsep.join(
            [ORACLE_DIR, os.path.join(ORACLE_DIR, "deps"), os.path.join(REPO, "src")]
        ),
    }
    return env


def _run(script_path, base, args):
    proc = subprocess.run(
        [PY, script_path, *args],
        env=_env(base),
        capture_output=True,
        text=True,
    )
    for ln in proc.stdout.splitlines():
        if ln.startswith("{"):
            return json.loads(ln)
    raise AssertionError("no probe output: %s / %s" % (proc.stdout, proc.stderr[-400:]))


def _build(env_location):
    """Tree: base/{target/, alias->target}. A script lives in target/sub.

    env_location controls where .env sits: 'in_target' (base/target/.env, only
    reachable walking up the real path) or 'in_base' (base/.env, reachable both
    ways). 'none' places no .env.
    """
    base = tempfile.mkdtemp()
    target = os.path.join(base, "target")
    sub = os.path.join(target, "sub")
    os.makedirs(sub)
    alias = os.path.join(base, "alias")
    os.symlink(target, alias)
    script = os.path.join(sub, "probe_script.py")
    with open(script, "w") as fh:
        fh.write(_PROBE)
    if env_location == "in_target":
        open(os.path.join(target, ".env"), "w").write("X=1\n")
    elif env_location == "in_base":
        open(os.path.join(base, ".env"), "w").write("X=1\n")
    # path to the script THROUGH the symlink:
    script_via_alias = os.path.join(alias, "sub", "probe_script.py")
    return base, script, script_via_alias


@pytest.mark.parametrize("env_location", ["in_target", "in_base", "none"])
@pytest.mark.parametrize("via", ["alias", "real"])
@pytest.mark.parametrize("usecwd", ["0", "1"])
def test_find_dotenv_symlinked_dir(env_location, via, usecwd):
    base, real_script, alias_script = _build(env_location)
    try:
        script = alias_script if via == "alias" else real_script
        data = _run(script, base, [".env", usecwd])
        assert data["oracle"] == data["mine"], (
            "env=%s via=%s usecwd=%s: %r" % (env_location, via, usecwd, data)
        )
    finally:
        shutil.rmtree(base)
