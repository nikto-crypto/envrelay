"""Original unit tests for envrelay, standing on their own (no oracle).

Every expected value here is asserted directly from envrelay's documented
behavior; these tests pass on any supported interpreter without the oracle.
"""

from __future__ import annotations

import io
import logging
import os
from collections import OrderedDict

import pytest

import envrelay


def dv(text, **kw):
    return envrelay.dotenv_values(stream=io.StringIO(text), **kw)


# --- parsing -----------------------------------------------------------------


def test_basic_pairs():
    assert dv("A=1\nB=two") == OrderedDict([("A", "1"), ("B", "two")])


def test_returns_ordered_dict_repr():
    assert repr(dv("A=1")) == "OrderedDict({'A': '1'})"


def test_bare_key_is_none_and_empty_is_blank():
    assert dv("A") == OrderedDict([("A", None)])
    assert dv("B=") == OrderedDict([("B", "")])


def test_export_prefix_and_keyword_key():
    assert dv("export A=1") == OrderedDict([("A", "1")])
    assert dv("export") == OrderedDict([("export", None)])
    assert dv("export=1") == OrderedDict([("export", "1")])


def test_comment_rules():
    assert dv("A=1 # c") == OrderedDict([("A", "1")])
    assert dv("B=1#c") == OrderedDict([("B", "1#c")])
    assert dv("A=#hash") == OrderedDict([("A", "#hash")])
    assert dv("K= # comment") == OrderedDict([("K", "")])


def test_quotes_and_escapes():
    assert dv(r"A='a\'b\nc'") == OrderedDict([("A", "a'b\\nc")])
    assert dv(r'A="a\nb"') == OrderedDict([("A", "a\nb")])
    assert dv(r'A="\x41"') == OrderedDict([("A", "\\x41")])
    assert dv('A="multi\nline"') == OrderedDict([("A", "multi\nline")])


def test_keys_quoted_and_special():
    assert dv("'q k'=1") == OrderedDict([("q k", "1")])
    assert dv('"dq"=2') == OrderedDict([('"dq"', "2")])
    assert dv("A.B-C:D=1") == OrderedDict([("A.B-C:D", "1")])


def test_duplicate_last_wins():
    assert dv("A=1\nB=2\nA=3") == OrderedDict([("A", "3"), ("B", "2")])


def test_bom_is_ignored():
    assert dv("﻿A=1") == OrderedDict([("A", "1")])


def test_parse_error_is_logged_and_skipped():
    records = []

    class _Cap(logging.Handler):
        def emit(self, record):
            records.append(record.getMessage())

    logger = logging.getLogger("envrelay")
    handler = _Cap()
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    try:
        result = dv("A=1\nbad bad\nB=2")
    finally:
        logger.removeHandler(handler)
    assert result == OrderedDict([("A", "1"), ("B", "2")])
    assert any("line 2" in m for m in records)


def test_stream_keeps_crlf_but_file_folds(tmp_path):
    assert dv('A="x\r\ny"') == OrderedDict([("A", "x\r\ny")])
    p = tmp_path / ".env"
    p.write_bytes(b'A="x\r\ny"')
    assert envrelay.dotenv_values(str(p)) == OrderedDict([("A", "x\ny")])


# --- interpolation -----------------------------------------------------------


def test_interpolation_basic_and_default():
    assert dv("A=${B}\nB=2") == OrderedDict([("A", ""), ("B", "2")])
    assert dv("A=${MISSING:-def}") == OrderedDict([("A", "def")])
    assert dv("A=$B\nB=2") == OrderedDict([("A", "$B"), ("B", "2")])


def test_interpolation_off_keeps_literal():
    assert dv("A=${B}\nB=2", interpolate=False) == OrderedDict(
        [("A", "${B}"), ("B", "2")]
    )


def test_interpolation_reads_environment(monkeypatch):
    monkeypatch.setenv("X", "5")
    assert dv("A=${X}\nX=1\nB=${X}") == OrderedDict(
        [("A", "5"), ("X", "1"), ("B", "1")]
    )


def test_dash_is_part_of_name_not_default():
    assert dv("A=${B-x}\nB=2") == OrderedDict([("A", ""), ("B", "2")])


# --- loading -----------------------------------------------------------------


def test_load_sets_environ_and_returns_true(monkeypatch):
    monkeypatch.delenv("A", raising=False)
    assert envrelay.load_dotenv(stream=io.StringIO("A=1")) is True
    assert os.environ["A"] == "1"


def test_load_respects_override(monkeypatch):
    monkeypatch.setenv("A", "old")
    assert envrelay.load_dotenv(stream=io.StringIO("A=new")) is True
    assert os.environ["A"] == "old"
    assert envrelay.load_dotenv(stream=io.StringIO("A=new"), override=True) is True
    assert os.environ["A"] == "new"


def test_load_empty_returns_false():
    assert envrelay.load_dotenv(stream=io.StringIO("# comment only")) is False


def test_disabled_flag(monkeypatch):
    monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "1")
    assert envrelay.load_dotenv(stream=io.StringIO("A=1")) is False


def test_disabled_flag_non_triggering_value(monkeypatch):
    monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "on")
    monkeypatch.delenv("A", raising=False)
    assert envrelay.load_dotenv(stream=io.StringIO("A=1")) is True


# --- editing -----------------------------------------------------------------


def test_set_key_quote_modes(tmp_path):
    p = str(tmp_path / ".env")
    assert envrelay.set_key(p, "C", "hello world") == (True, "C", "hello world")
    assert open(p, "rb").read() == b"C='hello world'\n"
    assert os.stat(p).st_mode & 0o777 == 0o600


def test_set_key_auto_and_never(tmp_path):
    p = str(tmp_path / ".env")
    envrelay.set_key(p, "K", "a_b", quote_mode="auto")
    assert open(p).read() == "K='a_b'\n"
    envrelay.set_key(p, "K", "plain", quote_mode="auto")
    assert "K=plain\n" in open(p).read()
    envrelay.set_key(p, "D", "v v", quote_mode="never")
    assert "D=v v\n" in open(p).read()


def test_set_key_unknown_quote_mode(tmp_path):
    p = str(tmp_path / ".env")
    with pytest.raises(ValueError, match="Unknown quote_mode: bogus"):
        envrelay.set_key(p, "K", "v", quote_mode="bogus")


def test_set_key_none_value_raises(tmp_path):
    p = str(tmp_path / ".env")
    with pytest.raises(AttributeError):
        envrelay.set_key(p, "Z", None)


def test_get_key_present_and_missing(tmp_path):
    p = str(tmp_path / ".env")
    open(p, "w").write("A=1\nB\n")
    assert envrelay.get_key(p, "A") == "1"
    assert envrelay.get_key(p, "B") is None
    assert envrelay.get_key(p, "MISSING") is None


def test_unset_key(tmp_path):
    p = str(tmp_path / ".env")
    open(p, "w").write("A=1\nB=2\n")
    assert envrelay.unset_key(p, "A") == (True, "A")
    assert open(p).read() == "B=2\n"
    assert envrelay.unset_key(p, "MISSING") == (None, "MISSING")


def test_set_key_rewrites_crlf_as_lf(tmp_path):
    p = str(tmp_path / ".env")
    open(p, "wb").write(b"A=1\r\nB=2\r\n")
    envrelay.set_key(p, "C", "x")
    assert open(p, "rb").read() == b"A=1\nB=2\nC='x'\n"


# --- find_dotenv -------------------------------------------------------------


def test_find_dotenv_walks_up(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("X=1\n")
    sub = tmp_path / "a" / "b"
    sub.mkdir(parents=True)
    monkeypatch.chdir(sub)
    assert envrelay.find_dotenv(usecwd=True) == str(tmp_path / ".env")


def test_find_dotenv_not_found(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert envrelay.find_dotenv("nothere.env", usecwd=True) == ""
    with pytest.raises(IOError):
        envrelay.find_dotenv("nothere.env", raise_error_if_not_found=True, usecwd=True)


# --- helper ------------------------------------------------------------------


def test_get_cli_string():
    assert envrelay.get_cli_string() == "dotenv"
    assert envrelay.get_cli_string("p", "get", "K") == "dotenv -f p get K"
    assert envrelay.get_cli_string("p", "set", "K", "v v") == 'dotenv -f p set K "v v"'
    assert (
        envrelay.get_cli_string("p", "set", "K", "v", quote="never")
        == "dotenv -q never -f p set K v"
    )


# --- surface -----------------------------------------------------------------


def test_all_and_no_version():
    assert len(envrelay.__all__) == 8
    assert not hasattr(envrelay, "__version__")


def test_missing_file_returns_empty(tmp_path):
    assert envrelay.dotenv_values(str(tmp_path / "nope.env")) == OrderedDict()
    assert envrelay.load_dotenv(str(tmp_path / "nope.env")) is False
