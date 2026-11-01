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

## Generated-case counts (final evidence run)

See PROVENANCE.md and the README for the exact figures produced by the final
run with `ENVRELAY_SCALE` set for the thresholds:

- ≥ 20,000 `.env` documents through the library readers in-process;
- ≥ 1,000 documents through the CLI in each of the three run modes;
- ≥ 5,000 editing sequences;
- ≥ 500 `find_dotenv` layouts;
- every hand-written CLI case in all three run modes.
