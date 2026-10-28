"""Bounded two-track study scheduling and an explicit pre-evaluation freeze."""

import hashlib
import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from experiments.m0.simglucose.recording import interruption, write_json
from experiments.m1.artifacts import digest, strict_json
from experiments.m1.validation import REVISION

from .run import ROOT, source_hashes


def cases(phase):
    if phase not in ("development", "evaluation"):
        raise ValueError("Unknown study phase")
    result = []
    profiles = range(1, 3) if phase == "development" else range(3, 11)
    seeds = (101, 102) if phase == "development" else range(1, 11)
    for engine, profiles_, seeds_, controllers in (
        ("simglucose", [f"adult#{p:03}" for p in profiles], seeds, ("basal_bolus", "pid")),
        ("lt1_cambridge", ["reference"], [101], ("lt1_pid", "lt1_mpc")),
    ):
        for p in profiles_:
            for seed in seeds_:
                for controller in controllers:
                    for condition in "ABCD":
                        cfg = {
                            "engine": engine,
                            "profile": p,
                            "seed": seed,
                            "controller": controller,
                            "condition": condition,
                        }
                        result.append(
                            {
                                "id": f"{engine}-{p}-{seed}-{controller}-{condition}",
                                "config": cfg,
                                "evidence_track": phase
                                if engine == "simglucose"
                                else "structural_development",
                            }
                        )
    return result


def locks():
    return {
        p: digest(ROOT / p)
        for p in (
            "uv.lock",
            "experiments/m0/simglucose/uv.lock",
            "experiments/m0/lt1/package-lock.json",
        )
    }


def validate_plan_data(plan):
    if not isinstance(plan, dict) or plan.get("schema") != "opent1d.m2-freeze/1":
        raise ValueError("Missing frozen M2 plan")
    if plan.get("cases") != cases("evaluation"):
        raise ValueError("Frozen evaluation schedule differs from OT-014")
    if not isinstance(plan.get("revision"), str) or not REVISION.fullmatch(plan["revision"]):
        raise ValueError("Missing frozen implementation revision")
    if plan.get("locks_sha256") != locks():
        raise ValueError("Locked dependencies changed after freeze")
    if plan.get("source_sha256") != source_hashes():
        raise ValueError("Sources changed after freeze; do not reuse evaluation silently")
    if plan.get("protocol_sha256") != digest(ROOT / "docs/research/m2-protocol.md"):
        raise ValueError("Protocol changed after freeze")
    if (
        plan.get("development_verified") is not True
        or plan.get("evaluation_previously_inspected") is not False
    ):
        raise ValueError("This gate requires verified development and an untouched evaluation")
    for key in ("development_report_sha256", "native_verification_sha256"):
        value = plan.get(key)
        if (
            not isinstance(value, str)
            or len(value) != 64
            or any(c not in "0123456789abcdef" for c in value)
        ):
            raise ValueError("Missing development verification identity")
    return plan


def validate_plan(path, *, execution=False):
    plan = validate_plan_data(strict_json(Path(path).read_bytes()))
    if execution:
        revision = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
        if revision != plan["revision"] or subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=ROOT
        ):
            raise ValueError("Evaluation requires the exact clean frozen checkout")
    return plan


def freeze(development, native_verification, output):
    from .analysis import read_run as cambridge_run
    from .report import reconstruct, verify_development

    if output.exists():
        raise FileExistsError(output)
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT):
        raise ValueError("Commit and verify the implementation before freezing evaluation")
    report = reconstruct(development)
    verification = verify_development(development)
    native = strict_json((native_verification / "verification.json").read_bytes())
    if (
        native.get("status") != "completed"
        or not native.get("exact_process_replay")
        or not native.get("simulator_free_reconstruction")
    ):
        raise ValueError("Native process verification is incomplete")
    first = cambridge_run(native_verification / "first")
    if first["manifest"]["status"] != "completed":
        raise ValueError("Missing native verification run")
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if (
        first["manifest"]["revision"] != revision
        or first["manifest"]["worktree_dirty"]
        or first["manifest"]["source_sha256"] != source_hashes()
    ):
        raise ValueError("Native verification must use this exact clean revision and sources")
    if any(c["revision"] != revision or c["worktree_dirty"] for c in report["cases"]):
        raise ValueError("Development must be rerun from this exact clean revision")
    plan = {
        "schema": "opent1d.m2-freeze/1",
        "revision": revision,
        "created_utc": datetime.now(UTC).isoformat(),
        "source_sha256": source_hashes(),
        "locks_sha256": locks(),
        "protocol_sha256": digest(ROOT / "docs/research/m2-protocol.md"),
        "development_verified": True,
        "development_checks": verification,
        "development_report_sha256": hashlib.sha256(
            json.dumps(report, sort_keys=True).encode()
        ).hexdigest(),
        "native_verification_sha256": digest(native_verification / "verification.json"),
        "evaluation_previously_inspected": False,
        "cases": cases("evaluation"),
    }
    validate_plan_data(plan)
    write_json(output, plan)
    return plan


def run(output, phase="development", plan_path=None, workers=4):
    from .report import write_report

    if type(workers) is not int or not 1 <= workers <= 8:
        raise ValueError("Use 1–8 independent run processes")
    plan = validate_plan(plan_path, execution=True) if phase == "evaluation" else None
    scheduled = cases(phase)
    output.mkdir(parents=True, exist_ok=False)
    (output / "inputs").mkdir()
    (output / "logs").mkdir()
    if plan:
        write_json(output / "evaluation-plan.json", plan)
    study = {
        "schema": "opent1d.m2-study/1",
        "phase": phase,
        "status": "started",
        "cases": scheduled,
    }
    write_json(output / "study.json", study)
    for case in scheduled:
        write_json(output / "inputs" / (case["id"] + ".json"), case["config"])
    pending = iter(scheduled)
    active = []
    errors = False
    failures = False
    exhausted = False
    try:
        with interruption(max(3600, len(scheduled) * 300)):
            while active or not exhausted:
                while len(active) < workers and not exhausted:
                    case = next(pending, None)
                    if case is None:
                        exhausted = True
                        break
                    command = [
                        sys.executable,
                        "-m",
                        "experiments.m2",
                        "case",
                        "--config",
                        str(output / "inputs" / (case["id"] + ".json")),
                        "--output",
                        str(output / case["id"]),
                    ]
                    if plan:
                        command += ["--plan", str(output / "evaluation-plan.json")]
                    log = (output / "logs" / (case["id"] + ".log")).open("wb")
                    try:
                        child = subprocess.Popen(
                            command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT
                        )
                    except BaseException:
                        log.close()
                        raise
                    active.append((child, log, case))
                for child, log, case in active[:]:
                    if child.poll() is None:
                        continue
                    log.close()
                    active.remove((child, log, case))
                    manifest = output / case["id"] / "manifest.json"
                    status = (
                        strict_json(manifest.read_bytes())["status"]
                        if manifest.exists()
                        else "missing"
                    )
                    # The case CLI exits 0 for completion and 1 for a native stop.
                    # A saved terminal status cannot excuse a later process crash.
                    expected = {"completed": 0, "terminated": 1}.get(status)
                    if (expected is not None and child.returncode != expected) or (
                        expected is None and child.returncode == 0
                    ):
                        raise RuntimeError(
                            f"Case {case['id']}: process exit {child.returncode} "
                            f"contradicts recorded status {status!r}; inspect retained logs"
                        )
                    failures |= status != "completed"
                    errors |= status not in ("completed", "terminated")
                    print(f"{case['id']}: {status}", flush=True)
                if active:
                    time.sleep(0.05)
    except BaseException as error:
        study["error"] = f"{type(error).__name__}: {error}"
        for child, log, _case in active:
            child.terminate()
        for child, log, _case in active:
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
            log.close()
        write_json(output / "study.json", study)
        raise
    study["status"] = "finished_with_failures" if failures else "completed"
    write_json(output / "study.json", study)
    write_report(output, output / "report")
    if errors:
        raise RuntimeError("Execution failures retained; inspect every planned case in the report")
