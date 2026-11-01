# Next steps

Living status file. A new session continues from here under BUILD_PROMPT.md's
rules (independence rules bind everything; probe the oracle only via the repo
wrappers in `scripts/`).

## Done

- Environment: `.venv` on the oracle interpreter (Python 3.15.2), click 8.5.0,
  IPython, pytest, hypothesis, ruff, mkdocs, tox, bump2version. `.python-version`
  pinned. No python-dotenv anywhere in the venv.
- Library implemented (`src/envrelay/`): parsing, interpolation, loading,
  editing, find_dotenv, get_cli_string, CLI (click), IPython magic, `__main__`.
  Core is click-free; CLI strings isolated in `_commandline.py`.
- Differential harness (`tests/differential/`): oracle interface, single
  normalizer (+own tests), conftest (oracle gate, fixed env, per-case temp dir),
  Hypothesis grammar, and tests for every channel: readers, loading, editing,
  find, helper, CLI (subprocess / forked CliRunner / pty, module + console, help
  at COLUMNS 80/100/120/unset), magic, misuse, special files (FIFO/dir), configs.
- Conformance (`tests/conformance/`): 100%. AST lint (`tests/test_ast_lint.py`).
  Standalone unit tests (`tests/unit/`).
- Repo artifacts: README, LICENSE, CHANGELOG, CONTRIBUTING, RELEASING,
  pyproject, .bumpversion.cfg, MANIFEST.in, Makefile, requirements*.txt,
  ruff.toml (clean), tox.ini, .editorconfig, .pre-commit-config.yaml, docs/ +
  mkdocs (builds --strict), .github (SECURITY, dependabot, test + release
  workflows). Coverage matrix filled.
- Full suite green under `ENVRELAY_REQUIRE_ORACLE=1` (195 passed, 0 skipped at
  ENVRELAY_SCALE=40). tox py315 green. Grep evidence clean.

## Complete

All "Done means" items are met. Evidence (oracle Python 3.15.2, click 8.5.0,
bytecode magic 520e0d0a):

- Full suite, `ENVRELAY_REQUIRE_ORACLE=1 ... -rs -p no:warnings`:
  391 passed, 0 skipped.
- ≥20,000 docs through readers in-process: `test_dotenv_values_all_modes` at
  `max_examples=20000` — passed.
- ≥1,000 docs through the CLI in each of 3 run modes:
  `test_cli_list_generated` (subprocess/clirunner/pty) at `max_examples=1000`
  each — 3 passed.
- ≥5,000 editing sequences: `test_edit_sequences` at `max_examples=5100` — passed.
- ≥500 find_dotenv layouts: `test_find_dotenv_matrix` — 540 layouts × run modes.
- API conformance 100%; tox py315 green; docs `mkdocs build --strict` clean;
  grep evidence clean (no dotenv import in the library, none in requirements or
  pip freeze).
- Independent review integrated; the one mismatch it found is fixed.

Per-channel differential result: zero mismatches on every channel (1–10).

### Re-running the evidence

```bash
ENVRELAY_REQUIRE_ORACLE=1 .venv/bin/python -m pytest -rs -p no:warnings            # full, 0 skipped
ENVRELAY_REQUIRE_ORACLE=1 ENVRELAY_SCALE=1000 .venv/bin/python -m pytest \
    tests/differential/test_readers.py::test_dotenv_values_all_modes \
    tests/differential/test_cli.py::test_cli_list_generated -p no:warnings
ENVRELAY_REQUIRE_ORACLE=1 ENVRELAY_SCALE=850 .venv/bin/python -m pytest \
    tests/differential/test_editing.py -p no:warnings
```

## Watch list / notes

- CLI differential depends on click 8.5.0 on both sides (pinned in .venv and
  tox). The pty mode folds `\r\n` back to `\n`.
- The library reads regular files and FIFOs but treats a directory as
  not-found; `run` rejects a FIFO (isfile check).
- Windows-only behavior is implemented by best reading and is unverified on this
  machine (listed as such).
