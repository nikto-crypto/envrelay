"""Run the IPython 'dotenv' magic for a given extension and command list.

Used to compare envrelay's magic with the oracle's. Args:
  argv[1] = extension module name ("dotenv" for oracle, "envrelay" for mine)
Reads a JSON list of magic argument strings from stdin; for each, runs
%dotenv <args> in a fresh-ish shell, capturing stdout/stderr and the resulting
values of a fixed set of probe env vars. Prints one JSON object per command.
Tracebacks are reduced to the final ExceptionClass: message line.
"""
import io
import os
import sys
import json
import contextlib

_base = os.path.expanduser(os.environ.get("ENVRELAY_ORACLE_DIR", "~/envrelay-oracle"))
for _p in (_base, os.path.join(_base, "deps")):
    sys.path.insert(0, _p)
_repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_repo, "src"))

from IPython.core.interactiveshell import InteractiveShell  # noqa: E402

PROBE_KEYS = ["A", "B", "C", "GREETING", "X"]


def reduce_tb(text):
    marker = "Traceback (most recent call last):"
    if marker not in text:
        return text
    before, _, tb = text.partition(marker)
    lines = [ln for ln in tb.splitlines() if ln.strip()]
    return before + (lines[-1] if lines else "")


def main():
    ext = sys.argv[1]
    base = os.environ.get("MAGIC_BASE", "")
    commands = json.load(sys.stdin)
    shell = InteractiveShell.instance()
    shell.run_line_magic("load_ext", ext)
    for cmd in commands:
        for k in PROBE_KEYS:
            os.environ.pop(k, None)
        out = io.StringIO()
        err = io.StringIO()
        error = None
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                shell.run_line_magic("dotenv", cmd)
            except BaseException as exc:  # noqa: BLE001
                error = "%s: %s" % (type(exc).__name__, exc)
        envnow = {k: os.environ.get(k) for k in PROBE_KEYS if os.environ.get(k) is not None}
        o = reduce_tb(out.getvalue())
        e = reduce_tb(err.getvalue())
        if base:
            o = o.replace(base, "<B>")
            e = e.replace(base, "<B>")
        print(json.dumps({"cmd": cmd, "out": o, "err": e, "error": error, "env": envnow}))


if __name__ == "__main__":
    main()
