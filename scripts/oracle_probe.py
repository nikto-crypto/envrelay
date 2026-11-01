"""Black-box probe for the python-dotenv 1.2.4 oracle.

This is the ONLY route this repo uses to execute the oracle. It:

* puts the oracle folder (and its bundled click) on ``sys.path`` so ``import
  dotenv`` resolves to the bytecode-only oracle install,
* runs a snippet of probe code supplied on the command line or stdin, and
* reduces any exception that escapes to a single ``ExceptionClass: message``
  line before printing, so a raw oracle traceback (with its file names and line
  numbers) can never reach a shell.

It never inspects the oracle: no ``help``/``dir``/``vars``/``inspect``/
``__doc__``/``__dict__`` and no import of a ``dotenv.`` submodule other than
``dotenv.cli`` (allowed only as a ``CliRunner`` target). It is probe tooling,
not part of the measured library.

Usage::

    python scripts/oracle_probe.py -c "print(dotenv.dotenv_values(stream=io.StringIO('A=1')))"
    echo "..." | python scripts/oracle_probe.py   # code on stdin

The snippet runs with these names available: ``dotenv`` (the oracle package),
``io``, ``os``, ``sys``, ``json``.
"""

from __future__ import annotations

import io
import json
import os
import sys


def oracle_dir() -> str:
    return os.environ.get(
        "ENVRELAY_ORACLE_DIR", os.path.expanduser("~/envrelay-oracle")
    )


def _configure_path() -> None:
    base = oracle_dir()
    deps = os.path.join(base, "deps")
    for p in (base, deps):
        if p not in sys.path:
            sys.path.insert(0, p)


def _final_exc_line(exc: BaseException) -> str:
    name = type(exc).__name__
    msg = str(exc)
    return f"{name}: {msg}" if msg else name


def main(argv: list[str]) -> int:
    _configure_path()
    if len(argv) >= 2 and argv[1] == "-c":
        code = argv[2] if len(argv) >= 3 else ""
    else:
        code = sys.stdin.read()

    import dotenv  # noqa: F401  (resolves to the oracle)

    ns = {"dotenv": dotenv, "io": io, "os": os, "sys": sys, "json": json}
    try:
        exec(compile(code, "<probe>", "exec"), ns)  # noqa: S102 (probe tooling)
    except BaseException as exc:  # noqa: BLE001  (reduce before printing)
        print(_final_exc_line(exc))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
