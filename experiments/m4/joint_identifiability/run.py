"""Archive protocol/source, execute the locked study twice, then reconstruct."""

import argparse
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from .common import HERE, REUSED, ROOT, SOURCES, VERSION, dump, file_hashes, read, validate
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
        shutil.copyfile(HERE / "protocol.json", output / "protocol.json")
        p = read(output / "protocol.json")
        validate(p)
        manifest["git_head"] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
        manifest["git_dirty"] = bool(
            subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT)
        )
        for name in SOURCES:
            shutil.copyfile(HERE / name, output / ("source-" + name))
        for name in REUSED:
            shutil.copyfile(ROOT / name, output / ("source-" + name.replace("/", "__")))
        for name in ("uv.lock", "pyproject.toml"):
            shutil.copyfile(ROOT / p["runtime"]["project"] / name, output / name)

        def call(module, args, logfile):
            command = [
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
            manifest["commands"].append(command)
            dump(output / "manifest.json", manifest)
            with (output / logfile).open("x") as stream:
                subprocess.run(
                    command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, check=True
                )

        call(
            "experiments.m4.joint_identifiability.worker", [str(output), str(output)], "worker.log"
        )
        call(
            "experiments.m4.joint_identifiability.worker",
            [str(output), str(output / "repeat")],
            "repeat.log",
        )
        manifest.update(status="calculated", files=file_hashes(output))
        dump(output / "manifest.json", manifest)
        report = reconstruct(output, allow_pending=True)
        dump(output / "report.json", report)
        if not report["passed"]:
            raise RuntimeError("BC-011 acceptance failed; complete evidence retained")
        manifest["files"] = file_hashes(output)
        dump(output / "manifest.json", manifest)
        call(
            "experiments.m4.joint_identifiability.plot",
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
    result = execute(args.output)
    print(f"BC-011 passed={result['passed']}; conditional synthetic recovery only")
