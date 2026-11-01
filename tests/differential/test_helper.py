"""Differential tests for get_cli_string (channel 6)."""

from __future__ import annotations

import itertools

import envrelay


def _norm(text, prog):
    # The program name is normalized: the helper's first word is 'dotenv'
    # (oracle) or 'envrelay' (mine).
    if text == prog:
        return "<PROG>"
    if text.startswith(prog + " "):
        return "<PROG>" + text[len(prog) :]
    return text


def test_get_cli_string_all_combos(oracle):
    paths = [None, "p", "a path", "/x/y.env"]
    actions = [None, "get", "set", "list", "unset", "run"]
    keys = [None, "K", "k k", "it's"]
    values = [None, "v", "v v", "a\tb", "x#y", ""]
    quotes = [None, "always", "never", "auto"]
    count = 0
    for path, action, key, value, quote in itertools.product(
        paths, actions, keys, values, quotes
    ):
        mine = envrelay.get_cli_string(path, action, key, value, quote)
        ora = oracle.get_cli_string(path, action, key, value, quote)
        assert _norm(mine, "dotenv") == _norm(ora, "dotenv"), (
            "get_cli_string(%r,%r,%r,%r,%r): mine=%r ora=%r"
            % (path, action, key, value, quote, mine, ora)
        )
        count += 1
    assert count >= 1000
