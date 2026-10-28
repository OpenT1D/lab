"""Self-authored artifact-contract fixture; no native fitted or human-data claim."""

import io
from pathlib import Path

from test_m3 import model, point

from experiments.m3.common import SCHEMA, digest, provenance, save
from experiments.m3.data import blocks, origins
from experiments.m3.worker import forecast_rows
from experiments.m3.workflow import seal


def study_fixture(folder):
    folder = Path(folder)
    folder.mkdir()
    prov = provenance()
    prov["dirty"] = False
    people = [
        {
            "id": f"p{i}",
            "source_person": f"invented-{i}",
            "train": {"file": f"p{i}-train.json", "sha256": "a" * 64, "start": 0, "end": 500},
            "evaluation": {"file": f"p{i}-test.json", "sha256": "b" * 64, "start": 600, "end": 800},
        }
        for i in range(2)
    ]
    registry = {
        "schema": SCHEMA,
        "kind": "synthetic",
        "source": "self-authored",
        "release": "contract-fixture/1",
        "rights": {"synthetic": True},
        "clock": "elapsed_synthetic",
        "people": people,
    }
    plan = {
        "schema": SCHEMA,
        "kind": "synthetic",
        "registry": registry,
        "registry_sha256": "c" * 64,
        "input_root": "/nonexistent/synthetic",
        "provenance": prov,
        "splits": {p["id"]: {k: list(v) for k, v in blocks(p).items()} for p in people},
        "status": "synthetic_freeze",
    }
    save(folder / "plan.json", plan)
    plan_sha = digest((folder / "plan.json").read_bytes())
    fitted = model()
    fitted["training_counts"] = {p["id"]: 1 for p in people}
    save(folder / "model.json", fitted)
    fit_result = {
        "status": "completed",
        "plan_sha256": plan_sha,
        "consumed_train_sha256": {p["id"]: p["train"]["sha256"] for p in people},
        "training_origins": {p["id"]: [25] for p in people},
    }
    save(folder / "fit-result.json", fit_result)
    validation = io.StringIO()
    for p in people:
        forecast_rows({t: point(t, 100) for t in range(500)}, p, "validation", fitted, validation)
    (folder / "validation.jsonl").write_text(validation.getvalue())
    save(
        folder / "freeze.json",
        {
            "schema": SCHEMA,
            "plan_sha256": plan_sha,
            "model_sha256": digest((folder / "model.json").read_bytes()),
            "provenance": prov,
            "fit_result_sha256": digest((folder / "fit-result.json").read_bytes()),
            "validation_sha256": digest((folder / "validation.jsonl").read_bytes()),
        },
    )
    cases = []
    for p in people:
        case = folder / p["id"]
        case.mkdir()
        with (case / "trace.jsonl").open("w") as stream:
            count = forecast_rows(
                {t: point(t, 100) for t in range(600, 800, 5)}, p, "evaluation", fitted, stream
            )
        (case / "worker.log").touch()
        save(
            case / "result.json",
            {
                "status": "completed",
                "rows": count,
                "consumed_input_sha256": p["evaluation"]["sha256"],
            },
        )
        seal(
            case, {"schema": SCHEMA, "status": "completed", "provenance": prov, "stage": "running"}
        )
        cases.append({"id": p["id"], "origins": origins(p, "evaluation"), "status": "completed"})
    save(
        folder / "study.json",
        {
            "schema": SCHEMA,
            "kind": "synthetic",
            "plan_sha256": plan_sha,
            "status": "completed",
            "reuse": False,
            "provenance": prov,
            "cases": cases,
        },
    )
    return folder
