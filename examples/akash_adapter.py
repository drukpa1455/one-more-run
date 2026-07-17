"""Compatibility entrypoint for the packaged Akash adapter."""

import sys

from one_more_run.akash_adapter import main


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
