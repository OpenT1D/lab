"""Frozen-model external evaluation; no external fitting command."""

import argparse
import json
import os
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("fixture")
    command.add_argument("--output", type=Path, required=True)
    command = commands.add_parser("export-model")
    command.add_argument("--plan", type=Path, required=True)
    command.add_argument("--fit", type=Path, required=True)
    command.add_argument("--output", type=Path, required=True)
    command = commands.add_parser("freeze")
    command.add_argument("--registry", type=Path, required=True)
    command.add_argument("--model", type=Path, required=True)
    command.add_argument("--output", type=Path, required=True)
    command = commands.add_parser("init-ledger")
    command.add_argument("--plan", type=Path, required=True)
    command = commands.add_parser("evaluate")
    command.add_argument("--plan", type=Path, required=True)
    command.add_argument("--output", type=Path, required=True)
    command.add_argument("--timeout", type=float, default=120)
    command = commands.add_parser("report")
    command.add_argument("--study", type=Path, required=True)
    command.add_argument("--output", type=Path, required=True)
    command = commands.add_parser("human-freeze")
    command.add_argument("--request", type=Path, required=True)
    command.add_argument("--output", type=Path, required=True)
    command = commands.add_parser("human-verify-freeze")
    command.add_argument("--bundle", type=Path, required=True)
    command.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "fixture":
            from .fixtures import generate

            generate(args.output)
        elif args.command == "export-model":
            from .model import export_model

            export_model(args.plan, args.fit, args.output)
        elif args.command == "report":
            from experiments.m3.azt1d.common import outside_repository

            from .analysis import reconstruct

            report = reconstruct(args.study)
            if report["kind"] == "human":
                outside_repository(args.output)
            descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "w") as stream:
                json.dump(report, stream, indent=2, allow_nan=False)
                stream.write("\n")
        elif args.command in ("human-freeze", "human-verify-freeze"):
            from . import human_freeze

            if args.command == "human-freeze":
                human_freeze.freeze(args.request, args.output)
            else:
                human_freeze.verify(args.bundle, args.output)
        else:
            from .study import freeze, init_ledger, run_study

            if args.command == "freeze":
                freeze(args.registry, args.model, args.output)
            elif args.command == "init-ledger":
                init_ledger(args.plan)
            else:
                run_study(args.plan, args.output, args.timeout)
    except BaseException as error:
        print(
            f"External M3 command failed ({type(error).__name__}); review private status.",
            file=sys.stderr,
        )
        return 1
    if args.command in ("human-freeze", "human-verify-freeze"):
        print("Private external freeze step completed; no prediction or scoring performed.")
    else:
        print("External M3 command completed. No model was fitted by this command.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
