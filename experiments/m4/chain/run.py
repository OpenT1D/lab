"""One command starts a fresh BC-001 reference and both existing kinetic branches."""

import argparse
import platform
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from .common import HERE, REUSED, ROOT, SOURCES, VERSION, dump, file_hashes, read, validate
from .report import reconstruct


def command(args, output, log_name):
    with (output / log_name).open("x") as log:
        subprocess.run(args, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)


def execute(output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    manifest = {
        "schema": "bc007-run/1",
        "implementation": VERSION,
        "status": "started",
        "parent_python": platform.python_version(),
        "started_utc": datetime.now(UTC).isoformat(),
        "files": {},
        "commands": [],
    }
    dump(output / "manifest.json", manifest)
    try:
        manifest["git_head"] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
        manifest["git_dirty"] = bool(
            subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT)
        )
        shutil.copyfile(HERE / "protocol.json", output / "protocol.json")
        p = read(output / "protocol.json")
        validate(p)
        shutil.copyfile(
            ROOT / "experiments/m4/paired_observation/protocol.json", output / "boundary.json"
        )
        for name in SOURCES:
            shutil.copyfile(HERE / name, output / f"source-{name}")
        for path in REUSED:
            shutil.copyfile(ROOT / path, output / ("source-" + path.replace("/", "__")))
        for branch, spec in p["runtime"].items():
            for name in ("uv.lock", "pyproject.toml"):
                shutil.copyfile(ROOT / spec["project"] / name, output / f"{branch}-{name}")

        def call(branch, args, log):
            cmd = [
                "uv",
                "run",
                "--locked",
                "--project",
                str(ROOT / p["runtime"][branch]["project"]),
                "python",
                *args,
            ]
            manifest["commands"].append(cmd)
            dump(output / "manifest.json", manifest)
            command(cmd, output, log)

        call(
            "cpeptide",
            [
                str(ROOT / "experiments/m4/beta_cell/runtime/run.py"),
                "--output",
                str(output / "secretion"),
            ],
            "secretion.log",
        )
        call("cpeptide", ["-m", "experiments.m4.chain.source", str(output)], "sampling.log")
        for branch in p["runtime"]:
            call(
                branch,
                ["-m", "experiments.m4.chain.worker", str(output), "--branch", branch],
                f"{branch}.log",
            )
        manifest.update(status="calculated", files=file_hashes(output))
        dump(output / "manifest.json", manifest)
        report = reconstruct(output, allow_pending=True)
        dump(output / "report.json", report)
        if not report["passed"]:
            raise RuntimeError("BC-007 criteria failed; inspect the preserved report")
        manifest["files"] = file_hashes(output)
        call(
            "cpeptide",
            [
                "-m",
                "experiments.m4.chain.plot",
                str(output),
                "--output",
                str(output / "figure.svg"),
                "--allow-pending",
            ],
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
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = execute(args.output)
    print(f"BC-007 completed: passed={report['passed']}; prescribed glucose, no glucose feedback")


if __name__ == "__main__":
    main()
