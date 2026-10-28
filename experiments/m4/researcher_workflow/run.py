"""One bounded execution route with isolated numerical runtimes and failure evidence."""

import argparse
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from experiments.m4.causal_secretion.run import execute as execute_causal
from experiments.m4.paired_kinetics.common import file_hashes

from .common import (
    HERE,
    REUSED,
    ROOT,
    SOURCES,
    VERSION,
    dump,
    dump_reports,
    intake,
    observer_settings,
    read,
    sha256,
    validate_protocol,
    verify_reference_sources,
)
from .process import causal_commands, command
from .report import reconstruct


def execute(output, config_path, reference_path=None):
    config, paths, declared = intake(config_path)
    p = validate_protocol(read(HERE / "protocol.json"))
    output = Path(output).absolute()
    if output.is_symlink():
        raise ValueError("Output cannot be a symlink")
    output = output.resolve()
    if any(output == path or output in path.parents for path in paths.values()):
        raise ValueError("Output cannot contain supplied input files")
    if reference_path is not None:
        from experiments.m4.causal_secretion.common import reference

        reference_path = Path(reference_path).absolute()
        if reference_path.is_symlink() or any(p.is_symlink() for p in reference_path.rglob("*")):
            raise ValueError("Reference cannot contain symlinks")
        reference_path = reference_path.resolve()
        if (
            output == reference_path
            or reference_path in output.parents
            or output in reference_path.parents
        ):
            raise ValueError("Output and reference must be separate directories")
        reference(reference_path)
        verify_reference_sources(reference_path)
    output.mkdir(parents=True, exist_ok=False)
    manifest = {
        "schema": VERSION,
        "protocol": p["id"],
        "status": "started",
        "stage": "prepare",
        "started_utc": datetime.now(UTC).isoformat(),
        "commands": [],
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
        dump(output / "config.json", config)
        shutil.copy2(HERE / "protocol.json", output / "protocol.json")
        shutil.copy2(paths["model"], output / "model.py")
        shutil.copy2(paths["declaration"], output / "model.json")
        if sha256(output / "model.py") != declared["source_sha256"]:
            raise ValueError("Supplied source changed during intake")
        shutil.copy2(
            ROOT / "experiments/m4/feedback_observation/protocol.json",
            output / "observation-protocol.json",
        )
        settings = observer_settings(output)
        for name in SOURCES:
            shutil.copy2(HERE / name, output / f"source-{name}")
        for name in REUSED:
            shutil.copy2(ROOT / name, output / ("source-" + name.replace("/", "__")))
        for name in ("uv.lock", "pyproject.toml"):
            shutil.copy2(
                ROOT / settings["runtime"]["project"] / name, output / ("observer-" + name)
            )

        def seal_stage(stage):
            manifest.update(stage=stage, files=file_hashes(output))
            dump(output / "manifest.json", manifest)

        def invoke(args, logfile):
            manifest["commands"].append(args)
            dump(output / "manifest.json", manifest)
            command(args, output, logfile, config["timeout_seconds"])

        seal_stage("reference")
        if reference_path is None:
            invoke(
                [
                    sys.executable,
                    "-m",
                    "experiments.m4.feedback.run",
                    "--output",
                    str(output / "reference"),
                ],
                "reference.log",
            )
        else:
            shutil.copytree(reference_path, output / "reference")
            (output / "reference.log").write_text(
                "Reused verified source-matched BC-008 reference.\n"
            )
        manifest["reference_manifest_sha256"] = sha256(output / "reference/manifest.json")
        seal_stage("causal")
        with causal_commands():
            execute_causal(
                output / "causal",
                output / "model.py",
                output / "model.json",
                output / "reference",
                config["timeout_seconds"],
            )
        manifest["causal_manifest_sha256"] = sha256(output / "causal/manifest.json")
        parent_before = file_hashes(output / "causal")
        for label in ("primary", "repeat"):
            seal_stage("observation_" + label)
            invoke(
                [
                    "uv",
                    "run",
                    "--locked",
                    "--project",
                    str(ROOT / settings["runtime"]["project"]),
                    "python",
                    "-m",
                    "experiments.m4.researcher_workflow.worker",
                    str(output),
                    "--label",
                    label,
                ],
                "observation-" + label + ".log",
            )
            if (
                file_hashes(output / "causal") != parent_before
                or sha256(output / "causal/manifest.json") != manifest["causal_manifest_sha256"]
            ):
                raise ValueError("Observation changed parent artifacts")
        manifest.update(status="calculated", stage="report", files=file_hashes(output))
        dump(output / "manifest.json", manifest)
        report = reconstruct(output, allow_pending=True)
        dump_reports(output, report)
        if not report["passed"]:
            manifest["verification_checks"] = report["observation_checks"]
            raise RuntimeError("Complete workflow numerical checks failed; inspect retained report")
        manifest.update(
            status="completed", stage="completed", finished_utc=datetime.now(UTC).isoformat()
        )
        manifest["files"] = file_hashes(output)
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
        failure = reconstruct(output, allow_failed=True)
        dump_reports(output, failure)
        manifest["files"] = file_hashes(output)
        dump(output / "manifest.json", manifest)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reference", type=Path)
    args = parser.parse_args()
    report = execute(args.output, args.config, args.reference)
    print(f"M4 researcher workflow: passed={report['passed']}; report={args.output / 'report.md'}")


if __name__ == "__main__":
    main()
