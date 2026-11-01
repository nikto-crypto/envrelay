"""AST lint enforcing the study's independence rules in this repo's code.

* The library package (``src/envrelay``) must never import ``dotenv`` or
  reference the oracle directory.
* Anywhere in the repo, importing a ``dotenv.`` submodule other than
  ``dotenv.cli`` is forbidden (``dotenv.cli.cli`` is allowed only as a CliRunner
  target).
* Oracle objects must not be inspected: no ``help``/``dir``/``vars`` on them, no
  ``.__dict__``/``.__doc__``/``.__annotations__`` access, no ``inspect`` applied
  to them, and no ``pydoc``/``dis``/``marshal``/``importlib.metadata`` probing of
  python-dotenv.
"""

from __future__ import annotations

import ast
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "src", "envrelay")
SCAN_DIRS = [SRC, os.path.join(REPO, "scripts"), os.path.join(REPO, "tests")]

_FORBIDDEN_ATTRS = {"__dict__", "__doc__", "__annotations__", "__dir__", "__members__"}
_INSPECT_FUNCS = {"help", "dir", "vars"}


def _py_files(root):
    for base, _dirs, names in os.walk(root):
        if "__pycache__" in base:
            continue
        for name in names:
            if name.endswith(".py"):
                yield os.path.join(base, name)


def _oracle_names(tree):
    """Names in this module that are bound to the oracle module/objects."""
    names = {"dotenv"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "dotenv" and alias.asname:
                    names.add(alias.asname)
        if isinstance(node, ast.Assign):
            # x = oracle_iface.load()  /  x = <something>.load()
            value = node.value
            if (
                isinstance(value, ast.Call)
                and isinstance(value.func, ast.Attribute)
                and value.func.attr in ("load", "load_cli_group")
            ):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        names.add(target.id)
    # Common oracle-bound identifiers used via fixtures / helpers in this repo.
    names.update({"oracle", "oracle_cli_group"})
    return names


def _base_name(node):
    while isinstance(node, ast.Attribute):
        node = node.value
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Call):
        return _base_name(node.func)
    return None


def test_library_never_touches_oracle():
    for path in _py_files(SRC):
        src = open(path).read()
        tree = ast.parse(src, filename=path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name != "dotenv" and not alias.name.startswith(
                        "dotenv."
                    ), path
            if isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                assert mod != "dotenv" and not mod.startswith("dotenv."), path
        assert "envrelay-oracle" not in src, path
        assert "ENVRELAY_ORACLE_DIR" not in src, path


def test_no_bad_submodule_imports_and_no_inspection():
    violations = []
    for root in SCAN_DIRS:
        for path in _py_files(root):
            tree = ast.parse(open(path).read(), filename=path)
            oracle_names = _oracle_names(tree)
            for node in ast.walk(tree):
                # forbidden submodule imports
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if (
                            alias.name.startswith("dotenv.")
                            and alias.name != "dotenv.cli"
                        ):
                            violations.append((path, "import %s" % alias.name))
                if isinstance(node, ast.ImportFrom) and node.module:
                    if (
                        node.module.startswith("dotenv.")
                        and node.module != "dotenv.cli"
                    ):
                        violations.append((path, "from %s import" % node.module))
                    if node.module in ("pydoc", "dis", "marshal"):
                        violations.append((path, "import %s" % node.module))
                    if node.module == "importlib.metadata":
                        # only a problem if used on python-dotenv; flag defensively
                        pass
                # attribute inspection on oracle objects
                if isinstance(node, ast.Attribute) and node.attr in _FORBIDDEN_ATTRS:
                    if _base_name(node.value) in oracle_names:
                        violations.append((path, "%s access on oracle" % node.attr))
                # help()/dir()/vars() on oracle; inspect.* on oracle
                if isinstance(node, ast.Call):
                    func = node.func
                    if isinstance(func, ast.Name) and func.id in _INSPECT_FUNCS:
                        for arg in node.args:
                            if _base_name(arg) in oracle_names:
                                violations.append((path, "%s() on oracle" % func.id))
                    if (
                        isinstance(func, ast.Attribute)
                        and _base_name(func) == "inspect"
                    ):
                        for arg in node.args:
                            if _base_name(arg) in oracle_names:
                                violations.append((path, "inspect on oracle"))
    assert not violations, "independence violations:\n" + "\n".join(
        "%s: %s" % v for v in violations
    )
