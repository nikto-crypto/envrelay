"""Tests for the single comparison normalizer."""

from __future__ import annotations

import normalizer


def test_version_line():
    assert (
        normalizer.normalize(
            "python -m dotenv, version 1.2.4\n", "python -m dotenv", "1.2.4"
        )
        == "<PROG>, version <VERSION>\n"
    )
    assert (
        normalizer.normalize(
            "python -m envrelay, version 0.1.0\n", "python -m envrelay", "0.1.0"
        )
        == "<PROG>, version <VERSION>\n"
    )


def test_usage_and_try_lines():
    text = "Usage: dotenv run [OPTIONS]...\nTry 'dotenv run --help' for help.\n"
    out = normalizer.normalize(text, "dotenv", "1.2.4")
    assert out == "Usage: <PROG> run [OPTIONS]...\nTry '<PROG> run --help' for help.\n"


def test_keeps_python_dotenv_message():
    # "python-dotenv" must survive; only the program name is mapped.
    text = "python-dotenv could not parse statement starting at line 2"
    assert normalizer.normalize(text, "dotenv", "1.2.4") == text


def test_traceback_reduced_to_final_line():
    tb = (
        "Traceback (most recent call last):\n"
        '  File "x.py", line 1, in <module>\n'
        '    raise IsADirectoryError(21, "Is a directory")\n'
        "IsADirectoryError: [Errno 21] Is a directory: 'adir'\n"
    )
    assert (
        normalizer.normalize(tb)
        == "IsADirectoryError: [Errno 21] Is a directory: 'adir'\n"
    )


def test_tmpdir_both_spellings():
    assert normalizer.normalize("at /var/x/.env", tmpdir="/var/x") == "at <TMPDIR>/.env"
    assert (
        normalizer.normalize("at /private/var/x/.env", tmpdir="/var/x")
        == "at <TMPDIR>/.env"
    )


def test_tmp_random_name():
    assert (
        normalizer.normalize("No such file: '/d/.tmp_ab12cd'")
        == "No such file: '/d/.tmp_<RAND>'"
    )


def test_none_passthrough():
    assert normalizer.normalize(None) is None
