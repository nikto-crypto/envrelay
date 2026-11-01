# Coverage matrix: input classes × channels

Channels (from BUILD_PROMPT.md):

1. Parsing (`dotenv_values`, files + streams, interpolate on/off, encodings)
2. Loading (`load_dotenv`, environ effect, override, verbose, disabled)
3. Log records (level + message, in order)
4. File editing (`set_key`/`get_key`/`unset_key`, bytes, perms, symlinks, listing)
5. Finding files (`find_dotenv`, run modes, tracer, frozen)
6. The helper (`get_cli_string`)
7. The command line (3 run modes, module + console, help widths)
8. The IPython magic
9. Public API surface
10. API misuse

A cell lists the test(s) that exercise that input class on that channel.
`dv` = `tests/differential/test_readers.py`, `ld` = loading tests there,
`ed` = `test_editing.py`, `fd` = `test_find.py`, `hp` = `test_helper.py`,
`cli` = `test_cli.py`, `mg` = `test_magic.py`, `cfg` = `test_configs.py`,
`mis` = `test_misuse.py`, `conf` = `tests/conformance/test_surface.py`,
`u` = `tests/unit/test_library.py`.

| Input class \ Channel | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| Plain keys (`A=1`) | dv,u | ld,u | dv | ed,u | — | — | cli,cfg | mg | — | — |
| Dotted/dashed/colon keys | dv,u | ld | dv | ed | — | — | cli | — | — | — |
| Non-ASCII keys/values | dv | ld | dv | ed | — | — | cli,cfg | — | — | — |
| Empty / quoted keys | dv,u | ld | dv | ed | — | — | cli | — | — | — |
| `export` prefix & near-misses | dv,u | ld | dv | ed | — | — | cli | — | — | — |
| `=` spacing (spaces/tabs) | dv | ld | dv | ed | — | — | cli | — | — | — |
| Unquoted values | dv,u | ld | dv | ed | — | hp | cli,cfg | — | — | — |
| Single-quoted values | dv,u | ld | dv | ed | — | — | cli | — | — | — |
| Double-quoted values | dv,u | ld | dv | ed | — | — | cli,cfg | — | — | — |
| Unterminated quotes | dv | ld | dv | — | — | — | cli | — | — | — |
| Escape sequences (all) | dv,u | ld | dv | ed | — | — | cli | — | — | — |
| Comments (every position) | dv,u | ld | dv | ed | — | — | cli,cfg | — | — | — |
| Interpolation `${X}`/`:-`/`$X` | dv,u | ld,u | dv | — | — | — | cli,cfg | mg | — | — |
| Interp forward/back/self | dv | ld | dv | — | — | — | cli | — | — | — |
| Unbalanced braces | dv | ld | dv | — | — | — | cli | — | — | — |
| Multiline values | dv,u | ld | dv | ed | — | — | cli,cfg | — | — | — |
| LF / CRLF / CR / mixed | dv,u | ld | dv | ed,u | — | — | cli | — | — | — |
| BOM | dv,u | ld | dv | ed | — | — | cli | — | — | — |
| Blank / whitespace lines | dv | ld | dv | ed | — | — | cli | — | — | — |
| No final newline | dv | ld | dv | ed,u | — | — | cli | — | — | — |
| Very long lines | dv | ld | dv | — | — | — | cli | — | — | — |
| Control chars incl. NUL | dv | ld,mis | dv | — | — | — | cli | — | — | mis |
| `=1` / empty-key lines | dv | ld | dv | — | — | — | cli | — | — | — |
| Preexisting env overlap | dv | ld | dv | — | — | — | cli | mg | — | — |
| Encodings (read/write) | dv | ld | dv | ed | — | — | cli | — | — | — |
| Editing: absent/empty/dup/CRLF | — | — | ed | ed,u | — | — | cli | — | — | — |
| Editing: quote modes/export | — | — | ed | ed,u | — | — | cli | — | — | mis |
| Editing: non-string values | — | — | — | ed | — | — | — | — | — | mis,u |
| Editing: perms/symlinks/follow | — | — | ed | ed | — | — | — | — | — | — |
| Editing: key shapes | — | — | ed | ed | — | — | cli | — | — | — |
| `find_dotenv` depths/usecwd/name | — | — | — | — | fd,u | — | — | — | — | — |
| `find_dotenv` run modes | — | — | — | — | fd | — | — | — | — | — |
| `find_dotenv` tracer/frozen | — | — | — | — | fd | — | — | — | — | — |
| `get_cli_string` combos | — | — | — | — | — | hp,u | — | — | — | — |
| CLI commands/options/errors | — | — | cli | cli | — | — | cli | — | — | — |
| CLI `-f -`, `-e` spellings | — | — | — | — | — | — | cli | — | — | — |
| CLI `run` (exec, override, status) | — | ld | — | — | — | — | cli | — | — | — |
| CLI help (80/100/120/unset) | — | — | — | — | — | — | cli | — | — | — |
| IPython magic flags/paths/errors | — | ld | — | — | — | — | — | mg | — | — |
| Misuse (types/dirs/kwargs) | — | — | — | — | — | — | — | — | — | mis |
| API surface (sig/__all__/tree) | — | — | — | — | — | — | — | — | conf | — |
| Realistic configs | cfg | cfg | cfg | — | — | — | cfg | — | — | — |

## Added by the independent review (extra coverage)

A fresh independence-bound review added these differential test files, filling
gaps in the grid above:

- `test_disabled.py` — `PYTHON_DOTENV_DISABLED` trigger/non-trigger values across
  `load_dotenv`, that `dotenv_values`/`get_key`/CLI `run` ignore it, and that the
  magic honors it (channels 2, 3, 7, 8).
- `test_reader_encoding.py` — non-UTF-8 reads (latin-1, utf-16, cp1252, BOM,
  ascii-strict, undecodable bytes) with matching/mismatching `encoding=`
  (channels 1–3).
- `test_edit_extra.py` — set_key with an unencodable value (new + existing file,
  byte-position parity), get_key/unset_key on valueless keys, read-only files
  (mode preserved, new inode, no leftover temp) (channel 4).
- `test_cli_extra.py` — `-e` boolean spellings, `--format` case sensitivity,
  `run --`, stdin piped to the `run` child, `-f -` for get/list, and `list` on
  undecodable-byte files, across all three run modes (channel 7).
- `test_find_symlink.py` — `find_dotenv` through symlinked directories
  (channel 5).

The review surfaced one real mismatch (set_key encoding-error byte position on a
non-empty file), which was then fixed in `src/envrelay/_editing.py` (per-piece
writing); the test now passes.

## Added by Fix round 1 (external evaluation)

New input classes now covered (see PROVENANCE.md / CHANGELOG.md):

- **Blank/whitespace lines directly above an edited key** (channel 4): editing
  scenarios now start from grammar-generated documents (blank lines,
  whitespace-only lines, comments, bare keys in every position) and run `set_key`
  and `unset_key` on every key — `test_editing.py::test_edit_every_key_of_generated_file`
  and `test_configs.py::test_config_per_key_edit`.
- **Every `${...}` brace form** (channels 1–3): each shell operator (`:-`, `-`,
  `:=`, `=`, `:?`, `?`, `:+`, `+`), colons/dashes in names and defaults, nested
  and unbalanced braces — added to the interpolation grammar, flowing through the
  readers and CLI.
- **`run` option passthrough** (channel 7): `--help`, `-h`, `--version` after the
  command, and with `--`, in all three run modes — `test_cli.py` run cases.
- **`find_dotenv` interactive detection** (channel 5): `sys.ps1`/`sys.ps2`
  (alone and combined with a tracer / `sys.frozen`) — `test_find.py`.
- **`None` CliRunner argument** (channel 7): `list --format None` and other
  None-argument cases — the CLI/misuse differential.
- **Realistic `.env.example` templates** (channels 1–4, 7): web app,
  self-hosting, and Docker Compose templates with comment blocks,
  blank-line-separated sections, and commented-out keys — read by every reader,
  listed by the CLI, and per-key edited (`test_configs.py`).

## Generated-case counts (final evidence run)

See PROVENANCE.md and the README for the exact figures produced by the final
run with `ENVRELAY_SCALE` set for the thresholds:

- ≥ 20,000 `.env` documents through the library readers in-process;
- ≥ 1,000 documents through the CLI in each of the three run modes;
- ≥ 5,000 editing sequences;
- ≥ 500 `find_dotenv` layouts;
- every hand-written CLI case in all three run modes.
