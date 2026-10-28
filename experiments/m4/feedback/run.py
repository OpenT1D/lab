"""Fresh BC-008 execution and full fresh-process repeat; no archive overwrites."""

import argparse
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from .common import HERE, REUSED, ROOT, SOURCES, VERSION, dump, file_hashes, read
from .contract import validate
from .report import reconstruct


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
        for name in ("protocol.json", "source-cases.json", "sources.json"):
            shutil.copyfile(HERE / name, output / name)
        p = read(output / "protocol.json")
        validate(p)
        for name in SOURCES:
            shutil.copyfile(HERE / name, output / ("source-" + name))
        for path in REUSED:
            shutil.copyfile(ROOT / path, output / ("source-" + path.replace("/", "__")))
        for name in ("uv.lock", "pyproject.toml"):
            shutil.copyfile(ROOT / p["runtime"]["project"] / name, output / name)

        def call(module, args, logfile):
            cmd = [
                "uv",
                "run",
                "--locked",
                "--project",
                str(ROOT / p["runtime"]["project"]),
                "python",
                "-m",
                module,
                *args,
            ]
            manifest["commands"].append(cmd)
            dump(output / "manifest.json", manifest)
            with (output / logfile).open("x") as log:
                subprocess.run(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)

        call("experiments.m4.feedback.worker", [str(output)], "worker.log")
        repeat = output / "repeat"
        repeat.mkdir()
        for name in ("protocol.json", "source-cases.json"):
            shutil.copyfile(output / name, repeat / name)
        call("experiments.m4.feedback.worker", [str(repeat)], "repeat.log")
        manifest.update(status="calculated", files=file_hashes(output))
        dump(output / "manifest.json", manifest)
        report = reconstruct(output, allow_pending=True)
        dump(output / "report.json", report)
        if not report["passed"]:
            raise RuntimeError(
                "BC-008 verification failed; preserved report contains every criterion"
            )
        manifest["files"] = file_hashes(output)
        dump(output / "manifest.json", manifest)
        call(
            "experiments.m4.feedback.plot",
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
    print(f"BC-008 completed: passed={report['passed']}; synthetic feedback only")
