"""Snapshot BC-014, run its numerical campaign twice and reconstruct evidence."""

import argparse
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from .common import HERE, REUSED, ROOT, SOURCES, VERSION, dump, file_hashes, read, validate
from .plot import render
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
        protocol = read(output / "protocol.json")
        validate(protocol)
        for name, source in (
            ("parent-profile.json", "profile_likelihood"),
            ("parent-volume.json", "volume_sensitivity"),
            ("parent-joint.json", "joint_identifiability"),
        ):
            shutil.copyfile(ROOT / "experiments/m4" / source / "protocol.json", output / name)
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
            shutil.copyfile(ROOT / protocol["runtime"]["project"] / name, output / name)

        def worker(destination, logfile):
            command = [
                "uv",
                "run",
                "--locked",
                "--project",
                str(ROOT / protocol["runtime"]["project"]),
                "python",
                "-m",
                "experiments.m4.coverage.worker",
                str(output),
                str(destination),
            ]
            manifest["commands"].append(command)
            dump(output / "manifest.json", manifest)
            with (output / logfile).open("x") as stream:
                subprocess.run(
                    command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, check=True
                )

        worker(output, "worker.log")
        worker(output / "repeat", "repeat.log")
        manifest.update(status="calculated", files=file_hashes(output))
        dump(output / "manifest.json", manifest)
        report = reconstruct(output, allow_pending=True)
        dump(output / "report.json", report)
        if not report["passed"]:
            raise RuntimeError("BC-014 numerical acceptance failed; complete evidence retained")
        (output / "figure.svg").write_text(render(report))
        manifest.update(
            status="completed",
            finished_utc=datetime.now(UTC).isoformat(),
            files=file_hashes(output),
        )
        dump(output / "manifest.json", manifest)
        if reconstruct(output) != report:
            raise RuntimeError("Completed report differs from independent reconstruction")
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
    print(
        f"BC-014 passed={report['passed']}; {report['new_draws']} new synthetic draws, "
        f"{report['analyses']} paired/boundary analyses"
    )
