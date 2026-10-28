"""Reconstruct M5 comparisons from retained values without importing models or fitting."""

import math

from experiments.m5.synthetic_prognosis.run import fixture, predict

from .contract import (
    ARCHIVE_FILES,
    PROTOCOL,
    ROOT,
    SOURCES,
    VERSION,
    declaration,
    decode,
    encode,
    keys,
    number,
    read_bytes,
    request,
    rows,
    sha,
    snapshot,
    worker_result,
)


def verify_baseline(model, development):
    """Check saved preprocessing and ridge normal equations, without solving/refitting."""
    keys(model, {"means", "scales", "coefficients"})
    for key, length in (("means", 3), ("scales", 3), ("coefficients", 4)):
        if not isinstance(model[key], list) or len(model[key]) != length:
            raise ValueError("Wrong baseline dimensions")
        for value in model[key]:
            number(value, minimum=-1e6, maximum=1e6)
    x = [row["baseline"] for _, row in development]
    n = len(x)
    means = [sum(column) / n for column in zip(*x, strict=True)]
    scales = [
        max(1e-12, (sum((value - mean) ** 2 for value in column) / n) ** 0.5)
        for column, mean in zip(zip(*x, strict=True), means, strict=True)
    ]
    if model["means"] != means or model["scales"] != scales:
        raise ValueError("Baseline preprocessing differs from development-only values")
    z = [[1.0] + [(v - m) / s for v, m, s in zip(row, means, scales, strict=True)] for row in x]
    for i in range(4):
        rhs = sum(
            values[i] * row["outcome"] for values, (_, row) in zip(z, development, strict=True)
        )
        lhs = sum(
            (sum(values[i] * values[j] for values in z) + (1.0 if i == j and i else 0.0))
            * model["coefficients"][j]
            for j in range(4)
        )
        if not math.isclose(lhs, rhs, rel_tol=1e-12, abs_tol=1e-10):
            raise ValueError("Saved baseline fails ridge normal equations")


def assess(packet, baseline, predictions, model_declaration):
    if encode(packet) != encode(fixture()):
        raise ValueError("Only the unchanged invented fixture is supported")
    development, evaluation, roster = rows()
    verify_baseline(baseline, development)
    if not isinstance(predictions, list) or len(predictions) != len(evaluation):
        raise ValueError("Missing or duplicate evaluation participant")
    results, pairs = [], []
    all_baseline_errors = []
    for saved, (alias, row) in zip(predictions, evaluation, strict=True):
        keys(saved, {"alias", "request", "baseline_prediction_u_day", "attempts"})
        expected_baseline = predict(baseline, row, include_function=False)
        number(saved["baseline_prediction_u_day"])
        if (
            saved["alias"] != alias
            or encode(saved["request"]) != encode(request(row))
            or saved["baseline_prediction_u_day"] != expected_baseline
        ):
            raise ValueError("Saved participant, causal request or baseline prediction differs")
        attempts = saved["attempts"]
        if not isinstance(attempts, list) or len(attempts) > 2:
            raise ValueError("Expected at most two sequential attempts per participant")
        for index, attempt in enumerate(attempts, 1):
            keys(attempt, {"attempt", "status", "prediction_u_day", "runtime"})
            if type(attempt["attempt"]) is not int or attempt["attempt"] != index:
                raise ValueError("Wrong attempt identity")
            if attempt["status"] == "completed":
                worker_result(
                    {
                        "schema": "m5-prognostic-worker/1",
                        "prediction_u_day": attempt["prediction_u_day"],
                        "runtime": attempt["runtime"],
                    },
                    model_declaration,
                )
            elif attempt["status"] not in {
                "timeout",
                "worker_failed",
                "invalid_output",
                "interrupted",
            } or (attempt["prediction_u_day"] is not None or attempt["runtime"] is not None):
                raise ValueError("Unsupported attempt failure record")
        if not attempts:
            status = "not_attempted"
        elif any(attempt["status"] == "interrupted" for attempt in attempts):
            status = "interrupted"
        elif len(attempts) < 2:
            status = "incomplete"
        elif any(attempt["status"] != "completed" for attempt in attempts):
            status = "failed"
        elif (
            attempts[0]["prediction_u_day"] != attempts[1]["prediction_u_day"]
            or attempts[0]["runtime"] != attempts[1]["runtime"]
        ):
            status = "not_reproducible"
        else:
            status = "completed"
        candidate = attempts[0]["prediction_u_day"] if status == "completed" else None
        item = {
            "alias": alias,
            "observed_reported_insulin_mean_u_day": row["outcome"],
            "baseline_prediction_u_day": expected_baseline,
            "candidate_prediction_u_day": candidate,
            "candidate_status": status,
            "attempts": attempts,
        }
        all_baseline_errors.append(abs(expected_baseline - row["outcome"]))
        results.append(item)
        if status == "completed":
            pairs.append(item)
    baseline_mae = candidate_mae = None
    if pairs:
        baseline_mae = sum(
            abs(p["baseline_prediction_u_day"] - p["observed_reported_insulin_mean_u_day"])
            for p in pairs
        ) / len(pairs)
        candidate_mae = sum(
            abs(p["candidate_prediction_u_day"] - p["observed_reported_insulin_mean_u_day"])
            for p in pairs
        ) / len(pairs)
    return {
        "schema": VERSION,
        "claim": "invented_pipeline_check_only",
        "human_execution_authorized": False,
        "treatment_effect_or_cure_estimated": False,
        "model_id": model_declaration["model_id"],
        "source_sha256": model_declaration["source_sha256"],
        "state_sha256": model_declaration["state_sha256"],
        "training_provenance": "researcher_declared_not_independently_verified",
        "roster_count": len(roster),
        "development_roster_count": sum(p["split"] == "development" for p in roster),
        "evaluation_roster_count": sum(p["split"] == "evaluation" for p in roster),
        "excluded_count": sum(not p["eligible"] for p in roster),
        "development_eligible_count": len(development),
        "evaluation_eligible_count": len(evaluation),
        "paired_count": len(pairs),
        "candidate_coverage": len(pairs) / len(evaluation),
        "comparison_status": "complete" if len(pairs) == len(evaluation) else "incomplete",
        "candidate_execution_complete": all(
            len(item["attempts"]) == 2
            and all(a["status"] != "interrupted" for a in item["attempts"])
            for item in predictions
        ),
        "metric": "mean absolute error in reported insulin U/day",
        "baseline_mae_all_eligible_u_day": sum(all_baseline_errors) / len(all_baseline_errors),
        "baseline_mae_paired_u_day": baseline_mae,
        "candidate_mae_paired_u_day": candidate_mae,
        "mae_change_candidate_minus_baseline_u_day": (
            candidate_mae - baseline_mae if pairs else None
        ),
        "people": roster,
        "evaluation_predictions": results,
    }


def markdown(report):
    def value(item):
        return "unavailable" if item is None else f"{item:.6f}"

    lines = [
        "# M5 researcher workflow report",
        "",
        "Invented software comparison; no human prognostic or treatment evidence.",
        "",
        f"Comparison: **{report['comparison_status']}**; reproducible pairs "
        f"**{report['paired_count']}/{report['evaluation_eligible_count']}**.",
        "",
        "An incomplete comparison describes successful pairs only; failures limit interpretation.",
        "",
        "| Metric | Reported insulin U/day |",
        "| --- | ---: |",
        f"| Baseline MAE, all eligible | {value(report['baseline_mae_all_eligible_u_day'])} |",
        f"| Baseline MAE, paired | {value(report['baseline_mae_paired_u_day'])} |",
        f"| Candidate MAE, paired | {value(report['candidate_mae_paired_u_day'])} |",
        "| Candidate minus baseline MAE | "
        f"{value(report['mae_change_candidate_minus_baseline_u_day'])} |",
        "",
        "| Participant | Candidate status | Observed | Baseline | Candidate |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for item in report["evaluation_predictions"]:
        lines.append(
            f"| {item['alias']} | {item['candidate_status']} | "
            f"{value(item['observed_reported_insulin_mean_u_day'])} | "
            f"{value(item['baseline_prediction_u_day'])} | "
            f"{value(item['candidate_prediction_u_day'])} |"
        )
    lines.extend(
        [
            "",
            "## Attempt outcomes",
            "",
            "| Participant | Attempt 1 | Attempt 2 |",
            "| --- | --- | --- |",
        ]
    )
    for item in report["evaluation_predictions"]:
        attempts = [
            attempt["status"]
            + (
                ": " + value(attempt["prediction_u_day"])
                if attempt["prediction_u_day"] is not None
                else ""
            )
            for attempt in item["attempts"]
        ]
        attempts += ["not_attempted"] * (2 - len(attempts))
        lines.append(f"| {item['alias']} | {attempts[0]} | {attempts[1]} |")
    lines.extend(
        [
            "",
            "## Complete roster",
            "",
            "| Participant | Split | Eligible | Exclusions | Later infusions (days) |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for person in report["people"]:
        issues = ", ".join(person["issues"]) or "none"
        infusions = ", ".join(map(str, person["intervening_infusion_days"])) or "none"
        lines.append(
            f"| {person['alias']} | {person['split']} | {person['eligible']} | "
            f"{issues} | {infusions} |"
        )
    lines.extend(
        [
            "",
            "## Source identity",
            "",
            f"Model: `{report['model_id']}`.",
            "",
            f"Source SHA-256: `{report['source_sha256']}`.",
            "",
            f"Frozen state SHA-256: `{report['state_sha256']}`.",
            "",
            "Training ancestry and rights are supplier declarations. Source versions, "
            "runtime and both attempts are retained in the archive.",
            "",
        ]
    )
    if "provenance" in report:
        provenance = report["provenance"]
        lines.extend(
            [
                f"Git revision at execution: `{provenance['git_revision']}`.",
                "",
                f"Python: `{provenance['host_runtime']['implementation']} "
                f"{provenance['host_runtime']['python_version']}`; worker deadline: "
                f"{provenance['worker_timeout_seconds']} seconds.",
                "",
                f"Tooling lock SHA-256: `{report['tooling_lock_sha256']}`.",
                "",
                "Local source bytes identify edits beyond the recorded Git revision:",
                "",
            ]
        )
        for name, digest in report["implementation_sha256"].items():
            lines.append(f"- `{name}`: `{digest}`")
        lines.append("")
    return "\n".join(lines).encode()


def from_snapshot(data):
    if data["protocol.json"] != encode(PROTOCOL) or data["fixture.json"] != encode(fixture()):
        raise ValueError("Changed synthetic protocol or fixture")
    model = declaration(decode(data["model.json"]), data["model.py"], data["state.json"])
    provenance = decode(data["provenance.json"])
    keys(
        provenance,
        {"schema", "git_revision", "host_runtime", "worker_timeout_seconds", "source_identity"},
    )
    revision = provenance["git_revision"]
    if (
        provenance["schema"] != "m5-researcher-provenance/1"
        or not isinstance(revision, str)
        or len(revision) != 40
        or any(char not in "0123456789abcdef" for char in revision)
        or provenance["source_identity"]
        != ("saved source bytes; git revision alone does not identify local edits")
    ):
        raise ValueError("Wrong archive provenance")
    number(provenance["worker_timeout_seconds"], minimum=0, maximum=60)
    if provenance["worker_timeout_seconds"] == 0:
        raise ValueError("Invalid worker deadline")
    worker_result(
        {
            "schema": "m5-prognostic-worker/1",
            "prediction_u_day": 0,
            "runtime": provenance["host_runtime"],
        },
        model,
    )
    if data["tooling-uv.lock"] != read_bytes(ROOT / "uv.lock"):
        raise ValueError("Different locked tooling identity")
    predictions = decode(data["predictions.json"])
    report = assess(
        decode(data["fixture.json"]),
        decode(data["baseline.json"]),
        predictions,
        model,
    )
    for saved in predictions:
        for attempt in saved["attempts"]:
            if attempt["status"] == "completed":
                worker_result(
                    {
                        "schema": "m5-prognostic-worker/1",
                        "prediction_u_day": attempt["prediction_u_day"],
                        "runtime": attempt["runtime"],
                    },
                    model,
                    expected_runtime=provenance["host_runtime"],
                )
    report["provenance"] = provenance
    report["tooling_lock_sha256"] = sha(data["tooling-uv.lock"])
    report["implementation_sha256"] = {name: sha(data[name]) for name in sorted(SOURCES)}
    return report


def reconstruct(directory):
    data = snapshot(directory, ARCHIVE_FILES | {"manifest.json"})
    manifest = decode(data.pop("manifest.json"))
    keys(manifest, {"schema", "files"})
    if manifest["schema"] != "m5-researcher-archive/1" or manifest["files"] != {
        name: sha(content) for name, content in data.items()
    }:
        raise ValueError("Changed archive bytes or manifest")
    for name, path in SOURCES.items():
        if data[name] != read_bytes(path):
            raise ValueError("Different M5 reconstruction implementation")
    # Model source and state remain opaque: hashes are verified without importing them.
    report = from_snapshot(data)
    if data["report.json"] != encode(report) or data["report.md"] != markdown(report):
        raise ValueError("Report differs from artifact-only reconstruction")
    return report
