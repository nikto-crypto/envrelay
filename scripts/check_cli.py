"""Differential check: envrelay CLI vs oracle CLI (module and console modes).

Each case runs in its own temp dir with an optional initial .env. Both programs
are invoked with the same cwd and COLUMNS; the oracle via scripts/oracle_cli
(which reduces tracebacks), envrelay directly (tracebacks reduced the same way).
Program name and version number are normalized before comparison.
"""
import os
import re
import sys
import shutil
import tempfile
import subprocess

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "scripts"))
from oracle_cli import run_oracle, reduce_traceback  # noqa: E402

PYEXE = os.path.join(HERE, ".venv", "bin", "python")
ENVRELAY_SCRIPT = os.path.join(HERE, ".venv", "bin", "envrelay")


def run_mine(args, mode, cwd, columns):
    env = dict(os.environ)
    env["COLUMNS"] = str(columns)
    env.pop("PYTHONPATH", None)
    if mode == "module":
        argv = [PYEXE, "-m", "envrelay", *args]
    else:
        argv = [ENVRELAY_SCRIPT, *args]
    proc = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True)
    return proc.returncode, proc.stdout, reduce_traceback(proc.stderr)


def normalize(text, prog, ver, tmp=None):
    text = text.replace(prog + ", version " + ver, "<PROG>, version <VER>")
    text = text.replace("Usage: " + prog, "Usage: <PROG>")
    text = text.replace("Try '" + prog, "Try '<PROG>")
    # random temp-file names in error messages
    text = re.sub(r"\.tmp_[A-Za-z0-9_]+", ".tmp_<RAND>", text)
    if tmp:
        text = text.replace(tmp, "<TMP>").replace(
            "/private" + tmp if not tmp.startswith("/private") else tmp, "<TMP>"
        )
    return text


def compare(label, initial, args, mode="module", columns=80, stdin=None):
    results = {}
    for who in ("oracle", "mine"):
        d = tempfile.mkdtemp()
        env_path = os.path.join(d, ".env")
        if initial is not None:
            with open(env_path, "wb") as fh:
                fh.write(initial)
        if who == "oracle":
            code, out, err = run_oracle(
                args, mode=mode, cwd=d, columns=columns, input_text=stdin
            )
            prog = "python -m dotenv" if mode == "module" else "dotenv"
            ver = "1.2.4"
        else:
            code, out, err = run_mine(args, mode, d, columns)
            prog = "python -m envrelay" if mode == "module" else "envrelay"
            ver = "0.1.0"
        after = None
        if os.path.exists(env_path):
            with open(env_path, "rb") as fh:
                after = fh.read()
        results[who] = (
            code,
            normalize(out, prog, ver, d),
            normalize(err, prog, ver, d),
            after,
        )
        shutil.rmtree(d)
    ok = results["oracle"] == results["mine"]
    if not ok:
        print("MISMATCH:", label, "args=", args, "mode=", mode)
        for who in ("oracle", "mine"):
            c, o, e, a = results[who]
            print(f"  {who}: exit={c} out={o!r} err={e!r} env={a!r}")
    return ok


ENV1 = b"A=1\nB=two words\nD=\nC=\xc3\xa9\nE\n"
CASES = [
    ("version", None, ["--version"]),
    ("help", None, ["--help"]),
    ("help get", None, ["get", "--help"]),
    ("help list", None, ["list", "--help"]),
    ("help set", None, ["set", "--help"]),
    ("help unset", None, ["unset", "--help"]),
    ("help run", None, ["run", "--help"]),
    ("list simple", ENV1, ["list"]),
    ("list json", ENV1, ["list", "--format=json"]),
    ("list shell", ENV1, ["list", "--format=shell"]),
    ("list export", ENV1, ["list", "--format=export"]),
    ("get A", ENV1, ["get", "A"]),
    ("get D empty", ENV1, ["get", "D"]),
    ("get E none", ENV1, ["get", "E"]),
    ("get missing", ENV1, ["get", "NOPE"]),
    ("get no arg", ENV1, ["get"]),
    ("list missing file", None, ["-f", "nope.env", "list"]),
    ("set spaces", b"A=1\n", ["set", "K", "a b"]),
    ("set quote never", b"A=1\n", ["-q", "never", "set", "K", "x y"]),
    ("set export", b"A=1\n", ["-e", "true", "set", "G", "1"]),
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
    ("set dir", None, ["-f", ".", "set", "A", "1"]),
    ("list dir", None, ["-f", ".", "list"]),
]


def main():
    total = 0
    passed = 0
    for mode in ("module", "console"):
        for label, initial, args in CASES:
            total += 1
            if compare(label, initial, args, mode=mode):
                passed += 1
    print(f"\n{passed}/{total} CLI cases passed")


if __name__ == "__main__":
    main()
