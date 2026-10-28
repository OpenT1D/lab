"""Private execution of the frozen PhysioCGM comparison; no acquisition or fitting."""

import argparse
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("prepare")
    command.add_argument("--request", type=Path, required=True)
    command.add_argument("--output", type=Path, required=True)
    command = commands.add_parser("evaluate")
    command.add_argument("--plan", type=Path, required=True)
    command.add_argument("--output", type=Path, required=True)
    command.add_argument("--timeout", type=float, default=120)
    command = commands.add_parser("report")
    command.add_argument("--study", type=Path, required=True)
    command.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "report":
            from .analysis import reconstruct

            reconstruct(args.study, args.output)
        else:
            from .study import prepare, run

            if args.command == "prepare":
                prepare(args.request, args.output)
            else:
                run(args.plan, args.output, args.timeout)
    except BaseException as error:
        print(
            f"Private evaluation command failed ({type(error).__name__}); inspect private status.",
            file=sys.stderr,
        )
        return 1
    print("Private evaluation step completed; no patient values or scores printed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
