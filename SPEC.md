# envrelay -- specification and design

`envrelay` reimplements, from scratch, the observable behavior of python-dotenv
1.2.4 (the "oracle"). This document describes the contract it must meet, the
architecture chosen to meet it, and the testing strategy. It is written in my
own words; no python-dotenv source, tests, docs, or prose were consulted. The
oracle is used only as a black box through the probe scripts in `scripts/`.

## The contract

The public surface (see `~/envrelay-oracle/API_SURFACE.json`) is:

- Eight functions on the `envrelay` package: `dotenv_values`, `find_dotenv`,
  `get_cli_string`, `get_key`, `load_dotenv`, `load_ipython_extension`,
  `set_key`, `unset_key`, with exactly the oracle's parameter names, order,
  kinds, and defaults; `__all__` lists these eight; the package exposes no
  top-level `__version__`.
- A command line (`envrelay`, `python -m envrelay`) built on click: a group with
  `-f/--file`, `-q/--quote`, `-e/--export`, `--version`, and subcommands
  `get`, `list`, `set`, `unset`, `run`.
- An IPython line magic named `dotenv` with `-o/--override`, `-v/--verbose`, and
  an optional path argument.

"Same output" means: for the same input, envrelay matches the oracle on parsing
results and reprs, `os.environ` effects, return values, exact file bytes and
permissions, raised exception classes and messages, log records (level +
message, in order; the logger sits under the `envrelay` hierarchy), and CLI
stdout/stderr/exit codes. The only permitted normalizations are the program
name, the version number, the random part of a temp-file name, the per-case
temp directory path, and traceback reduction to the final `ExceptionClass:
message` line.

## Architecture

`src/envrelay/` (every module is measured for similarity except the output-only
`_commandline`, which is called out in PROVENANCE.md):

- `__init__.py` -- re-exports the eight public names and `__all__`.
- `_version.py` -- the version string (not exposed at top level).
- `_parsing.py` -- the env-file grammar. A cursor-based scanner turns text into
  ordered `Segment`s (bindings and verbatim "raw" runs) and reports the lines of
  unparsable statements. Handles quoting, escapes, comments, line endings, and
  the CRLF/CR warning-line drift. `parse()` derives entries; `scan()` is used by
  the editor to rewrite in place.
- `_interpolate.py` -- `${name}` / `${name:-default}` expansion, single
  left-to-right pass, with the lookup priority used by `dotenv_values`
  (earlier values, then `os.environ`) and by `load_dotenv`/`run` (an effective
  environment honoring `override`).
- `_core.py` -- `dotenv_values`, `load_dotenv` (and the shared
  `load_into_environ`), `find_dotenv`, `get_cli_string`, source resolution, the
  `PYTHON_DOTENV_DISABLED` check, and the `envrelay.main` logger.
- `_editing.py` -- `set_key`, `get_key`, `unset_key`: value formatting per quote
  mode, in-place rewrite via `scan()` segments, atomic temp-file writes with
  permission preservation and symlink handling.
- `_cliglue.py` -- CLI mechanics with no user-facing prose: locale-encoding
  reads, `run` loading, process replacement.
- `_commandline.py` -- the click declarations and all CLI output strings
  (reproduced from the oracle's actual `--help`/error output).
- `__main__.py` -- `python -m envrelay` and the console-script entry, including
  the no-click fallback message.
- `_magic.py` -- the IPython magic (IPython imported lazily).

Design choices that are deliberately my own (not the oracle's internal layout):
the segment-based scanner, the explicit drift accounting for CRLF streams, the
`effective`-environment model for loading, and the module split above.

## Behavior notes (derived by probing)

- Grammar: optional `export ` prefix; key is a single-quoted run (quotes
  stripped) or a run of non-space/non-`=`/non-`#`/non-`'` chars (so a
  double-quoted key keeps its quotes); `KEY` alone -> value `None`; `KEY=` ->
  `''`. Unquoted values end at a ` #`/`\t#` comment or EOL and are stripped; a
  `#` right after `=` is literal. Single quotes decode `\\` and `\'` only;
  double quotes decode `\\ \' \" \a \b \f \n \r \t \v`; both may span lines.
- Line endings: from a file, CRLF/CR fold to LF before parsing; from a stream
  they do not, which also produces the CRLF warning-line drift (each failed line
  with a CR terminator adds one to a running offset applied at the next
  successful binding).
- Interpolation: only `${...}`; `$name` is literal; the default clause is
  substituted verbatim and never re-expanded; a name is "present" (so no
  default) when it resolves to any value including `''`.
- Editing: `always` quotes with single quotes and `\\`/`\'` escaping; `never`
  writes raw; `auto` leaves a value unquoted only if it is a non-empty run of
  alphanumerics (no `_`). New files get mode `0o600`; existing files keep their
  mode; writes are atomic via `.tmp_<random>` + rename.
- CLI: `list`/`get` read with the locale encoding and report
  `Error opening env file: ...` (exit 2) on `OSError`; `set`/`unset`/`run` use
  UTF-8; `run` requires a regular file for `-f`, ignores
  `PYTHON_DOTENV_DISABLED`, and replaces the process.

## Testing strategy

- `tests/conformance` walks `API_SURFACE.json` and checks signatures, `__all__`,
  the click tree, and the magic arguments.
- `tests/differential` runs identical inputs through envrelay and the oracle and
  compares every channel, with a single normalizer (its own tests). Hypothesis
  generates `.env` documents, editing sequences, and directory layouts from a
  grammar in the repo; realistic hand-written configs are included. The suite
  skips when the oracle or interpreter version does not match, unless
  `ENVRELAY_REQUIRE_ORACLE=1`.
- `tests/unit` stands on its own with hand-written assertions (no oracle).
- A coverage matrix (input classes x channels) is kept in the repo.
