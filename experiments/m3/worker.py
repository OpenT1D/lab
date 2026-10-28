"""Isolated estimator fitting and stateless saved-coefficient forecasts."""

import json
import sys
from pathlib import Path

from .common import read, require, save
from .data import blocks, history, load_observations, origins, target
from .estimator import predict, validate_model


def forecast_rows(rows, person, phase, model, stream):
    start, end = blocks(person)[phase]
    count = 0
    for origin in origins(person, phase):
        features, reason = history(rows, origin, start, phase)
        forecasts = (
            None
            if features is None
            else {"ridge": predict(model, features), "persistence": features[-1]}
        )
        # Only after computing the forecast do we inspect the target.
        outcome = target(rows, origin, end)
        point = {
            "person": person["id"],
            "phase": phase,
            "origin": origin,
            "features": features,
            "history_reason": reason,
            "history_rows": [rows.get(origin - 25 + 5 * i) for i in range(6)],
            "forecasts": forecasts,
            "target": outcome,
        }
        stream.write(json.dumps(point, allow_nan=False) + "\n")
        stream.flush()
        count += 1
    return count


def evaluate(study_path, person_id, output):
    plan, _ = read(Path(study_path) / "plan.json")
    model, _ = read(Path(study_path) / "model.json")
    validate_model(model)
    people = [p for p in plan["registry"]["people"] if p["id"] == person_id]
    require(len(people) == 1, "Unknown planned participant")
    person = people[0]
    rows, sha = load_observations(
        plan["input_root"], person, "evaluation", plan["registry"]["clock"]
    )
    with (output / "trace.jsonl").open("w") as trace:
        count = forecast_rows(rows, person, "evaluation", model, trace)
    save(
        output / "result.json", {"status": "completed", "rows": count, "consumed_input_sha256": sha}
    )


def main():
    from .workflow import failure, fit_worker

    args = sys.argv[1:]
    output = Path(args[-1])
    try:
        if args[0] == "fit":
            fit_worker(args[1], output)
        else:
            require(args[0] == "evaluate", "Unknown worker action")
            evaluate(args[1], args[2], output)
    except BaseException as error:
        save(output / "result.json", {"status": "failed", "error": failure(error)})
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
