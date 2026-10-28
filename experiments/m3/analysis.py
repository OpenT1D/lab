"""Strict saved-artifact reconstruction; standard library only."""

import math
import random
from collections import Counter
from pathlib import Path

from .common import METRIC, SCHEMA, Snapshot, digest, finite, require, validate_provenance
from .data import STATUSES, blocks, history, origins, validate_registry
from .estimator import predict, validate_model


def metrics(rows, model):
    errors, censored = [], []
    for row in rows:
        if row["forecasts"] is None:
            continue
        p, target = row["forecasts"][model], row["target"]
        if target["status"] == "measured":
            error = finite(p - target["value"], "forecast error")
            finite(error * error, "squared forecast error")
            errors.append(error)
        elif target["bound"] is not None:
            censored.append(
                max(0, target["bound"] - p)
                if target["status"] == "censored_high"
                else max(0, p - target["bound"])
            )
    for total in (sum(map(abs, errors)), sum(errors), sum(e * e for e in errors), sum(censored)):
        finite(total, "metric total")
    return {
        "scored": len(errors),
        "mae": sum(map(abs, errors)) / len(errors) if errors else None,
        "rmse": math.sqrt(sum(e * e for e in errors) / len(errors)) if errors else None,
        "bias": sum(errors) / len(errors) if errors else None,
        "censored_count": len(censored),
        "mean_censored_absolute_error_lower_bound": sum(censored) / len(censored)
        if censored
        else None,
    }


def cluster_interval(differences):
    if len(differences) < 2:
        return None
    rng = random.Random(301)
    means = sorted(
        sum(rng.choices(differences, k=len(differences))) / len(differences) for _ in range(2000)
    )
    return [means[49], means[1949]]


def validate_point(row, person, phase, model, expected_origin):
    require(
        set(row)
        == {
            "person",
            "phase",
            "origin",
            "features",
            "history_reason",
            "history_rows",
            "forecasts",
            "target",
        },
        "Invalid forecast row",
    )
    finite(row["origin"], "forecast origin", 0)
    require(
        row["person"] == person["id"]
        and row["phase"] == phase
        and row["origin"] == expected_origin,
        "Prediction schedule differs",
    )
    require(
        isinstance(row["history_rows"], list) and len(row["history_rows"]) == 6,
        "Missing causal audit",
    )
    from .data import observations

    present = [p for p in row["history_rows"] if p is not None]
    # Contract-validation also catches strings, bools and invalid availability in saved history.
    if present:
        values = observations(
            {
                "schema": SCHEMA,
                "person": person["id"],
                "clock": "elapsed_synthetic",
                "unit": "mg/dL",
                "rows": present,
            },
            person["id"],
            "elapsed_synthetic",
            max(0, expected_origin - 25),
            expected_origin + 1,
        )
    else:
        values = {}
    for offset, point in enumerate(row["history_rows"]):
        if point is not None:
            require(point["time"] == expected_origin - 25 + 5 * offset, "Future or shifted feature")
    expected, reason = history(values, expected_origin, blocks(person)[phase][0], phase)
    if row["features"] is not None:
        require(isinstance(row["features"], list) and len(row["features"]) == 6, "Invalid features")
        for value in row["features"]:
            finite(value, "saved feature", 0)
    require(
        row["features"] == expected and row["history_reason"] == reason, "Causal history mismatch"
    )
    if expected is None:
        require(row["forecasts"] is None, "Forecast without permitted history")
    else:
        require(
            isinstance(row["forecasts"], dict)
            and set(row["forecasts"]) == {"ridge", "persistence"},
            "Missing predictions",
        )
        for value in row["forecasts"].values():
            finite(value, "saved forecast")
        require(
            row["forecasts"] == {"ridge": predict(model, expected), "persistence": expected[-1]},
            "Forecast differs from frozen model",
        )
    target = row["target"]
    require(
        isinstance(target, dict) and set(target) == {"status", "value", "bound"}, "Invalid target"
    )
    require(
        target["status"] in (*STATUSES, "outside_split", "clock_discontinuity"),
        "Invalid target status",
    )
    if target["status"] == "measured":
        finite(target["value"], "target", 0)
        require(target["value"] > 0 and target["bound"] is None, "Invalid measured target")
    else:
        require(target["value"] is None, "Nonmeasured target has point value")
        if target["bound"] is not None:
            require(target["status"].startswith("censored"), "Invalid target bound")
            finite(target["bound"], "target bound", 0)
            require(target["bound"] > 0, "Invalid target bound")
    if expected_origin + 30 >= blocks(person)[phase][1]:
        require(target["status"] == "outside_split", "Target crosses split")
    else:
        require(target["status"] != "outside_split", "False target boundary exclusion")


def read_case(folder, person, phase, model):
    snap = Snapshot(folder)
    from experiments.m1.artifacts import strict_json

    state = strict_json(snap.read("state.json"))
    require(
        state.get("schema") == SCHEMA
        and state.get("status") in ("started", "completed", "failed", "interrupted"),
        "Invalid case status",
    )
    if state.get("stage") == "initializing":
        require(
            state["status"] in ("started", "failed", "interrupted"),
            "Completed initialization failure",
        )
        require(not snap.read("trace.jsonl"), "Initialization failure inherited output")
    else:
        require(state.get("stage") == "running", "Missing lifecycle stage")
        validate_provenance(state.get("provenance"))
    sealed = state["status"] != "started"
    if sealed:
        require(
            isinstance(state.get("files"), dict)
            and {"trace.jsonl", "worker.log"} <= state["files"].keys(),
            "Missing artifact inventory",
        )
        for name, sha in state["files"].items():
            require(digest(snap.read(name)) == sha, "Artifact bytes changed")
        actual = {
            p.name
            for p in Path(folder).iterdir()
            if p.name != "state.json" and not p.name.endswith(".tmp")
        }
        require(actual == set(state["files"]), "Uninventoried artifact")
    if state["status"] in ("failed", "interrupted"):
        require(
            isinstance(state.get("error"), dict) and state["error"].get("type"),
            "Missing original failure",
        )
    rows, fragment = [], False
    planned = origins(person, phase)
    for line in snap.read("trace.jsonl").splitlines(keepends=True):
        if not line.endswith(b"\n"):
            require(state["status"] != "completed", "Truncated completed trace")
            fragment = True
            break
        require(len(rows) < len(planned), "Extra prediction")
        row = strict_json(line)
        validate_point(row, person, phase, model, planned[len(rows)])
        rows.append(row)
    if state["status"] == "completed":
        result = strict_json(snap.read("result.json"))
        require(
            result.get("status") == "completed"
            and type(result.get("rows")) is int
            and result["rows"] == len(rows) == len(planned),
            "False case completion",
        )
        require(
            result.get("consumed_input_sha256") == person["evaluation"]["sha256"],
            "Missing consumed input provenance",
        )
    snap.verify_unchanged()
    return rows, state, {k: v for k, v in sorted(snap.sha256().items())}, fragment


def summary(rows, planned):
    predicted = sum(r["forecasts"] is not None for r in rows)
    scored = sum(r["forecasts"] is not None and r["target"]["status"] == "measured" for r in rows)
    return {
        "planned": planned,
        "attempted": len(rows),
        "not_attempted": planned - len(rows),
        "predicted": predicted,
        "prediction_coverage": predicted / planned if planned else None,
        "score_coverage": scored / planned if planned else None,
        "history_exclusions": dict(
            sorted(Counter(r["history_reason"] for r in rows if r["history_reason"]).items())
        ),
        "targets": dict(sorted(Counter(r["target"]["status"] for r in rows).items())),
        "ridge": metrics(rows, "ridge"),
        "persistence": metrics(rows, "persistence"),
    }


def origin_stratum(row):
    point = row["history_rows"][-1]
    if point is None or point["status"] != "measured" or point["available"] > row["origin"]:
        return "unknown"
    return "low" if point["value"] < 70 else "high" if point["value"] > 180 else "in_range"


def reconstruct(folder):
    folder = Path(folder)
    from experiments.m1.artifacts import strict_json

    snap = Snapshot(folder)

    def parsed(name):
        raw = snap.read(name)
        return strict_json(raw), digest(raw)

    study, study_sha = parsed("study.json")
    plan, plan_sha = parsed("plan.json")
    model, model_sha = parsed("model.json")
    frozen, frozen_sha = parsed("freeze.json")
    validate_model(model)
    require(
        study.get("schema") == plan.get("schema") == frozen.get("schema") == SCHEMA,
        "Invalid study contract",
    )
    for value in (study, plan, frozen):
        validate_provenance(value.get("provenance"))
    validate_registry(plan.get("registry"), Path(plan["input_root"]) / "registry.json")
    require(study.get("plan_sha256") == frozen.get("plan_sha256") == plan_sha, "Unbound plan")
    require(frozen.get("model_sha256") == model_sha, "Unbound model")
    require(
        study.get("kind") == plan.get("kind") == plan["registry"]["kind"], "Evidence kind mismatch"
    )
    require(type(study.get("reuse")) is bool, "Missing evaluation access status")
    people = plan["registry"]["people"]
    fit_result, fit_sha = parsed("fit-result.json")
    require(
        fit_sha == frozen.get("fit_result_sha256") and fit_result.get("status") == "completed",
        "Missing fit provenance",
    )
    require(fit_result.get("plan_sha256") == plan_sha, "Fit used a different plan")
    require(
        fit_result.get("consumed_train_sha256") == {p["id"]: p["train"]["sha256"] for p in people},
        "Missing actual training input provenance",
    )
    for person in people:
        fitted_origins = fit_result["training_origins"][person["id"]]
        start, end = blocks(person)["development"]
        require(
            isinstance(fitted_origins, list)
            and len(fitted_origins) == model["training_counts"][person["id"]],
            "Training count mismatch",
        )
        require(fitted_origins == sorted(set(fitted_origins)), "Repeated development window")
        for origin in fitted_origins:
            finite(origin, "fit origin", 0)
            require(origin - 25 >= start and origin + 30 < end, "Fit crossed development boundary")
    validation_bytes = snap.read("validation.jsonl")
    require(digest(validation_bytes) == frozen.get("validation_sha256"), "Validation bytes changed")
    validation_rows = [strict_json(line) for line in validation_bytes.splitlines()]
    expected_validation = [
        (person, origin) for person in people for origin in origins(person, "validation")
    ]
    require(len(validation_rows) == len(expected_validation), "Validation schedule incomplete")
    for row, (person, origin) in zip(validation_rows, expected_validation, strict=True):
        validate_point(row, person, "validation", model, origin)
    require(len(study.get("cases", [])) == len(people), "Incomplete planned cohort")
    results, inputs, differences, incomplete = [], {}, [], []
    for person, case in zip(people, study["cases"], strict=True):
        planned = origins(person, "evaluation")
        require(
            case.get("id") == person["id"] and case.get("origins") == planned,
            "Study schedule mismatch",
        )
        for origin in case["origins"]:
            finite(origin, "scheduled origin", 0)
        path = folder / case["id"]
        if not path.exists():
            require(case.get("status") == "not_attempted", "Missing attempted case")
            rows, status, error, fragment = [], "not_attempted", None, False
        else:
            rows, state, hashes, fragment = read_case(path, person, "evaluation", model)
            status, error = state["status"], state.get("error")
            require(
                case.get("status") == status
                or (study["status"] == "started" and case.get("status") == "not_attempted"),
                "Case status differs from study",
            )
            inputs[case["id"]] = hashes
        stats = summary(rows, len(planned))
        qualified = status == "completed" and stats["ridge"]["scored"] > 0
        if study["kind"] == "human":
            qualified = (
                qualified
                and stats["ridge"]["scored"] >= 288
                and model["training_counts"][person["id"]] >= 288
            )
        if qualified:
            differences.append(stats["ridge"]["mae"] - stats["persistence"]["mae"])
        else:
            incomplete.append(person["id"])
        strata = {}
        for name in ("low", "in_range", "high", "unknown"):
            subset = [r for r in rows if origin_stratum(r) == name]
            missing = len(planned) - len(rows) if name == "unknown" else 0
            strata[name] = summary(subset, len(subset) + missing)
        results.append(
            {
                "person": person["id"],
                "status": status,
                "error": error,
                "partial_fragment": fragment,
                "eligible_for_primary": qualified,
                **stats,
                "origin_strata": strata,
            }
        )
    states = Counter(r["status"] for r in results)
    require(
        study.get("status")
        in ("started", "completed", "finished_with_failures", "failed", "interrupted"),
        "Invalid study status",
    )
    if study["status"] == "completed":
        require(set(states) == {"completed"}, "False study completion")
    if study["status"] == "finished_with_failures":
        require(
            not any(k in states for k in ("started", "not_attempted"))
            and any(k in states for k in ("failed", "interrupted")),
            "False study failure accounting",
        )
    aggregate = {}
    for name in ("ridge", "persistence"):
        aggregate[name] = {
            metric: sum(r[name][metric] for r in results if r["eligible_for_primary"])
            / len(differences)
            if differences
            else None
            for metric in ("mae", "rmse", "bias")
        }
    snap.verify_unchanged()
    return {
        "schema": "opent1d.m3-report/1",
        "metric": METRIC,
        "kind": study["kind"],
        "study_status": study["status"],
        "evaluation_reuse": study["reuse"],
        "interpretation": "synthetic mechanics only"
        if study["kind"] == "synthetic"
        else "inconclusive coverage"
        if incomplete or len(differences) < 2
        else "descriptive later-period CGM prediction for known participants",
        "status_counts": dict(sorted(states.items())),
        "people": results,
        "primary": {
            "paired_people": len(differences),
            "excluded_people": incomplete,
            "mean_person_mae_difference": sum(differences) / len(differences)
            if differences
            else None,
            "participant_bootstrap_95": cluster_interval(differences),
            "person_differences": differences,
        },
        "equal_person_metrics": aggregate,
        "validation": summary(validation_rows, len(validation_rows)),
        "inputs_sha256": {
            "study.json": study_sha,
            "plan.json": plan_sha,
            "model.json": model_sha,
            "freeze.json": frozen_sha,
            "fit-result.json": fit_sha,
            "validation.jsonl": digest(validation_bytes),
            "cases": inputs,
        },
    }
