"""Native repeatability, baseline equivalence and artifact rejection for robustness."""

import argparse
import copy
import json
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import patch

from experiments.m0.simglucose.recording import write_json
from experiments.m1.artifacts import digest, strict_json

from .analysis import read_run
from .common import ROOT, configurations
from .conditions import VARIANTS
from .robustness import read_plan, reconstruct
from .run import execute


def verify(study, output):
    study, output = Path(study).resolve(), Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    original = reconstruct(study)
    if original["status"] != "completed":
        raise ValueError("Verify a completed, fully accounted robustness matrix")
    summary = {"status": "started", "checks": []}
    write_json(output / "verification.json", summary)
    for i, cfg in enumerate(configurations()):
        execute(cfg, output / f"reference-{i}")
        ref = read_run(output / f"reference-{i}")
        baseline = read_run(study / f"{i:02}-baseline")
        if ref["rows"] != baseline["rows"] or ref["status"] != baseline["status"]:
            raise ValueError("Robust baseline changed native numerical workflow")
        summary["checks"].append({"baseline": i, "exact_reference": True})
        write_json(output / "verification.json", summary)
    repeats = [f"{i:02}-{v}" for i in (0, 8) for v in VARIANTS] + [
        "09-gap-60",
        "09-parameter-1-high",
    ]
    for name in repeats:
        saved = read_run(study / name)
        execute(saved["config"], output / name)
        repeated = read_run(output / name)
        if (
            saved["rows"] != repeated["rows"]
            or saved["status"] != repeated["status"]
            or saved["inputs_sha256"]["sensor-audit.jsonl"]
            != repeated["inputs_sha256"]["sensor-audit.jsonl"]
        ):
            raise ValueError("New-process robustness repeat differs")
        summary["checks"].append({"repeat": name, "exact_trace_and_sensor_audit": True})
        write_json(output / "verification.json", summary)

    def invalid_reset_clock(rows):
        first = strict_json(rows[0])
        first["time_min"] = False
        rows[0] = (json.dumps(first) + "\n").encode()

    # Keep the bad artefact and resealed inventory: test semantic detection, not hash detection.
    for label, change in (
        ("masked-sensor-missing", lambda rows: rows.pop(2161)),
        ("invalid-reset-clock", invalid_reset_clock),
        ("parameter-extra-change", None),
    ):
        target = output / label
        shutil.copytree(study / "00-gap-60", target)
        if change:
            rows = (target / "sensor-audit.jsonl").read_bytes().splitlines(keepends=True)
            change(rows)
            (target / "sensor-audit.jsonl").write_bytes(b"".join(rows))
            modified = "sensor-audit.jsonl"
            reason = "sensor"
        else:
            runtime = strict_json((target / "runtime.json").read_bytes())
            runtime["settings"]["parameters"]["kd"] *= 1.1
            write_json(target / "runtime.json", runtime)
            modified = "runtime.json"
            reason = "parameters"
        manifest = strict_json((target / "manifest.json").read_bytes())
        manifest["files_sha256"][modified] = digest(target / modified)
        write_json(target / "manifest.json", manifest)
        try:
            read_run(target)
        except ValueError as error:
            if reason not in str(error):
                raise
        else:
            raise ValueError("Semantically changed robustness artifact accepted")
        summary["checks"].append({"rejected": label})
    partial = output / "partial-sensor-audit"
    shutil.copytree(study / "00-gap-60", partial)
    fragment = b'{"time_min":'
    with (partial / "sensor-audit.jsonl").open("ab") as stream:
        stream.write(fragment)
    manifest = strict_json((partial / "manifest.json").read_bytes())
    manifest.update(status="interrupted", error="Injected unfinished sensor write", returncode=-15)
    manifest["files_sha256"]["sensor-audit.jsonl"] = digest(partial / "sensor-audit.jsonl")
    write_json(partial / "manifest.json", manifest)
    saved = read_run(partial)
    assert saved["unfinished_sensor_bytes"] == len(fragment)
    assert saved["inputs_sha256"]["sensor-audit.jsonl"] == digest(partial / "sensor-audit.jsonl")
    manifest.update(status="completed", returncode=0)
    write_json(partial / "manifest.json", manifest)
    try:
        read_run(partial)
    except ValueError as error:
        if "unfinished" not in str(error):
            raise
    else:
        raise ValueError("Unfinished successful sensor audit accepted")
    summary["partial_sensor_audit_accounted"] = True
    plan, _ = read_plan(study / "frozen")
    bad_plan = output / "missing-plan-provenance"
    shutil.copytree(study / "frozen", bad_plan)
    invalid = copy.deepcopy(plan)
    del invalid["identity"]["source_sha256"]
    write_json(bad_plan / "plan.json", invalid)
    try:
        read_plan(bad_plan)
    except ValueError as error:
        if "frozen sources" not in str(error):
            raise
    else:
        raise ValueError("Missing frozen source provenance accepted")
    cancelled = output / "cancelled"
    command = [
        sys.executable,
        "-m",
        "experiments.verification.robustness",
        "run",
        "--plan",
        str(study / "frozen"),
        "--output",
        str(cancelled),
    ]
    with (output / "cancellation.log").open("wb") as stream:
        child = subprocess.Popen(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 30
            trace = cancelled / "00-baseline" / "trace.jsonl"
            while not trace.exists() or trace.stat().st_size == 0:
                if child.poll() is not None or time.monotonic() > deadline:
                    raise ValueError("Cancellation readiness failed")
                time.sleep(0.01)
            child.send_signal(signal.SIGTERM)
            child.wait(timeout=30)
            assert child.returncode != 0
        finally:
            if child.poll() is None:
                child.kill()
                child.wait()
    cancelled_report = reconstruct(cancelled)
    assert cancelled_report["status"] == "failed" and cancelled_report["planned"] == 170
    assert cancelled_report["status_counts"].get("not_attempted") == 169
    assert cancelled_report["status_counts"].get("interrupted") == 1
    timeout = output / "timeout"
    execute(plan["cases"][0]["config"], timeout, timeout=0.001)
    assert read_run(timeout)["status"] == "interrupted"
    summary["robustness_cancellation_and_timeout"] = True
    synthetic = output / "unattempted"
    synthetic.mkdir()
    shutil.copytree(study / "frozen", synthetic / "frozen")
    unfinished = copy.deepcopy(strict_json((study / "study.json").read_bytes()))
    unfinished["status"] = "started"
    write_json(synthetic / "study.json", unfinished)
    assert reconstruct(synthetic)["status_counts"] == {"not_attempted": 170}
    unfinished["status"] = "completed"
    write_json(synthetic / "study.json", unfinished)
    try:
        reconstruct(synthetic)
    except ValueError as error:
        if "False robustness" not in str(error):
            raise
    else:
        raise ValueError("False study completion accepted")
    subprocess.run(
        [
            sys.executable,
            "-S",
            "-m",
            "experiments.verification.robustness",
            "report",
            "--study",
            str(study),
            "--output",
            str(output / "reconstructed.json"),
        ],
        cwd=ROOT,
        check=True,
    )
    if (output / "reconstructed.json").read_bytes() != (study / "report.json").read_bytes():
        raise ValueError("Simulator-free reconstruction differs")
    iterate = Path.iterdir
    with patch.object(Path, "iterdir", lambda p: iter(reversed(list(iterate(p))))):
        reordered = reconstruct(study)
    if json.dumps(original) != json.dumps(reordered):
        raise ValueError("Directory enumeration changed report serialization")
    summary.update(
        directory_order_independent=True,
        status="completed",
        unattempted_cases_visible=True,
        false_completion_rejected=True,
        simulator_free_byte_exact=True,
    )
    write_json(output / "verification.json", summary)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    verify(args.study, args.output)
