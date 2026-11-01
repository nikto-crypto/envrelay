"""Differential tests for special file types: directories and FIFOs.

The library reads a regular file or a FIFO like a file but treats a directory as
"no configuration file"; the CLI ``run`` rejects a FIFO. These must match.
"""

from __future__ import annotations

import os
import shutil
import tempfile
import threading

import envrelay


def _read_fifo(module, body):
    directory = tempfile.mkdtemp()
    fifo = os.path.join(directory, "f.env")
    os.mkfifo(fifo)
    result = {}

    def reader():
        result["v"] = repr(module.dotenv_values(fifo))

    def writer():
        with open(fifo, "w") as handle:
            handle.write(body)

    tr = threading.Thread(target=reader)
    tw = threading.Thread(target=writer)
    tr.start()
    tw.start()
    tr.join(10)
    tw.join(10)
    shutil.rmtree(directory)
    return result.get("v")


def test_fifo_is_read_like_a_file(oracle):
    body = "Z=1\nA=${Z}\n"
    assert _read_fifo(envrelay, body) == _read_fifo(oracle, body)


def test_directory_reads_as_empty(oracle):
    directory = tempfile.mkdtemp()
    sub = os.path.join(directory, "adir")
    os.mkdir(sub)
    try:
        assert repr(envrelay.dotenv_values(sub)) == repr(oracle.dotenv_values(sub))
        assert envrelay.load_dotenv(sub) == oracle.load_dotenv(sub)
    finally:
        shutil.rmtree(directory)
