# envrelay

`envrelay` reads, loads, and edits `.env` files. The core library has no runtime
dependencies; the command line is an optional `cli` extra built on click, and an
IPython magic is included.

## Install

```bash
pip install envrelay          # library only
pip install "envrelay[cli]"   # with the command line
```

## A quick tour

```python
from envrelay import dotenv_values, load_dotenv, set_key

dotenv_values(".env")     # -> OrderedDict of name -> value (or None)
load_dotenv()             # push the nearest .env into os.environ
set_key(".env", "K", "v") # edit in place, atomically
```

See the [API reference](api.md) for the full surface, and the project's
`SPEC.md` for how `envrelay` reproduces the behavior of its reference
implementation exactly.
