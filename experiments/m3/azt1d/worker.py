"""Bounded fit/evaluation entrypoint; arbitrary data-bearing errors are never printed."""

import json
import sys
from pathlib import Path

from .common import SCHEMA, outside_repository, read, require, save, validate_provenance
from .data import eligibility, forecast_rows, origins, training_windows
from .service import load_conversion
from .study import metadata, plan_read


def snapshot(folder):
    return {
        name: read(Path(folder) / f"{name}.json")[0]
        for name in ("intake", "conversion", "observations", "status")
    }


def write_trace(stream, rows, pid, phase, bounds, model):
    for row in forecast_rows(rows, pid, phase, bounds, model):
        stream.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
        stream.flush()


def fit_worker(plan_path, output):
    from experiments.m3.estimator import fit

    output = Path(output)
    plan, plan_sha = plan_read(plan_path)
    if plan["kind"] == "human":
        outside_repository(output)
    from .ledger import verify_evidence

    anchor, _ = read(Path(plan_path).parent / "ledger-anchor.json")
    require(
        verify_evidence(plan["registry"]["ledger"], plan["identity"], anchor)["event_count"] == 0,
        "Evaluation access already recorded; do not refit",
    )
    samples, counts, inputs = {}, {}, {}
    for person in plan["registry"]["people"]:
        pid = person["id"]
        folder = person["development"]["folder"]
        expected = metadata(person["development"], "development", plan["kind"], pid)
        intake, rows, receipt_sha = load_conversion(
            folder,
            expected_phase="development",
            expected_intake=expected,
            expected_sha256=person["development"]["sha256"],
        )
        require(receipt_sha == person["development"]["sha256"], "Development changed")
        windows = training_windows(rows, intake["start_us"], intake["end_us"])
        eligible = eligibility([w[0] for w in windows])
        counts[pid] = {
            "eligible": eligible,
            "origins_us": [w[0] for w in windows],
            "registered_origins_us": origins(rows),
        }
        inputs[pid] = {"development": snapshot(folder)}
        if eligible:
            samples[pid] = windows
    save(output / "development.json", counts)
    save(output / "inputs.json", inputs)
    require(samples, "No participant meets development coverage floor")
    model = fit(samples)
    save(output / "model.json", model)
    schedules = {}
    validation = {}
    for person in plan["registry"]["people"]:
        pid, folder = person["id"], person["validation"]["folder"]
        expected = metadata(person["validation"], "validation", plan["kind"], pid)
        intake, rows, receipt_sha = load_conversion(
            folder,
            expected_phase="validation",
            expected_intake=expected,
            expected_sha256=person["validation"]["sha256"],
        )
        require(receipt_sha == person["validation"]["sha256"], "Validation changed")
        inputs[pid]["validation"] = snapshot(folder)
        schedules[pid] = origins(rows)
        validation[pid] = (rows, [intake["start_us"], intake["end_us"]])
    save(output / "inputs.json", inputs)
    save(output / "validation-schedule.json", schedules)
    with (output / "trace.jsonl").open("w") as trace:
        for pid, (rows, bounds) in validation.items():
            write_trace(trace, rows, pid, "validation", bounds, model)
    save(
        output / "result.json",
        {
            "schema": SCHEMA,
            "status": "completed",
            "plan_sha256": plan_sha,
            "development": counts,
            "training_people": list(samples),
            "validation_origins": schedules,
        },
    )


def evaluate_worker(study_path, person_id, output):
    study_path, output = Path(study_path), Path(output)
    plan, plan_sha = plan_read(study_path / "plan.json", verify_inputs=False)
    if plan["kind"] == "human":
        outside_repository(study_path, output)
    require(output.resolve() == (study_path / person_id / "run").resolve(), "Wrong worker output")
    state, _ = read(output / "state.json")
    require(state.get("status") == "started", "Worker attempt is not new")
    from .ledger import verify_evidence

    frozen, freeze_sha = read(study_path / "fit-freeze.json")
    validate_provenance(frozen.get("provenance"))
    require(frozen.get("plan_sha256") == plan_sha, "Worker plan differs from learned freeze")
    model, model_sha = read(study_path / "fit-model.json")
    require(model_sha == frozen.get("model_sha256"), "Worker model differs from learned freeze")
    for name, event in (
        ("normalization", "before_normalization"),
        ("execution", "before_execution"),
    ):
        evidence, _ = read(study_path / person_id / f"{name}-access.json")
        verify_evidence(plan["registry"]["ledger"], plan["identity"], evidence)
        require(
            evidence["freeze_sha256"] == freeze_sha
            and evidence["person"] == person_id
            and evidence["event"] == event
            and evidence["kind"] == plan["kind"],
            "Worker access evidence differs",
        )
    with (output / "worker-access.json").open("x") as claim:
        import json

        json.dump({"execution_event_sha256": evidence["event_sha256"]}, claim)
    people = [p for p in plan["registry"]["people"] if p["id"] == person_id]
    require(len(people) == 1, "Unplanned evaluation participant")
    person = people[0]
    expected, expected_sha = read(Path(person["evaluation"]["intake_reference"]["file"]))
    require(
        expected_sha == person["evaluation"]["intake_reference"]["sha256"],
        "Worker evaluation descriptor changed",
    )
    intake, rows, receipt_sha = load_conversion(
        study_path / person_id / "conversion", expected_phase="evaluation", expected_intake=expected
    )
    require(
        intake["kind"] == plan["kind"] and intake["person"] == person_id,
        "Evaluation identity changed",
    )
    require(
        expected_sha == person["evaluation"]["intake_reference"]["sha256"] and intake == expected,
        "Worker input differs from frozen evaluation",
    )
    require(
        origins(rows) == person["evaluation"]["origins_us"],
        "Registered evaluation schedule differs",
    )
    save(
        output / "schedule.json",
        {"person": person_id, "origins_us": origins(rows), "conversion_sha256": receipt_sha},
    )
    with (output / "trace.jsonl").open("w") as trace:
        write_trace(
            trace, rows, person_id, "evaluation", [intake["start_us"], intake["end_us"]], model
        )
    save(
        output / "result.json",
        {
            "schema": SCHEMA,
            "status": "completed",
            "person": person_id,
            "rows": len(rows),
            "conversion_sha256": receipt_sha,
        },
    )


def main():
    try:
        if sys.argv[1] == "fit" and len(sys.argv) == 4:
            fit_worker(sys.argv[2], sys.argv[3])
        elif sys.argv[1] == "evaluate" and len(sys.argv) == 5:
            evaluate_worker(sys.argv[2], sys.argv[3], sys.argv[4])
        else:
            raise ValueError("Invalid worker invocation")
    except BaseException as error:
        print(f"AZT1D worker failed ({type(error).__name__})", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
