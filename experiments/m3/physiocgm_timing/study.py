"""Bounded invented-data campaign and reconstruction, with no human intake API."""

import json
import os
from pathlib import Path

from experiments.m1.artifacts import strict_json
from experiments.m3.azt1d.analysis import _equal, _Snapshot
from experiments.m3.azt1d.data import forecast_rows as exact_forecasts
from experiments.m3.azt1d.data import validate_observations
from experiments.m3.common import digest, encoded, require
from experiments.m3.external.metrics import summarize_case as exact_summary
from experiments.m3.physiocgm.human import _state, _write

from .common import PROTOCOL, RADII_US, RULES, SCHEMA, provenance
from .fixtures import FIXTURE, model, observations
from .forecast import forecast_rows
from .metrics import compare_variants, summarize_case


def _fixture_payloads():
    documents = observations()
    payloads = {"model.json": encoded(model())}
    payloads.update(
        {f"{person}/observations.json": encoded(document) for person, document in documents.items()}
    )
    return payloads, documents


def _plan(payloads, documents):
    return {
        "schema": SCHEMA,
        "protocol": PROTOCOL,
        "kind": "synthetic",
        "fixture": FIXTURE,
        "model_origin": "hand-authored-test-coefficients-never-trained",
        "human_execution_supported": False,
        "rules": RULES,
        "inputs": {name: digest(raw) for name, raw in payloads.items()},
        "people": {
            person: {
                "bounds_us": document["bounds_us"],
                "origins_us": [row["time_us"] for row in document["rows"]],
            }
            for person, document in documents.items()
        },
        "provenance": provenance(),
    }


def _aggregate(plan, traces, states):
    people = plan["people"]
    return compare_variants(
        traces,
        planned_origins_by_person={p: value["origins_us"] for p, value in people.items()},
        bounds_by_person={p: value["bounds_us"] for p, value in people.items()},
        execution_statuses_by_radius_by_person=states,
    )


def _zero_summary(plan, person, rows):
    metadata = plan["people"][person]
    legacy = [{key: value for key, value in row.items() if key != "timing"} for row in rows]
    expected = exact_summary(
        metadata["origins_us"],
        legacy,
        execution_status="completed",
        bounds_us=metadata["bounds_us"],
    )
    actual = summarize_case(
        metadata["origins_us"],
        rows,
        execution_status="completed",
        bounds_us=metadata["bounds_us"],
        radius_us=0,
    )
    require(
        all(_equal(actual[key], value) for key, value in expected.items() if key != "metric"),
        "Zero-radius historical summary differs",
    )


def demo(output):
    """Generate the only supported input locally and retain every attempted prefix."""
    output = Path(output)
    require(not output.exists(), "Use a new synthetic output directory")
    payloads, documents = _fixture_payloads()
    plan = _plan(payloads, documents)
    output.mkdir(mode=0o700, parents=True)
    _write(output / "plan.json", encoded(plan))
    # A fresh directory and exclusive claim prevent rerunning a demo in place.
    _write(output / "execution-claim.json", encoded({"plan_sha256": digest(encoded(plan))}))
    states = {radius: {person: "not_attempted" for person in documents} for radius in RADII_US}
    state = {"schema": SCHEMA, "kind": "synthetic", "status": "started", "cases": states}
    _state(output / "state.json", state)
    traces = {radius: {person: [] for person in documents} for radius in RADII_US}
    try:
        for name, raw in payloads.items():
            _write(output / name, raw)
        saved_model = strict_json(payloads["model.json"])
        for radius in RADII_US:
            for person, document in documents.items():
                states[radius][person] = "started"
                _state(output / "state.json", state)
                bounds = document["bounds_us"]
                source = validate_observations(document, person, *bounds)
                legacy = (
                    iter(exact_forecasts(source, person, "evaluation", bounds, saved_model))
                    if radius == 0
                    else None
                )
                path = output / f"{person}/radius-{radius}.jsonl"
                _write(path, b"")
                fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW)
                with os.fdopen(fd, "w") as stream:
                    for row in forecast_rows(source, person, bounds, saved_model, radius):
                        if legacy is not None:
                            require(
                                _equal(
                                    {k: v for k, v in row.items() if k != "timing"}, next(legacy)
                                ),
                                "Zero-radius historical trace differs",
                            )
                        stream.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
                        stream.flush()
                        traces[radius][person].append(row)
                    os.fsync(stream.fileno())
                if legacy is not None:
                    require(next(legacy, None) is None, "Historical schedule is longer")
                    _zero_summary(plan, person, traces[radius][person])
                require(
                    digest(encoded(saved_model)) == plan["inputs"]["model.json"],
                    "Synthetic model changed",
                )
                states[radius][person] = "completed"
                _state(output / "state.json", state)
            # All zero-radius cases finish successfully before any wider variant starts.
        result = _aggregate(plan, traces, states)
        _write(output / "result.json", encoded(result))
        state["status"] = "completed"
        _state(output / "state.json", state)
    except BaseException as error:
        for cases in states.values():
            for person, status in cases.items():
                if status == "started":
                    cases[person] = (
                        "interrupted" if isinstance(error, KeyboardInterrupt) else "failed"
                    )
        state.update(
            status="interrupted" if isinstance(error, KeyboardInterrupt) else "failed",
            error_type=type(error).__name__,
        )
        _state(output / "state.json", state)
        raise
    finally:
        files = {
            str(path.relative_to(output)): digest(path.read_bytes())
            for path in output.rglob("*")
            if path.is_file()
        }
        _write(output / "inventory.json", encoded({"schema": SCHEMA, "files": files}))
    return {"schema": SCHEMA, "kind": "synthetic", "status": "completed", "variants": 3}


def verify(study):
    """Read only a declared, fixed invented fixture; recompute every saved trace.

    This is a synthetic artifact verifier, not a protected human-data reader.
    Human plans are rejected before any observation/model/trace payload read.
    """
    with _Snapshot(study) as snapshot:
        plan = snapshot.parsed("plan.json")
        require(
            isinstance(plan, dict)
            and plan.get("schema") == SCHEMA
            and plan.get("kind") == "synthetic"
            and plan.get("fixture") == FIXTURE
            and plan.get("human_execution_supported") is False,
            "Only the fixed invented example is supported",
        )
        payloads, documents = _fixture_payloads()
        expected_plan = _plan(payloads, documents)
        require(set(plan) == set(expected_plan), "Invalid synthetic plan fields")
        for key in expected_plan:
            if key != "provenance":
                require(_equal(plan[key], expected_plan[key]), "Synthetic plan rules changed")
        require(
            plan["provenance"]["sources"] == expected_plan["provenance"]["sources"],
            "Use the recorded timing implementation",
        )
        expected_files = set(payloads) | {
            "plan.json",
            "state.json",
            "execution-claim.json",
            "result.json",
        }
        expected_files |= {
            f"{person}/radius-{radius}.jsonl" for person in documents for radius in RADII_US
        }
        require(snapshot.names == expected_files | {"inventory.json"}, "Incomplete example")
        inventory = snapshot.parsed("inventory.json")
        require(
            set(inventory) == {"schema", "files"}
            and inventory["schema"] == SCHEMA
            and set(inventory["files"]) == expected_files,
            "Unexpected synthetic inventory",
        )
        for name in expected_files:
            require(digest(snapshot.read(name)) == inventory["files"][name], "Artifact changed")
        require(
            _equal(
                snapshot.parsed("execution-claim.json"),
                {"plan_sha256": digest(snapshot.read("plan.json"))},
            ),
            "Execution claim changed",
        )
        for name, raw in payloads.items():
            require(snapshot.read(name) == raw, "Not the fixed invented input")
        state = snapshot.parsed("state.json")
        require(
            state
            == {
                "schema": SCHEMA,
                "kind": "synthetic",
                "status": "completed",
                "cases": {str(r): {p: "completed" for p in documents} for r in RADII_US},
            },
            "Synthetic campaign is not completed",
        )
        saved_model = snapshot.parsed("model.json")
        traces = {radius: {} for radius in RADII_US}
        for radius in RADII_US:
            for person, document in documents.items():
                source = validate_observations(document, person, *document["bounds_us"])
                raw = snapshot.read(f"{person}/radius-{radius}.jsonl")
                require(raw.endswith(b"\n"), "Incomplete trace fragment")
                rows = [strict_json(line) for line in raw.splitlines()]
                expected = list(
                    forecast_rows(source, person, document["bounds_us"], saved_model, radius)
                )
                require(_equal(rows, expected), "Saved forecast or timing differs")
                if radius == 0:
                    old = list(
                        exact_forecasts(
                            source, person, "evaluation", document["bounds_us"], saved_model
                        )
                    )
                    require(
                        _equal(
                            [{k: v for k, v in row.items() if k != "timing"} for row in rows], old
                        ),
                        "Historical zero-radius equivalence failed",
                    )
                    _zero_summary(plan, person, rows)
                traces[radius][person] = rows
        statuses = {r: {p: "completed" for p in documents} for r in RADII_US}
        result = _aggregate(plan, traces, statuses)
        require(_equal(snapshot.parsed("result.json"), result), "Reconstructed summary differs")
        snapshot.verify()
    return {
        "schema": SCHEMA,
        "kind": "synthetic",
        "status": "verified",
        "zero_radius_equivalence": True,
        "nested_sets_verified": True,
        "model_refitted": False,
    }
