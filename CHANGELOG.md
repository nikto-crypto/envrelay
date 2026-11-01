# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/), and the project aims to follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

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
