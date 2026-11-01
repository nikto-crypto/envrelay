# Task

Build `envrelay`, a new Python library and command-line tool that does exactly what python-dotenv 1.2.4 (the PyPI release) does, written from scratch with its own design. It is the AI-assisted test group in a research study, with python-dotenv 1.2.4 as the control. After you finish, someone else will check two things, using tools and test inputs you won't see:

1. **Same function.** Given the same input (the same .env text, environment, files, function calls, and command lines), envrelay produces the same output as python-dotenv 1.2.4, as defined below.
2. **Unique code.** envrelay's source shares no code with python-dotenv, which will be measured with standard code-similarity tools.

Work in the phases under "How to work", commit after each one, and keep NEXT_STEPS.md current: what's done, the current pass rates, and exactly what comes next. If the session ends or the context runs short, a new session continues from NEXT_STEPS.md under these same rules. Keep going until every item under "Done means" is met, and don't stop for progress check-ins.

# Independence rules (no exceptions, and they bind every subagent you start)

- Never look at python-dotenv's source code, tests, docs, README, changelog, or repo, by any route: site-packages, inspect, dis or any disassembler or decompiler, downloading a package, GitHub, the project's documentation site, code search, mirrors, any existing port or rewrite of it by anyone, or web pages that quote it. You need no web access for this task, and the guard blocks it. Its docs and README contain code, so they are off limits too. The guard settings block the obvious routes. The rest is on you, and the session transcript will be audited.
- Never read, copy, adapt, or paraphrase python-dotenv's test suite, from any copy anywhere, and that includes reproducing its test cases or parametrized tables from memory. Seed examples for your tests must be invented and logged as such in PROVENANCE.md. A previous AI build of this library shipped the upstream tests verbatim and claimed it was written from documentation only; that is exactly what this study rules out. Every test in this repo is yours.
- Your memory of python-dotenv mixes several releases, and its main branch has changes that 1.2.4 does not (for example `~` expansion in paths, and temp-file errors that name the target file). Never trust recall. The oracle and the API surface file are the only authorities. Implement what 1.2.4 does, not what you remember or what a later version does. Don't write code from memory of python-dotenv either. If you notice yourself recalling its implementation (its parser design, helper names, regular expressions, or module layout), stop, note it in PROVENANCE.md, and take a different approach.
- Choose your own architecture. The public contract is the package API, the command line, and the IPython magic (listed below). Everything behind them, including private modules, helper names, data structures, the parsing approach, and how the work is split up, is yours. Don't reproduce python-dotenv's internal module layout or internal names. Describe your design in SPEC.md.
- Don't copy python-dotenv's README, docstrings, help text phrasing beyond what the command line prints (see "Output-only text"), or other prose. Write everything in your own words.
- Don't disguise code or pad it. No exec, eval, compile, `marshal.loads`, embedded or encoded code, dynamic imports of the oracle, dead code, or filler written to change how the source looks. Similarity is judged on the library package alone.
- Use the oracle only as a black box. It is a bytecode-only install of python-dotenv 1.2.4 in ~/envrelay-oracle (location overridable with the environment variable `ENVRELAY_ORACLE_DIR`).
  - Test code may put that folder on sys.path, import `dotenv`, and call the functions in its public API (the eight names in API_SURFACE.json), then compare the results with envrelay doing the same. Test code may also run `python -m dotenv ...` with that folder on `PYTHONPATH`, and may run the installed console script ~/envrelay-oracle/bin/dotenv as a program, without reading it, by passing it to the project interpreter with that folder on `PYTHONPATH` (its own first line points at an interpreter without click).
  - The one internal object test code may use is the oracle's click group, `dotenv.cli.cli`, and only as the target of `click.testing.CliRunner`. Allowlist that single import in the lint below.
  - Probe the oracle only through a small wrapper script in your repo that reduces any traceback to its final `ExceptionClass: message` line before printing. Never run the oracle directly in a shell where a raw traceback could print.
  - Read ~/envrelay-oracle/API_SURFACE.json for the public names, signatures, and command-line option tree.
  - Never inspect the oracle any other way: no `help()`, `__doc__`, `dir()`, `vars()`, `__dict__`, underscore attributes, `__annotations__`, importing its internal modules, pickle or copy of oracle objects, traceback frames, pydoc, `inspect`, reading any file under ~/envrelay-oracle/dotenv or its dist-info, or `importlib.metadata` on python-dotenv (its METADATA file contains the full README and changelog). Add an AST lint to the test suite that fails on these patterns applied to oracle objects and on any import of a `dotenv.` submodule other than `dotenv.cli`.
  - Wrap every oracle call so errors are recorded only as (exception class name, message). Never print an oracle traceback, and run pytest with `-p no:warnings`.
  - The only copy of python-dotenv anywhere in your environment is the oracle. No dependency may pull it in. Many web and settings packages do, including pydantic-settings and therefore bump-my-version: use `bump2version` for `.bumpversion.cfg`, and check every new development dependency with `pip install --dry-run --report report.json <package>` before installing it, then search report.json in a separate command (a single command line containing both `pip install` and `dotenv` is blocked by the guard). requirements files must not contain it, `pip freeze` in the project environment must not list it, and the harness must assert that `dotenv.__file__` is under the oracle folder.
  - The library must never import or locate the oracle, and must not embed tables of output captured from it, except the output-only text described below.
- Don't put "dotenv" in the name of any file or folder you create. The guard may block reading such paths, including your own.
- Runtime dependencies: none for the core library. The command line, like python-dotenv's, is an optional `cli` extra that depends on click. Develop and test against click 8.5.0, the version the oracle's command line runs with in your environment. click is a third-party library, not part of python-dotenv, so using it is allowed; building the command line on it is expected, and overlap that the shared command line forces (option names, defaults, choices) is fine. IPython is a test dependency for the magic. Any standard library module is allowed. Overlap that the shared public API forces, such as function and parameter names, message text, and use of standard library modules, is expected and fine.

# What "same output" means

For the same input, envrelay must match python-dotenv 1.2.4 on every channel below. The harness may apply only these normalizations, and no others:

- the program name: `dotenv` is treated as `envrelay` and `python -m dotenv` as `python -m envrelay`, only where it appears as the program name (usage lines, `Try ... for help` hints, the `--version` line, and the first word returned by `get_cli_string`);
- the version number in the `--version` line (envrelay reports its own version);
- the random part of a temporary file's name inside an error message (the directory part must match);
- the absolute path of the per-case temporary directory, replaced by a placeholder (on macOS both the `/var/...` and `/private/var/...` spellings);
- a traceback on stderr, reduced to its final `ExceptionClass: message` line. Apply this reduction to oracle output before anything is stored, printed, or compared, so oracle file names and line numbers never appear anywhere.

All other text must match verbatim, including messages that mention "python-dotenv" by name and the environment variable name `PYTHON_DOTENV_DISABLED`. Keep the normalizer in one small function with its own tests. The oracle defines the contract, including its oddities. Don't fix or improve anything. Run every comparison in a fixed environment: a temporary `HOME`, fixed `TERM`, `COLUMNS`, `LANG`/`LC_ALL`, and `TZ`, `PYTHONUTF8` unset and the locale fixed (the command line's `list` and `get` open files with the locale's default encoding, while `set`, `unset`, and `run` use UTF-8), a clean environment with no inherited variables that the case uses, and every case in its own temporary directory outside your home folder (on macOS this also avoids privacy prompts). Assert that no `.env` exists in any parent of the temporary root, because `find_dotenv` walks upward.

1. **Parsing.** `dotenv_values` for files and streams, with `interpolate` on and off, and with different encodings: the returned type and its repr, the keys and their order, every value (including None for a key with no `=`), and the log records it emits.
2. **Loading.** `load_dotenv` for files and streams: the return value, the exact effect on `os.environ` (variables added, changed, left alone), `override`, interpolation against variables already in the environment, `verbose`, `PYTHON_DOTENV_DISABLED`, and the log records.
3. **Log records.** For every call: the level and message of each record, in order. The logger must sit under the `envrelay` logger hierarchy; the rest of its name is exempt. Records that reach stderr with no handler configured (Python's last-resort handler) are output, covered by channel 7.
4. **File editing.** `set_key`, `get_key`, `unset_key` in sequences, across every `quote_mode`, `export`, `encoding`, and `follow_symlinks` value: return values, the exact bytes of the resulting file, the file's permission bits, whether a symlink is kept or replaced and what its target contains, raised errors (class and message), log records, and the full listing of the case directory afterwards (names, types, permission bits, inode changes, symlink targets), so leftover temporary files and file replacement are caught.
5. **Finding files.** `find_dotenv` with each argument combination, called from scripts at different depths of a directory tree, from `python -c`, from `python -m`, from code read on stdin, from an interactive-style session, under an active tracer (`sys.settrace`, as coverage tools and debuggers install), with `sys.frozen` set, and from inside your own test code: the returned path, or the error class and message.
6. **The helper.** `get_cli_string` for every argument combination.
7. **The command line,** run three ways for every case: in-process through `click.testing.CliRunner`, as a real subprocess, and through a pseudo-terminal (Python's `pty` module). In each: exit code, stdout, stderr, the resulting `.env` bytes, and for `run`, the child's environment, exit status, and process identity. Every in-process case runs in a forked child (`os.fork`) that changes into the case directory first and only then imports both command-line modules (the `-f` default is fixed at import time), runs CliRunner, and sends the results back. This also contains a successful `run`, which replaces the calling process. The click group object must be named `cli`, because under CliRunner click uses that name as the program name (`--version` prints `cli, version 1.2.4`). The program must behave identically as `python -m envrelay` and as the installed `envrelay` console script, compared with the oracle's `python -m dotenv` and its `dotenv` console script. Help text for every command is included at `COLUMNS` 80, 100, 120, and unset. Below 80, the longer program name changes where click wraps the usage line, so narrower widths are exempt. CliRunner agreement alone is never evidence; the library must never contain code that detects or imitates the test tool.
8. **The IPython magic.** In an IPython `InteractiveShell` instance: `%load_ext envrelay`, then `%dotenv` with each flag and path form, `-h`, and bad flags, compared with `%load_ext dotenv` on the oracle in a separate process: printed output, `os.environ` effects, and errors.
9. **Public API surface.** The eight functions in API_SURFACE.json exist as `envrelay.<name>` with the same parameter names, order, kinds, and defaults. `envrelay.__all__` lists the same eight names. Like the oracle, the top-level `envrelay` package must not expose `__version__`; keep the version string in a submodule of your choosing and read it from there in pyproject.toml and `--version`. The command-line tree (commands, options, arguments, types, choices, defaults, flags) matches API_SURFACE.json, with the program name normalized. The magic is named `dotenv` (that is what users type) and takes the arguments listed there.
10. **API misuse.** Wrong argument types (None, ints, bytes, `pathlib.Path`, binary streams), missing files, directories where files are expected, unreadable files, invalid `quote_mode`, and unknown keyword arguments: the same exception class and message.

## Output-only text

The command line's help text, its command and option descriptions, and its error messages are output, so they must match the oracle exactly. Reproduce them from the oracle's actual output (`--help` for each command), never from memory, keep the command-line definitions in a single module, and list that module in PROVENANCE.md so the similarity check can treat it separately. That module holds only the click declarations, the output strings, and calls into the library. Glue that needs click (error mapping, exit codes, starting the command for `run`) goes in a separate module inside the package, which is measured like everything else; the core library never imports click. Every module the package contains is measured, and logic must not move outside `src/envrelay`. The same applies to the IPython magic's help and error strings (`%dotenv -h`, a bad flag, and `cannot find .env file`).

## Exempt from parity

- type annotations in signatures;
- the logger name below the `envrelay` hierarchy;
- Windows-only behavior, which can't be verified on this machine. Implement your best reading of it and list it as unverified;
- the full text of tracebacks (the exception class and message are not exempt);
- help text at `COLUMNS` below 80 (see channel 7).

## Known traps (verified against python-dotenv 1.2.4)

This list is not complete. Results are shown as Python reprs.

**Parsing**

- `dotenv_values` returns an `OrderedDict`; its repr is `OrderedDict({'A': '1'})`.
- `export A=1` gives `'1'`. `A=1 # c` gives `'1'`, but `B=1#c` gives `'1#c'`. `K= # comment` gives `''`.
- `A` alone (no `=`) gives `None`; `B=` gives `''`.
- Single quotes: `A='a\'b\nc'` gives `"a'b\\nc"` (the escaped quote is unescaped, `\n` stays literal). Double quotes decode escape sequences, and a double-quoted value may span lines.
- Keys: `"dq"=2` gives the key `'"dq"'` (quotes kept), while `'q k'=1` gives `'q k'`. `A B` and `A='x' y` are parse errors. A line that is just `export` gives the key `export` with value None, and `export=1` gives the key `export`. In double quotes, `é`, `\x41`, and `\q` stay literal.
- Duplicate keys: the last one wins. The key `A.B-C:D` is accepted. A leading UTF-8 BOM is ignored.
- A line that can't be parsed logs WARNING `python-dotenv could not parse statement starting at line 2` (with its line number), and parsing continues with the next line. The line number is where the statement's leading blank lines begin, not the bad line itself: in `A=1\n\n\n'bad\nB=2\n` the bad statement is on line 4 but the warning says `line 2`. An unterminated quote on line 1 logs that warning for line 1, and `B=2` on line 2 is still read.
- Line endings depend on the source. Read from a path, CRLF and CR become LF before parsing. Read from a stream, they don't: `B="x\r\ny"` gives `'x\r\ny'` from a stream but `'x\ny'` from a file, and in a stream with CRLF endings, warning line numbers drift after each bad line (`A=1\r\nx y\r\nB=2\r\nz w\r\nC=3\r\n` warns at lines 2 and 5). Feed the grammar's documents through both paths and streams.
- Interpolation: `${A}` expands, `${MISSING:-def}` gives `'def'`, `$A` does not expand, and a single-quoted `'${A}'` does expand. `interpolate=False` keeps `${A}` literally. Values resolve in file order: with `A=${B:-x}${C}`, then `B=2`, then `C=${B}`, the result is `{'A': 'x', 'B': '2', 'C': '2'}`.
- Shell intuition is wrong here. With `A=` (empty) or a bare `A` earlier in the file, `${A:-d}` gives `''`, not `'d'`. `${A-x}` gives `''` (it looks up a variable named `A-x`). With an empty `A`, `${A:-${C}}` gives `'}'`; there is no nesting. `${}` gives `''`, and `X=${X}` gives `''`.
- Override changes which side interpolation reads. With `A=9` in the environment and the file `A=1\nB=${A}`, `load_dotenv` without override and `run --no-override` give `B` the value `9`, while `dotenv_values` and `get` give `1`.

**Loading**

- Without `override`, an existing environment variable keeps its value; with `override=True` it is replaced. Keys with value None are not set.
- A missing file returns `False` and logs nothing. With `verbose=True` it logs INFO `python-dotenv could not find configuration file /nonexistent/.env.`
- Paths are used as given: `~` is not expanded. `dotenv_values('', verbose=True)` returns `OrderedDict()` and logs INFO `python-dotenv could not find configuration file .env.`. A missing path together with a stream reads the stream: `dotenv_values('nope', stream=StringIO('Z=1'))` gives `{'Z': '1'}`. A FIFO is read like a file. `load_dotenv` returns `True` when the file's only key has value None.
- `PYTHON_DOTENV_DISABLED` set to `1`, `t`, `true`, `y`, or `yes` (any case) disables loading: the call returns `False` and logs DEBUG `python-dotenv: .env loading disabled by PYTHON_DOTENV_DISABLED environment variable`. Values such as `on`, ` 1` (with a space), `0`, `false`, empty, or `x` do not disable it. It affects `load_dotenv` and the magic only; `dotenv_values`, `get_key`, and every command, including `run`, ignore it.

**File editing**

- `set_key` returns `(True, key, value)`. The default `quote_mode='always'` writes `C='hello world'`. An existing key's line is rewritten in place, and every duplicate of that key is rewritten (`A=1\nB=2\nA=3` becomes `A='x'\nB=2\nA='x'\n`). An `export` prefix on the rewritten line is dropped unless `export=True`. The whole file is rewritten with LF line endings (`b"A=1\r\nB=2\r\n"` plus a new key gives `b"A=1\nB=2\nC='x'\n"`). `'never'` writes `D=v v`. `'auto'` writes `K=v` and `K=é1` unquoted but `K='a b'`, `K='x#y'`, `K='a_b'`, and `K=''` quoted. `export=True` writes `export G='1'`. An unknown mode raises `ValueError: Unknown quote_mode: bogus`.
- A single quote is escaped as `Q='it\'s'`; backslashes are doubled. A value containing a newline is written with a real newline inside the quotes.
- A newly created file gets mode `0o600`; an existing file keeps its mode, even a read-only one, which is still rewritten (as a new file, with a new inode). By default a symlink is replaced by a regular file; with `follow_symlinks=True` the target is written. A missing directory raises `FileNotFoundError: [Errno 2] No such file or directory: '/nonexistent/dir/.tmp_<random>'`.
- `get_key` on a missing key returns `None` and logs WARNING `Key NOPE not found in <path>.` On a missing file it first logs INFO `python-dotenv could not find configuration file nope.env.`
- `unset_key` returns `(True, key)`. A missing key returns `(None, key)` and logs WARNING `Key NOPE not removed from <path> - key doesn't exist.` A missing file returns `(None, key)` and logs WARNING `Can't delete from /nonexistent/.env - it doesn't exist.` An invalid `quote_mode` is ignored by `unset_key`.

**Finding files**

- From a script in `a/b/` with `.env` in `a/`, `find_dotenv()` returns the absolute path to `a/.env`. It searches from the calling script's location, not from the working directory, unless `usecwd=True`.
- With nothing found it returns `''`; with `raise_error_if_not_found=True` it raises `OSError: File not found`.
- Under `python -c` it searches from the working directory. Run from code piped on stdin, it raises AssertionError. Assert statements in your code matter: never run anything with `-O`.

**Helper**

- `get_cli_string()` gives `'dotenv'`; `('p', 'get', 'K')` gives `'dotenv -f p get K'`; `('p', 'set', 'K', 'v v')` gives `'dotenv -f p set K "v v"'`; `('p', 'set', 'K', 'v', quote='never')` gives `'dotenv -q never -f p set K v'`.

**Command line** (shown as `python -m dotenv`)

- `--version` prints `python -m dotenv, version 1.2.4`; the console script prints `dotenv, version 1.2.4`.
- `list` prints keys sorted, `A=1` and `B=two words` (no quotes), and skips keys whose value is None. `--format=json` prints indented, ASCII-escaped JSON (`"é"`) including `"D": null`; `--format=shell` prints `B='two words'`; `--format=export` prints `export A=1`.
- `get` on a missing key or a None value exits 1 and prints nothing. An empty value prints an empty line and exits 0.
- `set K "a b"` prints `K=a b` (unquoted) while the file gets `K='a b'`. `-q never` and `-e true` change what is written.
- `unset A` prints `Successfully removed A`. A missing key exits 1 with the logging warning on stderr.
- `-f nope.env list` exits 2 with `Error opening env file: [Errno 2] No such file or directory: 'nope.env'`.
- `run` checks the file first: a missing `.env` or a directory exits 2 with `Error: Invalid value: Invalid value for '-f' "<path>" does not exist.` after the usage lines. Only when the file exists does `run` with no command exit 1 and print `No command given.` on stdout. A command that doesn't exist exits 1 with `Command not found: nosuchcmd` on stderr. Unknown options pass through as the command: `run -x echo hi` gives `Command not found: -x`. `run` rejects a FIFO, which the library functions accept. `run` overrides existing variables by default; `--no-override` keeps them.
- Errors the command line doesn't catch end in a traceback with exit 1, for example `run /etc` (`PermissionError`), `-f <directory> set A 1` (`IsADirectoryError`), and `list` on a file with an undecodable byte (`UnicodeDecodeError`). Compare these through the traceback normalization.
- Without click installed, `python -m dotenv` writes `It seems python-dotenv is not installed with cli option. \nRun pip install "python-dotenv[cli]" to fix this.` to stderr, with no trailing newline, and exits 1. Reproduce it verbatim (confirm it by running the oracle in an environment without click).
- `run` replaces the current process with the command (the child has the same process id), so its exit status is the program's exit status: `run sh -c 'exit 7'` exits 7.

# How to work

1. **Plan.** Save this prompt verbatim as BUILD_PROMPT.md, so later sessions can read it. Create the project environment on the oracle's interpreter: run `<path> -m venv .venv`, where the path is the second line of ~/envrelay-oracle/ORACLE_PYTHON.txt, and write that interpreter's version to `.python-version`. Install click 8.5.0, IPython, and your test tools into it. Then write SPEC.md in your own words: the contract, your architecture, and the test strategy.
2. **Check the API surface first.** Write a conformance test that walks API_SURFACE.json and checks every function signature, `__all__`, the command-line tree, and the magic's arguments in envrelay. It fails until the build is complete.
3. **Build the differential harness before the library.** `tests/differential/` runs the same input against envrelay and the oracle and compares every channel above. It runs only on the Python minor version and bytecode magic number recorded in ~/envrelay-oracle/ORACLE_PYTHON.txt, with click 8.5.0. It skips when the oracle is missing or the versions don't match, but setting `ENVRELAY_REQUIRE_ORACLE=1` must turn every such skip into a failure. Feed it:
   - **Hypothesis-generated .env documents** built from a grammar you write: keys (plain, dotted, dashed, with colons, non-ASCII, empty, quoted), `export` prefixes and near-misses, `=` with spaces and tabs around it, unquoted, single-quoted, double-quoted, and unterminated values, every escape sequence (known, unknown, and malformed), comments in every position, interpolations (`${X}`, `${X:-d}`, `$X`, unbalanced braces, references forward, backward, and to itself), multiline values, LF, CRLF, CR, and mixed line endings, a BOM, blank and whitespace-only lines, no final newline, very long lines, and non-UTF-8 bytes read with other encodings;
   - **each document through every reader, with generated preexisting environment variables that overlap the file's keys:** `dotenv_values` (path and stream, interpolate on and off; interpolation reads the environment too: with `X=5` set, `A=${X}\nX=1\nB=${X}` gives `{'A': '5', 'X': '1', 'B': '1'}`), `load_dotenv` (override on and off, verbose), and the command line's `list` in every format and `get` for every key;
   - **control characters in keys and values,** including NUL (`load_dotenv` raises `ValueError: embedded null byte` partway through, after setting earlier keys), and lines such as `=1`;
   - **Hypothesis-generated editing sequences:** `set_key`, `get_key`, and `unset_key` over starting files that are absent, empty, without a final newline, with CRLF, with duplicate keys, with comments and `export` lines, with every quote mode, `export`, encoding, and value shape (quotes, backslashes, newlines, `#`, `${}`, empty, non-ASCII), plus generated key shapes (spaces, `=`, quotes, `#`, empty) and non-string values (`set_key(p, 'a b=c', 'v')` writes `a b=c='v'`; `set_key(p, 'Z', None)` raises `AttributeError: 'NoneType' object has no attribute 'replace'`), `get_key` on keys with no `=` (returns None and logs nothing), encodings that can't represent the value (error positions must match), permission bits, symlinks, and `follow_symlinks`;
   - **generated directory trees for `find_dotenv`,** with scripts at varying depths, symlinked directories, `usecwd`, `filename`, and every way of running Python listed in channel 5, plus `load_dotenv()` and `dotenv_values()` called with no path (they search the same way);
   - **every command, option, and error path of the command line,** run three ways, and as both `python -m` and the console script, including `-f -`, every spelling of `-e` (`1`, `yes`, `off`, bad values), `--format` in other cases, `run --`, and stdin passed through to the `run` child;
   - **the IPython magic,** and **every misuse case** in channel 10;
   - **a suite of realistic configuration files you write yourself,** in the style of web apps, data pipelines, container setups, and CI jobs, none copied from anywhere.

   Keep a coverage matrix (input classes by channels) in the repo and fill every cell with real cases. A large case count made of trivial cases doesn't count.
4. **Implement in phases until the harness shows zero mismatches:** parsing, interpolation, loading, file editing, finding files, the helper, the command line, then the magic. After each phase, commit and record the differential pass rate in PROVENANCE.md. When something differs, find the general rule by probing the oracle with smaller inputs. Never special-case a test input.
5. **Write original unit tests** with their own assertions, so the suite stands on its own without the oracle.
6. **Create the repo artifacts** below.
7. **Get a fresh review.** Ask a subagent that hasn't seen this conversation, and is bound by the same independence rules, to look for channels, input classes, or run modes the harness doesn't cover, and add what it finds.

# Repo artifacts (the same set as the python-dotenv repo, your own content throughout)

- **README.md,** which must explain how to build the oracle and run the differential suite, so the evidence can be reproduced from the repo.
- **LICENSE:** MIT, copyright Nick Serapiglia.
- **CHANGELOG.md, CONTRIBUTING.md, RELEASING.md**
- **pyproject.toml:** setuptools backend, src layout, distribution and import name `envrelay`, `requires-python >=3.10`, no core runtime dependencies, a `cli` extra requiring a click range that includes 8.5.0, the console script `envrelay`, `python -m envrelay` support, and the version read from the package.
- **.bumpversion.cfg, MANIFEST.in, Makefile** (clean, sdist, test, format, coverage, coverage-html, and release targets), **requirements.txt** (development) and **requirements-docs.txt**
- **ruff.toml, tox.ini, .editorconfig, .gitignore, .pre-commit-config.yaml**
- **src/envrelay/,** with `py.typed`.
- **tests/**
- **docs/** and a root-level **mkdocs.yml:** an MkDocs site with an API reference generated from your docstrings, plus index, changelog, contributing, and license pages, in your own words and with your own examples. It must build without errors.
- **.github/:** SECURITY.md, dependabot.yml, a test workflow for Python 3.10 to 3.15, and a release workflow triggered only by manual dispatch.
- **PROVENANCE.md:** the model and version, the dates, every information source consulted, the pass rate after each phase, the output-only text module, and every moment the independence rules came close to being broken.
- **SPEC.md, NEXT_STEPS.md, BUILD_PROMPT.md,** and the coverage matrix.

Commit as you go with Conventional Commit messages.

# Done means

Report with evidence, meaning each command and its actual output rather than a summary:

- the full pytest run on the oracle's Python version, with `ENVRELAY_REQUIRE_ORACLE=1`, `-rs` and `-p no:warnings`, showing zero skipped differential tests, the interpreter version, and the click version. Other Python versions run the unit tests only;
- API surface conformance at 100%;
- the number of generated cases: at least 20,000 .env documents through the library readers in-process, at least 1,000 of those documents through the command line in each of the three run modes, at least 5,000 editing sequences, at least 500 `find_dotenv` layouts, and every hand-written command-line case in all three run modes;
- a per-channel differential table with zero mismatches. Any remaining mismatch, listed with a minimal repro, means not done;
- tox results for every Python version installed on this machine;
- the docs build output;
- grep output showing that the library never imports `dotenv`, never references the oracle folder, and that no requirements file or `pip freeze` line contains python-dotenv;
- the coverage matrix with every cell filled.

Don't run any code-similarity tool. That check, and a final differential run on inputs you haven't seen, happen separately.
