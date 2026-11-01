"""Run the oracle's command line as a subprocess, black-box, safely.

This is the ONLY route this repo uses to invoke the oracle's CLI. It runs either
``python -m dotenv`` or the installed console script (passed to the project
interpreter, never read), with the oracle folder and its bundled click on
``PYTHONPATH``. Crucially it reduces any traceback on stderr to its final
``ExceptionClass: message`` line *before* anything is printed or returned, so an
oracle traceback (file names, line numbers) can never reach a shell or a stored
comparison.

CLI usage (for probing)::

    python scripts/oracle_cli.py --mode module --cwd DIR --columns 80 -- list
    python scripts/oracle_cli.py --mode console -- --version

Prints a JSON object: {"exit", "stdout", "stderr"} with stderr already reduced.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

_TB_MARKER = "Traceback (most recent call last):"


def reduce_traceback(text: str) -> str:
    """Collapse a Python traceback to its final ``ExceptionClass: message`` line.

    Text before the (first) traceback marker is kept; the traceback itself is
    replaced by its last non-empty line. If there is no traceback, the text is
    returned unchanged.
    """
    if _TB_MARKER not in text:
        return text
    before, _, tb = text.partition(_TB_MARKER)
    lines = [ln for ln in tb.splitlines() if ln.strip()]
    final = lines[-1] if lines else ""
    trailing = "\n" if text.endswith("\n") else ""
    return before + final + trailing


def oracle_dir() -> str:
    return os.environ.get(
        "ENVRELAY_ORACLE_DIR", os.path.expanduser("~/envrelay-oracle")
    )


def build_env(base: dict, columns, with_click: bool = True) -> dict:
    env = dict(base)
    od = oracle_dir()
    parts = [od]
    if with_click:
        parts.append(os.path.join(od, "deps"))
    env["PYTHONPATH"] = os.pathsep.join(parts)
    if columns is not None:
        env["COLUMNS"] = str(columns)
    return env


def run_oracle(
    args,
    mode: str = "module",
    cwd=None,
    columns=None,
    env=None,
    input_text=None,
    with_click: bool = True,
):
    """Run the oracle CLI and return (exit_code, stdout, reduced_stderr)."""
    interpreter = sys.executable
    if mode == "module":
        argv = [interpreter, "-m", "dotenv", *args]
    elif mode == "console":
        argv = [interpreter, os.path.join(oracle_dir(), "bin", "dotenv"), *args]
    else:
        raise ValueError("mode must be 'module' or 'console'")
    full_env = build_env(env if env is not None else os.environ, columns, with_click)
    proc = subprocess.run(
        argv,
        cwd=cwd,
        env=full_env,
        input=input_text,
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout, reduce_traceback(proc.stderr)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["module", "console"], default="module")
    ap.add_argument("--cwd", default=None)
    ap.add_argument("--columns", default=None)
    ap.add_argument("--no-click", action="store_true")
    ap.add_argument("rest", nargs=argparse.REMAINDER)
    ns = ap.parse_args(argv)
    rest = ns.rest
    if rest and rest[0] == "--":
        rest = rest[1:]
    code, out, err = run_oracle(
        rest,
        mode=ns.mode,
        cwd=ns.cwd,
        columns=ns.columns,
        with_click=not ns.no_click,
    )
    print(json.dumps({"exit": code, "stdout": out, "stderr": err}))


if __name__ == "__main__":
    main(sys.argv[1:])
