"""Run the command line three ways, for both envrelay and the oracle.

Modes:

* ``subprocess`` -- a real child process (``python -m <pkg>`` or the console
  script).
* ``clirunner`` -- ``click.testing.CliRunner`` inside a forked child that chdirs
  into the case directory and only then imports the command-line module (so the
  ``-f`` default is fixed there); a successful ``run`` replaces that child, whose
  wait status and inherited-fd output are then collected.
* ``pty`` -- a real child driven through a pseudo-terminal on stdout.

Each runner returns ``(exit_code, stdout, stderr)`` with the oracle's tracebacks
already reduced. The program name under CliRunner is ``cli`` for both sides.
"""

from __future__ import annotations

import json
import os
import pty
import select
import subprocess
import sys

import oracle_iface

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
PYEXE = os.path.join(REPO, ".venv", "bin", "python")
CONSOLE = os.path.join(REPO, ".venv", "bin", "envrelay")
ORACLE_DIR = oracle_iface.ORACLE_DIR

_TB = "Traceback (most recent call last):"


def reduce_tb(text):
    if _TB not in text:
        return text
    before, _, tb = text.partition(_TB)
    lines = [ln for ln in tb.splitlines() if ln.strip()]
    trailing = "\n" if text.endswith("\n") else ""
    return before + (lines[-1] if lines else "") + trailing


def _base_env(columns, extra=None):
    env = {
        "PATH": os.environ.get("PATH", ""),
        "TERM": "dumb",
        "LANG": "en_US.UTF-8",
        "LC_ALL": "en_US.UTF-8",
        "TZ": "UTC",
        "HOME": os.environ.get("HOME", "/tmp"),
    }
    if columns is not None:
        env["COLUMNS"] = str(columns)
    if extra:
        env.update(extra)
    return env


# --- subprocess --------------------------------------------------------------

def run_subprocess(which, invocation, args, cwd, columns, input_text=None, extra_env=None):
    env = _base_env(columns, extra_env)
    if which == "oracle":
        env["PYTHONPATH"] = os.pathsep.join([ORACLE_DIR, os.path.join(ORACLE_DIR, "deps")])
        if invocation == "module":
            argv = [PYEXE, "-m", "dotenv", *args]
        else:
            argv = [PYEXE, os.path.join(ORACLE_DIR, "bin", "dotenv"), *args]
    else:
        env.pop("PYTHONPATH", None)
        if invocation == "module":
            argv = [PYEXE, "-m", "envrelay", *args]
        else:
            argv = [CONSOLE, *args]
    proc = subprocess.run(argv, cwd=cwd, env=env, input=input_text, capture_output=True, text=True)
    return proc.returncode, proc.stdout, reduce_tb(proc.stderr)


# --- CliRunner in a forked child --------------------------------------------

_CHILD = r'''
import os, sys, json
cwd, which, columns, args_json, input_text, out_path, err_path, payload_path = (
    sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6],
    sys.argv[7], sys.argv[8])
args = json.loads(args_json)
os.chdir(cwd)
os.environ["COLUMNS"] = columns
# Redirect OS-level stdout/stderr so a successful `run` (which execs) is captured;
# the CliRunner result for ordinary commands is written to a separate payload fd.
ofd = os.open(out_path, os.O_WRONLY)
efd = os.open(err_path, os.O_WRONLY)
os.dup2(ofd, 1); os.dup2(efd, 2)
if which == "oracle":
    ob = os.environ.get("ORACLE_DIR")
    sys.path[:0] = [ob, ob + "/deps"]
    from dotenv.cli import cli
else:
    from envrelay._commandline import cli
from click.testing import CliRunner
try:
    runner = CliRunner(mix_stderr=False)
except TypeError:
    runner = CliRunner()
result = runner.invoke(cli, args, input=(input_text or None), catch_exceptions=True)
try:
    err = result.stderr
except Exception:
    err = ""
payload = {"exit": result.exit_code, "stdout": result.stdout, "stderr": err}
pfd = os.open(payload_path, os.O_WRONLY)
os.write(pfd, json.dumps(payload).encode())
os.close(pfd)
'''


def run_clirunner(which, args, cwd, columns, input_text=None):
    """Run CliRunner inside a helper subprocess that chdirs and then imports.

    A separate helper process means the test process is never at risk from a
    ``run`` that execs; OS-level stdout/stderr are captured so that exec case is
    observable, and the ordinary-command result is written to a payload file.
    """
    import tempfile

    paths = []
    for _ in range(3):
        fd, p = tempfile.mkstemp()
        os.close(fd)
        paths.append(p)
    out_path, err_path, payload_path = paths
    env = _base_env(columns)
    env.pop("PYTHONPATH", None)
    if which == "oracle":
        env["ORACLE_DIR"] = ORACLE_DIR
    argv = [
        PYEXE, "-c", _CHILD, cwd, which, str(columns), json.dumps(args),
        input_text or "", out_path, err_path, payload_path,
    ]
    proc = subprocess.run(argv, env=env, capture_output=True, text=True)
    with open(out_path) as fh:
        fd_out = fh.read()
    with open(err_path) as fh:
        fd_err = fh.read()
    with open(payload_path) as fh:
        payload = fh.read()
    for p in paths:
        os.unlink(p)
    if payload:
        data = json.loads(payload)
        return data["exit"], data["stdout"], reduce_tb(data["stderr"])
    # No payload: a successful `run` exec'd and replaced the child. Use the
    # captured fd output and the child's exit status.
    return proc.returncode, fd_out, reduce_tb(fd_err)


# --- pseudo-terminal ---------------------------------------------------------

def run_pty(which, invocation, args, cwd, columns, input_text=None, extra_env=None):
    env = _base_env(columns, extra_env)
    if which == "oracle":
        env["PYTHONPATH"] = os.pathsep.join([ORACLE_DIR, os.path.join(ORACLE_DIR, "deps")])
        if invocation == "module":
            argv = [PYEXE, "-m", "dotenv", *args]
        else:
            argv = [PYEXE, os.path.join(ORACLE_DIR, "bin", "dotenv"), *args]
    else:
        env.pop("PYTHONPATH", None)
        if invocation == "module":
            argv = [PYEXE, "-m", "envrelay", *args]
        else:
            argv = [CONSOLE, *args]

    master, slave = pty.openpty()
    err_r, err_w = os.pipe()
    proc = subprocess.Popen(
        argv, cwd=cwd, env=env, stdin=subprocess.PIPE, stdout=slave, stderr=err_w,
        close_fds=True,
    )
    os.close(slave)
    os.close(err_w)
    if input_text:
        proc.stdin.write(input_text.encode())
    proc.stdin.close()
    out = bytearray()
    err = bytearray()
    fds = [master, err_r]
    while fds:
        ready, _, _ = select.select(fds, [], [], 5)
        if not ready:
            break
        for fd in ready:
            try:
                chunk = os.read(fd, 4096)
            except OSError:
                chunk = b""
            if not chunk:
                fds.remove(fd)
                continue
            (out if fd == master else err).extend(chunk)
    os.close(master)
    os.close(err_r)
    code = proc.wait()
    # A pty turns \n into \r\n on output; fold it back.
    stdout = out.decode("utf-8", "replace").replace("\r\n", "\n")
    stderr = err.decode("utf-8", "replace")
    return code, stdout, reduce_tb(stderr)
