"""Entry point for ``python -m envrelay`` and the ``envrelay`` console script.

click is optional (the ``cli`` extra). When it is missing we print the same
guidance the reference prints -- verbatim, including its mention of
python-dotenv -- and exit 1, rather than letting an ImportError traceback out.
"""

from __future__ import annotations

import sys


def main(prog_name=None):
    try:
        import click  # noqa: F401
    except ImportError:
        sys.stderr.write(
            "It seems python-dotenv is not installed with cli option. \n"
            'Run pip install "python-dotenv[cli]" to fix this.'
        )
        sys.exit(1)
    from ._commandline import cli

    if prog_name is not None:
        cli(prog_name=prog_name)
    else:
        cli()


if __name__ == "__main__":
    main(prog_name="python -m envrelay")
