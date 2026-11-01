"""Compare envrelay's dotenv_values(stream/file) against the oracle.

Runs a battery of inputs through both and reports mismatches in value dict and
in the emitted warning line numbers. Usage: python scripts/check_parse.py
"""
import io
import os
import sys
import json
import logging

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "src"))

base = os.path.expanduser(os.environ.get("ENVRELAY_ORACLE_DIR", "~/envrelay-oracle"))
for p in (base, os.path.join(base, "deps")):
    sys.path.insert(0, p)

import dotenv as oracle  # noqa: E402
import envrelay  # noqa: E402

mine_log = []
ora_log = []


class Cap(logging.Handler):
    def __init__(self, sink):
        super().__init__()
        self.sink = sink

    def emit(self, r):
        self.sink.append((r.levelname, r.getMessage()))


lg_mine = logging.getLogger("envrelay")
lg_mine.setLevel(logging.DEBUG)
lg_mine.addHandler(Cap(mine_log))
lg_mine.propagate = False
lg_ora = logging.getLogger("dotenv")
lg_ora.setLevel(logging.DEBUG)
lg_ora.addHandler(Cap(ora_log))
lg_ora.propagate = False


def norm_log(records):
    # map envrelay log messages back to dotenv for comparison (none needed: msgs
    # already say "python-dotenv"); just return as-is
    return records


def one(text, interpolate, as_file):
    mine_log.clear()
    ora_log.clear()
    if as_file:
        import tempfile

        fd, path = tempfile.mkstemp()
        os.write(fd, text.encode("utf-8"))
        os.close(fd)
        try:
            m = envrelay.dotenv_values(path, interpolate=interpolate)
            o = oracle.dotenv_values(path, interpolate=interpolate)
        finally:
            os.unlink(path)
    else:
        m = envrelay.dotenv_values(stream=io.StringIO(text), interpolate=interpolate)
        o = oracle.dotenv_values(stream=io.StringIO(text), interpolate=interpolate)
    ok = (repr(m) == repr(o)) and (mine_log == ora_log)
    return ok, m, o, list(mine_log), list(ora_log)


CASES = [
    "A=1", "A=1 # c", "B=1#c", "K= # comment", "A", "B=", "export A=1", "export",
    "export=1", "'q k'=1", '"dq"=2', "A.B-C:D=1", "=1", "A B", "A='x' y",
    "A=1\nB=2\nA=3", "A=1\n\n\n'bad\nB=2", "A=1\r\nB=2", "A='a\\'b\\nc'",
    'A="a\\nb"', 'A="\\x41"', 'A="\\q"', 'A="é"', "A=#onlyhash", 'A="a"b',
    "A====", 'A="unterminated', "A='unterminated", "A # c", 'A="q" # c',
    "A=val\t#c", "A=''", 'A=""', "A=1;B=2", "A=$B", "A=a b\tc # x",
    'A="multi\nline" # c', "x y\nA=1", "A=1\n\nx y\n\nB=2",
    "A=1\r\nx y\r\nB=2\r\nz w\r\nC=3", "﻿A=1", "é=1", "A#B=1",
    "export 'q k'=1", "A=   ", "A=\t\tval\t\t", "#c\nA#x=1",
    "A=1\rB=2\rz w\rC=3", "A=${B}\nB=2", "A=${MISSING:-def}", "A=$B\nB=2",
    "A='${B}'\nB=2", "A=${B:-x}${C}\nB=2\nC=${B}", "A=\nB=${A:-d}", "A=${A-x}",
    "A=\nB=${A:-${C}}\nC=9", "A=${}", "X=${X}", "A=${B-d}\nB=2",
    "A=${B:-${C:-x}}", "B=2\nA=\\${B}", "B=2\nA=$${B}", "A=${B}}\nB=9",
    "A=text${B:-de fault}more", "x y\r\ne f\r\nD=4\r\ng h",
    "A=1\r\nx y\r\ne f\r\nB=2\r\nz w", "A=1\r\nB=2\r\nz w\r\nD=4\r\ne f",
]


def main():
    fails = 0
    total = 0
    for text in CASES:
        for interp in (True, False):
            for as_file in (False, True):
                total += 1
                ok, m, o, ml, ol = one(text, interp, as_file)
                if not ok:
                    fails += 1
                    print("MISMATCH", json.dumps({"in": text, "interp": interp, "file": as_file}))
                    print("   mine:", repr(m), ml)
                    print("   ora :", repr(o), ol)
    print(f"\n{total - fails}/{total} passed")


if __name__ == "__main__":
    main()
