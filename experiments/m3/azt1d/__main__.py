"""AZT1D conversion, frozen study execution and artifact reconstruction."""

import argparse
import json
import os
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("fixture", "study-fixture"):
        command = commands.add_parser(name)
        command.add_argument("--output", type=Path, required=True)
    command = commands.add_parser("normalize")
    command.add_argument("--input", type=Path, required=True)
    command.add_argument("--intake", type=Path, required=True)
    command.add_argument("--output", type=Path, required=True)
    command = commands.add_parser("prepare")
    command.add_argument("--conversion", type=Path, required=True)
    command.add_argument("--output", type=Path, required=True)
    command = commands.add_parser("freeze")
    command.add_argument("--registry", type=Path, required=True)
    command.add_argument("--output", type=Path, required=True)
    command = commands.add_parser("init-ledger")
    command.add_argument("--plan", type=Path, required=True)
    for name in ("fit", "evaluate"):
        command = commands.add_parser(name)
        command.add_argument("--plan", type=Path, required=True)
        command.add_argument("--output", type=Path, required=True)
        command.add_argument("--timeout", type=float, default=120)
        if name == "evaluate":
            command.add_argument("--fit", type=Path, required=True)
    command = commands.add_parser("report")
    command.add_argument("--study", type=Path, required=True)
    command.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command in ("fixture", "study-fixture"):
            from .fixtures import generate, generate_study

            (generate if args.command == "fixture" else generate_study)(args.output)
        elif args.command in ("normalize", "prepare"):
            from .service import normalize, prepare

            if args.command == "normalize":
                normalize(args.input, args.intake, args.output)
            else:
                prepare(args.conversion, args.output)
        elif args.command == "report":
            from .analysis import reconstruct
            from .common import outside_repository

            report = reconstruct(args.study)
            if report["kind"] == "human":
                outside_repository(args.output)
            descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "w") as stream:
                json.dump(report, stream, indent=2, allow_nan=False)
                stream.write("\n")
        else:
            from .study import fit_plan, freeze, init_ledger, run_study

            if args.command == "freeze":
                freeze(args.registry, args.output)
            elif args.command == "init-ledger":
                init_ledger(args.plan)
            elif args.command == "fit":
                fit_plan(args.plan, args.output, args.timeout)
            else:
                run_study(args.plan, args.fit, args.output, args.timeout)
    except BaseException as error:
        print(
            f"AZT1D command failed ({type(error).__name__}); review private status.",
            file=sys.stderr,
        )
        return 1
    print("AZT1D command completed. Results depend on the declared input kind.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
