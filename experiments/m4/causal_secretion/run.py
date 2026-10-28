"""Run a trusted local causal secretion source on frozen BC-008 tasks."""

import argparse
import os
import platform
import shutil
import signal
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from experiments.m4.paired_kinetics.common import dump, file_hashes, read

from .common import (
    HERE,
    REUSED,
    ROOT,
    SOURCES,
    VERSION,
    declaration,
    protocol,
    reference,
    sha256,
)
from .report import reconstruct


def command(args, output, log_name, timeout):
    with (output / log_name).open("x") as log:
        process = subprocess.Popen(
            args, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, start_new_session=True
        )
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            raise TimeoutError(f"Causal worker exceeded {timeout} seconds") from exc
        if code:
            raise RuntimeError(f"Causal worker exited {code}; inspect {log_name}")


def execute(output, model, declaration_path, reference_path, timeout=600):
    output = Path(output).resolve()
    model = Path(model).absolute()
    declaration_path = Path(declaration_path).absolute()
    reference_path = Path(reference_path).absolute()
    if model.is_symlink() or not model.is_file() or model.suffix != ".py":
        raise ValueError("Model must be one regular Python source file")
    if declaration_path.is_symlink() or not declaration_path.is_file():
        raise ValueError("Model declaration must be a regular JSON file")
    if reference_path.is_symlink() or not reference_path.is_dir():
        raise ValueError("Reference must be a regular BC-008 archive directory")
    if not isinstance(timeout, int) or isinstance(timeout, bool) or not 1 <= timeout <= 1800:
        raise ValueError("Worker timeout must be between 1 and 1800 seconds")
    declared = declaration(read(declaration_path))
    if sha256(model) != declared["source_sha256"]:
        raise ValueError("Researcher source hash differs from declaration")
    bc, _, _, _ = reference(reference_path)
    task = protocol(read(HERE / "protocol.json"), bc)
    if any(path.is_symlink() for path in reference_path.rglob("*")):
        raise ValueError("BC-008 archive cannot contain symlinks")
    if output == reference_path or reference_path in output.parents:
        raise ValueError("Output cannot be inside the reference archive")
    output.mkdir(parents=True, exist_ok=False)
    manifest = {
        "schema": "m4-causal-run/1",
        "implementation": VERSION,
        "status": "started",
        "started_utc": datetime.now(UTC).isoformat(),
        "parent_python": platform.python_version(),
        "model_source_sha256": declared["source_sha256"],
        "reference_protocol": task["reference_id"],
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
        shutil.copy2(HERE / "protocol.json", output / "protocol.json")
        shutil.copy2(model, output / "model.py")
        shutil.copy2(declaration_path, output / "model.json")
        shutil.copytree(reference_path, output / "reference")
        reference(output / "reference")
        for name in SOURCES:
            shutil.copy2(HERE / name, output / f"source-{name}")
        for name in REUSED:
            shutil.copy2(ROOT / name, output / ("source-" + name.replace("/", "__")))
        runtime = ROOT / bc["runtime"]["project"]
        for name in ("uv.lock", "pyproject.toml"):
            shutil.copy2(runtime / name, output / name)
        for label in ("primary", "repeat"):
            args = [
                "uv",
                "run",
                "--locked",
                "--project",
                str(runtime),
                "python",
                "-m",
                "experiments.m4.causal_secretion.worker",
                str(output),
                "--label",
                label,
            ]
            manifest["commands"].append(args)
            dump(output / "manifest.json", manifest)
            command(args, output, f"{label}.log", timeout)
            if sha256(output / "model.py") != declared["source_sha256"]:
                raise ValueError("Archived researcher source changed during execution")
        manifest.update(status="calculated", files=file_hashes(output))
        dump(output / "manifest.json", manifest)
        report = reconstruct(output, allow_pending=True)
        dump(output / "report.json", report)
        if not report["passed"]:
            raise RuntimeError("Causal numerical checks failed; inspect preserved report")
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
            error={"type": type(exc).__name__, "message": str(exc)[:500]},
            files=file_hashes(output),
        )
        dump(output / "manifest.json", manifest)
        try:
            failure = reconstruct(output, allow_failed=True)
        except Exception:
            failure = {
                "schema": "m4-causal-report/1",
                "passed": False,
                "error": manifest["error"],
                "scenarios": {},
                "limitations": ["Incomplete execution; no scenario contrast accepted"],
            }
        dump(output / "failure-report.json", failure)
        manifest["files"] = file_hashes(output)
        dump(output / "manifest.json", manifest)
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--declaration", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args()
    report = execute(args.output, args.model, args.declaration, args.reference, args.timeout)
    print(f"M4 causal secretion completed: passed={report['passed']}")


if __name__ == "__main__":
    main()
