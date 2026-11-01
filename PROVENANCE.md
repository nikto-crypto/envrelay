# Provenance

## Builder

- Model: Claude Opus 4.8 (`claude-opus-4-8`), via Claude Code.
- Build start: 2026-11-01.
- Task: build `envrelay`, a from-scratch reimplementation matching the
  observable behavior of python-dotenv 1.2.4, as the AI-assisted arm of a
  research study. Full task text is in [BUILD_PROMPT.md](BUILD_PROMPT.md).

## Information sources consulted

- `~/envrelay-oracle/API_SURFACE.json` — public names, signatures, and the
  click option tree. This is one of the two authorities named by the task.
- The oracle itself, used strictly as a black box through
  `scripts/oracle_probe.py` (puts the oracle on `sys.path`, runs a snippet,
  reduces any escaping exception to its final `ExceptionClass: message` line).
- `~/envrelay-oracle/ORACLE_PYTHON.txt` — interpreter path and version
  (`3 15 520e0d0a`; `/opt/homebrew/opt/python@3.15/bin/python3.15`, 3.15.2).
- The "Known traps" section of the build prompt (behavior the task author
  verified against 1.2.4 and handed to me directly).

No python-dotenv source, tests, docs, README, changelog, repo, METADATA, or any
third-party port/rewrite was read, by any route. No web access was used.

## Independence near-misses

- 2026-11-01, session start: ran `head -1 ~/envrelay-oracle/bin/dotenv` while
  orienting. The guard **blocked** the read before any bytes were shown. No
  oracle source was seen. Policy adopted afterward: never read
  `~/envrelay-oracle/bin/dotenv` (only execute it), use absolute paths for
  everything under `~/envrelay-oracle` (`cd` into that tree is blocked by the
  guard), and treat the whole oracle tree as execute-only / black-box.

## Recall-interruption log

(Any moment I noticed myself recalling python-dotenv internals — parser design,
helper names, regexes, module layout — and deliberately took a different
approach is recorded here. Nothing yet.)

## Output-only text module

The click declarations, help/description strings, and CLI error-message strings
that must match the oracle verbatim are confined to a single module:
`src/envrelay/_commandline.py`. This is the module the similarity check should
treat separately (it reproduces output strings from the oracle's actual
`--help` / error output, which the task explicitly permits). The click glue
(error mapping, exit codes, `run` process replacement) lives in
`src/envrelay/_cliglue.py`, which is measured like every other module. The core
library never imports click.

## Differential pass rate by phase

(Recorded as each phase completes.)

- Plan + harness scaffold: pending.
