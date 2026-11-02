"""Hypothesis strategies that build .env documents and related inputs.

The grammar aims to exercise every input class the study calls for: key shapes,
export prefixes and near-misses, spacing around "=", unquoted/single/double/
unterminated values, every escape sequence (known, unknown, malformed), comments
in each position, interpolations (forward/backward/self, defaults, unbalanced
braces), multiline values, LF/CRLF/CR/mixed endings, a BOM, blank and
whitespace-only lines, no final newline, long lines, control characters, and
non-ASCII. All seed fragments here are invented for this project.
"""

from __future__ import annotations

from hypothesis import strategies as st

# --- key fragments -----------------------------------------------------------
_PLAIN_KEYS = ["A", "B", "KEY", "name", "foo", "VAR1", "x"]
_FANCY_KEYS = [
    "A.B",
    "A-B",
    "A:B",
    "A.B-C:D",
    "a_b",
    "café",
    "SNAKE_CASE",
    "export",  # the keyword as a key
    "'quoted key'",
    "'q k'",
    '"dq"',
    "KEY#x",  # a '#' splits here
    "''",  # empty single-quoted key (a parse error)
    "' '",  # single-quoted space key
    '""',  # double-quoted empty -> key '""'
]
keys = st.sampled_from(_PLAIN_KEYS + _FANCY_KEYS)

# --- value fragments ---------------------------------------------------------
_SIMPLE_VALUES = ["1", "", "value", "two words", "é", "a_b", "x#y", "123", "-7"]
_ESCAPES = [
    r"\n",
    r"\t",
    r"\r",
    r"\\",
    r"\'",
    r"\"",
    r"\a",
    r"\b",
    r"\f",
    r"\v",
    r"\0",
    r"\x41",
    r"A",
    r"\q",
    r"\ ",
]
_INTERP = [
    "${A}",
    "${MISSING:-def}",
    "$A",
    "${A:-x}${C}",
    "${A-x}",
    "${A:-${C}}",
    "${}",
    "${A}}",
    "pre${B}post",
    "$${A}",
    "\\${A}",
    "${A:-de fault}",
    "${self}",
    # every brace form / shell operator (only ${name} and ${name:-default}
    # expand; all other colon forms stay literal)
    "${A:?err}",
    "${A:+alt}",
    "${A:=d}",
    "${A?e}",
    "${A+p}",
    "${A=d}",
    "${A-a:b}",
    "${a:b:-c}",
    "${A::}",
    "${A:}",
    "${:-x}",
    "${:-}",
    "${a:-b:-c}",
    "${A.B:-x}",
    "${A-B-C}",
    "${A B:-x}",
    "${A",
    "${{A}}",
    "x${A:?e}y${B}",
    # malformed / unclosed brace forms followed by a valid reference
    "${a:x${B}",
    "${a${B}",
    "${${B}}",
    "${a:${B}}",
    "${a:-x${B}}",
    "${a}x${B}",
    "pre${a:b${B}post",
]
_CONTROL = ["a\x01b", "tab\there", "bell\x07", "x\x0cy"]

# Every character for which str.isspace() is true (space, tab, the C0 whitespace
# controls, NEL, NBSP, line/paragraph separators, and representative Unicode
# spaces), plus a couple of non-whitespace control characters.
_WS = [
    " ",
    "\t",
    "\x0b",
    "\x0c",
    "\x1c",
    "\x1d",
    "\x1e",
    "\x1f",
    "\x85",
    "\xa0",
    " ",
    " ",
    " ",
    "　",
]
_CTRL = ["\x00", "\x01", "\x07"]


@st.composite
def _unquoted_value(draw):
    return draw(st.sampled_from(_SIMPLE_VALUES + _INTERP + _CONTROL))


@st.composite
def _single_quoted(draw):
    body = draw(
        st.sampled_from(
            ["a'b", "plain", "line1\nline2", "${A}", r"\n stays", "", "it\\'s"]
        )
    )
    return "'" + body + "'"


@st.composite
def _double_quoted(draw):
    body = draw(
        st.sampled_from(
            [
                "plain",
                r"a\nb",
                r"x\r\ny",
                "line1\nline2",
                "${A}",
                r"\x41 stays",
                r"\q stays",
                "é",
                "with # hash",
                "",
            ]
        )
    )
    return '"' + body + '"'


@st.composite
def _value(draw):
    kind = draw(st.integers(min_value=0, max_value=4))
    if kind == 0:
        return draw(_unquoted_value())
    if kind == 1:
        return draw(_single_quoted())
    if kind == 2:
        return draw(_double_quoted())
    if kind == 3:
        # unterminated quote
        return draw(st.sampled_from(['"oops', "'oops", '"a${A}']))
    return draw(st.sampled_from(_ESCAPES))  # bare escape as unquoted value


@st.composite
def _ws(draw):
    """A short run of horizontal whitespace, biased toward exotic characters."""
    n = draw(st.integers(min_value=0, max_value=2))
    return "".join(draw(st.sampled_from(_WS)) for _ in range(n))


@st.composite
def _binding_line(draw):
    key = draw(keys)
    export = draw(
        st.sampled_from(["", "export ", "export\t", "export  ", "export\xa0"])
    )
    lead = draw(_ws())  # whitespace before the key / export
    has_eq = draw(st.booleans())
    if not has_eq:
        # bare key, maybe trailing whitespace/comment (exotic ws included)
        tail = draw(_ws())
        comment = draw(st.sampled_from(["", "# c", "#x"]))
        return lead + export + key + tail + comment
    pre = draw(_ws())
    post = draw(_ws())
    value = draw(_value())
    trail = draw(_ws())
    comment = draw(st.sampled_from(["", "# c", "#nospace", "\t# c"]))
    return lead + export + key + pre + "=" + post + value + trail + comment


@st.composite
def _other_line(draw):
    return draw(
        st.sampled_from(
            [
                "",
                "   ",
                "\t",
                "# a full comment",
                "   # indented comment",
                "A B",  # parse error: space in bare key
                "A='x' y",  # parse error: trailing junk
                "=1",  # parse error: empty key
                "key with space=1",  # parse error
                "A" + "x" * 300 + "=longkey",  # long line
                "LONG=" + "v" * 500,  # long value
                "''=x",  # parse error: empty single-quoted key
                "''",  # parse error: empty single-quoted key, no value
                '""=x',  # key '""' kept
                "' '=x",  # key ' '
                "export ''=x",  # parse error
                "A=val\xa0",  # trailing exotic whitespace
                "A\xa0=b",  # exotic whitespace before '='
                "　A=1",  # leading exotic whitespace
                "A=v\x0c",  # trailing form feed
                "A=v\x1e# c",  # exotic whitespace before comment
                "A=\x85v",  # exotic whitespace after '='
            ]
        )
    )


@st.composite
def _line(draw):
    if draw(st.integers(min_value=0, max_value=4)) == 0:
        return draw(_other_line())
    return draw(_binding_line())


_TERMINATORS = ["\n", "\r\n", "\r"]


@st.composite
def env_documents(draw):
    """A full .env document (text), with varied line endings and shape."""
    n = draw(st.integers(min_value=0, max_value=8))
    lines = [draw(_line()) for _ in range(n)]
    # choose a terminator per line (mixed endings allowed)
    pieces = []
    for ln in lines:
        term = draw(st.sampled_from(_TERMINATORS))
        pieces.append(ln + term)
    text = "".join(pieces)
    # maybe drop the final newline
    if draw(st.booleans()) and text.endswith(("\n", "\r")):
        text = text.rstrip("\r\n")
    # maybe prepend a BOM
    if draw(st.integers(min_value=0, max_value=5)) == 0:
        text = "﻿" + text
    return text


_EDIT_KEYS = [
    "A",
    "B",
    "C",
    "NOPE",
    "a b=c",
    "a_b",
    "café",
    "'q'",
    "K#x",
    "export",
    "",
    "' '",
    '""',
]
_EDIT_VALUES = [
    "v",
    "a b",
    "x#y",
    "",
    "é1",
    "it's",
    "a\\b",
    "a\nb",
    "${A}",
    "123",
    "a_b",
]
_QUOTE_MODES = ["always", "never", "auto"]
_INITIALS = [
    None,
    b"",
    b"A=1\n",
    b"A=1",
    b"A=1\nB=2\nA=3\n",
    b"A=1\r\nB=2\r\n",
    b"# c\nexport A=1\nB=2\n",
    b"A='x'\nB=\"y\"\n",
    b"x y\nA=1\n",
]


@st.composite
def edit_op(draw):
    which = draw(st.integers(min_value=0, max_value=2))
    if which == 0:
        return (
            "set_key",
            draw(st.sampled_from(_EDIT_KEYS)),
            draw(st.sampled_from(_EDIT_VALUES)),
            draw(st.sampled_from(_QUOTE_MODES)),
            draw(st.booleans()),  # export
            "utf-8",
            draw(st.booleans()),  # follow_symlinks
        )
    if which == 1:
        return ("get_key", draw(st.sampled_from(_EDIT_KEYS)))
    return (
        "unset_key",
        draw(st.sampled_from(_EDIT_KEYS)),
        draw(st.sampled_from(_QUOTE_MODES)),
        "utf-8",
        draw(st.booleans()),  # follow_symlinks
    )


@st.composite
def edit_scenario(draw):
    initial = draw(st.sampled_from(_INITIALS))
    ops = draw(st.lists(edit_op(), min_size=1, max_size=4))
    make_symlink = (
        draw(st.integers(min_value=0, max_value=4)) == 0 and initial is not None
    )
    return initial, ops, make_symlink


@st.composite
def preexisting_env(draw):
    """A small dict of environment variables that may overlap document keys."""
    names = draw(
        st.lists(
            st.sampled_from(["A", "B", "C", "X", "MISSING", "self"]),
            min_size=0,
            max_size=3,
            unique=True,
        )
    )
    return {name: draw(st.sampled_from(["env", "5", "", "9"])) for name in names}
