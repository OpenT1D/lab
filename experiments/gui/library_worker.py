"""Owned stdlib indexing and fixed maintained-reader verification; no archived code."""

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path

from experiments.catalogue import core
from experiments.catalogue.storage import load_sealed

from . import library_m5, library_observations, library_sampling
from .library_paths import resolve_archive
from .service import MAX_REPORT, bounded_bytes, decode_json, encode, inventory, read_json

SCHEMA = "opent1d.gui-library-worker/1"
REQUEST = "opent1d.gui-library-request/1"
ARTIFACTS = ("report.json", "report.md", "figure.svg")
ARTIFACTS_BY_TASK = {
    "m4-study-secure": ARTIFACTS,
    "m3-forecast": ("report.json", "report.md"),
    "m3-compare": ("report.json", "report.md"),
    "m5-prognosis": ("report.json", "report.md"),
    "mmtt-sensitivity": library_observations.ARTIFACTS,
    "mmtt-sampling": library_sampling.ARTIFACTS,
}
REPORT_SCHEMAS = {
    "m4-study-secure": "m4-secure-study-report/1",
    "m3-forecast": "opent1d.m3.researcher/1",
    "m3-compare": "opent1d.m3.comparison/1",
    "m5-prognosis": library_m5.SCHEMA,
    "mmtt-sensitivity": library_observations.SCHEMA,
    "mmtt-sampling": library_sampling.SCHEMA,
}


def validate_report(task, report):
    """Check presentation shape; scientific validation stays with the native reader."""
    if not isinstance(report, dict) or report.get("schema") != REPORT_SCHEMAS[task]:
        raise ValueError("Unsupported native report for registered task")
    if task == "m4-study-secure":
        return report
    if task == "m5-prognosis":
        return library_m5.validate_report(report)
    if task == "mmtt-sampling":
        return library_sampling.validate_report(report)
    if task == "mmtt-sensitivity":
        return library_observations.validate_report(report)
    coverage = report.get("evaluation" if task == "m3-forecast" else "common")
    if (
        report.get("kind") != "synthetic"
        or report.get("human_evaluation") is not False
        or not isinstance(coverage, dict)
        or type(coverage.get("complete_cohort")) is not bool
        or type(coverage.get("planned_people")) is not int
        or coverage["planned_people"] < 1
        or type(coverage.get("contributing_people")) is not int
        or not 0 <= coverage["contributing_people"] <= coverage["planned_people"]
        or not isinstance(coverage.get("people"), dict)
        or len(coverage["people"]) != coverage["planned_people"]
        or any(not isinstance(item, dict) for item in coverage["people"].values())
    ):
        raise ValueError("Malformed synthetic M3 report coverage")
    if task == "m3-forecast":
        if not isinstance(report.get("predictor"), dict):
            raise ValueError("Malformed synthetic M3 predictor")
    else:
        order = report.get("candidate_order")
        candidates = report.get("candidates")
        if (
            not isinstance(order, list)
            or len(order) < 2
            or any(not isinstance(name, str) or not name for name in order)
            or len(set(order)) != len(order)
            or not isinstance(candidates, dict)
            or set(candidates) != set(order)
            or any(not isinstance(item, dict) for item in candidates.values())
        ):
            raise ValueError("Malformed synthetic M3 candidate roster")
    return report


def file_digest(path, maximum=67108864):
    return hashlib.sha256(bounded_bytes(path, maximum)).hexdigest()


def verify_missing_m3_report(item, output):
    """Use the fixed sealed reader when passive metadata lacks its original report."""
    source = Path(item["archive"])
    result = {
        "status": "failed",
        "complete": False,
        "reader_exit_code": None,
        "error": None,
        "source_archive_sha256": item["archive_sha256"],
        "metadata_scope": "unavailable_original_report; fixed_native_reader",
    }
    try:
        if item["task"] not in {"m3-forecast", "m3-compare"} or (source / "report.json").exists():
            raise ValueError("Missing-report fallback requires an existing fixed M3 task")
        if core.inventory(source) != item["inventory"]:
            raise ValueError("Source archive changed since indexing")
        args = [
            sys.executable,
            "-B",
            "-E",
            "-s",
            "-S",
            *core.reconstruction_args(item["task"], source, output, allow_failed=True),
        ]
        operation = core.supervise(
            args, output.parent / (output.name + ".log"), core.ROOT, core.environment(), 120
        )
        result["reader_exit_code"] = operation["exit_code"]
        if operation["status"] == "interrupted":
            result["interruption_signal"] = operation["signal"]
        if core.inventory(source) != item["inventory"]:
            raise ValueError("Native reader changed source archive")
        if operation["exit_code"] != 0:
            raise ValueError("Authoritative sealed M3 reconstruction failed")
        report = validate_report(
            item["task"], decode_json(bounded_bytes(output / "report.json", MAX_REPORT))
        )
        coverage = report["evaluation" if item["task"] == "m3-forecast" else "common"]
        result.update(status="verified_reconstruction", complete=coverage["complete_cohort"])
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        result["error"] = type(error).__name__ + ": " + str(error)[:300]
    return result


def execute(request, output):
    if (
        not isinstance(request, dict)
        or set(request) != {"schema", "operation", "entry", "expected_inventory"}
        or request["schema"] != REQUEST
        or request["operation"] not in {"library_index", "library_verify"}
    ):
        raise ValueError("Unsupported library worker request")
    entry = request["entry"]
    if entry["task"] not in core.TASKS:
        raise ValueError("Unsupported catalogue task")
    source, _ = resolve_archive(entry["root_identity"], entry["path"], entry["archive_identity"])
    if source == output or source in output.parents or output in source.parents:
        raise ValueError("Derived output overlaps the source archive")
    result = {
        "schema": SCHEMA,
        "request_sha256": hashlib.sha256(encode(request)).hexdigest(),
        "operation": request["operation"],
        "entry_id": entry["id"],
        "status": "failed",
        "error": None,
        "source_inventory_sha256": None,
        "catalogue_sha256": None,
        "verification": "not_requested",
        "report_completeness": "unavailable",
        "artifacts_sha256": {},
    }
    try:
        before = inventory(source, files=True)
        source_sha = hashlib.sha256(encode(before)).hexdigest()
        result["source_inventory_sha256"] = source_sha
        if request["operation"] == "library_verify":
            if entry["task"] not in ARTIFACTS_BY_TASK:
                raise ValueError("Historical tasks require a separate compatible trusted reader")
            if source_sha != request["expected_inventory"]:
                result["verification"] = "changed_since_verification"
                raise ValueError("Source archive changed since indexing")
        (output / "source-inventory.json").write_bytes(encode(before))
        config = output / "catalogue-request.json"
        config.write_bytes(
            encode(
                {
                    "schema": core.REQUEST,
                    "entries": [
                        {
                            "id": entry["id"],
                            "task": entry["task"],
                            "archive": str(source),
                            "tags": entry["tags"],
                        }
                    ],
                }
            )
        )
        data = core.index(config, output / "catalogue")
        load_sealed(output / "catalogue")
        item = data["entries"][0]
        result["catalogue_sha256"] = file_digest(output / "catalogue" / "catalogue.json")
        if request["operation"] == "library_verify":
            verified = (
                verify_missing_m3_report(item, output / "reconstructed")
                if entry["task"] in {"m3-forecast", "m3-compare"}
                and not (source / "report.json").exists()
                else core.verify_one(item, output / "reconstructed", allow_failed=True)
            )
            result["native_result"] = verified
            if verified["status"] != "verified_reconstruction":
                result["verification"] = "verification_failed"
                raise ValueError(verified["error"] or "Authoritative native reconstruction failed")
            if entry["task"] == "m5-prognosis":
                if inventory(source, files=True) != before:
                    result["verification"] = "changed_since_verification"
                    raise ValueError("Source archive changed during native M5 verification")
                target = output / "reconstructed"
                target.mkdir(exist_ok=False)
                for name in ARTIFACTS_BY_TASK[entry["task"]]:
                    raw = bounded_bytes(source / name, library_m5.MAX_NATIVE_FILE)
                    if hashlib.sha256(raw).hexdigest() != before.get(name):
                        result["verification"] = "changed_since_verification"
                        raise ValueError("Source M5 report changed during copy")
                    (target / name).write_bytes(raw)
                raw = bounded_bytes(source / "model.json", library_m5.MAX_NATIVE_FILE)
                if hashlib.sha256(raw).hexdigest() != before.get("model.json"):
                    result["verification"] = "changed_since_verification"
                    raise ValueError("Source M5 declaration changed during copy")
                declared = decode_json(raw)
                models = item["metadata"]["models"]
                if len(models) != 1 or declared != models[0]["declaration"]:
                    raise ValueError("Verified M5 catalogue declaration differs")
                report = validate_report(
                    entry["task"],
                    decode_json(bounded_bytes(target / "report.json", library_m5.MAX_NATIVE_FILE)),
                )
                result["model_declaration"] = library_m5.validate_declaration(declared, report)
                result["model_declaration_sha256"] = library_m5.declaration_digest(declared)
            result["artifacts_sha256"] = {
                name: file_digest(output / "reconstructed" / name)
                for name in ARTIFACTS_BY_TASK[entry["task"]]
            }
            if entry["task"] == "m5-prognosis" and any(
                result["artifacts_sha256"][name] != before.get(name)
                for name in ARTIFACTS_BY_TASK[entry["task"]]
            ):
                result["verification"] = "verification_failed"
                raise ValueError("Copied native M5 snapshot artifact changed")
            report = validate_report(
                entry["task"],
                decode_json(bounded_bytes(output / "reconstructed/report.json", MAX_REPORT)),
            )
            if type(verified.get("complete")) is not bool:
                raise ValueError("Native reader did not report boolean completeness")
            if entry["task"].startswith("m3-"):
                coverage = report["evaluation" if entry["task"] == "m3-forecast" else "common"]
                if coverage["complete_cohort"] != verified["complete"]:
                    raise ValueError("Native report and reader completeness differ")
            if (
                entry["task"] == "m5-prognosis"
                and library_m5.complete(report) != verified["complete"]
            ):
                raise ValueError("Native M5 report and reader completeness differ")
            if entry["task"] in {"mmtt-sensitivity", "mmtt-sampling"} and (
                report["coverage"]["complete_cohort"] != verified["complete"]
            ):
                raise ValueError("Observation report and reader completeness differ")
            result["verification"] = "native_reader_verified"
            result["report_completeness"] = (
                "complete"
                if verified["complete"]
                else "failed"
                if entry["task"] == "m4-study-secure"
                else "incomplete"
            )
        resolve_archive(entry["root_identity"], entry["path"], entry["archive_identity"])
        if inventory(source, files=True) != before:
            result["verification"] = "changed_since_verification"
            raise ValueError("Source archive changed during the owned operation")
        result["status"] = "completed"
    except (OSError, ValueError, KeyError, TypeError, RecursionError) as error:
        result["error"] = type(error).__name__ + ": " + str(error)[:300]
        if result["verification"] == "native_reader_verified":
            result["verification"] = "verification_failed"
    (output / "worker-result.json").write_bytes(encode(result))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve(strict=True)
    if args.request.parent.resolve(strict=True) != output:
        raise ValueError("Library request must be frozen in its owned job folder")
    result = execute(read_json(args.request), output)
    print(encode(result).decode(), end="")
    return 0 if result["status"] == "completed" else 1


if __name__ == "__main__":
    sys.exit(main())
