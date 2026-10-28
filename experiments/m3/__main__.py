"""Canonical local M3 CLI; no patient acquisition or external calls."""

import argparse
from pathlib import Path

from .common import save


def main():
    p = argparse.ArgumentParser(description=__doc__)
    commands = p.add_subparsers(dest="command", required=True)
    f = commands.add_parser("fixture")
    f.add_argument("--output", type=Path, required=True)
    f = commands.add_parser("freeze")
    f.add_argument("--registry", type=Path, required=True)
    f.add_argument("--output", type=Path, required=True)
    f = commands.add_parser("fit")
    f.add_argument("--plan", type=Path, required=True)
    f.add_argument("--output", type=Path, required=True)
    f.add_argument("--timeout", type=float, default=120)
    f = commands.add_parser("evaluate")
    f.add_argument("--plan", type=Path, required=True)
    f.add_argument("--fit", type=Path, required=True)
    f.add_argument("--output", type=Path, required=True)
    f.add_argument("--timeout", type=float, default=120)
    f.add_argument("--reuse", action="store_true")
    f = commands.add_parser("report")
    f.add_argument("--study", type=Path, required=True)
    f.add_argument("--output", type=Path, required=True)
    f = commands.add_parser("normalize")
    f.add_argument("--input", type=Path, required=True)
    f.add_argument("--intake", type=Path, required=True)
    f.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if args.command == "normalize":
        from .intake import normalize

        normalize(args.input, args.intake, args.output)
    elif args.command == "fixture":
        from .fixtures import generate

        generate(args.output)
    elif args.command == "freeze":
        from .workflow import freeze

        freeze(args.registry, args.output)
    elif args.command == "fit":
        from .workflow import fit_plan

        fit_plan(args.plan, args.output, args.timeout)
    elif args.command == "evaluate":
        from .workflow import run_study

        run_study(args.plan, args.fit, args.output, args.timeout, args.reuse)
    else:
        from .analysis import reconstruct

        if args.output.exists():
            p.error("Output exists; preserve the original report")
        report = reconstruct(args.study)
        if report["kind"] == "human":
            from .common import ROOT, require

            require(
                not args.output.resolve().is_relative_to(ROOT),
                "Human report must remain outside repository",
            )
        save(args.output, report)


if __name__ == "__main__":
    main()
