# Contributing

Thanks for your interest in `envrelay`.

## Getting set up

Use the interpreter the oracle was built for (see
`~/envrelay-oracle/ORACLE_PYTHON.txt`), then:

```bash
"$(sed -n 2p ~/envrelay-oracle/ORACLE_PYTHON.txt)" -m venv .venv
.venv/bin/python -m pip install -e ".[cli]"
.venv/bin/python -m pip install -r requirements.txt
```

## Running the tests

```bash
make test
# or, to require the oracle (no silent skips):
ENVRELAY_REQUIRE_ORACLE=1 .venv/bin/python -m pytest -rs -p no:warnings
```

`ENVRELAY_SCALE` scales the number of generated cases.

## Style

- `make format` runs ruff's formatter and autofixes.
- Keep the core library free of third-party runtime dependencies; click belongs
  only to the `cli` extra, and only `src/envrelay/_commandline.py` and
  `src/envrelay/_cliglue.py` may import it.
- New behavior should come with both an original unit test (no oracle) and a
  differential test.

## Independence rules

This project is a from-scratch reimplementation. Do not copy from the reference
implementation's source, tests, or docs; the reference is used only as a
black-box oracle through the wrappers in `scripts/`. See `PROVENANCE.md`.
