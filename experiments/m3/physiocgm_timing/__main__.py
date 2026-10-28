"""CLI accepts only generated synthetic examples, never a human input path."""

import argparse
import json

from .study import demo, verify


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("demo").add_argument("--output", required=True)
    commands.add_parser("verify").add_argument("--study", required=True)
    args = parser.parse_args()
    try:
        result = demo(args.output) if args.command == "demo" else verify(args.study)
    except Exception as error:
        # Exception types suffice; never print payloads or potentially private paths.
        print(json.dumps({"status": "failed", "error_type": type(error).__name__}))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
