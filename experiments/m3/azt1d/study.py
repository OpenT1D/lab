"""Frozen AZT1D study orchestration; native fitting lives in a separate worker."""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from experiments.m0.simglucose.recording import RunInterrupted, interruption
from experiments.m3.workflow import failure

from .common import (
    PHASES,
    ROOT,
    SCHEMA,
    digest,
    finite,
    outside_repository,
    provenance,
    read,
    require,
    save,
    validate_provenance,
)
from .service import validate_intake


def reference(folder):
    return {
        "folder": str(Path(folder).resolve()),
        "sha256": digest((Path(folder) / "conversion.json").read_bytes()),
    }


def metadata(ref, phase, kind, person):
    """Read only intake/receipt metadata, never glucose observations."""
    require(
        isinstance(ref, dict) and set(ref) == {"folder", "sha256"}, "Invalid conversion reference"
    )
    folder = Path(ref["folder"])
    require(folder.is_absolute(), "Absolute conversion path required")
    if kind == "human":
        outside_repository(folder)
    receipt, sha = read(folder / "conversion.json")
    require(sha == ref["sha256"], "Conversion receipt changed")
    intake, intake_sha = read(folder / "intake.json")
    validate_intake(intake)
    require(intake_sha == receipt.get("intake_sha256"), "Intake changed")
    require(
        all(receipt.get(k) == intake.get(k) for k in ("kind", "person", "phase", "source_sha256")),
        "Conversion identity changed",
    )
    require(
        (intake["kind"], intake["person"], intake["phase"]) == (kind, person, phase),
        "Unexpected conversion identity",
    )
    validate_provenance(receipt.get("provenance"))
    state, _ = read(folder / "status.json")
    require(
        state.get("status") == "completed" and state.get("kind") == kind, "Incomplete conversion"
    )
    return intake


def evaluation_metadata(ref, kind, person):
    require(
        isinstance(ref, dict) and set(ref) == {"intake_reference", "origins_us"},
        "Invalid evaluation descriptor",
    )
    pointer = ref["intake_reference"]
    require(
        isinstance(pointer, dict) and set(pointer) == {"file", "sha256"}, "Invalid intake reference"
    )
    path = Path(pointer["file"])
    require(path.is_absolute(), "Absolute intake path required")
    if kind == "human":
        outside_repository(path)
    intake, sha = read(path)
    require(sha == pointer["sha256"], "Evaluation descriptor changed")
    validate_intake(intake)
    require(
        (intake["kind"], intake["person"], intake["phase"]) == (kind, person, "evaluation"),
        "Wrong evaluation identity",
    )
    times = ref["origins_us"]
    require(
        isinstance(times, list) and all(type(t) is int for t in times),
        "Registered schedule required",
    )
    require(
        times == sorted(set(times))
        and all(intake["start_us"] <= t < intake["end_us"] for t in times),
        "Invalid evaluation schedule",
    )
    require(0 < len(times) <= intake["row_stop"] - intake["row_start"], "Invalid origin count")
    return intake


def validate_registry(registry):
    require(isinstance(registry, dict) and registry.get("schema") == SCHEMA, "Wrong study schema")
    kind = registry.get("kind")
    require(kind in ("human", "synthetic"), "Explicit study kind required")
    require(
        isinstance(registry.get("people"), list) and registry["people"], "Study people required"
    )
    require(
        isinstance(registry.get("ledger"), str) and Path(registry["ledger"]).is_absolute(),
        "Absolute ledger path required",
    )
    if kind == "human":
        outside_repository(registry["ledger"])
        require(len(registry["people"]) == 20, "Preserve twenty study participants")
        reviews = registry.get("reviews", {})
        for key in (
            "authorized_fitting",
            "authorized_evaluation",
            "overlap_reviewed",
            "prior_access_disclosed",
        ):
            require(reviews.get(key) is True, "Study review incomplete")
        require(
            isinstance(reviews.get("reference"), str) and reviews["reference"].strip(),
            "Study authorization reference required",
        )
    identities, ids, sources = [], set(), set()
    for person in registry["people"]:
        pid = person["id"]
        require(pid not in ids, "Repeated study participant")
        ids.add(pid)
        require(Path(person["source"]).is_absolute(), "Absolute source path required")
        if kind == "human":
            outside_repository(person["source"])
        requests = {p: metadata(person[p], p, kind, pid) for p in PHASES[:2]}
        requests["evaluation"] = evaluation_metadata(person["evaluation"], kind, pid)
        native = requests["development"]["source_sha256"]
        require(native not in sources, "Repeated source across people")
        sources.add(native)
        for req in requests.values():
            require(req["source_sha256"] == native, "Cross-phase source mismatch")
            require(
                req["origin_local"] == requests["development"]["origin_local"]
                and req["policy"] == requests["development"]["policy"],
                "Cross-phase convention mismatch",
            )
            if kind == "human":
                from .service import human_metadata_gate

                human_metadata_gate(req, person["source"], registry["ledger"], registry["ledger"])
        first, middle, last = (requests[p] for p in PHASES)
        total = last["end_us"]
        require(
            first["start_us"] == 0
            and first["end_us"] == middle["start_us"]
            and middle["end_us"] == last["start_us"],
            "Nonadjacent phases",
        )
        # Fractional boundaries are represented by integer ceilings, never rounded timestamps.
        require(
            first["end_us"] == (3 * total + 4) // 5 and middle["end_us"] == (4 * total + 4) // 5,
            "Expected elapsed 60/20/20 split",
        )
        require(
            first["row_start"] == 1
            and first["row_stop"] == middle["row_start"]
            and middle["row_stop"] == last["row_start"],
            "Nonadjacent native slices",
        )
        identities.append(
            {
                "id": pid,
                "source_sha256": native,
                "phases": {
                    p: {k: requests[p][k] for k in ("start_us", "end_us", "row_start", "row_stop")}
                    for p in PHASES
                },
                "policy": first["policy"],
                "allocation": first.get("allocation_reference"),
                "evaluation_origins_us": person["evaluation"]["origins_us"],
            }
        )
    if kind == "human":
        allocations = {i["allocation"]["sha256"] for i in identities}
        require(len(allocations) == 1, "Study allocation differs")
    return {"schema": SCHEMA, "kind": kind, "people": identities}


def freeze(registry_path, output):
    registry, sha = read(registry_path)
    identity = validate_registry(registry)
    if registry["kind"] == "human":
        outside_repository(registry_path, output)
    prov = provenance()
    if registry["kind"] == "human":
        require(not prov["dirty"], "Commit reviewed sources before human freeze")
    registry_raw = Path(registry_path).read_bytes()
    require(digest(registry_raw) == sha, "Registry changed during freeze")
    plan = {
        "schema": SCHEMA,
        "kind": registry["kind"],
        "registry": registry,
        "registry_sha256": sha,
        "registry_source_utf8": registry_raw.decode("utf-8"),
        "identity": identity,
        "provenance": prov,
    }
    with private_directory(output):
        save(Path(output) / "plan.json", plan)
    return plan


class private_directory:
    def __init__(self, path):
        self.path = Path(path)

    def __enter__(self):
        self.mask = os.umask(0o077)
        try:
            self.path.mkdir(parents=True, exist_ok=False)
        except BaseException:
            os.umask(self.mask)
            raise
        return self.path

    def __exit__(self, *_):
        os.umask(self.mask)


def plan_read(path, *, verify_inputs=True):
    plan, sha = read(path)
    require(
        plan.get("schema") == SCHEMA and plan.get("kind") in ("human", "synthetic"), "Invalid plan"
    )
    validate_provenance(plan.get("provenance"))
    require(plan["kind"] == plan["registry"]["kind"], "Plan kind mismatch")
    if plan["kind"] == "human":
        outside_repository(path)
        require(plan["provenance"]["dirty"] is False, "Dirty human freeze")
    if verify_inputs:
        require(
            validate_registry(plan["registry"]) == plan["identity"], "Frozen identities changed"
        )
    return plan, sha


def init_ledger(plan_path):
    from .ledger import create_ledger

    plan, _ = plan_read(plan_path)
    anchor_path = Path(plan_path).parent / "ledger-anchor.json"
    require(not anchor_path.exists(), "Ledger anchor already exists")
    evidence = create_ledger(
        plan["registry"]["ledger"], plan["identity"], plan["registry"]["prior_access"], plan["kind"]
    )
    save(anchor_path, evidence)
    return evidence


def seal(folder, state):
    state["files"] = {
        str(p.relative_to(folder)): digest(p.read_bytes())
        for p in sorted(folder.rglob("*"))
        if p.is_file() and p != folder / "state.json" and not p.name.endswith(".tmp")
    }
    save(folder / "state.json", state)


def supervise(command, folder, timeout):
    with private_directory(folder) as folder:
        state = {"schema": SCHEMA, "status": "started", "provenance": provenance()}
        save(folder / "state.json", state)
        (folder / "trace.jsonl").touch()
        child, primary = None, None
        started = time.monotonic()
        try:
            finite(timeout, "deadline", 0)
            require(timeout > 0, "Positive deadline required")
            with interruption(timeout, arm_timer=False), (folder / "worker.log").open("wb") as log:
                child = subprocess.Popen(
                    command + [str(folder)],
                    cwd=ROOT,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                    env=dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1"),
                )
                code = child.wait(timeout=max(0.0, timeout - (time.monotonic() - started)))
            require(code == 0, "Worker exit/status conflict")
            result, _ = read(folder / "result.json")
            require(result.get("status") == "completed", "Worker exit/status conflict")
            state["status"] = "completed"
        except BaseException as error:
            primary = error
            if child is not None and child.poll() is None:
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                child.wait()
            state.update(
                status="interrupted"
                if isinstance(error, (RunInterrupted, KeyboardInterrupt, subprocess.TimeoutExpired))
                else "failed",
                error=failure(error),
            )
        finally:
            state["elapsed_seconds"] = time.monotonic() - started
            try:
                seal(folder, state)
            except BaseException:
                if primary is None:
                    raise
        if primary is not None:
            raise primary
    return state


def fit_plan(plan_path, output, timeout=120):
    from .ledger import verify_evidence

    finite(timeout, "deadline", 0)
    require(timeout > 0, "Positive deadline required")
    plan, sha = plan_read(plan_path)
    if plan["kind"] == "human":
        outside_repository(output)
    anchor, _ = read(Path(plan_path).parent / "ledger-anchor.json")
    context = verify_evidence(plan["registry"]["ledger"], plan["identity"], anchor)
    require(context["event_count"] == 0, "Evaluation access already recorded; do not refit")
    command = [
        str(ROOT / "experiments/m3/runtime/.venv/bin/python"),
        "-m",
        "experiments.m3.azt1d.worker",
        "fit",
        str(Path(plan_path).resolve()),
    ]
    supervise(command, output, timeout)
    output = Path(output)
    state, _ = read(output / "state.json")
    try:
        from experiments.m3.estimator import validate_model

        model, model_sha = read(output / "model.json")
        validate_model(model)
        require(
            verify_evidence(plan["registry"]["ledger"], plan["identity"], anchor)["event_count"]
            == 0,
            "Evaluation accessed while fitting",
        )
        frozen = {
            "schema": SCHEMA,
            "stage": "learned",
            "plan_sha256": sha,
            "model_sha256": model_sha,
            "validation_sha256": digest((output / "trace.jsonl").read_bytes()),
            "result_sha256": digest((output / "result.json").read_bytes()),
            "inputs_sha256": digest((output / "inputs.json").read_bytes()),
            "ledger_anchor": anchor,
            "provenance": provenance(),
        }
        save(output / "freeze.json", frozen)
        seal(output, state)
    except BaseException as error:
        state.update(status="failed", error=failure(error))
        seal(output, state)
        raise
    return frozen


def learned_read(plan_path, fit_path):
    from .analysis import verify_inventory, verify_learned
    from .ledger import verify_evidence

    plan, plan_sha = plan_read(plan_path)
    fit_path = Path(fit_path)
    if plan["kind"] == "human":
        outside_repository(fit_path)
    state = verify_inventory(fit_path)
    require(state["status"] == "completed", "Incomplete fit")
    frozen, freeze_sha = read(fit_path / "freeze.json")
    validate_provenance(frozen.get("provenance"))
    require(
        frozen.get("schema") == SCHEMA
        and frozen.get("stage") == "learned"
        and frozen.get("plan_sha256") == plan_sha,
        "Learned freeze mismatch",
    )
    for name, key in (
        ("model.json", "model_sha256"),
        ("trace.jsonl", "validation_sha256"),
        ("result.json", "result_sha256"),
        ("inputs.json", "inputs_sha256"),
    ):
        require(digest((fit_path / name).read_bytes()) == frozen[key], "Learned artifact changed")
    verify_evidence(plan["registry"]["ledger"], plan["identity"], frozen["ledger_anchor"])
    verify_learned(plan_path, fit_path)
    return plan, frozen, freeze_sha


def authorize_evaluation(intake, input_path, authorization, event):
    from .ledger import record_access

    require(
        isinstance(authorization, dict) and set(authorization) == {"plan", "fit"},
        "Human evaluation conversion is not enabled without a learned freeze",
    )
    plan, frozen, freeze_sha = learned_read(authorization["plan"], authorization["fit"])
    require(plan["kind"] == intake["kind"], "Evaluation kind differs")
    selected = [p for p in plan["registry"]["people"] if p["id"] == intake["person"]]
    require(len(selected) == 1, "Unplanned evaluation participant")
    person = selected[0]
    expected = evaluation_metadata(person["evaluation"], plan["kind"], person["id"])
    require(
        intake == expected and Path(input_path).resolve() == Path(person["source"]).resolve(),
        "Evaluation differs from frozen request",
    )
    return record_access(
        plan["registry"]["ledger"], plan["identity"], freeze_sha, event, person["id"]
    )


def run_study(plan_path, fit_path, output, timeout=120):
    from .analysis import reconstruct
    from .ledger import record_access, snapshot_ledger
    from .service import normalize

    finite(timeout, "deadline", 0)
    require(timeout > 0, "Positive deadline required")
    plan, frozen, freeze_sha = learned_read(plan_path, fit_path)
    if plan["kind"] == "human":
        outside_repository(output)
    fit_path, output = Path(fit_path), Path(output)
    with private_directory(output):
        for name in ("plan.json",):
            (output / name).write_bytes(Path(plan_path).read_bytes())
        fit_state, _ = read(fit_path / "state.json")
        for name in (*fit_state["files"], "state.json"):
            require(Path(name).name == name, "Unexpected fit artifact layout")
            (output / ("fit-" + name)).write_bytes((fit_path / name).read_bytes())
            if name != "state.json":
                require(
                    digest((output / ("fit-" + name)).read_bytes()) == fit_state["files"][name],
                    "Fit changed while copying artifacts",
                )
        cases = [
            {"id": p["id"], "origins_us": p["evaluation"]["origins_us"], "status": "not_attempted"}
            for p in plan["registry"]["people"]
        ]
        study = {
            "schema": SCHEMA,
            "kind": plan["kind"],
            "status": "started",
            "cases": cases,
            "freeze_sha256": freeze_sha,
            "provenance": provenance(),
        }
        save(output / "study.json", study)
        try:
            for person, case in zip(plan["registry"]["people"], cases, strict=True):
                case_dir = output / person["id"]
                case_dir.mkdir(mode=0o700)
                try:
                    req = evaluation_metadata(person["evaluation"], plan["kind"], person["id"])
                    if plan["kind"] == "synthetic":
                        evidence = authorize_evaluation(
                            req,
                            person["source"],
                            {"plan": plan_path, "fit": fit_path},
                            "before_normalization",
                        )
                        save(case_dir / "normalization-access.json", evidence)
                    normalize(
                        person["source"],
                        person["evaluation"]["intake_reference"]["file"],
                        case_dir / "conversion",
                        evaluation_authorization={"plan": plan_path, "fit": fit_path},
                    )
                    if plan["kind"] == "human":
                        receipt, _ = read(case_dir / "conversion/conversion.json")
                        save(case_dir / "normalization-access.json", receipt["evaluation_access"])
                    evidence = record_access(
                        plan["registry"]["ledger"],
                        plan["identity"],
                        freeze_sha,
                        "before_execution",
                        person["id"],
                    )
                    save(case_dir / "execution-access.json", evidence)
                    command = [
                        sys.executable,
                        "-m",
                        "experiments.m3.azt1d.worker",
                        "evaluate",
                        str(output.resolve()),
                        person["id"],
                    ]
                    supervise(command, case_dir / "run", timeout)
                    case["status"] = "completed"
                except BaseException as error:
                    case["error"] = failure(error)
                    case["status"] = (
                        "interrupted"
                        if isinstance(
                            error, (RunInterrupted, KeyboardInterrupt, subprocess.TimeoutExpired)
                        )
                        else "failed"
                    )
                    interrupted = case["status"] == "interrupted"
                    worker_state = case_dir / "run/state.json"
                    if worker_state.exists():
                        case["status"] = read(worker_state)[0]["status"]
                    if interrupted or not isinstance(error, Exception):
                        raise
                finally:
                    save(output / "study.json", study)
            study["status"] = (
                "completed"
                if all(c["status"] == "completed" for c in cases)
                else "finished_with_failures"
            )
        except BaseException as error:
            study.update(
                status="interrupted"
                if isinstance(error, (RunInterrupted, KeyboardInterrupt, subprocess.TimeoutExpired))
                else "failed",
                error=failure(error),
            )
            raise
        finally:
            save(output / "study.json", study)
            (output / "ledger.jsonl").write_bytes(
                snapshot_ledger(
                    plan["registry"]["ledger"], plan["identity"], frozen["ledger_anchor"]
                )
            )
            save(
                output / "inventory.json",
                {
                    str(p.relative_to(output)): digest(p.read_bytes())
                    for p in sorted(output.rglob("*"))
                    if p.is_file() and p != output / "inventory.json"
                },
            )
        try:
            report = reconstruct(output)
            save(output / "report.json", report)
        except BaseException as error:
            study.update(status="failed", error=failure(error))
            save(output / "study.json", study)
            save(
                output / "inventory.json",
                {
                    str(p.relative_to(output)): digest(p.read_bytes())
                    for p in sorted(output.rglob("*"))
                    if p.is_file() and p.name != "report.json" and p != output / "inventory.json"
                },
            )
            raise
    return report
