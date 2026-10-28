"""M2 population gate and saved M1-semantics reader; no simulator imports."""

import hashlib
from pathlib import Path

from experiments.m1.artifacts import digest, strict_json
from experiments.m1.contracts import MEALS, Row, number, validate_rows
from experiments.m1.metrics import summarize
from experiments.m1.validation import (
    REVISION,
    Snapshot,
    hashes,
    text_value,
    validate_native_provenance,
    validate_warnings,
)

from .run import ROOT, source_hashes


def validate_config(value):
    if not isinstance(value, dict) or set(value) != {
        "engine",
        "profile",
        "seed",
        "controller",
        "condition",
    }:
        raise ValueError("Require engine, profile, seed, controller and condition")
    if value["engine"] != "simglucose" or value["controller"] not in ("basal_bolus", "pid"):
        raise ValueError(
            "simglucose supports native basal_bolus and pid only; LT1 controllers are separate"
        )
    if value["condition"] not in tuple("ABCD"):
        raise ValueError("Unsupported condition")
    profile = value["profile"]
    dev = profile in ("adult#001", "adult#002")
    if not dev and profile not in tuple(f"adult#{i:03}" for i in range(3, 11)):
        raise ValueError("Unsupported adult virtual profile")
    seeds = (101, 102) if dev else range(1, 11)
    if type(value["seed"]) is not int or value["seed"] not in seeds:
        raise ValueError("Seed does not belong to the declared development/evaluation split")
    return value


def evaluation_gate(cfg, plan_path):
    if cfg["profile"] in ("adult#001", "adult#002"):
        return
    if plan_path is None or not Path(plan_path).is_file():
        raise ValueError("Evaluation requires a frozen plan after development verification")
    from .study import validate_plan

    plan = validate_plan(Path(plan_path), execution=True)
    if cfg not in [case["config"] for case in plan["cases"]]:
        raise ValueError("Evaluation case is not in the frozen plan")


def read_run(output):
    snapshot = Snapshot(output)
    m = strict_json(snapshot.read("manifest.json"))
    if not isinstance(m, dict) or m.get("schema") != "opent1d.simglucose-m2/1" or "config" not in m:
        raise ValueError("Unsupported M2 simglucose manifest")
    status = m.get("status")
    if status not in ("started", "completed", "terminated", "failed", "interrupted"):
        raise ValueError("Unsupported run status")
    count = m.get("completed_rows")
    if type(count) is not int or count < 0:
        raise ValueError("Invalid row count")
    sealed = status != "started"
    hashes(m.get("files_sha256"), "artifact inventory")
    if sealed:
        number(m.get("elapsed_seconds"), "runtime", 0)
        files = m["files_sha256"]
        if not {"trace.jsonl", "native.jsonl", "run.log"} <= files.keys():
            raise ValueError("Missing required artifacts")
        actual = {
            p.name
            for p in Path(output).iterdir()
            if p.name != "manifest.json" and not p.name.endswith(".tmp")
        }
        if actual != set(files):
            raise ValueError("Missing or uninventoried artifact")
        for name, expected in files.items():
            if hashlib.sha256(snapshot.read(name)).hexdigest() != expected:
                raise ValueError(f"Artifact hash mismatch: {name}")
    if status in ("failed", "interrupted", "terminated"):
        text_value(m.get("error"), "failure reason")
    cfg = m["config"]
    if cfg is not None:
        validate_config(cfg)
        if strict_json(snapshot.read("config.json")) != cfg:
            raise ValueError("Configuration ownership differs")
        hashes(m.get("source_sha256"), "source provenance", source_hashes())
        for path in (
            "experiments/m2/simglucose.py",
            "experiments/m1/contracts.py",
            "experiments/m1/metrics.py",
        ):
            if m["source_sha256"][path] != source_hashes()[path]:
                raise ValueError("Use the recorded analysis revision")
        if not isinstance(m.get("revision"), str) or not REVISION.fullmatch(m["revision"]):
            raise ValueError("Missing implementation revision")
        if type(m.get("worktree_dirty")) is not bool:
            raise ValueError("Invalid dirty-worktree flag")
        if hashlib.sha256(snapshot.read("protocol.md")).hexdigest() != digest(
            ROOT / "docs/research/m2-protocol.md"
        ):
            raise ValueError("Unsupported M2 protocol")
        for name in ("uv.lock", "protocol-settings.json", "baseline.json"):
            if (
                snapshot.read("simglucose-" + name)
                != (ROOT / "experiments/m0/simglucose" / name).read_bytes()
            ):
                raise ValueError("Unsupported M1 numerical context")
        if cfg["profile"] not in ("adult#001", "adult#002"):
            from .study import validate_plan_data

            plan = strict_json(snapshot.read("evaluation-plan.json"))
            validate_plan_data(plan)
            if cfg not in [c["config"] for c in plan["cases"]]:
                raise ValueError("Run not in frozen evaluation schedule")
    rows, fragment = [], False
    for line in snapshot.read("trace.jsonl").splitlines(keepends=True):
        if not line.endswith(b"\n"):
            if status in ("completed", "terminated"):
                raise ValueError("Truncated successful trace")
            fragment = True
            break
        rows.append(Row(**strict_json(line)))
    duration = validate_rows(rows)
    if sealed and len(rows) != count:
        raise ValueError("Manifest row count differs")
    native = None
    if rows or status in ("completed", "terminated"):
        if cfg is None:
            raise ValueError("Trace without owning configuration")
        native = strict_json(snapshot.read("runtime.json"))
        if native.get("config") != cfg:
            raise ValueError("Native configuration differs")
        validate_native_provenance(native)
        for key in ("python", "platform", "architecture"):
            text_value(native.get(key), "native " + key)
        if native["upstream_revision"] != "a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc":
            raise ValueError("Unsupported upstream revision")
        initial = strict_json(snapshot.read("initial.json"))
        if set(initial) != {
            "time_min",
            "glucose_mg_dl",
            "cgm_mg_dl",
            "true_meal_g",
            "delivered_u_min",
            "terminal",
        }:
            raise ValueError("Invalid initial snapshot")
        for key in ("glucose_mg_dl", "cgm_mg_dl", "true_meal_g", "delivered_u_min", "time_min"):
            number(initial[key], key, 0)
        if (
            initial["time_min"] != 0
            or initial["terminal"] is not False
            or initial["true_meal_g"] != 0
            or initial["delivered_u_min"] != 0
        ):
            raise ValueError("Invalid initial point semantics")
        held = (0, initial["cgm_mg_dl"])
        for row in rows:
            if (row.controller_source_min, row.controller_cgm_mg_dl) != held:
                raise ValueError("Controller saw an unavailable observation")
            if row.sensor_available:
                held = (row.end_min, row.raw_cgm_mg_dl)
            fraction = (
                1 if row.start_min < 1440 else {"A": 1, "B": 0, "C": 0.5, "D": 1}[cfg["condition"]]
            )
            if row.announced_g != dict(MEALS).get(
                row.start_min, 0
            ) * fraction or row.true_meal_g != dict(MEALS).get(row.start_min, 0):
                raise ValueError("Meal/announcement differs from M1 conventions")
            if row.sensor_available != (
                not (cfg["condition"] == "D" and 2160 <= row.end_min < 2190)
            ):
                raise ValueError("Sensor masking differs")
            if row.terminal != (row.glucose_mg_dl < 10 or row.glucose_mg_dl > 600):
                raise ValueError("Native terminal flag differs")
    warnings_data = snapshot.read("warnings.json", optional=True)
    if warnings_data is not None:
        validate_warnings(strict_json(warnings_data))
    if status in ("completed", "terminated"):
        snapshot.read("native-diagnostic.csv")
        if warnings_data is None or strict_json(snapshot.read("result.json")) != {"status": status}:
            raise ValueError("Missing completion evidence")
        if (status == "completed" and (duration != 2880 or rows[-1].terminal)) or (
            status == "terminated" and (not rows or not rows[-1].terminal)
        ):
            raise ValueError("False completion/termination")
    snapshot.verify_unchanged()
    return {
        "manifest": m,
        "runtime": native,
        "metrics": summarize(rows),
        "input_sha256": snapshot.sha256(),
        "unsealed": not sealed,
        "discarded_trailing_fragment": fragment,
    }
