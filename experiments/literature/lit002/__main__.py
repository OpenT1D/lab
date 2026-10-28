"""Bounded LIT-002 execution and simulation-free report reconstruction."""

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    execute = commands.add_parser("run", help="Execute all 18 frozen synthetic cases")
    execute.add_argument("--output", type=Path, required=True)
    report = commands.add_parser("report", help="Reconstruct a report from sealed artifacts only")
    report.add_argument("--study", type=Path, required=True)
    report.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "run":
        from .run import run

        result = run(args.output)
    else:
        from .report import write_report

        result = write_report(args.study, args.output)
    print(json.dumps({"all_passed": result["all_passed"], "output": str(args.output.resolve())}))
    if not result["all_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
