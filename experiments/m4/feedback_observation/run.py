"""Fresh feedback reference or verified archive, then a reproducible observer."""

import argparse
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from experiments.m4.hepatic.report import reconstruct as parent_report
from experiments.m4.hepatic.run import execute as new_parent

from .common import HERE, REUSED, ROOT, SOURCES, VERSION, digest, dump, file_hashes, read, validate
from .report import reconstruct


def copy_parent(source, target):
    result = parent_report(source)
    if not result["passed"]:
        raise ValueError("Parent must pass its complete numerical protocol")
    manifest = read(source / "manifest.json")
    target.mkdir()
    # Copy only listed, hash-verified files, never unrelated files in the folder.
    for name in (*manifest["files"], "manifest.json"):
        dest = target / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / name, dest)
    if digest(source / "manifest.json") != digest(target / "manifest.json"):
        raise ValueError("Parent copy provenance mismatch")


def execute(output, source=None):
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
        if source is None:
            manifest["parent_mode"] = "fresh_BC009_execution"
            new_parent(output / "hepatic")
        else:
            source = Path(source).resolve()
            if source == output or source in output.parents:
                raise ValueError("Output must be outside the parent archive")
            manifest["parent_mode"] = "verified_existing_archive"
            copy_parent(source, output / "hepatic")
        manifest["parent_manifest_sha256"] = digest(output / "hepatic/manifest.json")

        def call(module, args, log):
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
            with (output / log).open("x") as stream:
                subprocess.run(cmd, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, check=True)

        call("experiments.m4.feedback_observation.worker", [str(output), str(output)], "worker.log")
        call(
            "experiments.m4.feedback_observation.worker",
            [str(output), str(output / "repeat")],
            "repeat.log",
        )
        manifest.update(status="calculated", files=file_hashes(output))
        dump(output / "manifest.json", manifest)
        report = reconstruct(output, allow_pending=True)
        dump(output / "report.json", report)
        if not report["passed"]:
            raise RuntimeError("BC-010 criteria failed; evidence retained")
        manifest["files"] = file_hashes(output)
        dump(output / "manifest.json", manifest)
        call(
            "experiments.m4.feedback_observation.plot",
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
    parser.add_argument(
        "--source",
        type=Path,
        help="Optional completed BC-009 archive; otherwise execute a fresh parent",
    )
    args = parser.parse_args()
    result = execute(args.output, args.source)
    print(f"BC-010 passed={result['passed']}; synthetic forward observations only")
