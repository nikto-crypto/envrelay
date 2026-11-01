"""Print the IPython 'dotenv' magic's docstring for a given extension.

Loads the extension named in argv[1] ("dotenv" for the oracle, "envrelay" for
mine) into a fresh InteractiveShell and prints the magic's ``__doc__`` as a JSON
string. This is the help shown by ``%dotenv?`` and
``ip.find_line_magic('dotenv').__doc__`` (not the trailing ``File:`` line).
Any escaping exception is reduced to its final ``ExceptionClass: message`` line.
"""

import json
import os
import sys

_base = os.path.expanduser(os.environ.get("ENVRELAY_ORACLE_DIR", "~/envrelay-oracle"))
for _p in (_base, os.path.join(_base, "deps")):
    sys.path.insert(0, _p)
_repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_repo, "src"))

from IPython.core.interactiveshell import InteractiveShell  # noqa: E402


def main():
    ext = sys.argv[1]
    shell = InteractiveShell.instance()
    try:
        shell.run_line_magic("load_ext", ext)
        doc = shell.find_line_magic("dotenv").__doc__
        print(json.dumps({"doc": doc}))
    except BaseException as exc:  # noqa: BLE001
        print(json.dumps({"error": "%s: %s" % (type(exc).__name__, exc)}))


if __name__ == "__main__":
    main()
