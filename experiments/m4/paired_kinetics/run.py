"""Orchestrate two scientific workers with explicit artifacts; root stays tooling-only."""

import argparse
import platform
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from experiments.m4.paired_observation.run import ARCHIVE as BOUNDARY_FILES

from .common import (
    HERE,
    REUSED,
    ROOT,
    SOURCES,
    VERSION,
    cases,
    dump,
    file_hashes,
    read,
    validate,
)
from .report import reconstruct


def command(args, output, log_name):
    with (output / log_name).open("x") as log:
        subprocess.run(args, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)


def execute(boundary_run, protocol, output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    manifest = {
        "schema": "bc005-run/1",
        "implementation": VERSION,
        "status": "started",
        "started_utc": datetime.now(UTC).isoformat(),
        "parent_python": platform.python_version(),
        "files": {},
    }
    dump(output / "manifest.json", manifest)
    try:
        manifest["git_head"] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
        manifest["git_dirty"] = bool(
            subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT)
        )
        shutil.copyfile(protocol, output / "protocol.json")
        p = read(output / "protocol.json")
        validate(p)
        for name in SOURCES:
            shutil.copyfile(HERE / name, output / f"source-{name}")
        for path in REUSED:
            shutil.copyfile(ROOT / path, output / ("source-" + path.replace("/", "__")))
        for branch, runtime in p["runtime"].items():
            for name in ("uv.lock", "pyproject.toml"):
                shutil.copyfile(ROOT / runtime["project"] / name, output / f"{branch}-{name}")
        boundary_run = Path(boundary_run).resolve()
        cases(boundary_run, p)
        allowed = {*BOUNDARY_FILES, "protocol.json", "preflight.json"}
        original = read(boundary_run / "manifest.json")
        if set(original["files"]) != allowed:
            raise ValueError(
                "Unexpected boundary artifacts; only the fixed synthetic archive is accepted"
            )
        (output / "boundary").mkdir()
        for name in sorted(allowed | {"manifest.json"}):
            shutil.copyfile(boundary_run / name, output / "boundary" / name)
        manifest["commands"] = []
        for branch in p["branches"]:
            args = [
                "uv",
                "run",
                "--locked",
                "--project",
                str(ROOT / p["runtime"][branch]["project"]),
                "python",
                "-m",
                "experiments.m4.paired_kinetics.worker",
                str(output),
                "--branch",
                branch,
            ]
            manifest["commands"].append(args)
            dump(output / "manifest.json", manifest)
            command(args, output, f"{branch}.log")
        manifest.update(status="calculated", files=file_hashes(output))
        dump(output / "manifest.json", manifest)
        report = reconstruct(output, allow_pending=True)
        dump(output / "report.json", report)
        if not report["passed"]:
            raise RuntimeError("Paired numerical criteria failed; inspect preserved report")
        manifest["files"] = file_hashes(output)
        dump(output / "manifest.json", manifest)
        command(
            [
                "uv",
                "run",
                "--locked",
                "--project",
                str(ROOT / p["runtime"]["cpeptide"]["project"]),
                "python",
                "-m",
                "experiments.m4.paired_kinetics.plot",
                str(output),
                "--output",
                str(output / "figure.svg"),
                "--allow-pending",
            ],
            output,
            "plot.log",
        )
        manifest.update(
            status="completed",
            finished_utc=datetime.now(UTC).isoformat(),
            files=file_hashes(output),
        )
        dump(output / "manifest.json", manifest)
        return report
    except BaseException as exc:
        manifest.update(
            status="failed",
            finished_utc=datetime.now(UTC).isoformat(),
            error={"type": type(exc).__name__, "message": str(exc)},
            files=file_hashes(output),
        )
        dump(output / "manifest.json", manifest)
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--boundary-run", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, default=HERE / "protocol.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = execute(args.boundary_run, args.protocol, args.output)
    print(f"BC-005 completed: passed={report['passed']}; paired kinetics only")


if __name__ == "__main__":
    main()
