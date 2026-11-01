"""Shared fixtures and skip policy for the differential suite.

The suite compares envrelay against the python-dotenv 1.2.4 oracle. It runs only
when the interpreter matches what the oracle was built for; otherwise every
differential test skips -- unless ``ENVRELAY_REQUIRE_ORACLE=1``, which turns each
such skip into a failure.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import oracle_iface  # noqa: E402

_OK, _REASON = oracle_iface.availability()
_REQUIRE = os.environ.get("ENVRELAY_REQUIRE_ORACLE") == "1"


def _gate():
    if _OK:
        return
    message = "oracle unavailable: %s" % _REASON
    if _REQUIRE:
        pytest.fail(message, pytrace=False)
    pytest.skip(message)


@pytest.fixture(scope="session")
def oracle():
    _gate()
    return oracle_iface.load()


@pytest.fixture(scope="session")
def oracle_cli_group():
    _gate()
    return oracle_iface.load_cli_group()


@pytest.fixture(autouse=True)
def _gate_every_test():
    """Ensure every test in this directory honours the oracle gate."""
    _gate()


@pytest.fixture(autouse=True)
def fixed_environment(monkeypatch):
    """Pin the locale/terminal environment and give each test a clean slate.

    ``os.environ`` is restored after the test by monkeypatch. Variables that a
    case sets for interpolation/override are removed up front so nothing is
    inherited.
    """
    monkeypatch.setenv("TERM", "dumb")
    monkeypatch.setenv("COLUMNS", "80")
    monkeypatch.setenv("LANG", "en_US.UTF-8")
    monkeypatch.setenv("LC_ALL", "en_US.UTF-8")
    monkeypatch.setenv("TZ", "UTC")
    monkeypatch.delenv("PYTHONUTF8", raising=False)
    monkeypatch.delenv("PYTHON_DOTENV_DISABLED", raising=False)
    for name in ("A", "B", "C", "D", "E", "X", "Y", "Z", "GREETING", "FOO", "BAR"):
        monkeypatch.delenv(name, raising=False)
    yield


def _no_env_above(path):
    current = os.path.abspath(path)
    while True:
        if os.path.exists(os.path.join(current, ".env")):
            return False
        parent = os.path.dirname(current)
        if parent == current:
            return True
        current = parent


@pytest.fixture
def case_dir(tmp_path):
    """A per-case directory, verified to have no ``.env`` in any parent."""
    d = tmp_path
    assert _no_env_above(
        os.path.dirname(str(d))
    ), "a .env exists above the temp root; find_dotenv would walk into it"
    return str(d)


def subprocess_env(columns=80, extra=None):
    """A clean environment dict for subprocess/pty CLI runs."""
    env = {
        "PATH": os.environ.get("PATH", ""),
        "TERM": "dumb",
        "COLUMNS": str(columns),
        "LANG": "en_US.UTF-8",
        "LC_ALL": "en_US.UTF-8",
        "TZ": "UTC",
        "HOME": os.environ.get("HOME", "/tmp"),
    }
    if extra:
        env.update(extra)
    return env
