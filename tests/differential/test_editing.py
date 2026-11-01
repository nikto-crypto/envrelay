"""Differential tests for set_key / get_key / unset_key sequences (channel 4).

Each scenario applies a sequence of edits to a starting file (absent, empty,
duplicate keys, CRLF, comments/export, quoted) and compares the return values,
log records, raised errors, the resulting directory (names, types, permission
bits, symlink targets, exact bytes), and whether the target's inode changed.
"""

from __future__ import annotations

import os

from hypothesis import given, settings, HealthCheck

import diff_helpers
import grammar

_SCALE = int(os.environ.get("ENVRELAY_SCALE", "300"))

_COMMON = dict(
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large],
)


@settings(max_examples=_SCALE * 17, **_COMMON)
@given(scenario=grammar.edit_scenario())
def test_edit_sequences(scenario):
    initial, ops, make_symlink = scenario
    ok, summaries = diff_helpers.compare_edit_sequence(
        initial, ops, make_symlink=make_symlink
    )
    assert ok, "edit mismatch: initial=%r ops=%r symlink=%s\n mine=%r\n ora =%r" % (
        initial,
        ops,
        make_symlink,
        summaries["mine"],
        summaries["ora"],
    )
