"""Frozen synthetic M4 source comparison; passive checks and saved reconstruction."""

import argparse
import json
import sys
from pathlib import Path

from .common import check, require
from .report import reconstruct
from .run import run_study


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("check", help="Metadata only; no supplied source execution")
    prepare.add_argument("--config", type=Path, required=True)
    prepare.add_argument("--reference", type=Path)
    run = commands.add_parser("run")
    run.add_argument("--config", type=Path, required=True)
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--reference", type=Path)
    saved = commands.add_parser("reconstruct")
    saved.add_argument("--archive", type=Path, required=True)
    saved.add_argument("--output", type=Path, required=True)
    saved.add_argument("--allow-failed", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "check":
            print(json.dumps(check(args.config, args.reference), sort_keys=True))
            return 0
        if args.command == "run":
            result = run_study(args.config, args.output, args.reference)
        else:
            require(
                not args.output.exists() and not args.output.is_symlink(),
                "Reconstruction output must be a new directory",
            )
            result = reconstruct(args.archive, args.output, allow_failed=args.allow_failed)
        print(f"M4 comparison reports saved: {args.output / 'report.md'}")
        return 0 if args.command != "run" or result["passed"] else 1
    except (Exception, KeyboardInterrupt) as error:
        print(f"M4 comparison failed ({type(error).__name__}).", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
