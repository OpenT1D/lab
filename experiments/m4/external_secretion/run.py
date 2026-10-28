"""Archive one trusted secretion model and compare it on the frozen BC-007 task."""

import argparse
import os
import platform
import shutil
import signal
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from experiments.m4.paired_kinetics.common import dump, file_hashes

from .common import (
    HERE,
    REUSED,
    ROOT,
    SOURCES,
    VERSION,
    declaration,
    read,
    reference,
    samples,
    sha256,
)
from .report import reconstruct


def command(args, output, log_name):
    with (output / log_name).open("x") as log:
        subprocess.run(args, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)


def model_command(args, output, timeout):
    with (output / "model.log").open("x") as log:
        process = subprocess.Popen(
            args, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, start_new_session=True
        )
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            raise TimeoutError(f"Researcher model exceeded {timeout} seconds") from exc
        if code:
            raise RuntimeError(f"Researcher model failed with exit code {code}; see model.log")


def execute(output, model, declaration_path, reference_path, model_python, timeout=30):
    output = Path(output).resolve()
    model = Path(model).absolute()
    declaration_path = Path(declaration_path).absolute()
    reference_path = Path(reference_path).absolute()
    if model.suffix != ".py" or not model.is_file() or model.is_symlink():
        raise ValueError("Model must be one regular Python source file")
    if not declaration_path.is_file() or declaration_path.is_symlink():
        raise ValueError("Model declaration must be a regular JSON file")
    if not reference_path.is_dir() or reference_path.is_symlink():
        raise ValueError("Reference must be a regular BC-007 archive directory")
    if not 1 <= timeout <= 600:
        raise ValueError("Model timeout must be between 1 and 600 seconds")
    declared = declaration(read(declaration_path))
    if sha256(model) != declared["source_sha256"]:
        raise ValueError("Researcher source hash differs from declaration")
    reference(reference_path)
    if any(path.is_symlink() for path in reference_path.rglob("*")):
        raise ValueError("Reference archive cannot contain symlinks")
    if output == reference_path or reference_path in output.parents:
        raise ValueError("Output cannot be inside the reference archive")
    output.mkdir(parents=True, exist_ok=False)
    manifest = {
        "schema": "m4-external-run/1",
        "implementation": VERSION,
        "status": "started",
        "started_utc": datetime.now(UTC).isoformat(),
        "parent_python": platform.python_version(),
        "model_source_sha256": declared["source_sha256"],
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
        shutil.copy2(model, output / "model.py")
        shutil.copy2(declaration_path, output / "model.json")
        shutil.copytree(reference_path, output / "reference")
        protocol, source, _, _ = reference(output / "reference")
        for name in SOURCES:
            shutil.copy2(HERE / name, output / f"source-{name}")
        for name in REUSED:
            shutil.copy2(ROOT / name, output / ("source-" + name.replace("/", "__")))
        for branch, spec in protocol["runtime"].items():
            for name in ("uv.lock", "pyproject.toml"):
                shutil.copy2(ROOT / spec["project"] / name, output / f"{branch}-{name}")
        request = {"times_min": source["times_min"], "glucose_mmol_l": source["glucose_mmol_l"]}
        dump(output / "model-input.json", request)
        # Keep a venv's executable path: resolving its symlink may select the base interpreter.
        model_python = str(Path(model_python).absolute())
        manifest["model_python"] = model_python
        manifest["model_python_version"] = subprocess.check_output(
            [model_python, "--version"], text=True
        ).strip()
        args = [
            model_python,
            "-I",
            str(HERE / "model_host.py"),
            str(output / "model.py"),
            str(output / "model-input.json"),
            str(output / "model-samples.json"),
        ]
        manifest["commands"].append(args)
        dump(output / "manifest.json", manifest)
        model_command(args, output, timeout)
        if (
            sha256(output / "model.py") != declared["source_sha256"]
            or sha256(model) != declared["source_sha256"]
        ):
            raise ValueError("Researcher source changed during execution")
        samples(read(output / "model-samples.json"), source["times_min"], source["glucose_mmol_l"])
        for branch, spec in protocol["runtime"].items():
            args = [
                "uv",
                "run",
                "--locked",
                "--project",
                str(ROOT / spec["project"]),
                "python",
                "-m",
                "experiments.m4.external_secretion.worker",
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
            raise RuntimeError("Candidate kinetic checks failed; inspect preserved report")
        manifest.update(
            status="completed",
            finished_utc=datetime.now(UTC).isoformat(),
            files=file_hashes(output),
        )
        dump(output / "manifest.json", manifest)
        reconstruct(output)
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
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--declaration", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--model-python", default=sys.executable)
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()
    report = execute(
        args.output, args.model, args.declaration, args.reference, args.model_python, args.timeout
    )
    print(f"M4 external secretion completed: passed={report['passed']}")


if __name__ == "__main__":
    main()
