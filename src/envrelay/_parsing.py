"""Turn the text of an env document into an ordered list of entries.

The grammar implemented here was derived entirely from black-box observation of
the reference's behavior (see ``scripts/`` probes and SPEC.md); none of the
reference's own source, regexes, or module layout were consulted.

A *document* is a sequence of *statements*. A statement is one of:

* a blank line or a whitespace-only line (ignored),
* a comment line beginning (after optional spaces/tabs) with ``#`` (ignored),
* a binding ``KEY`` or ``KEY=VALUE``.

Bindings and the quirks of comment, quote, escape, and line-ending handling are
documented inline. The parser also reports, for each statement it cannot make
sense of, the 1-based line where that statement began -- including the odd line
drift that appears when a document read from a stream uses CRLF/CR endings.
"""

from __future__ import annotations

import re
from typing import NamedTuple


# A unit of parsed content. ``value is None`` marks a key written with no "="
# (e.g. a bare ``FOO`` line).
class Entry(NamedTuple):
    key: str
    value: str | None


class ParseResult(NamedTuple):
    entries: list  # list[Entry]
    error_lines: list  # list[int] -- 1-based reported line of each bad statement


class Segment(NamedTuple):
    """A piece of the document, for in-place rewriting.

    ``kind`` is "bind" for a binding (``key``/``value`` set) or "raw" for text
    kept verbatim (blank lines, comments, and lines that failed to parse).
    ``text`` is the exact original span (newline-normalized).
    """

    kind: str
    key: str | None
    value: str | None
    text: str


class ScanResult(NamedTuple):
    segments: list  # list[Segment]
    error_lines: list


# --- character classes -------------------------------------------------------
# Horizontal whitespace that may pad tokens. Newlines are handled separately.
_H = r"[ \t]"
# A line terminator: CRLF first so it is taken as a single break.
_TERM = re.compile(r"\r\n|\r|\n")
# Counts universal line breaks in a chunk of text.
_BREAKS = re.compile(r"\r\n|\r|\n")

# A single blank / whitespace-only line (with its terminator), and a single
# comment line (with its terminator). A trailing blank/comment line with no
# terminator (at end of file) is matched separately.
_BLANK_LINE = re.compile(_H + r"*(?:\r\n|\r|\n)")
_COMMENT_LINE = re.compile(_H + r"*#[^\r\n]*(?:\r\n|\r|\n)")
_TRAILING_BLANK = re.compile(_H + r"*(?:#[^\r\n]*)?\Z")

# A key: either a complete single-quoted run (quotes stripped), or a bare run
# whose first character is not whitespace/"="/"#"/"'" and whose remaining
# characters are not whitespace/"="/"#". So a "'" only starts a quoted key (which
# must be terminated, else it is a parse error), but a "'" later in a bare key is
# an ordinary character, and a double-quoted key keeps its quotes.
_KEY = re.compile(r"'[^']*'|[^\s=#'][^\s=#]*")
# The optional ``export`` keyword, only when followed by whitespace.
_EXPORT = re.compile(r"export" + _H + r"+")

# Quoted values. An escaped character is a backslash followed by anything; this
# lets a quote be escaped inside its own quoting without ending the value.
_SINGLE = re.compile(r"'(?:\\.|[^'\\])*'", re.DOTALL)
_DOUBLE = re.compile(r'"(?:\\.|[^"\\])*"', re.DOTALL)

# Sentinel returned by _try_binding for an "export + comment" line: no entry and
# no parse error.
_COMMENT = object()
# Sentinel returned by _try_binding for a parse error; paired with the furthest
# position the attempt reached, so recovery resumes from there (which matters
# when a quoted value already consumed one or more newlines before the failure).
_ERROR = object()

_ESCAPE = re.compile(r"\\(.)", re.DOTALL)
# Escapes decoded inside double quotes.
_DQ_MAP = {
    "\\": "\\",
    "'": "'",
    '"': '"',
    "a": "\a",
    "b": "\b",
    "f": "\f",
    "n": "\n",
    "r": "\r",
    "t": "\t",
    "v": "\v",
}
# Escapes decoded inside single quotes.
_SQ_MAP = {"\\": "\\", "'": "'"}


def _decode(inner: str, table: dict) -> str:
    def repl(m: re.Match) -> str:
        c = m.group(1)
        if c in table:
            return table[c]
        return "\\" + c

    return _ESCAPE.sub(repl, inner)


def _count_breaks(text: str) -> int:
    return len(_BREAKS.findall(text))


def normalize_newlines(text: str) -> str:
    """Collapse CRLF and lone CR to LF.

    Applied to text read from a file path (but never to text from a stream),
    matching the reference's split behavior between the two sources.
    """
    return text.replace("\r\n", "\n").replace("\r", "\n")


class _Cursor:
    """A forward-only reader over the document, tracking the current line."""

    __slots__ = ("text", "pos", "line")

    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.line = 1

    def at_end(self) -> bool:
        return self.pos >= len(self.text)

    def advance_to(self, new_pos: int) -> None:
        self.line += _count_breaks(self.text[self.pos : new_pos])
        self.pos = new_pos


def _match_value(text: str, i: int):
    """Parse a value starting at ``i`` (already past "=" and padding).

    Returns ``(value, end_index)`` where ``end_index`` is just past the value
    token (for quoted values) or just past the last non-comment character (for
    unquoted values). Returns ``None`` on an unterminated quote.
    """
    n = len(text)
    # Look past spaces/tabs to decide whether a quoted value follows.
    j = i
    while j < n and text[j] in " \t":
        j += 1
    if j < n and text[j] == "'":
        m = _SINGLE.match(text, j)
        if not m:
            return None
        return _decode(m.group(0)[1:-1], _SQ_MAP), m.end()
    if j < n and text[j] == '"':
        m = _DOUBLE.match(text, j)
        if not m:
            return None
        return _decode(m.group(0)[1:-1], _DQ_MAP), m.end()
    # Unquoted: the value runs from just after "=" to end of line, then a
    # trailing " #..." comment (a "#" preceded by whitespace) and surrounding
    # spaces/tabs are trimmed. A "#" that directly follows "=" stays part of the
    # value, so leading whitespace is kept until after comment detection.
    k = i
    while k < n and text[k] not in "\r\n":
        k += 1
    raw = text[i:k]
    cm = re.search(r"[ \t]#", raw)
    if cm:
        raw = raw[: cm.start()]
    return raw.strip(" \t"), k


def _try_binding(text: str, start: int):
    """Try to parse one binding beginning at ``start``.

    Returns ``(Entry, end_index)`` on success (``end_index`` is just past the
    line terminator, or len(text) at EOF), or ``None`` if the statement is not a
    valid binding.
    """
    n = len(text)
    i = start
    # leading horizontal whitespace
    while i < n and text[i] in " \t":
        i += 1
    # optional export prefix (only as a standalone keyword + whitespace)
    em = _EXPORT.match(text, i)
    if em:
        i = em.end()
        # "export" + whitespace + comment is a comment line (no entry, no
        # error); "export" + whitespace + end-of-line or "=" is an error.
        if i < n and text[i] == "#":
            j = i
            while j < n and text[j] not in "\r\n":
                j += 1
            tm = _TERM.match(text, j)
            return _COMMENT, (tm.end() if tm else j)
    # key
    km = _KEY.match(text, i)
    if not km:
        return _ERROR, i
    raw_key = km.group(0)
    i = km.end()
    if len(raw_key) >= 2 and raw_key[0] == "'" and raw_key[-1] == "'":
        key = raw_key[1:-1]
    else:
        key = raw_key
    # padding after key
    while i < n and text[i] in " \t":
        i += 1
    # end of line, or comment -> bare key with no value
    if i >= n or text[i] in "\r\n":
        return _finish(text, key, None, i)
    if text[i] == "#":
        # comment runs to end of line
        while i < n and text[i] not in "\r\n":
            i += 1
        return _finish(text, key, None, i)
    if text[i] != "=":
        return _ERROR, i
    i += 1  # consume "="
    value_start = i
    parsed = _match_value(text, i)
    if parsed is None:
        return _ERROR, value_start
    value, i = parsed
    # trailing padding + optional comment, then must reach end of line
    while i < n and text[i] in " \t":
        i += 1
    if i < n and text[i] == "#":
        while i < n and text[i] not in "\r\n":
            i += 1
    if i < n and text[i] not in "\r\n":
        return _ERROR, i
    return _finish(text, key, value, i)


def _finish(text: str, key: str, value, i: int):
    """Consume a single trailing line terminator and build the entry."""
    m = _TERM.match(text, i)
    end = m.end() if m else i
    return Entry(key, value), end


def _skip_bad_line(text: str, i: int):
    """Skip the remainder of a line after a parse failure.

    Returns ``(terminator_is_crlf, end_index)``. ``end_index`` is just past the
    next terminator (or EOF). Only a ``\r\n`` terminator feeds the line drift; a
    lone ``\r`` does not.
    """
    m = _TERM.search(text, i)
    if not m:
        return False, len(text)
    return (m.group(0) == "\r\n"), m.end()


def scan(text: str) -> ScanResult:
    """Scan ``text`` into ordered segments and the reported bad-statement lines.

    A leading UTF-8 BOM is dropped (and not re-emitted), matching the reference.
    (Testing the first character with ``in`` also means a bytes value -- e.g. a
    binary stream passed by mistake -- raises the same ``TypeError`` the
    reference raises, rather than a differently-worded one.)
    """
    if "﻿" in text[:1]:
        text = text[1:]
    cur = _Cursor(text)
    segments: list = []
    error_lines: list = []
    # Line-number drift seen when text from a stream uses CR-bearing endings.
    # A statement that fails on a CR-terminated line leaves a stray carry of 1;
    # that carry is folded into the running ``drift`` at the next non-blank,
    # non-failing event (a comment or a successful binding) -- and, for a run of
    # consecutive failures, one statement late. Blank lines are transparent.
    drift = 0
    carry = 0
    guard = 0
    n = len(text)
    while not cur.at_end():
        guard += 1
        if guard > n + 2:
            break
        # Consume leading blank and comment lines. The reported line for the
        # statement that follows is the start of the run of blank lines that
        # immediately precedes it; a comment line resets that start (blanks
        # before a comment do not count), while blank lines after a comment do.
        start_line = cur.line
        consumed_leading = True
        while consumed_leading and not cur.at_end():
            consumed_leading = False
            mb = _BLANK_LINE.match(text, cur.pos)
            if mb and mb.end() > cur.pos:
                segments.append(Segment("raw", None, None, text[cur.pos : mb.end()]))
                cur.advance_to(mb.end())
                consumed_leading = True
                continue
            mc = _COMMENT_LINE.match(text, cur.pos)
            if mc and mc.end() > cur.pos:
                segments.append(Segment("raw", None, None, text[cur.pos : mc.end()]))
                cur.advance_to(mc.end())
                start_line = cur.line  # a comment resets the leading-blank start
                drift += carry  # a comment folds in any pending carry
                carry = 0
                consumed_leading = True
                continue
        if cur.at_end():
            break
        # a final blank/comment line with no terminator ends the document
        tb = _TRAILING_BLANK.match(text, cur.pos)
        if tb and tb.end() == n:
            segments.append(Segment("raw", None, None, text[cur.pos : n]))
            cur.advance_to(n)
            break
        result = _try_binding(text, cur.pos)
        if result[0] is _COMMENT:
            # An "export + comment" line is a comment: no entry, no error; it
            # folds in any pending carry like any other comment line.
            end = result[1]
            segments.append(Segment("raw", None, None, text[cur.pos : end]))
            cur.advance_to(end)
            drift += carry
            carry = 0
        elif result[0] is _ERROR:
            error_lines.append(start_line + drift)
            # Resume after whatever the failed attempt consumed (a quoted value
            # may have crossed newlines) and skip to the next terminator.
            is_crlf, end = _skip_bad_line(text, result[1])
            segments.append(Segment("raw", None, None, text[cur.pos : end]))
            cur.advance_to(end)
            # Fold in the previous statement's carry, then leave our own.
            drift += carry
            carry = 1 if is_crlf else 0
        else:
            entry, end = result
            segments.append(
                Segment("bind", entry.key, entry.value, text[cur.pos : end])
            )
            cur.advance_to(end)
            drift += carry
            carry = 0
    return ScanResult(segments, error_lines)


def parse(text: str) -> ParseResult:
    """Parse ``text`` into entries and the reported lines of bad statements."""
    result = scan(text)
    entries = [
        Entry(seg.key, seg.value) for seg in result.segments if seg.kind == "bind"
    ]
    return ParseResult(entries, result.error_lines)
