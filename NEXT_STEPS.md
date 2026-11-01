# Next steps

Living status file. A new session continues from here under BUILD_PROMPT.md's
rules (independence rules bind everything; probe the oracle only via the repo
wrappers in `scripts/`).

## Done so far

- Environment: `.venv` on the oracle interpreter (Python 3.15.2), click 8.5.0,
  IPython, pytest, hypothesis installed. `.python-version` pinned. No
  python-dotenv in the venv.
- Oracle probe wrappers: `scripts/oracle_probe.py` (library calls, reduces
  tracebacks), `scripts/oracle_cli.py` (CLI subprocess, reduces tracebacks),
  `scripts/find_probe.py`, `scripts/magic_runner.py`.
- Library implemented and matching the oracle on ad-hoc differential checks:
  - Parsing/interpolation (`scripts/check_parse.py`): 268/268.
  - Editing + get_cli_string (`scripts/checkedit.py` style): matches.
  - CLI, module + console (`scripts/check_cli.py`): 66/66 incl. help at COLUMNS 80.
  - find_dotenv across script/module/-m/-c/stdin/tracer/frozen
    (`scripts/check_find.py`): 66/66; -c and stdin verified inline too.
  - IPython magic (`scripts/magic_runner.py` + driver): all cases match.
- Package installs (`pip install -e .`), API surface correct, no top-level
  `__version__`, no dotenv in `pip freeze`.

## Still to do (in priority order)

1. **Formal differential harness** under `tests/differential/` (pytest):
   - conftest: oracle availability + interpreter/bytecode-magic match; skip
     unless matched; `ENVRELAY_REQUIRE_ORACLE=1` turns skips into failures;
     fixed env (temp HOME, TERM, COLUMNS, LANG/LC_ALL, TZ, PYTHONUTF8 unset,
     locale fixed); per-case temp dir outside HOME; assert no `.env` in parents.
   - one small normalizer function + its own tests.
   - Hypothesis grammar for .env docs; reach the required counts:
     >=20,000 docs through library readers in-process; >=1,000 docs through the
     CLI in each of 3 run modes (CliRunner-in-fork, subprocess, pty);
     >=5,000 editing sequences; >=500 find_dotenv layouts; all hand-written CLI
     cases in 3 modes; the magic; all channel-10 misuse cases.
   - per-channel differential table, zero mismatches.
2. **API conformance test** (`tests/conformance`) walking API_SURFACE.json.
3. **AST lint test**: no oracle inspection patterns; no `dotenv.` submodule
   import except `dotenv.cli` (allowlisted).
4. **Original unit tests** (`tests/unit`) standing alone without the oracle.
5. **Coverage matrix** (input classes x channels) filled with real cases.
6. **Repo artifacts**: README, LICENSE (MIT, Nick Serapiglia), CHANGELOG,
   CONTRIBUTING, RELEASING, .bumpversion.cfg (bump2version), MANIFEST.in,
   Makefile, requirements*.txt, ruff.toml, tox.ini, .editorconfig,
   .pre-commit-config.yaml, docs/ + mkdocs.yml, .github/ (SECURITY, dependabot,
   test + release workflows).
7. **Fresh-review subagent** (independence-bound) to find uncovered
   channels/inputs; add what it finds.
8. **Final evidence run**: full pytest on 3.15 with `ENVRELAY_REQUIRE_ORACLE=1
   -rs -p no:warnings` (zero skipped differential tests), tox across installed
   Pythons, docs build, grep evidence, coverage matrix.

## Known open questions / watch list

- Confirm set_key leftover-temp behavior on write errors (encoding that can't
  encode) matches the oracle's (inode/dir-listing channel).
- Confirm help text at COLUMNS 100/120/unset.
- NUL-byte partial-apply in load_dotenv (`ValueError: embedded null byte`).
- Binary stream / Path / bytes / int misuse messages (channel 10).
- pty run mode specifics.
