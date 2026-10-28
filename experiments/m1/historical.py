"""Check new M1 studies against independently archived pre-review trajectories."""

import hashlib
from pathlib import Path

from experiments.m0.simglucose.runtime_context import expected_context

from .artifacts import ROOT, read_run, strict_json
from .validation import Snapshot


def record(study):
    study = Path(study)
    snapshot = Snapshot(study)
    schedule = strict_json(snapshot.read("study.json"))
    if schedule.get("schema") != "opent1d.study/1" or schedule.get("status") not in (
        "completed",
        "finished_with_failures",
    ):
        raise ValueError("Historical comparison requires a finalized study")
    result = {}
    for case in schedule["cases"]:
        identifier = case["id"]
        if (
            not isinstance(identifier, str)
            or Path(identifier).name != identifier
            or identifier in (".", "..")
            or identifier in result
        ):
            raise ValueError("Invalid historical case id")
        saved = read_run(study / identifier)
        m = saved["manifest"]
        if m["status"] not in ("completed", "terminated") or m["config"] != case["config"]:
            raise ValueError("Historical comparison requires attributable native results")
        result[identifier] = {
            "config": m["config"],
            "status": m["status"],
            "completed_rows": m["completed_rows"],
            "upstream_revision": m["upstream_revision"],
            "upstream_files_digest": m["upstream_files_digest"],
            "packages": m["packages"],
            "effective_settings": m["effective_settings"],
            "lock_sha256": saved["input_sha256"]["uv.lock"],
            "protocol_sha256": saved["input_sha256"]["protocol-settings.json"],
            "trace_sha256": saved["input_sha256"]["trace.jsonl"],
            "initial_sha256": saved["input_sha256"]["initial.json"],
        }
    snapshot.verify_unchanged()
    return result


def check_record(observed, baseline):
    expected = baseline["cases"]
    if set(observed) != set(expected):
        raise ValueError("Scheduled cases differ from the archived M1 demonstration")
    shared = baseline.get("shared", {})
    extension = None
    if "lock_sha256" in shared:
        locks = {case.get("lock_sha256") for case in observed.values()}
        if len(locks) != 1:
            raise ValueError("Historical M1 runtime locks differ across scheduled cases")
        shared, extension = expected_context("m1", baseline, locks.pop())
    for identifier, values in expected.items():
        for field, value in (shared | values).items():
            if observed[identifier].get(field) != value:
                raise ValueError(f"Historical M1 context differs: {identifier}/{field}")
    # Match one entire recorded collection, not an arbitrary mixture of per-case digests.
    outputs = {
        key: {field: value[field] for field in ("trace_sha256", "initial_sha256")}
        for key, value in observed.items()
    }
    for collection in baseline["collections"]:
        if outputs == collection["outputs_sha256"]:
            result = {
                "matched": True,
                "collection": collection["name"],
                "origin": collection["origin"],
                "cases": len(observed),
                "tolerance_applied": False,
            }
            if extension is not None:
                result["runtime_extension"] = extension
            return result
    raise ValueError(
        "Historical M1 trajectories differ; preserve and investigate before changing the baseline"
    )


def check(study):
    data = (ROOT / "experiments/m1/baseline.json").read_bytes()
    baseline = strict_json(data)
    if baseline["schema"] != "opent1d.m1-baseline/1":
        raise ValueError("Unsupported M1 baseline")
    result = check_record(record(study), baseline)
    result["baseline_sha256"] = hashlib.sha256(data).hexdigest()
    return result
