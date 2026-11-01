"""Search for the newline-accounting algorithm that reproduces observed
warning line numbers. Pure local reasoning from black-box observations."""
import re

# (content, expected_warning_lines)
OBS = [
    ("=1", [1]),
    ("A B", [1]),
    ("A='x' y", [1]),
    ("A=1\n\n\n'bad\nB=2", [2]),
    ("x y\nA=1", [1]),
    ("A=1\n\nx y\n\nB=2", [2]),
    ("A=1\r\nx y\r\nB=2\r\nz w\r\nC=3", [2, 5]),
    ("x y\r\nz w\r\nC=3", [1, 2]),
    ("A=1\r\nx y\r\nC=3", [2]),
    ("x y\nz w\nC=3", [1, 2]),
    ("A=1\r\nx y\r\nB=2\r\nz w\r\ne f\r\nC=3", [2, 5, 6]),
    ("x y\r\nB=2\r\nz w\r\nC=3", [1, 4]),
    ("A=1\nx y\nB=2\nz w\nC=3", [2, 4]),
    ("x y\r\nC=3", [1]),
    ("A=1\r\nz w", [2]),
    ("A=1\r\nB=2\r\nz w", [3]),
    ("A=1\r\nB=2\r\nC=3\r\nz w", [4]),
    ("A=1\r\nB=2\r\nC=3\r\nD=4\r\nz w", [5]),
    ("A=1\nB=2\nC=3\nz w", [4]),
    ("A\r\nB\r\nz w", [3]),
    ("A=1\nB=2\r\nz w", [3]),
    ("A=1\r\nB=2\nz w", [3]),
    ("A=\"x\r\ny\"\r\nz w", [3]),
    ("A=1\r\n\r\nz w", [2]),
    ("A=1\r\nB=2\r\nz w\r\nD=4\r\ne f", [3, 6]),
    ("x y\r\nD=4\r\ne f", [1, 4]),
    ("x y\r\nD=4\r\nE=5\r\nf g", [1, 5]),
    ("A=1\r\nx y\r\nB=2\r\nC=3\r\nz w", [2, 6]),
    ("x y\r\ne f\r\nD=4\r\ng h", [1, 2, 6]),
    ("A=1\r\nx y\r\ne f\r\nB=2\r\nz w", [2, 3, 7]),
]

# Binding grammar (my own), returns match length (consumed, NOT incl terminator)
# or None if the statement at this point is a parse error.
KEY = r"(?:export[ \t\f\v]+)?(?:'[^']*'|[^\s=]+)"
# value branches
SQ = r"'(?:\\'|[^'])*'"
DQ = r'"(?:\\"|[^"])*"'
# A single "logical line" up to the first real newline (\n) — but double-quote
# values may contain newlines.

def match_binding(rest):
    """Return (consumed_len) of KEY[=VALUE] not including the line terminator,
    or None if parse error. The terminator handling is done by caller."""
    m = re.match(r"[ \t\f\v]*", rest)
    i = m.end()
    km = re.match(KEY, rest[i:])
    if not km:
        return None
    j = i + km.end()
    # after key: optional ws
    m2 = re.match(r"[ \t\f\v]*", rest[j:])
    j += m2.end()
    if j >= len(rest) or rest[j] in "\r\n":
        # bare key, value None. OK as long as nothing else on line (handled: we're at EOL)
        return j
    if rest[j] == "#":
        return j  # trailing comment, bare key
    if rest[j] != "=":
        return None
    j += 1  # consume '='
    m3 = re.match(r"[ \t\f\v]*", rest[j:])
    j += m3.end()
    # value
    if j < len(rest) and rest[j] == "'":
        vm = re.match(SQ, rest[j:])
        if not vm:
            return None
        j += vm.end()
    elif j < len(rest) and rest[j] == '"':
        vm = re.match(DQ, rest[j:], re.DOTALL)
        if not vm:
            return None
        j += vm.end()
    else:
        # unquoted: up to end-of-line or ws+comment
        vm = re.match(r"[^\r\n]*?(?=[ \t]+#|[ \t]*(?:\r|\n|$))", rest[j:])
        j += vm.end()
        # swallow trailing ws+comment on this line
    # trailing ws + optional comment, must reach EOL
    tm = re.match(r"[ \t\f\v]*(?:#[^\r\n]*)?", rest[j:])
    j += tm.end()
    if j < len(rest) and rest[j] not in "\r\n":
        return None
    return j


def simulate(content, term_counts_cr, recovery_mode):
    rest = content
    line = 1
    warnings = []
    guard = 0
    while rest:
        guard += 1
        if guard > 10000:
            break
        stmt_start = line
        # leading blank/comment/whitespace lines
        bm = re.match(r"(?:[ \t\f\v]*(?:#[^\r\n]*)?(?:\r\n|\r|\n))*", rest)
        blanks = bm.group(0)
        # but only if what's after is not immediately content on same prefix...
        line += blanks.count("\n")
        rest = rest[bm.end():]
        if not rest:
            break
        consumed = match_binding(rest)
        if consumed is not None:
            text = rest[:consumed]
            line += text.count("\n")
            rest = rest[consumed:]
            # consume terminator
            tm = re.match(r"\r\n|\r|\n", rest)
            if tm:
                t = tm.group(0)
                if t == "\n" or t == "\r\n":
                    line += 1
                elif t == "\r":
                    line += 1 if term_counts_cr else 0
                rest = rest[tm.end():]
        else:
            warnings.append(stmt_start)
            if recovery_mode == "to_nl_incl":
                nl = rest.find("\n")
                if nl < 0:
                    rest = ""
                else:
                    line += 1
                    rest = rest[nl + 1:]
            elif recovery_mode == "dot_star":
                # consume .* (up to \n not incl), leaving \n for next prefix
                dm = re.match(r"[^\n]*", rest)
                rest = rest[dm.end():]
                # do not count line here; the \n left will be counted by next blanks
    return warnings


def main():
    for term_cr in (True, False):
        for rec in ("to_nl_incl", "dot_star"):
            ok = 0
            fails = []
            for content, exp in OBS:
                got = simulate(content, term_cr, rec)
                if got == exp:
                    ok += 1
                else:
                    fails.append((content, exp, got))
            print(f"term_cr={term_cr} rec={rec}: {ok}/{len(OBS)}")
            if fails and ok >= len(OBS) - 6:
                for c, e, g in fails:
                    print("   FAIL", repr(c), "exp", e, "got", g)


if __name__ == "__main__":
    main()
