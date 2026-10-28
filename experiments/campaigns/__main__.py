"""Check, execute, explicitly resume or reconstruct a frozen local M4 campaign."""

import argparse
import json
from pathlib import Path

from .common import check
from .report import reconstruct
from .run import resume, run_study


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    passive = commands.add_parser("check")
    passive.add_argument("--config", type=Path, required=True)
    fresh = commands.add_parser("run")
    fresh.add_argument("--config", type=Path, required=True)
    fresh.add_argument("--output", type=Path, required=True)
    again = commands.add_parser("resume")
    again.add_argument("--campaign", type=Path, required=True)
    saved = commands.add_parser("reconstruct")
    saved.add_argument("--campaign", type=Path, required=True)
    saved.add_argument("--output", type=Path, required=True)
    saved.add_argument("--allow-failed", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "check":
            result = check(args.config)
        elif args.command == "run":
            result = run_study(args.config, args.output)
        elif args.command == "resume":
            result = resume(args.campaign)
        else:
            result = reconstruct(args.campaign, args.output, args.allow_failed)
        print(json.dumps(result, sort_keys=True, allow_nan=False))
        return 0 if args.command in {"check", "reconstruct"} or result["passed"] else 1
    except (OSError, ValueError, KeyError, TypeError, ImportError, KeyboardInterrupt) as error:
        print(json.dumps({"error_type": type(error).__name__, "error": str(error)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
