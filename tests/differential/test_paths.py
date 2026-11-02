"""Differential tests for path resolution with .env in parent folders.

Deliberately places a ``.env`` (regular file, FIFO, or directory) in parent
folders *inside* the case directory, then runs path-taking calls from a script at
depth beneath them with empty, None, and relative paths. Confirms that an empty
path never searches/loads an unintended file, that None searches, and that the
upward search accepts regular files and FIFOs but not directories -- matching the
oracle. (The suite's root-level "no .env above the temp root" assertion still
holds; these files live inside the per-case temp dir.)
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
PROBE = os.path.join(REPO, "scripts", "path_probe.py")

_OK, _REASON = oracle_iface.availability()
pytestmark = pytest.mark.skipif(not _OK, reason=_REASON)


def _make_env(path, kind):
    if kind == "file":
        with open(path, "w") as fh:
            fh.write("SECRET=leak\nX=1\n")
    elif kind == "fifo":
        os.mkfifo(path)
    elif kind == "dir":
        os.mkdir(path)


def _run(base, script_dir, mode):
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env["PATH_BASE"] = base
    script = os.path.join(script_dir, "p.py")
    with open(script, "w") as fh:
        fh.write(open(PROBE).read())
    proc = subprocess.run(
        [PY, script, mode],
        cwd=script_dir,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    rows = {}
    for line in proc.stdout.splitlines():
        if line.startswith("{"):
            data = json.loads(line)
            rows[data["label"]] = (data["oracle"], data["mine"])
    assert rows, "path_probe no output: %s" % proc.stderr[-500:]
    return rows


@pytest.mark.parametrize("kind", ["file", "fifo", "dir", "none"])
@pytest.mark.parametrize("where", ["base", "mid"])
@pytest.mark.parametrize("depth", [1, 2, 3])
def test_parent_env_resolution(kind, where, depth):
    base = tempfile.mkdtemp()
    parts = [base] + ["d%d" % i for i in range(depth)]
    leaf = os.path.join(*parts)
    os.makedirs(leaf)
    if kind != "none":
        target_dir = base if where == "base" else os.path.join(base, "d0")
        if os.path.isdir(target_dir):
            _make_env(os.path.join(target_dir, ".env"), kind)
    # A FIFO .env would block the reader calls (no writer), so for that kind only
    # the non-reading find_dotenv calls are exercised.
    mode = "find" if kind == "fifo" else "all"
    try:
        rows = _run(base, leaf, mode)
        for label, (oracle, mine) in rows.items():
            assert oracle == mine, "%s/%s/d%d %s: oracle=%r mine=%r" % (
                kind,
                where,
                depth,
                label,
                oracle,
                mine,
            )
    finally:
        shutil.rmtree(base)
