"""Native command line for the frozen configurable synthetic study."""

import argparse
import json
from pathlib import Path

from .common import prepare


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    check = sub.add_parser("check")
    check.add_argument("--config", type=Path, required=True)
    run = sub.add_parser("run")
    run.add_argument("--config", type=Path, required=True)
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--reference", type=Path)
    reconstruct = sub.add_parser("reconstruct")
    reconstruct.add_argument("--archive", type=Path, required=True)
    reconstruct.add_argument("--output", type=Path, required=True)
    reconstruct.add_argument("--allow-failed", action="store_true")
    args = parser.parse_args()
    if args.action == "check":
        print(json.dumps(prepare(args.config), sort_keys=True))
        return
    if args.action == "run":
        from .run import run_study

        result = run_study(args.config, args.output, args.reference)
    else:
        from .report import reconstruct as read_archive

        result = read_archive(args.archive, write_to=args.output, allow_failed=args.allow_failed)
    print(str(args.output / "report.json"))
    if not result["passed"] and not (args.action == "reconstruct" and args.allow_failed):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
