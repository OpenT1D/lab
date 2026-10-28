"""Canonical M2 commands; physiology remains in isolated native workers."""

import argparse
from pathlib import Path

from experiments.m1.artifacts import strict_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    case = sub.add_parser("case")
    case.add_argument("--config", type=Path, required=True)
    case.add_argument("--output", type=Path, required=True)
    case.add_argument("--plan", type=Path)
    case.add_argument("--timeout-seconds", type=float, default=300)
    demo = sub.add_parser("demo")
    demo.add_argument("--output", type=Path, required=True)
    demo.add_argument("--workers", type=int, default=4)
    evaluation = sub.add_parser("evaluate")
    evaluation.add_argument("--plan", type=Path, required=True)
    evaluation.add_argument("--output", type=Path, required=True)
    evaluation.add_argument("--workers", type=int, default=4)
    freeze = sub.add_parser("freeze")
    freeze.add_argument("--development", type=Path, required=True)
    freeze.add_argument("--native-verification", type=Path, required=True)
    freeze.add_argument("--output", type=Path, required=True)
    verify = sub.add_parser("verify-study")
    verify.add_argument("--study", type=Path, required=True)
    verify.add_argument("--output", type=Path, required=True)
    report = sub.add_parser("report")
    report.add_argument("--study", type=Path, required=True)
    report.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "case":
        from .run import execute

        # Invalid or missing input is still passed to the recorder for failure retention.
        try:
            cfg = strict_json(args.config.read_bytes())
            driver = "simglucose" if cfg.get("engine") == "simglucose" else "cambridge"
        except (ValueError, OSError, AttributeError):
            driver = "cambridge"
        result = execute(
            args.config,
            args.output,
            args.timeout_seconds,
            _driver=driver,
            evaluation_plan=args.plan,
        )
        if result["status"] != "completed":
            raise SystemExit(1)
    elif args.command in ("demo", "evaluate"):
        from .study import run

        run(
            args.output.resolve(),
            "development" if args.command == "demo" else "evaluation",
            getattr(args, "plan", None),
            args.workers,
        )
    elif args.command == "freeze":
        from .study import freeze

        freeze(args.development, args.native_verification, args.output)
    elif args.command == "verify-study":
        from .verify_study import verify

        verify(args.study, args.output)
    else:
        from .report import write_report

        write_report(args.study, args.output)


if __name__ == "__main__":
    main()
