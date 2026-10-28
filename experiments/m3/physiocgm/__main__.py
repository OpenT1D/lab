"""Synthetic preparation and private human conversion; no model evaluation."""

import argparse
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("fixture")
    command.add_argument("--output", type=Path, required=True)
    command = commands.add_parser("prepare")
    command.add_argument("--request", type=Path, required=True)
    command.add_argument("--output", type=Path, required=True)
    command = commands.add_parser("verify")
    command.add_argument("--bundle", type=Path, required=True)
    command = commands.add_parser("human-freeze")
    command.add_argument("--request", type=Path, required=True)
    command.add_argument("--output", type=Path, required=True)
    command = commands.add_parser("human-prepare")
    command.add_argument("--plan", type=Path, required=True)
    command.add_argument("--output", type=Path, required=True)
    command = commands.add_parser("human-verify")
    command.add_argument("--bundle", type=Path, required=True)
    command.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "fixture":
            from .fixtures import generate

            generate(args.output)
        elif args.command == "prepare":
            from .service import prepare

            prepare(args.request, args.output)
        elif args.command == "verify":
            from .service import verify

            verify(args.bundle)
        else:
            from . import human

            if args.command == "human-freeze":
                human.freeze(args.request, args.output)
            elif args.command == "human-prepare":
                human.prepare(args.plan, args.output)
            else:
                human.verify(args.bundle, args.output)
    except BaseException as error:
        print(
            f"CGM preparation failed ({type(error).__name__}); preserve the attempt.",
            file=sys.stderr,
        )
        return 1
    if args.command.startswith("human-"):
        print("Private human CGM conversion step completed; no model evaluation.")
    else:
        print("Synthetic CGM preparation completed; human release unverified; no model evaluation.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
