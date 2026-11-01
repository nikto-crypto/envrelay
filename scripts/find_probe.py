"""Call find_dotenv on both envrelay and the oracle from one frame and compare.

Prints JSON {"oracle":..., "mine":...}; exceptions are reduced to
"ExceptionClass: message". A base directory to strip is read from FIND_BASE so
absolute paths can be compared. Args: filename usecwd raise_flag chdir_to
"""
import os
import sys
import json

_base = os.path.expanduser(os.environ.get("ENVRELAY_ORACLE_DIR", "~/envrelay-oracle"))
for _p in (_base, os.path.join(_base, "deps")):
    sys.path.insert(0, _p)

import dotenv as oracle  # noqa: E402

# Ensure envrelay resolves from the repo src if not installed.
_repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_repo, "src"))
import envrelay  # noqa: E402


def call(fn, filename, usecwd, raise_flag):
    try:
        return fn(filename, raise_error_if_not_found=raise_flag, usecwd=usecwd)
    except BaseException as exc:  # noqa: BLE001
        return "%s: %s" % (type(exc).__name__, exc)


def main():
    filename = sys.argv[1] if len(sys.argv) > 1 else ".env"
    usecwd = sys.argv[2] == "1" if len(sys.argv) > 2 else False
    raise_flag = sys.argv[3] == "1" if len(sys.argv) > 3 else False
    if len(sys.argv) > 4 and sys.argv[4]:
        os.chdir(sys.argv[4])
    base = os.environ.get("FIND_BASE", "")

    def norm(v):
        if isinstance(v, str) and base and base in v:
            return v.replace(base, "<B>")
        if isinstance(v, str) and base:
            pv = ("/private" + base) if not base.startswith("/private") else base
            if pv in v:
                return v.replace(pv, "<B>")
        return v

    o = norm(call(oracle.find_dotenv, filename, usecwd, raise_flag))
    m = norm(call(envrelay.find_dotenv, filename, usecwd, raise_flag))
    print(json.dumps({"oracle": o, "mine": m}))


main()
