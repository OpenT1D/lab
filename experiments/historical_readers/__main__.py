"""Reconstruct saved evidence with an explicit trusted historical Git checkout."""

import argparse
import json
import subprocess
from pathlib import Path

from .core import TASKS, reconstruct


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    saved = commands.add_parser("reconstruct")
    saved.add_argument("task", choices=TASKS)
    saved.add_argument("--archive", type=Path, required=True)
    saved.add_argument("--checkout", type=Path, required=True)
    saved.add_argument("--revision", required=True)
    saved.add_argument("--output", type=Path, required=True)
    saved.add_argument("--timeout-seconds", type=int, default=120)
    saved.add_argument("--allow-failed", action="store_true")
    args = parser.parse_args()
    try:
        result = reconstruct(
            args.task,
            args.archive,
            args.checkout,
            args.revision,
            args.output,
            timeout_seconds=args.timeout_seconds,
            allow_failed=args.allow_failed,
        )
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(json.dumps({"error_type": type(error).__name__, "error": str(error)[:300]}))
        return 2
    print(
        json.dumps(
            {
                key: result[key]
                for key in ("status", "verified_reconstruction", "complete", "exit_code", "errors")
            },
            sort_keys=True,
        )
    )
    return 0 if result["verified_reconstruction"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
