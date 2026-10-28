"""Synthetic, frozen researcher CGM forecasts with complete failure accounting."""

import argparse
import sys
from pathlib import Path

from .fixtures import fixture
from .study import reconstruct, run_study


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("fixture", "verify"):
        command = commands.add_parser(name)
        command.add_argument("--output", type=Path, required=True)
    run = commands.add_parser("run")
    run.add_argument("--config", type=Path, required=True)
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--timeout", type=float, default=120)
    report = commands.add_parser("report")
    report.add_argument("--study", type=Path, required=True)
    report.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "fixture":
            fixture(args.output)
        elif args.command == "verify":
            from .verify import verify

            verify(args.output)
        elif args.command == "report":
            reconstruct(args.study, args.output)
        else:
            result = run_study(args.config, args.output, args.timeout)
            if any(
                c["execution_status"] != "completed"
                for c in result["evaluation"]["people"].values()
            ):
                print(
                    "Synthetic run retained execution failures; inspect report.md.", file=sys.stderr
                )
                return 1
    except (Exception, KeyboardInterrupt) as error:
        print(f"Researcher forecast workflow failed ({type(error).__name__}).", file=sys.stderr)
        return 1
    print("Synthetic researcher forecast artifacts saved; no human evaluation.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
