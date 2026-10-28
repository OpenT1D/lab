"""Single-person stateless evaluation; no training entrypoint or sklearn import."""

import json
import sys
from pathlib import Path

from experiments.m3.azt1d.data import forecast_rows
from experiments.m3.common import digest, read, require, save

from .common import SCHEMA
from .study import access_check, plan_read


def evaluate(study_path, person_id, output):
    study_path, output = Path(study_path), Path(output)
    plan, plan_sha, model = plan_read(study_path / "plan.json")
    matches = [p for p in plan["registry"]["people"] if p["id"] == person_id]
    require(len(matches) == 1, "Person is not in the frozen external cohort")
    person = matches[0]
    folder = study_path / person_id
    require(output.resolve() == (folder / "run").resolve(), "Wrong external worker output")
    state, _ = read(output / "state.json")
    require(
        state.get("schema") == SCHEMA and state.get("status") == "started",
        "Worker attempt is not new",
    )
    anchor, _ = read(study_path / "ledger-anchor.json")
    first, _ = read(folder / "input-access.json")
    second, _ = read(folder / "execution-access.json")
    access_check(plan, plan_sha, anchor, first, person_id, "before_normalization")
    access_check(plan, plan_sha, anchor, second, person_id, "before_execution")
    require(first["sequence"] < second["sequence"], "External access event order differs")
    with (output / "worker-access.json").open("x") as claim:
        json.dump({"execution_event_sha256": second["event_sha256"]}, claim)
    # Both receipts are checked before any external observation is read.
    document, sha = read(folder / "observations.json")
    require(sha == person["input"]["sha256"], "Materialized input changed")
    from experiments.m3.azt1d.data import validate_observations

    rows = validate_observations(document, person_id, *person["bounds_us"])
    require(sorted(rows) == person["origins_us"], "External worker schedule changed")
    with (output / "trace.jsonl").open("w") as stream:
        for row in forecast_rows(rows, person_id, "evaluation", person["bounds_us"], model):
            stream.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
            stream.flush()
    save(
        output / "result.json",
        {
            "schema": SCHEMA,
            "status": "completed",
            "person": person_id,
            "planned": len(person["origins_us"]),
            "model_bundle_sha256": plan["model_bundle_sha256"],
            "trace_sha256": digest((output / "trace.jsonl").read_bytes()),
        },
    )


def main():
    try:
        require(len(sys.argv) == 4, "External worker requires study, person and output")
        evaluate(*sys.argv[1:])
    except BaseException as error:
        print(f"External evaluation worker failed ({type(error).__name__}).", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
