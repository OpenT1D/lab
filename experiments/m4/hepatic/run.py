"""Run a frozen hepatic comparison twice, preserving every attempt."""

import argparse
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from .common import HERE, REUSED, ROOT, SOURCES, VERSION, dump, file_hashes, read, validate
from .report import reconstruct


def inputs(directory):
    shutil.copyfile(HERE / "protocol.json", directory / "protocol.json")
    shutil.copyfile(ROOT / "experiments/m4/feedback/protocol.json", directory / "parent.json")
    check = directory / "source-check"
    check.mkdir()
    for name in ("protocol.json", "source-cases.json"):
        shutil.copyfile(ROOT / "experiments/m4/feedback" / name, check / name)


def execute(output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    manifest = {
        "schema": VERSION,
        "status": "started",
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
        inputs(output)
        p, parent = read(output / "protocol.json"), read(output / "parent.json")
        validate(p, parent)
        shutil.copyfile(HERE / "sources.json", output / "sources.json")
        for name in SOURCES:
            shutil.copyfile(HERE / name, output / ("source-" + name))
        for name in REUSED:
            shutil.copyfile(ROOT / name, output / ("source-" + name.replace("/", "__")))
        for name in ("uv.lock", "pyproject.toml"):
            shutil.copyfile(ROOT / parent["runtime"]["project"] / name, output / name)

        def call(module, args, log):
            cmd = [
                "uv",
                "run",
                "--locked",
                "--project",
                str(ROOT / parent["runtime"]["project"]),
                "python",
                "-m",
                module,
                *args,
            ]
            manifest["commands"].append(cmd)
            dump(output / "manifest.json", manifest)
            with (output / log).open("x") as stream:
                subprocess.run(cmd, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, check=True)

        call("experiments.m4.hepatic.worker", [str(output)], "worker.log")
        repeat = output / "repeat"
        repeat.mkdir()
        inputs(repeat)
        call("experiments.m4.hepatic.worker", [str(repeat)], "repeat.log")
        manifest.update(status="calculated", files=file_hashes(output))
        dump(output / "manifest.json", manifest)
        report = reconstruct(output, allow_pending=True)
        dump(output / "report.json", report)
        if not report["passed"]:
            raise RuntimeError("Hepatic comparison failed; all evidence and failures preserved")
        manifest["files"] = file_hashes(output)
        dump(output / "manifest.json", manifest)
        call(
            "experiments.m4.hepatic.plot",
            [str(output), "--output", str(output / "figure.svg"), "--allow-pending"],
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = execute(args.output)
    print(f"BC-009 completed: passed={report['passed']}; conditional structural sensitivity only")
