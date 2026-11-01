"""The single normalizer used before any differential comparison.

It applies exactly the normalizations the study allows and no others:

* reduce a traceback to its final ``ExceptionClass: message`` line;
* map the program name (``dotenv`` / ``python -m dotenv`` vs the envrelay
  equivalents) to ``<PROG>`` where it appears as the program name -- in usage
  lines, ``Try '... --help'`` hints, and the ``--version`` line;
* map the version number to ``<VERSION>`` in the ``--version`` line;
* map the per-case temp directory (both ``/var`` and ``/private/var`` spellings)
  to ``<TMPDIR>``;
* map the random part of a ``.tmp_<random>`` temporary file name to ``<RAND>``.

The same function is applied to both the oracle's and envrelay's output with the
side-appropriate ``prog``/``version``, so matching inputs produce identical text.
"""

from __future__ import annotations

import re

_TB_MARKER = "Traceback (most recent call last):"
_TMP_RE = re.compile(r"\.tmp_[A-Za-z0-9_]+")


def normalize(text, prog=None, version=None, tmpdir=None):
    if text is None:
        return None
    # 1. traceback reduction
    if _TB_MARKER in text:
        before, _, tb = text.partition(_TB_MARKER)
        lines = [ln for ln in tb.splitlines() if ln.strip()]
        trailing = "\n" if text.endswith("\n") else ""
        text = before + (lines[-1] if lines else "") + trailing
    # 2. program name + version
    if prog is not None:
        if version is not None:
            text = text.replace(
                "%s, version %s" % (prog, version), "<PROG>, version <VERSION>"
            )
        text = text.replace("Usage: %s" % prog, "Usage: <PROG>")
        text = text.replace("Try '%s" % prog, "Try '<PROG>")
    # 3. temp directory (both spellings)
    if tmpdir:
        private = tmpdir if tmpdir.startswith("/private") else "/private" + tmpdir
        text = text.replace(private, "<TMPDIR>")
        text = text.replace(tmpdir, "<TMPDIR>")
    # 4. random temp file names
    text = _TMP_RE.sub(".tmp_<RAND>", text)
    return text
