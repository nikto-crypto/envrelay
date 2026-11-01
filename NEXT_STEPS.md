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

## Remaining

1. Integrate the fresh-review subagent's findings (it may add differential
   tests under `tests/differential/`).
2. Final evidence run at high `ENVRELAY_SCALE` to hit the thresholds:
   - readers: `ENVRELAY_SCALE=1000` (→ 20,000 docs through readers);
   - editing: `ENVRELAY_SCALE>=300` (→ 5,000+ sequences);
   - CLI generated: `ENVRELAY_SCALE=1000` (→ 1,000 docs/mode × 3 modes);
   - find: fixed 540 layouts.
   Then capture the full `pytest -rs -p no:warnings` run (zero skips), tox,
   docs build, and grep evidence for the final report.

## Watch list / notes

- CLI differential depends on click 8.5.0 on both sides (pinned in .venv and
  tox). The pty mode folds `\r\n` back to `\n`.
- The library reads regular files and FIFOs but treats a directory as
  not-found; `run` rejects a FIFO (isfile check).
- Windows-only behavior is implemented by best reading and is unverified on this
  machine (listed as such).
