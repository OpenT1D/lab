"""Metadata freeze and supervised external evaluation; never fit a model."""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from experiments.m0.simglucose.recording import RunInterrupted, interruption
from experiments.m3.azt1d.analysis import _Snapshot
from experiments.m3.azt1d.data import integer_time, validate_observations
from experiments.m3.azt1d.ledger import (
    create_ledger,
    record_access,
    snapshot_ledger,
    verify_evidence,
)
from experiments.m3.azt1d.study import private_directory
from experiments.m3.common import ID, ROOT, SHA, digest, encoded, finite, read, require, save
from experiments.m3.workflow import failure

from .common import FORMAT, PROTOCOL, RULES, SCHEMA, absolute, provenance, validate_provenance
from .model import load_model


def registry_check(registry):
    require(
        isinstance(registry, dict)
        and set(registry) == {"schema", "kind", "source", "ledger", "prior_access", "people"}
        and registry["schema"] == SCHEMA,
        "Invalid external registry",
    )
    # An unverified native provider format must not become authorized via Boolean flags.
    require(
        registry["kind"] == "synthetic",
        "Human external intake is not implemented; a reviewed native adapter is required",
    )
    source = registry["source"]
    require(
        isinstance(source, dict)
        and set(source) == {"id", "reference", "format"}
        and source["format"] == FORMAT
        and all(isinstance(source[k], str) and source[k].strip() for k in ("id", "reference")),
        "External source and normalized format must be explicit",
    )
    absolute(registry["ledger"])
    prior = registry["prior_access"]
    require(
        isinstance(prior, dict)
        and set(prior) == {"reviewed", "status", "reference"}
        and prior["reviewed"] is True
        and prior["status"] == "present"
        and isinstance(prior["reference"], str)
        and prior["reference"].strip(),
        "Prior generation/conversion of normalized inputs must be disclosed",
    )
    people = registry["people"]
    require(isinstance(people, list) and people, "All planned external people are required")
    identifiers, hashes, paths = set(), set(), set()
    for person in people:
        require(
            isinstance(person, dict) and set(person) == {"id", "input", "bounds_us", "origins_us"},
            "External people have evaluation metadata only",
        )
        pid = person["id"]
        require(
            isinstance(pid, str)
            and ID.fullmatch(pid)
            and pid not in identifiers
            and pid != "model",
            "Invalid or reserved external alias",
        )
        identifiers.add(pid)
        ref = person["input"]
        require(
            isinstance(ref, dict) and set(ref) == {"file", "sha256"}, "Input reference required"
        )
        path = Path(os.path.normpath(absolute(ref["file"])))
        require(path not in paths, "Repeated external input path")
        paths.add(path)
        require(
            isinstance(ref["sha256"], str)
            and SHA.fullmatch(ref["sha256"])
            and ref["sha256"] not in hashes,
            "Duplicate or invalid external input identity",
        )
        hashes.add(ref["sha256"])
        bounds, origins = person["bounds_us"], person["origins_us"]
        require(isinstance(bounds, list) and len(bounds) == 2, "External bounds required")
        start, end = map(integer_time, bounds)
        require(end > start, "Empty external interval")
        require(isinstance(origins, list) and origins, "Registered external origins required")
        require(
            all(start <= integer_time(t) < end for t in origins), "Origin outside external period"
        )
        require(origins == sorted(set(origins)), "Duplicate or unordered external origins")
    return {
        "schema": SCHEMA,
        "protocol": PROTOCOL,
        "kind": registry["kind"],
        "source": source,
        "rules": RULES,
        "people": [
            {k: p[k] for k in ("id", "bounds_us", "origins_us")}
            | {"source_sha256": p["input"]["sha256"]}
            for p in people
        ],
    }


def copy_bundle(source, destination):
    _, _, sha = load_model(source)
    destination.mkdir(mode=0o700)
    with _Snapshot(source) as snapshot:
        for name in sorted(snapshot.names):
            (destination / name).write_bytes(snapshot.read(name))
        snapshot.verify()
    require(load_model(destination)[2] == sha, "Model bundle changed while copying")
    return sha


def model_cohort_check(registry, origin):
    require(origin["kind"] == registry["kind"], "Human/synthetic model kind differs")
    require(
        not set(origin["source_people"]).intersection(p["id"] for p in registry["people"]),
        "External aliases overlap the source cohort",
    )
    source_hashes = {p["source_sha256"] for p in origin["source_study_identity"]["people"]}
    require(
        not source_hashes.intersection(p["input"]["sha256"] for p in registry["people"]),
        "External input repeats a source-cohort file",
    )


def freeze(registry_path, model_bundle, output):
    registry, _ = read(registry_path)
    identity = registry_check(registry)  # This never opens an observation file.
    _, origin, model_sha = load_model(model_bundle)
    model_cohort_check(registry, origin)
    with private_directory(output) as folder:
        require(copy_bundle(model_bundle, folder / "model") == model_sha, "Export changed")
        plan = {
            "schema": SCHEMA,
            "protocol": PROTOCOL,
            "kind": registry["kind"],
            "registry": registry,
            "registry_sha256": digest(encoded(registry)),
            "identity": identity,
            "rules": RULES,
            "model_bundle_sha256": model_sha,
            "provenance": provenance(),
        }
        save(folder / "plan.json", plan)
    return plan


def validate_plan(plan):
    require(
        isinstance(plan, dict)
        and set(plan)
        == {
            "schema",
            "protocol",
            "kind",
            "registry",
            "registry_sha256",
            "identity",
            "rules",
            "model_bundle_sha256",
            "provenance",
        },
        "Invalid external freeze",
    )
    require(
        plan["schema"] == SCHEMA and plan["protocol"] == PROTOCOL and plan["rules"] == RULES,
        "External conventions changed",
    )
    require(
        plan["kind"] == plan["registry"]["kind"]
        and plan["identity"] == registry_check(plan["registry"]),
        "External roster or identity changed",
    )
    require(
        plan["registry_sha256"] == digest(encoded(plan["registry"])),
        "Canonical external registry identity changed",
    )
    for key in ("registry_sha256", "model_bundle_sha256"):
        require(
            isinstance(plan[key], str) and SHA.fullmatch(plan[key]),
            "Invalid external artifact identity",
        )
    validate_provenance(plan["provenance"])


def plan_read(path):
    plan, sha = read(path)
    validate_plan(plan)
    model, origin, bundle_sha = load_model(Path(path).parent / "model")
    require(
        bundle_sha == plan["model_bundle_sha256"] and origin["kind"] == plan["kind"],
        "Frozen model/scaler changed",
    )
    model_cohort_check(plan["registry"], origin)
    return plan, sha, model


def init_ledger(plan_path):
    plan, _, _ = plan_read(plan_path)
    anchor_path = Path(plan_path).parent / "ledger-anchor.json"
    require(not anchor_path.exists(), "External ledger already initialized")
    evidence = create_ledger(
        plan["registry"]["ledger"], plan["identity"], plan["registry"]["prior_access"], plan["kind"]
    )
    save(anchor_path, evidence)
    return evidence


def observations(raw, person):
    from experiments.m1.artifacts import strict_json

    require(digest(raw) == person["input"]["sha256"], "External observation bytes changed")
    document = strict_json(raw)
    rows = validate_observations(document, person["id"], *person["bounds_us"])
    require(sorted(rows) == person["origins_us"], "External schedule differs from freeze")
    return rows


def access_check(plan, plan_sha, anchor, receipt, person, event, *, raw_ledger=None):
    from experiments.m3.azt1d.ledger import verify_snapshot

    check = (
        (lambda evidence: verify_snapshot(raw_ledger, plan["identity"], evidence))
        if raw_ledger is not None
        else (
            lambda evidence: verify_evidence(plan["registry"]["ledger"], plan["identity"], evidence)
        )
    )
    require(
        anchor.get("event") == "created" and anchor.get("sequence") == 0,
        "External ledger anchor is not its creation",
    )
    context = check(anchor)
    require(
        context["kind"] == plan["kind"]
        and context["prior_access"] == plan["registry"]["prior_access"],
        "External access disclosure changed",
    )
    check(receipt)
    require(
        receipt["freeze_sha256"] == plan_sha
        and receipt["person"] == person
        and receipt["event"] == event
        and receipt["phase"] == "evaluation",
        "Wrong external access receipt",
    )
    return context


def seal(folder, state):
    state["files"] = {
        p.name: digest(p.read_bytes())
        for p in sorted(folder.iterdir())
        if p.is_file() and p.name != "state.json"
    }
    save(folder / "state.json", state)


def supervise(command, folder, timeout):
    with private_directory(folder) as folder:
        state = {"schema": SCHEMA, "status": "started", "provenance": provenance()}
        save(folder / "state.json", state)
        (folder / "trace.jsonl").touch()
        child, error_saved = None, None
        started = time.monotonic()
        try:
            with interruption(timeout, arm_timer=False), (folder / "worker.log").open("wb") as log:
                child = subprocess.Popen(
                    command + [str(folder)],
                    cwd=ROOT,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
                code = child.wait(timeout=max(0.0, timeout - (time.monotonic() - started)))
            require(
                code == 0 and read(folder / "result.json")[0].get("status") == "completed",
                "External worker failed",
            )
            state["status"] = "completed"
        except BaseException as error:
            error_saved = error
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
            seal(folder, state)
        if error_saved is not None:
            raise error_saved


def inventory(folder):
    with _Snapshot(folder) as snapshot:
        hashes = {
            name: digest(snapshot.read(name))
            for name in sorted(snapshot.names)
            if name not in ("inventory.json", "report.json")
        }
        snapshot.verify()
    save(folder / "inventory.json", hashes)


def run_study(plan_path, output, timeout=120):
    finite(timeout, "deadline", 0)
    require(timeout > 0, "Positive external deadline required")
    plan, plan_sha, _ = plan_read(plan_path)
    anchor, _ = read(Path(plan_path).parent / "ledger-anchor.json")
    require(
        anchor.get("event") == "created" and anchor.get("sequence") == 0,
        "External ledger anchor is not its creation",
    )
    verify_evidence(plan["registry"]["ledger"], plan["identity"], anchor)
    output = Path(output)
    with private_directory(output):
        with _Snapshot(Path(plan_path).parent, only={Path(plan_path).name}) as snapshot:
            raw_plan = snapshot.read(Path(plan_path).name)
            require(digest(raw_plan) == plan_sha, "Plan changed before execution")
            (output / "plan.json").write_bytes(raw_plan)
            snapshot.verify()
        save(output / "ledger-anchor.json", anchor)
        require(
            copy_bundle(Path(plan_path).parent / "model", output / "model")
            == plan["model_bundle_sha256"],
            "Model changed before execution",
        )
        cases = [{"id": p["id"], "status": "not_attempted"} for p in plan["registry"]["people"]]
        study = {
            "schema": SCHEMA,
            "status": "started",
            "plan_sha256": plan_sha,
            "cases": cases,
            "provenance": provenance(),
        }
        save(output / "study.json", study)
        try:
            for person, case in zip(plan["registry"]["people"], cases, strict=True):
                folder = output / person["id"]
                try:
                    folder.mkdir(mode=0o700)
                    receipt = record_access(
                        plan["registry"]["ledger"],
                        plan["identity"],
                        plan_sha,
                        "before_normalization",
                        person["id"],
                    )
                    save(folder / "input-access.json", receipt)
                    access_check(
                        plan, plan_sha, anchor, receipt, person["id"], "before_normalization"
                    )
                    source = Path(person["input"]["file"])
                    with _Snapshot(source.parent, only={source.name}) as snapshot:
                        raw = snapshot.read(source.name)
                        observations(raw, person)
                        snapshot.verify()
                    (folder / "observations.json").write_bytes(raw)
                    receipt = record_access(
                        plan["registry"]["ledger"],
                        plan["identity"],
                        plan_sha,
                        "before_execution",
                        person["id"],
                    )
                    save(folder / "execution-access.json", receipt)
                    supervise(
                        [
                            sys.executable,
                            "-m",
                            "experiments.m3.external.worker",
                            str(output.resolve()),
                            person["id"],
                        ],
                        folder / "run",
                        timeout,
                    )
                    case["status"] = "completed"
                except BaseException as error:
                    interrupted = isinstance(
                        error, (RunInterrupted, KeyboardInterrupt, subprocess.TimeoutExpired)
                    )
                    case.update(
                        status="interrupted" if interrupted else "failed", error=failure(error)
                    )
                    state_path = folder / "run/state.json"
                    if state_path.exists():
                        case["status"] = read(state_path)[0]["status"]
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
            try:
                (output / "ledger.jsonl").write_bytes(
                    snapshot_ledger(plan["registry"]["ledger"], plan["identity"], anchor)
                )
            except BaseException as error:
                save(output / "ledger-snapshot-failure.json", failure(error))
                raise
            finally:
                inventory(output)
        from .analysis import reconstruct

        report = reconstruct(output)
        save(output / "report.json", report)
        return report
