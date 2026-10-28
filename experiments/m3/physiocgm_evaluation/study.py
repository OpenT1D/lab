"""Prepare and supervise a private, explicitly authorized external assessment."""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from experiments.m0.simglucose.recording import RunInterrupted, interruption
from experiments.m1.artifacts import strict_json
from experiments.m3.azt1d.analysis import _hashes, _Snapshot
from experiments.m3.azt1d.ledger import (
    create_ledger,
    record_access,
    snapshot_ledger,
    verify_evidence,
)
from experiments.m3.azt1d.study import private_directory
from experiments.m3.common import ROOT, digest, encoded, finite, require
from experiments.m3.external import human_freeze as frozen
from experiments.m3.physiocgm.access import record_access as source_access
from experiments.m3.physiocgm.human import _private, _read_private, _state, _write
from experiments.m3.workflow import failure

from .common import (
    PROTOCOL,
    SCHEMA,
    access_check,
    identity,
    observations,
    prepared_members,
    provenance,
    read_plan,
    seal_output,
    validate_request,
    verify_prepared,
)


def _copy(source, target, names, hashes):
    """Copy only the verified member set and require the same byte identities."""
    with _Snapshot(source) as snapshot:
        require(names <= snapshot.names, "Source package incomplete")
        for name in sorted(names):
            raw = snapshot.read(name)
            require(digest(raw) == hashes[name], "Source changed during copying")
            _write(target / name, raw)
        snapshot.verify()


def prepare(request_path, output):
    request_raw = _read_private(request_path)
    request = strict_json(request_raw)
    validate_request(request)
    request_sha = digest(request_raw)
    source = _private(request["freeze"]["directory"], existing=True)
    require(
        digest(_read_private(source / "manifest.json")) == request["freeze"]["manifest_sha256"],
        "Requested freeze changed",
    )
    output = _private(output)
    with private_directory(output):
        _write(output / "request.json", request_raw)
        try:
            # Existing verifier logs before opening health snapshots, and checks member roles.
            frozen.verify(source, output / "verification")
            source_access(
                output / "copy-access.jsonl",
                request_sha,
                "before_bundle_read",
                "freeze",
                request["freeze"]["manifest_sha256"],
            )
            raw_manifest = _read_private(source / "manifest.json")
            require(digest(raw_manifest) == request["freeze"]["manifest_sha256"], "Freeze changed")
            hashes = _hashes(strict_json(raw_manifest)["files"]) | {
                "manifest.json": digest(raw_manifest)
            }
            _copy(source, output / "freeze", set(hashes), hashes)
            registry = strict_json(_read_private(output / "freeze/registry.json"))
            original = strict_json(_read_private(output / "freeze/request.json"))
            study_identity = identity(registry, request["freeze"]["manifest_sha256"])
            ledger = output / "ledger.jsonl"
            anchor = create_ledger(ledger, study_identity, request["prior_access"], "human")
            _write(output / "ledger-anchor.json", encoded(anchor))
            prov = provenance()
            for name, sha in prov["sources"].items():
                raw = (ROOT / name).read_bytes()
                require(digest(raw) == sha, "Execution code changed during preparation")
                _write(output / "code" / name, raw)
            plan = {
                "schema": SCHEMA,
                "protocol": PROTOCOL,
                "kind": "human",
                "stage": "execution",
                "request_sha256": request_sha,
                "freeze_manifest_sha256": request["freeze"]["manifest_sha256"],
                "registry": registry,
                "identity": study_identity,
                "rules": frozen.RULES,
                "model_sha256": original["donor"]["model"]["sha256"],
                "donor_verification": frozen.VERIFICATION,
                "ledger": str(ledger),
                "provenance": prov,
            }
            _write(output / "plan.json", encoded(plan))
            read_plan(output / "plan.json")
            seal_output(output, exclude={"ledger.jsonl"})
            verify_prepared(output)
            return plan
        except BaseException as error:
            _write(output / "failure.json", encoded(failure(error)))
            raise


def seal(folder, state):
    with _Snapshot(folder) as snapshot:
        state["files"] = {
            name: digest(snapshot.read(name)) for name in snapshot.names if name != "state.json"
        }
        snapshot.verify()
    _state(folder / "state.json", state)


def supervise(command, folder, timeout):
    with private_directory(folder):
        state = {"schema": SCHEMA, "status": "started", "provenance": provenance()}
        _state(folder / "state.json", state)
        _write(folder / "trace.jsonl", b"")
        child, saved = None, None
        started = time.monotonic()
        try:
            with interruption(timeout, arm_timer=False):
                fd = os.open(folder / "worker.log", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, "wb") as log:
                    child = subprocess.Popen(
                        command + [str(folder)],
                        cwd=ROOT,
                        stdout=log,
                        stderr=subprocess.STDOUT,
                        start_new_session=True,
                    )
                    code = child.wait(timeout=max(0.0, timeout - (time.monotonic() - started)))
            require(
                code == 0
                and strict_json(_read_private(folder / "result.json"))["status"] == "completed",
                "Human external worker failed",
            )
            state["status"] = "completed"
        except BaseException as error:
            saved = error
            if child is not None and child.poll() is None:
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                child.wait()
            state.update(
                status="interrupted" if _interrupted(error) else "failed", error=failure(error)
            )
        finally:
            state["elapsed_seconds"] = time.monotonic() - started
            seal(folder, state)
        if saved is not None:
            raise saved


def _interrupted(error):
    return isinstance(error, (RunInterrupted, KeyboardInterrupt, subprocess.TimeoutExpired))


def inventory(folder):
    with _Snapshot(folder) as snapshot:
        hashes = {
            n: digest(snapshot.read(n))
            for n in sorted(snapshot.names)
            if n not in {"inventory.json", "report.json"}
        }
        snapshot.verify()
    _write(folder / "inventory.json", encoded(hashes))


def run(plan_path, output, timeout=120):
    finite(timeout, "deadline", 0)
    require(timeout > 0, "Positive deadline required")
    plan_path = _private(plan_path, existing=True)
    plan, plan_sha = read_plan(plan_path)
    prepared = plan_path.parent
    require(Path(plan["ledger"]) == prepared / "ledger.jsonl", "Use the original prepared ledger")
    anchor = strict_json(_read_private(prepared / "ledger-anchor.json"))
    verify_evidence(plan["ledger"], plan["identity"], anchor)
    output = _private(output)
    with private_directory(output):
        cases = [{"id": p["id"], "status": "not_attempted"} for p in plan["registry"]["people"]]
        state = {
            "schema": SCHEMA,
            "kind": "human",
            "status": "started",
            "plan_sha256": plan_sha,
            "cases": cases,
            "provenance": provenance(),
        }
        _state(output / "study.json", state)
        try:
            claim = {"schema": SCHEMA, "plan_sha256": plan_sha, "output": str(output)}
            # One durable claim shared across fresh output directories for this plan.
            _write(prepared / "execution-claim.json", encoded(claim))
            _write(output / "execution-claim.json", encoded(claim))
            receipt = record_access(
                plan["ledger"], plan["identity"], plan_sha, "before_normalization", "cohort"
            )
            _write(output / "source-access.json", encoded(receipt))
            access_check(plan, plan_sha, anchor, receipt, "cohort", "before_normalization")
            raw_manifest = _read_private(prepared / "manifest.json")
            hashes = _hashes(strict_json(raw_manifest)["files"]) | {
                "manifest.json": digest(raw_manifest)
            }
            require(set(hashes) == prepared_members(prepared), "Prepared membership changed")
            _copy(prepared, output / "prepared", set(hashes), hashes)
            # Verify the very copy used by workers, under its own durable receipt.
            frozen.verify(output / "prepared/freeze", output / "verification")
            verify_prepared(output / "prepared")
            for person, case in zip(plan["registry"]["people"], cases, strict=True):
                folder = output / person["id"]
                try:
                    folder.mkdir(mode=0o700)
                    first = record_access(
                        plan["ledger"],
                        plan["identity"],
                        plan_sha,
                        "before_normalization",
                        person["id"],
                    )
                    _write(folder / "input-access.json", encoded(first))
                    access_check(
                        plan, plan_sha, anchor, first, person["id"], "before_normalization"
                    )
                    raw = _read_private(output / "prepared/freeze" / person["input"])
                    observations(raw, person)
                    _write(folder / "observations.json", raw)
                    second = record_access(
                        plan["ledger"], plan["identity"], plan_sha, "before_execution", person["id"]
                    )
                    _write(folder / "execution-access.json", encoded(second))
                    supervise(
                        [
                            sys.executable,
                            "-S",
                            "-m",
                            "experiments.m3.physiocgm_evaluation.worker",
                            str(output),
                            person["id"],
                        ],
                        folder / "run",
                        timeout,
                    )
                    case["status"] = "completed"
                except BaseException as error:
                    case.update(
                        status="interrupted" if _interrupted(error) else "failed",
                        error=failure(error),
                    )
                    if _interrupted(error) or not isinstance(error, Exception):
                        raise
                finally:
                    _state(output / "study.json", state)
            state["status"] = (
                "completed"
                if all(c["status"] == "completed" for c in cases)
                else "finished_with_failures"
            )
        except BaseException as error:
            state.update(
                status="interrupted" if _interrupted(error) else "failed", error=failure(error)
            )
            raise
        finally:
            _state(output / "study.json", state)
            try:
                _write(
                    output / "ledger.jsonl",
                    snapshot_ledger(plan["ledger"], plan["identity"], anchor),
                )
            except BaseException as error:
                _write(output / "ledger-snapshot-failure.json", encoded(failure(error)))
                raise
            finally:
                inventory(output)
    return state
