"""Variable expansion for parsed values.

Only the brace form is recognised: ``${name}`` and ``${name:-default}``. A bare
``$name`` is left untouched, a ``$`` not followed by ``{`` is literal, and the
default clause is substituted verbatim (it is never expanded again). The name
runs up to the first ``}``; the first ``:-`` inside splits name from default, so
``${a-b}`` looks up a variable literally named ``a-b``.

A name counts as *present* when it resolves in the lookup (empty string
included); only a genuinely absent name falls back to the default (or to the
empty string when there is no default). Expansion is a single left-to-right
pass with no nesting.
"""

from __future__ import annotations

import re
from collections import OrderedDict
from collections.abc import Callable

_REF = re.compile(r"\$\{([^}]*)\}")


def expand(value: str, lookup: Callable[[str], tuple[bool, str | None]]) -> str:
    """Expand ``${...}`` references in ``value`` using ``lookup``.

    ``lookup(name)`` returns ``(found, value)``.
    """

    def repl(match: re.Match) -> str:
        inner = match.group(1)
        sep = inner.find(":-")
        if sep >= 0:
            name = inner[:sep]
            default = inner[sep + 2 :]
        else:
            name = inner
            default = None
        found, resolved = lookup(name)
        if found:
            return resolved if resolved is not None else ""
        return default if default is not None else ""

    return _REF.sub(repl, value)


def resolve(entries, environ) -> OrderedDict:
    """Resolve a list of entries into an OrderedDict, expanding as we go.

    A reference resolves against values already produced (earlier in the
    document) first, then against ``environ``. Entries with ``value is None``
    are kept as ``None`` and are not treated as a source for expansion.
    """
    out: OrderedDict = OrderedDict()
    for key, value in entries:
        if value is None:
            out[key] = None
            continue

        def lookup(name: str):
            # A key already seen (even one with value None, which expands to "")
            # counts as present, so its ":-default" does not fire.
            if name in out:
                return True, out[name]
            if name in environ:
                return True, environ[name]
            return False, None

        out[key] = expand(value, lookup)
    return out


def resolve_plain(entries) -> OrderedDict:
    """Build an OrderedDict with no interpolation (last duplicate wins)."""
    out: OrderedDict = OrderedDict()
    for key, value in entries:
        out[key] = value
    return out
