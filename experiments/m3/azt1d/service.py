"""Phase-bound conversion and development preparation; never fit/evaluate a model."""

import math
import os
import re
from collections import Counter
from decimal import ROUND_CEILING, Decimal
from pathlib import Path

from experiments.m3.common import SHA, Snapshot
from experiments.m3.workflow import failure

from .common import (
    MINUTE,
    PHASES,
    SCHEMA,
    digest,
    outside_repository,
    provenance,
    read,
    require,
    save,
    validate_provenance,
)


def bound_reference(ref):
    require(isinstance(ref, dict) and set(ref) == {"file", "sha256"}, "Invalid bound reference")
    require(isinstance(ref["file"], str) and ref["file"], "Missing reference path")
    require(isinstance(ref["sha256"], str) and SHA.fullmatch(ref["sha256"]), "Missing hash")
    outside_repository(ref["file"])
    value, sha = read(ref["file"])
    require(sha == ref["sha256"], "Reference bytes changed")
    return value


def seconds_to_us(value):
    require(type(value) in (float, int) and math.isfinite(value) and value >= 0, "Invalid bound")
    # Integer instants in [fractional start, fractional end) start at the ceiling of each bound.
    return int((Decimal(str(value)) * 1_000_000).to_integral_value(rounding=ROUND_CEILING))


def human_metadata_gate(intake, input_path, intake_path, output):
    outside_repository(input_path, intake_path, output)
    reviews = intake.get("reviews")
    require(isinstance(reviews, dict), "Human intake reviews required")
    for key in (
        "authorized_processing",
        "derived_retention",
        "release_reviewed",
        "units_reviewed",
        "status_policy_reviewed",
        "availability_reviewed",
        "clock_reviewed",
    ):
        require(reviews.get(key) is True, "Human intake review incomplete")
    for key in ("authorization_reference", "retention_reference", "availability_reference"):
        require(
            isinstance(reviews.get(key), str) and reviews[key].strip(), "Missing review reference"
        )
    allocation = bound_reference(intake.get("allocation_reference"))
    require(
        isinstance(allocation, dict) and isinstance(allocation.get("files"), list),
        "Allocation required",
    )
    members = allocation["files"]
    require(len(members) == 25, "Preserve the original allocation")
    require(
        Counter(p.get("group") for p in members) == {"study": 20, "reserved": 5},
        "Preserve twenty study and five reserved people",
    )
    aliases = [p.get("alias") for p in members]
    hashes = [p.get("sha256") for p in members]
    require(
        all(isinstance(x, str) and x for x in aliases)
        and all(isinstance(x, str) and SHA.fullmatch(x) for x in hashes)
        and len(set(aliases)) == len(set(hashes)) == 25,
        "Duplicate or invalid allocation identities",
    )
    require(
        isinstance(allocation.get("policy_sha256"), str)
        and SHA.fullmatch(allocation["policy_sha256"]),
        "Allocation policy hash required",
    )
    chosen = [p for p in members if p["alias"] == intake["person"]]
    require(len(chosen) == 1 and chosen[0]["group"] == "study", "Reserved or unknown participant")
    require(chosen[0]["sha256"] == intake["source_sha256"], "Allocation/source mismatch")
    split = bound_reference(intake.get("partition_reference"))
    require(
        split.get("schema") == "opent1d.azt1d.partition-reference/1"
        and split.get("alias") == intake["person"]
        and split.get("phase") == intake["phase"]
        and split.get("source_sha256") == intake["source_sha256"]
        and split.get("policy_sha256") == allocation.get("policy_sha256"),
        "Partition differs from frozen allocation",
    )
    require(
        split.get("data_row_start_inclusive") == intake["row_start"]
        and split.get("data_row_stop_exclusive") == intake["row_stop"]
        and split.get("rows") == intake["row_stop"] - intake["row_start"],
        "Partition row bounds changed",
    )
    require(
        [seconds_to_us(x) for x in split["bounds_seconds"]]
        == [intake["start_us"], intake["end_us"]],
        "Partition time bounds changed",
    )


def human_gate(intake, input_path, intake_path, output, evaluation_authorization=None):
    human_metadata_gate(intake, input_path, intake_path, output)
    if intake["phase"] == "evaluation":
        from .study import authorize_evaluation

        return authorize_evaluation(
            intake, input_path, evaluation_authorization, "before_normalization"
        )
    return None


def validate_intake(intake):
    require(isinstance(intake, dict) and intake.get("schema") == SCHEMA, "Wrong intake schema")
    require(intake.get("kind") in ("synthetic", "human"), "Explicit input kind required")
    require(
        isinstance(intake.get("person"), str)
        and re.fullmatch(r"[A-Za-z0-9_-]{1,64}", intake["person"]),
        "Invalid local alias",
    )
    require(intake.get("phase") in PHASES, "Unsupported phase")
    require(
        isinstance(intake.get("source_sha256"), str) and SHA.fullmatch(intake["source_sha256"]),
        "Native source hash required",
    )
    for key in ("start_us", "end_us", "row_start", "row_stop"):
        require(type(intake.get(key)) is int and intake[key] >= 0, "Integer bounds required")
    require(intake["end_us"] > intake["start_us"], "Empty time block")
    require(intake["row_stop"] > intake["row_start"] >= 1, "Invalid source row range")


def normalize(input_path, intake_path, output, *, evaluation_authorization=None):
    from .data import validate_observations
    from .intake import convert_csv

    intake, intake_sha = read(intake_path)
    validate_intake(intake)
    access = None
    if intake["kind"] == "human":
        access = human_gate(intake, input_path, intake_path, output, evaluation_authorization)
    output = Path(output)
    previous_mask = os.umask(0o077)
    try:
        output.mkdir(parents=True, exist_ok=False)
        state = {"schema": SCHEMA, "status": "started", "kind": intake["kind"]}
        save(output / "status.json", state)
        try:
            prov = provenance()
            source = Snapshot(Path(input_path).parent)
            raw = source.read(Path(input_path).name)
            require(digest(raw) == intake["source_sha256"], "Native input bytes changed")
            value = convert_csv(
                raw,
                person=intake["person"],
                origin_local=intake["origin_local"],
                start_us=intake["start_us"],
                end_us=intake["end_us"],
                row_start=intake["row_start"],
                row_stop=intake["row_stop"],
                policy=intake["policy"],
            )
            rows = validate_observations(
                value, intake["person"], intake["start_us"], intake["end_us"]
            )
            source.verify_unchanged()
            save(output / "intake.json", intake)
            save(output / "observations.json", value)
            save(
                output / "conversion.json",
                {
                    "schema": SCHEMA,
                    "kind": intake["kind"],
                    "person": intake["person"],
                    "phase": intake["phase"],
                    "source_sha256": digest(raw),
                    "submitted_intake_sha256": intake_sha,
                    "intake_sha256": digest((output / "intake.json").read_bytes()),
                    "observations_sha256": digest((output / "observations.json").read_bytes()),
                    "source_rows": intake["row_stop"] - intake["row_start"],
                    "registered_origins": len(rows),
                    "statuses": dict(Counter(r["status"] for r in rows.values())),
                    "provenance": prov,
                    "availability_assumption": "measurement time approximates availability",
                    "excluded_channels": "all non-glucose treatment and event fields",
                    "model_fit_or_evaluation": False,
                    "evaluation_access": access,
                },
            )
            state["status"] = "completed"
        except BaseException as error:
            state.update(status="failed", error=failure(error))
            save(output / "status.json", state)
            raise
        save(output / "status.json", state)
    finally:
        os.umask(previous_mask)


def load_conversion(folder, *, expected_phase=None, expected_intake=None, expected_sha256=None):
    from .data import validate_observations

    folder = Path(folder)
    receipt, receipt_sha = read(folder / "conversion.json")
    if expected_sha256 is not None:
        require(receipt_sha == expected_sha256, "Conversion receipt changed")
    require(receipt.get("schema") == SCHEMA, "Wrong conversion schema")
    require(receipt.get("kind") in ("human", "synthetic"), "Missing conversion kind")
    if expected_phase is not None:
        require(expected_phase in PHASES, "Unsupported requested phase")
        require(receipt.get("phase") == expected_phase, "Unexpected conversion phase")
    if receipt["kind"] == "human":
        outside_repository(folder)
    state, _ = read(folder / "status.json")
    require(
        state.get("schema") == SCHEMA
        and state.get("status") == "completed"
        and state.get("kind") == receipt["kind"],
        "Conversion did not complete",
    )
    validate_provenance(receipt.get("provenance"))
    intake, intake_sha = read(folder / "intake.json")
    require(intake_sha == receipt["intake_sha256"], "Intake changed")
    validate_intake(intake)
    if expected_intake is not None:
        require(intake == expected_intake, "Conversion intake differs from frozen request")
    require(
        all(intake[k] == receipt[k] for k in ("person", "phase", "kind", "source_sha256")),
        "Conversion identity mismatch",
    )
    # Metadata and the caller's phase restriction are checked before opening glucose.
    document, document_sha = read(folder / "observations.json")
    require(document_sha == receipt["observations_sha256"], "Observations changed")
    rows = validate_observations(document, intake["person"], intake["start_us"], intake["end_us"])
    require(
        len(rows) == receipt["registered_origins"]
        and [i for row in rows.values() for i in row["source_rows"]]
        == list(range(intake["row_start"], intake["row_stop"]))
        and receipt["source_rows"] == intake["row_stop"] - intake["row_start"]
        and receipt["statuses"] == dict(Counter(r["status"] for r in rows.values())),
        "Source row accounting mismatch",
    )
    return intake, rows, receipt_sha


def prepare(folder, output):
    """Build development windows only; no estimator import/fitting and no held-out scoring."""
    from .data import eligibility, history, origins, target, timing_summary, training_windows

    intake, rows, receipt_sha = load_conversion(folder, expected_phase="development")
    if intake["kind"] == "human":
        outside_repository(output)
    start, end = intake["start_us"], intake["end_us"]
    windows = training_windows(rows, start, end)
    excluded = Counter()
    for origin in origins(rows):
        _, reason = history(rows, origin, start, "development")
        if reason:
            excluded[reason] += 1
        else:
            outcome = target(rows, origin, end)
            if outcome["status"] != "measured":
                excluded["target_" + outcome["status"]] += 1
            elif rows[origin + 30 * MINUTE]["available_us"] >= end:
                excluded["target_unavailable_before_block_end"] += 1
    require(len(windows) + sum(excluded.values()) == len(rows), "Window denominator mismatch")
    previous_mask = os.umask(0o077)
    try:
        output = Path(output)
        output.mkdir(parents=True, exist_ok=False)
        save(
            output / "development.json",
            {
                "schema": SCHEMA,
                "kind": intake["kind"],
                "person": intake["person"],
                "phase": "development",
                "conversion_sha256": receipt_sha,
                "provenance": provenance(),
                "registered_origins_us": origins(rows),
                "training_windows": [
                    {"origin_us": t, "features": x, "target": y} for t, x, y in windows
                ],
                "window_exclusions": dict(excluded),
                "eligible_development": eligibility([t for t, _, _ in windows]),
                "minimum_windows": 288,
                "minimum_span_us": 1440 * MINUTE,
                "timing": timing_summary(rows, start, end),
                "model_fit_or_evaluation": False,
                "status": "development_prepared_not_a_study_freeze",
            },
        )
    finally:
        os.umask(previous_mask)
