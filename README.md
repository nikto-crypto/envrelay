# envrelay

`envrelay` reads, loads, and edits `.env` files. It is a small, dependency-free
library with an optional command line (built on [click](https://click.palletsprojects.com/))
and an IPython magic. The core library needs nothing but the Python standard
library; `requires-python >= 3.10`.

## Install

```bash
pip install envrelay          # library only
pip install "envrelay[cli]"   # adds the `envrelay` command line (click)
```

## Library

```python
from envrelay import dotenv_values, load_dotenv, set_key, get_key, find_dotenv

# Parse without touching the environment
values = dotenv_values(".env")          # OrderedDict of name -> value (or None)

# Push into os.environ (existing variables win unless override=True)
load_dotenv()                            # finds the nearest .env and loads it

# Edit in place (atomic write)
set_key(".env", "TOKEN", "s3cr3t")
print(get_key(".env", "TOKEN"))
```

`${NAME}` and `${NAME:-default}` references are expanded by default (pass
`interpolate=False` to keep them literal). A bare `$NAME` is left alone.

## Command line

```bash
envrelay list                 # print every key=value
envrelay list --format=json   # or shell / export
envrelay get KEY
envrelay set KEY VALUE
envrelay unset KEY
envrelay run -- mycommand     # run a command with the .env loaded
```

`python -m envrelay` behaves identically to the `envrelay` console script.

## IPython magic

```text
%load_ext envrelay
%dotenv            # load .env
%dotenv -o -v path # override + verbose, from a given path
```

## This repository is a differential reimplementation

`envrelay` was written from scratch to reproduce the *observable behavior* of
python-dotenv 1.2.4, which is used only as a black-box "oracle". The test suite
proves equivalence by running identical inputs through both and comparing every
channel (parsing, loading, log records, file editing, file finding, the helper,
the command line in three run modes, the IPython magic, the API surface, and API
misuse). See [SPEC.md](SPEC.md), [PROVENANCE.md](PROVENANCE.md), and
[COVERAGE_MATRIX.md](COVERAGE_MATRIX.md).

### Building the oracle and running the differential suite

The differential tests need a bytecode-only install of python-dotenv 1.2.4 in
`~/envrelay-oracle` (override with `ENVRELAY_ORACLE_DIR`), containing:

- `dotenv/` — the compiled package,
- `deps/click/` — click 8.5.0 (so the oracle's CLI runs),
- `bin/dotenv` — the installed console script,
- `API_SURFACE.json`, `ORACLE_PYTHON.txt` — the public contract and the
  interpreter (Python minor version + bytecode magic) the oracle was built for.

Create the project environment on that interpreter and install the test tools:

```bash
"$(sed -n 2p ~/envrelay-oracle/ORACLE_PYTHON.txt)" -m venv .venv
.venv/bin/python -m pip install -e ".[cli]"
.venv/bin/python -m pip install -r requirements.txt
```

Run the suite (the differential tests skip unless the interpreter matches the
oracle; `ENVRELAY_REQUIRE_ORACLE=1` turns those skips into failures):

```bash
ENVRELAY_REQUIRE_ORACLE=1 .venv/bin/python -m pytest -rs -p no:warnings
```

`ENVRELAY_SCALE` controls how many generated cases run (higher = more). The
oracle is only ever reached through the reducing wrappers in `scripts/`; the
library itself never imports or locates it.

## Development

```bash
make test        # run the test suite
make format      # ruff format + fix
make coverage    # coverage report
make docs        # build the MkDocs site
```

## License

MIT — see [LICENSE](LICENSE).
