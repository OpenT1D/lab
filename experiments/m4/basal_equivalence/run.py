"""Archive two trusted causal sources and execute the frozen synthetic search."""

import argparse
import os
import platform
import shutil
import signal
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from experiments.m4.causal_secretion.common import declaration, sha256
from experiments.m4.paired_kinetics.common import dump, file_hashes, read

from .common import HERE, REUSED, ROOT, SLOTS, SOURCES, VERSION, context, verify_reference_adapter
from .report import reconstruct


def command(args, output, label, timeout):
    with (output / f"{label}.log").open("x") as log:
        process = subprocess.Popen(
            args, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, start_new_session=True
        )
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            raise TimeoutError(f"Basal-equivalence worker exceeded {timeout} seconds") from exc
        if code:
            raise RuntimeError(f"Basal-equivalence worker exited {code}; inspect {label}.log")


def execute(output, sources, reference_path, timeout=1800):
    output = Path(output).resolve()
    reference_path = Path(reference_path).absolute()
    if set(sources) != set(SLOTS):
        raise ValueError("Exactly two declared causal source slots are required")
    if not isinstance(timeout, int) or isinstance(timeout, bool) or not 1 <= timeout <= 3600:
        raise ValueError("Worker timeout must be between 1 and 3600 seconds")
    if reference_path.is_symlink() or not reference_path.is_dir():
        raise ValueError("Reference must be a regular BC-008 archive directory")
    if any(path.is_symlink() for path in reference_path.rglob("*")):
        raise ValueError("BC-008 archive cannot contain symlinks")
    if output == reference_path or reference_path in output.parents:
        raise ValueError("Output cannot be inside the reference archive")
    declared = {}
    for slot in SLOTS:
        source_path, declaration_path = (Path(path).absolute() for path in sources[slot])
        if slot == SLOTS[0]:
            verify_reference_adapter(declaration_path)
        if source_path.is_symlink() or not source_path.is_file() or source_path.suffix != ".py":
            raise ValueError(f"{slot} must be one regular Python source file")
        if declaration_path.is_symlink() or not declaration_path.is_file():
            raise ValueError(f"{slot} declaration must be a regular JSON file")
        value = declaration(read(declaration_path))
        if sha256(source_path) != value["source_sha256"]:
            raise ValueError(f"{slot} source hash differs from declaration")
        declared[slot] = (source_path, declaration_path, value)
    if declared[SLOTS[0]][2]["model_id"] == declared[SLOTS[1]][2]["model_id"]:
        raise ValueError("Comparison models must have different IDs")
    bc, _, _, _, _, _ = context(reference_path, HERE / "protocol.json")
    output.mkdir(parents=True, exist_ok=False)
    manifest = {
        "schema": "m4-basal-equivalence-run/1",
        "implementation": VERSION,
        "status": "started",
        "started_utc": datetime.now(UTC).isoformat(),
        "parent_python": platform.python_version(),
        "source_hashes": {slot: declared[slot][2]["source_sha256"] for slot in SLOTS},
        "reference_manifest_sha256": sha256(reference_path / "manifest.json"),
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
        shutil.copytree(reference_path, output / "reference")
        for slot in SLOTS:
            source_path, declaration_path, _ = declared[slot]
            shutil.copy2(source_path, output / f"{slot}.py")
            shutil.copy2(declaration_path, output / f"{slot}.json")
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
                "experiments.m4.basal_equivalence.worker",
                str(output),
                "--label",
                label,
            ]
            manifest["commands"].append(args)
            dump(output / "manifest.json", manifest)
            command(args, output, label, timeout)
            for slot in SLOTS:
                if sha256(output / f"{slot}.py") != declared[slot][2]["source_sha256"]:
                    raise ValueError(f"Archived {slot} source changed during execution")
        manifest.update(status="calculated", files=file_hashes(output))
        dump(output / "manifest.json", manifest)
        report = reconstruct(output, allow_pending=True)
        dump(output / "report.json", report)
        if not report["passed"]:
            raise RuntimeError("Basal-equivalence numerical checks failed")
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
                "schema": "m4-basal-equivalence-report/1",
                "passed": False,
                "error": manifest["error"],
                "models": {},
                "limitations": ["Incomplete execution; no SC equivalence accepted"],
            }
        dump(output / "failure-report.json", failure)
        manifest["files"] = file_hashes(output)
        dump(output / "manifest.json", manifest)
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--reference-model", type=Path, required=True)
    parser.add_argument("--reference-declaration", type=Path, required=True)
    parser.add_argument("--variant-model", type=Path, required=True)
    parser.add_argument("--variant-declaration", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=1800)
    args = parser.parse_args()
    report = execute(
        args.output,
        {
            SLOTS[0]: (args.reference_model, args.reference_declaration),
            SLOTS[1]: (args.variant_model, args.variant_declaration),
        },
        args.reference,
        args.timeout,
    )
    print(f"M4 synthetic basal equivalence: passed={report['passed']}")
    print(f"All models solved: {report['all_solved']}")


if __name__ == "__main__":
    main()
