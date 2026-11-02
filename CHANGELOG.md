# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/), and the project aims to follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Fixed (Fix round 3 — from an external evaluation)

A 30,000-case adversarial fuzz against python-dotenv 1.2.4 surfaced three
divergences; all are now matched, with the whole input class covered:

- Every character Python considers whitespace (not just space/tab) is treated as
  whitespace wherever whitespace is allowed — around keys, around `=`, before and
  after values, and before `#` comments. Only `\r`/`\n` are line terminators.
- An empty single-quoted key (`''`) is a parse error (logs the warning, yields
  nothing), as in 1.2.4.
- `${...}` expansion matches only `${name}` and `${name:-default}` (name up to the
  first `:` or `}`), so an unclosed `${a:` leaves its own text literal while a
  later well-formed `${B}` still expands.

### Fixed (Fix round 2 — from an external review)

- The IPython `%dotenv` magic's docstring help now lists the `dotenv_path`
  positional argument with its help text ("Search in increasingly higher folders
  for the `dotenv_path`"), matching python-dotenv 1.2.4.

### Fixed (Fix round 1 — from an external evaluation)

An independent evaluation on 1,250 unseen `.env` files surfaced five behavioral
divergences from python-dotenv 1.2.4; all are now matched, with the whole input
class covered by the differential suite:

- `set_key`/`unset_key` (and CLI `set`/`unset`) now remove blank /
  whitespace-only lines directly above the edited key (comments break the run).
- `${...}` expansion is limited to `${name}` and `${name:-default}`; every other
  colon form (`:?`, `:+`, `:=`, `::`, bare `:`, …) stays literal.
- `run` passes every token after the command name (including `--help`) to the
  command; `run --help` with no command still shows run's help.
- `find_dotenv` searches from the working directory when `sys.ps1`/`sys.ps2` is
  set, a tracer is active, the program is frozen, or `__main__` lacks `__file__`.
- `list --format <unknown>` (e.g. `None` via CliRunner) falls back to the simple
  format.

### Added

- First implementation of `envrelay`: a dependency-free library for reading,
  loading, and editing `.env` files.
- Public API: `dotenv_values`, `load_dotenv`, `find_dotenv`, `get_cli_string`,
  `get_key`, `set_key`, `unset_key`, and `load_ipython_extension`.
- Optional `cli` extra: the `envrelay` command line and `python -m envrelay`,
  with `get`, `list`, `set`, `unset`, and `run`.
- IPython line magic `%dotenv`.
- An extensive differential test suite proving behavioral equivalence with the
  reference implementation across every documented channel.

## [0.1.0]

- Initial development version.
