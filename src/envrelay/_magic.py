"""IPython line magic: ``%dotenv [-o] [-v] [path]``.

Registered by ``%load_ext envrelay``. IPython is imported lazily so importing
``envrelay`` never requires it. The help and error strings are reproduced from
the reference's actual output and kept in this module.
"""

from __future__ import annotations

from ._core import find_dotenv, load_dotenv

_USAGE = "%dotenv [-o] [-v] [dotenv_path]"


def load_ipython_extension(ipython):
    """Entry point for ``%load_ext envrelay``."""
    from IPython.core.magic import line_magic, magics_class, Magics
    from IPython.core.magic_arguments import (
        argument,
        magic_arguments,
        parse_argstring,
    )

    @magics_class
    class _EnvRelayMagics(Magics):
        @line_magic("dotenv")
        @magic_arguments()
        @argument(
            "-o",
            "--override",
            action="store_true",
            help="Indicate to override existing variables",
        )
        @argument(
            "-v",
            "--verbose",
            action="store_true",
            help="Indicate function calls to be verbose",
        )
        @argument("dotenv_path", nargs="?", type=str, default=".env")
        def dotenv(self, line):
            args = parse_argstring(self.dotenv, line)
            try:
                path = find_dotenv(
                    args.dotenv_path, raise_error_if_not_found=True, usecwd=True
                )
            except IOError:
                print("cannot find .env file")
                return
            load_dotenv(path, verbose=args.verbose, override=args.override)

    ipython.register_magics(_EnvRelayMagics)
