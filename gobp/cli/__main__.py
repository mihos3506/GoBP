"""Module entry point — allows `python -m gobp.cli`."""

import sys

from gobp.cli.commands import main

if __name__ == "__main__":
    sys.exit(main())
