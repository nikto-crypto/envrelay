"""API-surface conformance: envrelay must match API_SURFACE.json.

Checks the eight public function signatures, ``__all__``, the absence of a
top-level ``__version__``, the click command/option tree (names, opts, types,
choices, flags, nargs, required, defaults with the working directory
normalized), and the IPython magic's arguments. This does not need the oracle.
"""

from __future__ import annotations

import inspect
import json
import os

import pytest

import envrelay

API_PATH = os.path.join(
    os.environ.get("ENVRELAY_ORACLE_DIR", os.path.expanduser("~/envrelay-oracle")),
    "API_SURFACE.json",
)

pytestmark = pytest.mark.skipif(
    not os.path.exists(API_PATH), reason="API_SURFACE.json not found"
)


def _api():
    with open(API_PATH) as fh:
        return json.load(fh)


def test_public_functions_exist_with_signatures():
    api = _api()
    for name, info in api["package_api"].items():
        assert hasattr(envrelay, name), "missing %s" % name
        got = str(inspect.signature(getattr(envrelay, name)))
        assert got == info["signature"], "%s: %s != %s" % (name, got, info["signature"])


def test_all_lists_the_eight_names():
    api = _api()
    expected = sorted(api["package_api"].keys())
    assert sorted(envrelay.__all__) == expected
    assert len(envrelay.__all__) == 8


def test_no_top_level_version():
    assert not hasattr(envrelay, "__version__"), api_msg()


def api_msg():
    return "the top-level package must not expose __version__"


def _param_map(command):
    return {p.name: p for p in command.params}


def test_cli_tree_matches():
    api = _api()["cli"]
    from envrelay._commandline import cli

    assert cli.name == "cli"
    params = _param_map(cli)
    cwd_default = os.path.join(os.getcwd(), ".env")
    for spec in api["params"]:
        name = spec["name"]
        if name == "version":
            assert "--version" in params["version"].opts
            continue
        param = params[name]
        assert set(spec["opts"]) <= set(param.opts), name
        assert bool(spec["is_flag"]) == bool(getattr(param, "is_flag", False)), name
        assert bool(spec["multiple"]) == bool(param.multiple), name
        # type / choices
        tinfo = spec["type"]
        if tinfo.get("class") == "Choice":
            assert list(param.type.choices) == tinfo["choices"], name
        if name == "file":
            assert param.default == cwd_default
        elif name == "quote":
            assert param.default == "always"
        elif name == "export":
            assert param.default is False

    subcommands = dict(cli.commands)
    assert set(subcommands) == set(api["subcommands"])
    for sub_name, sub_spec in api["subcommands"].items():
        command = subcommands[sub_name]
        got = _param_map(command)
        for pspec in sub_spec["params"]:
            pname = pspec["name"]
            assert pname in got, "%s missing param %s" % (sub_name, pname)
            param = got[pname]
            assert set(pspec["opts"]) <= set(param.opts), (sub_name, pname)
            assert bool(pspec["required"]) == bool(param.required), (sub_name, pname)
            if pspec["nargs"] == -1:
                assert param.nargs == -1, (sub_name, pname)
            tinfo = pspec["type"]
            if tinfo.get("class") == "Choice":
                assert list(param.type.choices) == tinfo["choices"], (sub_name, pname)


def test_magic_arguments():
    api = _api()["ipython"]
    assert api["magic"] == "dotenv"
    # The magic function exists and accepts the IPython shell.
    assert callable(envrelay.load_ipython_extension)
    assert list(inspect.signature(envrelay.load_ipython_extension).parameters) == ["ipython"]
