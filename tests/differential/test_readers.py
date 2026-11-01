"""Differential tests for dotenv_values and load_dotenv (channels 1-3).

Each generated document is read every way: dotenv_values via stream and via file,
with interpolation on and off, and load_dotenv with override on/off and verbose,
against generated preexisting environment variables. Results, log records, and
os.environ effects must match the oracle exactly.
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


@settings(max_examples=_SCALE * 20, **_COMMON)
@given(text=grammar.env_documents())
def test_dotenv_values_all_modes(text):
    for interpolate in (True, False):
        for via_file in (False, True):
            ok, detail = diff_helpers.compare_dotenv_values(text, interpolate, via_file)
            assert ok, (
                "dotenv_values mismatch: interpolate=%s via_file=%s text=%r\n%r"
                % (interpolate, via_file, text, detail)
            )


@settings(max_examples=_SCALE * 5, **_COMMON)
@given(text=grammar.env_documents(), env=grammar.preexisting_env())
def test_dotenv_values_with_env_overlap(text, env):
    saved = dict(os.environ)
    os.environ.update(env)
    try:
        ok, detail = diff_helpers.compare_dotenv_values(text, True, False)
    finally:
        os.environ.clear()
        os.environ.update(saved)
    assert ok, "dotenv_values(env overlap) mismatch: env=%r text=%r\n%r" % (
        env,
        text,
        detail,
    )


@settings(max_examples=_SCALE * 5, **_COMMON)
@given(text=grammar.env_documents(), env=grammar.preexisting_env())
def test_load_dotenv_effects(text, env):
    for override in (False, True):
        for interpolate in (True, False):
            ok, detail = diff_helpers.compare_load_dotenv(
                text, override, interpolate, verbose=True, base_env=env
            )
            assert ok, (
                "load_dotenv mismatch: override=%s interpolate=%s env=%r text=%r\n%r"
                % (override, interpolate, env, text, detail)
            )
