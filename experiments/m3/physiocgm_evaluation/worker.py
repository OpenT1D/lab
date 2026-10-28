"""One isolated fixed-model worker; never fit, export or reopen donor observations."""

import json
import os
import stat
import sys
from pathlib import Path

from experiments.m1.artifacts import strict_json
from experiments.m3.azt1d.data import forecast_rows
from experiments.m3.common import digest, encoded, require
from experiments.m3.physiocgm.human import _read_private, _write

from .common import SCHEMA, access_check, model, observations, read_plan


def _trace_stream(path):
    descriptor = os.open(path, os.O_WRONLY | os.O_NOFOLLOW)
    try:
        opened, current = os.fstat(descriptor), path.lstat()
        require(
            stat.S_ISREG(opened.st_mode)
            and opened.st_nlink == 1
            and not opened.st_mode & 0o077
            and opened.st_size == 0
            and (opened.st_dev, opened.st_ino) == (current.st_dev, current.st_ino),
            "Trace must be the empty private regular file created for this worker",
        )
        return os.fdopen(descriptor, "wb")
    except BaseException:
        os.close(descriptor)
        raise


def evaluate(study_path, person_id, output):
    study_path, output = Path(study_path), Path(output)
    prepared = study_path / "prepared"
    plan, plan_sha = read_plan(prepared / "plan.json")
    people = [p for p in plan["registry"]["people"] if p["id"] == person_id]
    require(len(people) == 1, "Person not in frozen cohort")
    person = people[0]
    folder = study_path / person_id
    require(output.absolute() == folder / "run", "Unexpected worker output")
    state = strict_json(_read_private(output / "state.json"))
    require(state["schema"] == SCHEMA and state["status"] == "started", "Worker is not new")
    anchor = strict_json(_read_private(prepared / "ledger-anchor.json"))
    first = strict_json(_read_private(folder / "input-access.json"))
    second = strict_json(_read_private(folder / "execution-access.json"))
    access_check(plan, plan_sha, anchor, first, person_id, "before_normalization")
    access_check(plan, plan_sha, anchor, second, person_id, "before_execution")
    require(first["sequence"] < second["sequence"], "Wrong worker access order")
    expected_claim = {"schema": SCHEMA, "plan_sha256": plan_sha, "output": str(study_path)}
    require(
        strict_json(_read_private(study_path / "execution-claim.json")) == expected_claim
        and strict_json(_read_private(Path(plan["ledger"]).parent / "execution-claim.json"))
        == expected_claim,
        "Worker not bound to the exclusive study attempt",
    )
    _write(
        output / "worker-access.json", encoded({"execution_event_sha256": second["event_sha256"]})
    )
    # The claim and both live receipts are durable before model/input reads.
    fitted = model(prepared)
    rows = observations(_read_private(folder / "observations.json"), person)
    with _trace_stream(output / "trace.jsonl") as stream:
        try:
            for row in forecast_rows(rows, person_id, "evaluation", person["bounds_us"], fitted):
                stream.write((json.dumps(row, sort_keys=True, allow_nan=False) + "\n").encode())
                stream.flush()
        finally:
            stream.flush()
            os.fsync(stream.fileno())
    _write(
        output / "result.json",
        encoded(
            {
                "schema": SCHEMA,
                "status": "completed",
                "person": person_id,
                "planned": len(person["origins_us"]),
                "model_sha256": plan["model_sha256"],
                "trace_sha256": digest(_read_private(output / "trace.jsonl")),
            }
        ),
    )


def main():
    try:
        require(len(sys.argv) == 4, "Worker requires study, person and output")
        evaluate(*sys.argv[1:])
    except BaseException as error:
        print(f"Human external worker failed ({type(error).__name__}).", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
