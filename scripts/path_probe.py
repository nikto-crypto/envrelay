"""Compare envrelay vs the oracle for path-resolution calls, from one frame.

Run as a script placed at some depth beneath directories that may contain a
``.env`` (a regular file, a FIFO, or a directory). Prints one JSON line per call
with the oracle's and envrelay's result (or reduced error), so a test can assert
they agree. Absolute paths are normalized against ``PATH_BASE``.

This exercises the "empty path is not no-path" rule and which file types the
upward search accepts, from real scripts at varying depth.
"""

import json
import os
import sys

_base = os.path.expanduser(os.environ.get("ENVRELAY_ORACLE_DIR", "~/envrelay-oracle"))
for _p in (_base, os.path.join(_base, "deps")):
    sys.path.insert(0, _p)
_repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_repo, "src"))

import dotenv as oracle  # noqa: E402

import envrelay  # noqa: E402

BASE = os.environ.get("PATH_BASE", "")


def norm(value):
    if not isinstance(value, str) or not BASE:
        return value
    out = value.replace(BASE, "<B>")
    private = BASE if BASE.startswith("/private") else "/private" + BASE
    return out.replace(private, "<B>")


def call(fn):
    try:
        return norm(repr(fn()))
    except BaseException as exc:  # noqa: BLE001
        return "%s: %s" % (type(exc).__name__, exc)


# "find" calls never read the located file (safe when .env is a FIFO with no
# writer); "read" calls do. The caller selects a mode via argv[1].
FIND_CALLS = {
    "find()": lambda m: m.find_dotenv(),
    "find(raise)": lambda m: m.find_dotenv(raise_error_if_not_found=True),
}
READ_CALLS = {
    "dv('')": lambda m: m.dotenv_values(""),
    "dv(None)": lambda m: m.dotenv_values(None),
    "dv()": lambda m: m.dotenv_values(),
    "dv('rel.env')": lambda m: m.dotenv_values("rel.env"),
    "ld('')": lambda m: _ld(m, ""),
    "ld(None)": lambda m: _ld(m, None),
    "ld()": lambda m: _ld(m),
    "get('','K')": lambda m: m.get_key("", "K"),
}


def _ld(module, *args):
    for key in ("SECRET", "X", "A"):
        os.environ.pop(key, None)
    ret = module.load_dotenv(*args)
    env = {k: os.environ.get(k) for k in ("SECRET", "X", "A") if os.environ.get(k)}
    for key in ("SECRET", "X", "A"):
        os.environ.pop(key, None)
    return (ret, env)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    calls = dict(FIND_CALLS)
    if mode != "find":
        calls.update(READ_CALLS)
    for label, fn in calls.items():
        o = call(lambda: fn(oracle))
        m = call(lambda: fn(envrelay))
        print(json.dumps({"label": label, "oracle": o, "mine": m}))


main()
