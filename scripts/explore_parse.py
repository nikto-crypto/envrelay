"""Probe the oracle's parser behavior for many stream inputs at once.

Black-box only: imports the oracle via the same sys.path trick as
oracle_probe.py, attaches a logging handler to the 'dotenv' logger to capture
(level, message) records, and prints the dotenv_values result plus records for
each input. Any escaping exception is reduced to its final line.

Inputs are supplied as JSON list of strings on stdin (each parsed via a
StringIO stream unless the string starts with the marker 'FILE:' in which case
it is written to a temp file and read as a path). interpolate flag via argv[1].
"""
from __future__ import annotations
import io
import os
import sys
import json
import logging
import tempfile

base = os.environ.get("ENVRELAY_ORACLE_DIR", os.path.expanduser("~/envrelay-oracle"))
for p in (base, os.path.join(base, "deps")):
    if p not in sys.path:
        sys.path.insert(0, p)

import dotenv  # noqa: E402

records = []

class Cap(logging.Handler):
    def emit(self, r):
        records.append((r.levelname, r.getMessage()))

logger = logging.getLogger("dotenv")
logger.setLevel(logging.DEBUG)
logger.addHandler(Cap())
logger.propagate = False

interpolate = (len(sys.argv) > 1 and sys.argv[1] == "nointerp")

data = json.load(sys.stdin)
for s in data:
    records.clear()
    try:
        if s.startswith("FILE:"):
            body = s[5:]
            fd, path = tempfile.mkstemp()
            os.write(fd, body.encode("utf-8"))
            os.close(fd)
            res = dotenv.dotenv_values(path, interpolate=not interpolate)
            os.unlink(path)
        else:
            res = dotenv.dotenv_values(stream=io.StringIO(s), interpolate=not interpolate)
        out = repr(res)
    except BaseException as e:
        out = f"!! {type(e).__name__}: {e}"
    print(json.dumps({"in": s, "out": out, "log": list(records)}))
