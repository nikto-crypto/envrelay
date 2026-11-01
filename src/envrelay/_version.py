"""Single source of truth for the package version.

The top-level package deliberately does not re-export this, mirroring the
contract: ``import envrelay; envrelay.__version__`` must raise
``AttributeError``. The console script, ``python -m envrelay``, and
``pyproject.toml`` all read the string from here.
"""

VERSION = "0.1.0"
