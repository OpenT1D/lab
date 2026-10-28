"""Owned campaign pointers and immutable matrices; HTTP reads only cached reports."""

import copy
import functools
import os
import re
import stat
import uuid

from experiments.maintained_campaigns import common
from experiments.platform_files import atomic_write_bytes, is_link, open_regular

from .service import (
    MAX_JSON,
    MAX_REPORT,
    bounded_bytes,
    decode_json,
    digest,
    encode,
    inventory,
    read_json,
    timestamp,
)

CONFIGURATION = "opent1d.gui-campaign-configuration/1"
ENTRY = "opent1d.gui-campaign-entry/1"
FREEZE = "opent1d.gui-campaign-freeze/1"
REQUEST = "opent1d.gui-campaign-request/1"
RESULT = "opent1d.gui-campaign-worker/1"
OPERATIONS = frozenset(
    "campaign_" + name for name in ("check", "install", "run", "resume", "reconstruct")
)
ARTIFACTS = ("report.json", "report.md")
PREFIXES = {
    "configuration": "campaign-config-",
    "campaign": "campaign-",
    "study": "config-",
    "job": "job-",
}


def synchronized(method):
    @functools.wraps(method)
    def locked(self, *args, **kwargs):
        with self.service.lock:
            return method(self, *args, **kwargs)

    return locked


def identity(value, kind):
    prefix = PREFIXES[kind]
    common.require(
        isinstance(value, str) and re.fullmatch(prefix + r"[0-9a-f]{32}", value),
        "Invalid opaque " + kind + " ID",
    )
    return value


def atomic(path, value):
    temporary = path.with_suffix(".tmp")
    if os.name == "nt":
        atomic_write_bytes(path, encode(value), temporary=temporary)
        return
    common.require(not is_link(temporary), "Administration temporary path is a symlink")
    descriptor = open_regular(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        common.require(
            stat.S_ISREG(os.fstat(stream.fileno()).st_mode),
            "Administration temporary path is nonregular",
        )
        stream.write(encode(value))
    os.replace(temporary, path)


def validate_request(request):
    common.require(
        isinstance(request, dict)
        and set(request)
        == {
            "schema",
            "operation",
            "configuration_id",
            "campaign_id",
            "matrix_sha256",
            "freeze_sha256",
            "checked_identity",
            "expected_inventory",
        }
        and request["schema"] == REQUEST
        and request["operation"] in OPERATIONS,
        "Unsupported campaign worker request",
    )
    identity(request["configuration_id"], "configuration")
    if request["campaign_id"] is not None:
        identity(request["campaign_id"], "campaign")
    common.require(
        (request["campaign_id"] is not None)
        == (request["operation"] in {"campaign_run", "campaign_resume", "campaign_reconstruct"}),
        "Campaign request target differs",
    )
    for key in ("matrix_sha256", "freeze_sha256"):
        common.require(
            isinstance(request[key], str) and common.SHA.fullmatch(request[key]),
            "Invalid frozen campaign identity",
        )
    for key in ("checked_identity", "expected_inventory"):
        common.require(
            request[key] is None
            or isinstance(request[key], str)
            and common.SHA.fullmatch(request[key]),
            "Invalid campaign readiness/snapshot identity",
        )
    common.require(
        request["operation"] not in {"campaign_run", "campaign_resume"}
        or request["checked_identity"] is not None,
        "Check this campaign configuration before running or resuming",
    )
    return request


def validate_freeze(folder, request):
    raw = bounded_bytes(folder / "manifest.json", 1024 * 1024)
    common.require(digest(raw) == request["freeze_sha256"], "Frozen campaign manifest changed")
    manifest = decode_json(raw)
    common.require(
        isinstance(manifest, dict)
        and set(manifest) == {"schema", "files"}
        and manifest["schema"] == FREEZE,
        "Invalid campaign configuration freeze",
    )
    files = inventory(folder, files=True)
    files.pop("manifest.json", None)
    common.require(files == manifest["files"], "Frozen campaign source/configuration changed")
    matrix = bounded_bytes(folder / "matrix.json", MAX_JSON)
    common.require(digest(matrix) == request["matrix_sha256"], "Frozen matrix changed")
    return common.validate_config(decode_json(matrix))


def validate_report(report, record):
    common.require(
        isinstance(report, dict)
        and report.get("schema") == common.REPORT_SCHEMA
        and report.get("task") == common.TASK
        and report.get("protocol") == "MAINTAINED-CAMPAIGN/1"
        and report.get("status") in {"completed", "failed", "interrupted", "not_attempted"}
        and type(report.get("passed")) is bool
        and isinstance(report.get("slots"), list)
        and isinstance(report.get("sessions"), list),
        "Wrong campaign report shape",
    )
    matrix = {"cells": record["cells"], "repeats": record["repeats"]}
    expected = common.slots(matrix)
    counts = {
        cell["id"]: len(cell["source_ids"]) * len(cell["scenarios"]) for cell in record["cells"]
    }
    common.require(len(report["slots"]) == len(expected), "Campaign report roster differs")
    accepted, cases = 0, 0
    for slot, planned in zip(report["slots"], expected, strict=True):
        common.require(
            isinstance(slot, dict)
            and all(slot.get(key) == value for key, value in planned.items())
            and type(slot.get("accepted")) is bool
            and isinstance(slot.get("attempts"), list)
            and slot.get("planned_source_scenarios") == counts[planned["cell"]]
            and all(isinstance(attempt, dict) for attempt in slot["attempts"]),
            "Campaign report slot shape differs",
        )
        accepted += slot["accepted"]
        cases += counts[planned["cell"]] if slot["accepted"] else 0
    common.require(
        all(
            type(report.get(key)) is int and report[key] == value
            for key, value in {
                "planned_slots": record["planned_slots"],
                "accepted_slots": accepted,
                "planned_source_scenarios": record["planned_source_scenarios"],
                "accepted_source_scenarios": cases,
            }.items()
        )
        and (not report["passed"] or accepted == len(expected) and report["status"] == "completed"),
        "Campaign report denominator differs",
    )
    return report


class Campaigns:
    def __init__(self, service):
        self.service = service
        self.data = service.safe_path(service.data / "campaigns", exists=False)
        for name in ("configurations", "entries", "archives"):
            service.safe_path(self.data / name, exists=False).mkdir(parents=True, exist_ok=True)
        self.records, self.registered = {}, {}
        self.load()

    def folder(self, value):
        return self.service.safe_path(
            self.data / "configurations" / identity(value, "configuration")
        )

    def archive(self, value, *, exists=False):
        return self.service.safe_path(
            self.data / "archives" / identity(value, "campaign") / "campaign", exists=exists
        )

    def persist_configuration(self, record):
        atomic(self.folder(record["id"]) / "record.json", record)

    def persist_entry(self, entry):
        path = self.service.safe_path(self.data / "entries" / (entry["id"] + ".json"), exists=False)
        atomic(path, entry)

    def validate_record(self, record):
        common.require(isinstance(record, dict), "Invalid saved campaign configuration")
        identity(record["id"], "configuration")
        common.require(
            record["schema"] == CONFIGURATION
            and isinstance(record["created_at"], str)
            and type(record["ready"]) is bool,
            "Invalid saved campaign configuration",
        )
        for key in ("matrix_sha256", "freeze_sha256"):
            common.require(
                isinstance(record[key], str) and common.SHA.fullmatch(record[key]),
                "Invalid saved freeze hash",
            )
        common.require(
            record["checked_identity"] is None
            or isinstance(record["checked_identity"], str)
            and common.SHA.fullmatch(record["checked_identity"]),
            "Invalid saved readiness hash",
        )
        if record["check_job"] is not None:
            identity(record["check_job"], "job")
        frozen = self.folder(record["id"]) / "frozen"
        raw = bounded_bytes(self.service.safe_path(frozen / "manifest.json"), 1048576)
        common.require(digest(raw) == record["freeze_sha256"], "Saved manifest changed")
        manifest = decode_json(raw)
        common.require(
            isinstance(manifest, dict)
            and manifest.get("schema") == FREEZE
            and isinstance(manifest.get("files"), dict),
            "Invalid saved manifest",
        )
        values = {}
        for name in ("matrix.json", "bindings.json"):
            raw = bounded_bytes(self.service.safe_path(frozen / name), MAX_JSON)
            common.require(
                digest(raw) == manifest["files"][name], "Saved configuration metadata changed"
            )
            values[name] = decode_json(raw)
            if name == "matrix.json":
                common.require(digest(raw) == record["matrix_sha256"], "Saved matrix changed")
        matrix = common.validate_config(values["matrix.json"])
        common.require(
            isinstance(values["bindings.json"], dict)
            and encode(record["cells"]) == encode(values["bindings.json"].get("cells"))
            and isinstance(record["cells"], list),
            "Saved cell bindings differ",
        )
        common.require(
            type(record["repeats"]) is int
            and type(record["timeout_seconds"]) is int
            and record["repeats"] == matrix["repeats"]
            and record["timeout_seconds"] == matrix["timeout_seconds"]
            and [c["id"] for c in record["cells"]] == [c["id"] for c in matrix["cells"]],
            "Saved matrix summary differs",
        )
        cases = 0
        for cell, planned in zip(record["cells"], matrix["cells"], strict=True):
            common.require(
                isinstance(cell, dict)
                and set(cell)
                == {
                    "id",
                    "configuration_id",
                    "source_ids",
                    "scenarios",
                    "timeout_seconds",
                    "source_timeout_seconds",
                },
                "Invalid saved cell summary",
            )
            identity(cell["configuration_id"], "study")
            raw = bounded_bytes(self.service.safe_path(frozen / planned["config"]), MAX_JSON)
            common.require(
                digest(raw) == manifest["files"][planned["config"]],
                "Saved cell configuration changed",
            )
            native = decode_json(raw)
            common.require(
                isinstance(native, dict)
                and isinstance(native.get("sources"), list)
                and isinstance(native.get("scenarios"), list)
                and cell["source_ids"] == [source["id"] for source in native["sources"]]
                and all(
                    cell[key] == native[key]
                    for key in ("scenarios", "timeout_seconds", "source_timeout_seconds")
                ),
                "Saved native summary differs",
            )
            cases += len(cell["source_ids"]) * len(cell["scenarios"])
        common.require(
            type(record["planned_slots"]) is int
            and record["planned_slots"] == len(common.slots(matrix))
            and type(record["planned_source_scenarios"]) is int
            and record["planned_source_scenarios"] == cases * matrix["repeats"],
            "Saved denominator differs",
        )
        return record

    def validate_entry(self, entry):
        common.require(
            isinstance(entry, dict) and entry.get("schema") == ENTRY,
            "Invalid saved campaign pointer",
        )
        identity(entry["id"], "campaign")
        identity(entry["configuration_id"], "configuration")
        common.require(
            entry["configuration_id"] in self.records, "Unknown saved campaign configuration"
        )
        record = self.records[entry["configuration_id"]]
        common.require(
            entry["matrix_sha256"] == record["matrix_sha256"]
            and entry["status"] in {"not_attempted", "completed", "failed", "interrupted"}
            and entry["verification"]
            in {
                "not_requested",
                "native_reader_verified",
                "recorded_verification",
                "changed_since_verification",
                "verification_failed",
            }
            and entry["report_completeness"] in {"complete", "failed", "unavailable"}
            and type(entry["forensic_unsealed"]) is bool
            and isinstance(entry["created_at"], str),
            "Invalid saved campaign status",
        )
        for key in ("creator_job", "last_job", "snapshot_job"):
            if entry[key] is not None:
                identity(entry[key], "job")
        common.require(
            entry["error"] is None or isinstance(entry["error"], str),
            "Invalid saved campaign error",
        )
        common.require(
            entry["source_inventory_sha256"] is None
            or isinstance(entry["source_inventory_sha256"], str)
            and common.SHA.fullmatch(entry["source_inventory_sha256"]),
            "Invalid saved inventory hash",
        )
        common.require(
            isinstance(entry["artifacts_sha256"], dict)
            and (
                not entry["artifacts_sha256"]
                if entry["snapshot_job"] is None
                else set(entry["artifacts_sha256"]) == set(ARTIFACTS)
            )
            and all(
                isinstance(value, str) and common.SHA.fullmatch(value)
                for value in entry["artifacts_sha256"].values()
            ),
            "Invalid saved artifact hashes",
        )
        for key in ("accepted_slots", "accepted_source_scenarios"):
            common.require(
                type(entry[key]) is int
                and 0 <= entry[key] <= record[key.replace("accepted", "planned")],
                "Invalid saved accepted count",
            )
        return entry

    @synchronized
    def load(self):
        for path in sorted((self.data / "configurations").glob("campaign-config-*/record.json"))[
            :128
        ]:
            try:
                self.service.safe_path(path)
                record = read_json(path)
                self.validate_record(record)
                common.require(
                    record["schema"] == CONFIGURATION and record["id"] == path.parent.name,
                    "Invalid saved campaign configuration",
                )
                common.require(
                    digest(bounded_bytes(path.parent / "frozen/matrix.json", MAX_JSON))
                    == record["matrix_sha256"],
                    "Saved matrix changed",
                )
                record["ready"] = False
                self.records[record["id"]] = record
                self.persist_configuration(record)
            except (OSError, ValueError, KeyError, TypeError):
                continue
        for path in sorted((self.data / "entries").glob("campaign-*.json"))[:128]:
            try:
                self.service.safe_path(path)
                entry = read_json(path)
                self.validate_entry(entry)
                origin = self.service.jobs[entry["creator_job"]]
                common.require(
                    entry["schema"] == ENTRY
                    and entry["id"] == path.stem
                    and entry["configuration_id"] in self.records,
                    "Invalid saved campaign pointer",
                )
                common.require(
                    origin["operation"] == "campaign_run"
                    and origin["request"]["campaign_id"] == entry["id"]
                    and origin["request"]["configuration_id"] == entry["configuration_id"],
                    "Campaign pointer lacks its own originating job",
                )
                if entry["verification"] == "native_reader_verified":
                    entry["verification"] = "recorded_verification"
                self.archive(entry["id"])
                self.registered[entry["id"]] = entry
                self.persist_entry(entry)
            except (OSError, ValueError, KeyError, TypeError):
                continue

    @synchronized
    def configure(self, body):
        common.require(
            isinstance(body, dict) and set(body) == {"cells", "repeats", "timeout_seconds"},
            "Campaign configuration fields differ",
        )
        common.require(isinstance(body["cells"], list), "Campaign cells must be an ordered list")
        matrix = {
            "schema": common.CONFIG_SCHEMA,
            "task": common.TASK,
            "cells": [],
            "repeats": body["repeats"],
            "timeout_seconds": body["timeout_seconds"],
        }
        for cell in body["cells"]:
            common.require(
                isinstance(cell, dict) and set(cell) == {"id", "configuration_id"},
                "Each cell needs id and configuration_id",
            )
            identity(cell["configuration_id"], "study")
            matrix["cells"].append({"id": cell["id"], "config": f"cells/{cell['id']}/config.json"})
        common.validate_config(matrix)
        with self.service.lock:
            common.require(len(self.records) < 128, "At most 128 campaign configurations supported")
            value = "campaign-config-" + uuid.uuid4().hex
            folder = self.service.safe_path(self.data / "configurations" / value, exists=False)
            folder.mkdir()
            frozen = folder / "frozen"
            frozen.mkdir()
            cells = []
            try:
                for cell in body["cells"]:
                    original = self.service.resolve_configuration(cell["configuration_id"])
                    source_folder = self.service.safe_path(self.service.data / original["id"])
                    raw = bounded_bytes(source_folder / "config.json", MAX_JSON)
                    common.require(
                        digest(raw) == original["sha256"],
                        "Original frozen study configuration changed",
                    )
                    config = decode_json(raw)
                    target = frozen / "cells" / cell["id"]
                    target.mkdir(parents=True)
                    (target / "original-config.json").write_bytes(raw)
                    cloned = copy.deepcopy(config)
                    for source in cloned["sources"]:
                        common.require(
                            isinstance(source["id"], str) and common.ID.fullmatch(source["id"]),
                            "Invalid frozen source ID",
                        )
                        destination = target / "sources" / source["id"]
                        destination.mkdir(parents=True)
                        for key, name, limit in (
                            ("model", "model.py", 1048576),
                            ("declaration", "model.json", MAX_JSON),
                        ):
                            path = self.service.safe_path(source[key])
                            common.require(
                                source_folder / "sources" / source["id"] in path.parents,
                                "Study source must be its own frozen copy",
                            )
                            copied = bounded_bytes(path, limit)
                            common.require(
                                digest(copied) == original["source_sha256"][str(path)],
                                "Saved study source changed during campaign freeze",
                            )
                            (destination / name).write_bytes(copied)
                            source[key] = f"sources/{source['id']}/{name}"
                    (target / "config.json").write_bytes(encode(cloned))
                    self.service.unchanged(original)
                    cells.append(
                        {
                            "id": cell["id"],
                            "configuration_id": original["id"],
                            "source_ids": [source["id"] for source in cloned["sources"]],
                            "scenarios": cloned["scenarios"],
                            "timeout_seconds": cloned["timeout_seconds"],
                            "source_timeout_seconds": cloned["source_timeout_seconds"],
                        }
                    )
                (frozen / "matrix.json").write_bytes(encode(matrix))
                metadata = common.prepare(frozen / "matrix.json")
                (frozen / "bindings.json").write_bytes(encode({"cells": cells}))
                manifest = {"schema": FREEZE, "files": inventory(frozen, files=True)}
                (frozen / "manifest.json").write_bytes(encode(manifest))
                record = {
                    "schema": CONFIGURATION,
                    "id": value,
                    "created_at": timestamp(),
                    "cells": cells,
                    "repeats": matrix["repeats"],
                    "timeout_seconds": matrix["timeout_seconds"],
                    "planned_slots": metadata["planned_slots"],
                    "planned_source_scenarios": metadata["planned_source_scenarios"],
                    "matrix_sha256": digest((frozen / "matrix.json").read_bytes()),
                    "freeze_sha256": digest(encode(manifest)),
                    "ready": False,
                    "checked_identity": None,
                    "check_job": None,
                }
                self.records[value] = record
                self.persist_configuration(record)
            except BaseException:
                # Retain incomplete inputs for diagnosis; they have no registered record.
                raise
            return self.get_configuration(value)

    @synchronized
    def get_configuration(self, value):
        identity(value, "configuration")
        common.require(value in self.records, "Unknown campaign configuration")
        record = self.records[value]
        return {
            key: copy.deepcopy(record[key])
            for key in (
                "id",
                "created_at",
                "cells",
                "repeats",
                "timeout_seconds",
                "planned_slots",
                "planned_source_scenarios",
                "matrix_sha256",
                "ready",
                "check_job",
            )
        } | {"readiness_scope": "recorded_check"}

    @synchronized
    def configurations(self):
        return [self.get_configuration(value) for value in reversed(self.records)]

    @synchronized
    def invalidate_readiness(self):
        for record in self.records.values():
            record.update(ready=False, checked_identity=None)
            self.persist_configuration(record)

    @synchronized
    def request(self, operation, *, configuration_id=None, campaign_id=None):
        common.require(operation in OPERATIONS, "Unsupported campaign operation")
        expected = None
        if operation in {"campaign_resume", "campaign_reconstruct"}:
            identity(campaign_id, "campaign")
            common.require(campaign_id in self.registered, "Unknown own campaign")
            entry = self.registered[campaign_id]
            configuration_id, expected = (
                entry["configuration_id"],
                entry.get("source_inventory_sha256"),
            )
        else:
            common.require(campaign_id is None, "New operation cannot supply a campaign ID")
            if operation == "campaign_run":
                common.require(len(self.registered) < 128, "At most 128 own campaigns supported")
                campaign_id = "campaign-" + uuid.uuid4().hex
        self.get_configuration(configuration_id)
        record = self.records[configuration_id]
        if operation in {"campaign_run", "campaign_resume"}:
            common.require(
                record["ready"], "Check this campaign configuration before running or resuming"
            )
        return validate_request(
            {
                "schema": REQUEST,
                "operation": operation,
                "configuration_id": configuration_id,
                "campaign_id": campaign_id,
                "matrix_sha256": record["matrix_sha256"],
                "freeze_sha256": record["freeze_sha256"],
                "checked_identity": record["checked_identity"] if record["ready"] else None,
                "expected_inventory": expected,
            }
        )

    @synchronized
    def started(self, job):
        request = validate_request(job["request"])
        common.require(
            job["operation"] == request["operation"], "Job and campaign operation differ"
        )
        job.update(
            campaign_configuration_id=request["configuration_id"],
            campaign_id=request["campaign_id"],
        )
        if request["operation"] == "campaign_run":
            common.require(
                request["campaign_id"] not in self.registered, "Campaign ID is already registered"
            )
            record = self.records[request["configuration_id"]]
            entry = {
                "schema": ENTRY,
                "id": request["campaign_id"],
                "configuration_id": record["id"],
                "creator_job": job["id"],
                "created_at": timestamp(),
                "matrix_sha256": record["matrix_sha256"],
                "status": "not_attempted",
                "accepted_slots": 0,
                "accepted_source_scenarios": 0,
                "verification": "not_requested",
                "report_completeness": "unavailable",
                "last_job": job["id"],
                "snapshot_job": None,
                "source_inventory_sha256": None,
                "artifacts_sha256": {},
                "forensic_unsealed": False,
                "error": None,
            }
            self.registered[entry["id"]] = entry
            self.persist_entry(entry)
        elif request["campaign_id"] is not None:
            entry = self.registered[request["campaign_id"]]
            entry.update(last_job=job["id"], error=None)
            # A new worker owns the next verification; retain the prior bounded
            # snapshot as recorded evidence until this job supplies a fresh one.
            if entry["verification"] == "native_reader_verified":
                entry["verification"] = "recorded_verification"
            self.persist_entry(entry)

    @synchronized
    def commands(self, job):
        request = validate_request(job["request"])
        record = self.records[request["configuration_id"]]
        common.require(
            request["matrix_sha256"] == record["matrix_sha256"]
            and request["freeze_sha256"] == record["freeze_sha256"],
            "Campaign request freeze differs",
        )
        folder = self.service.safe_path(self.service.data / identity(job["id"], "job"))
        path = folder / "campaign-request.json"
        common.require(
            not path.exists() and not path.is_symlink(), "Campaign request must be fresh"
        )
        path.write_bytes(encode(request))
        operation = request["operation"]
        budget = (
            240
            if operation == "campaign_check"
            else 2100
            if operation == "campaign_install"
            else 900
            if operation == "campaign_reconstruct"
            else 1200 + record["planned_slots"] * (record["timeout_seconds"] + 30)
        )
        return [
            (
                [
                    self.service.python,
                    "-B",
                    "-E",
                    "-s",
                    "-S",
                    "-m",
                    "experiments.gui.campaign_worker",
                    "--request",
                    str(path),
                    "--output",
                    str(folder),
                ],
                budget,
            )
        ]

    @synchronized
    def finish(self, job):
        request = validate_request(job["request"])
        record = self.records[request["configuration_id"]]
        folder = self.service.safe_path(self.service.data / job["id"])
        entry = self.registered.get(request["campaign_id"])
        try:
            if (
                not (folder / "campaign-result.json").exists()
                and job.get("cancel_requested")
                and not job.get("error")
                and not job.get("cleanup_forced")
                and not job.get("remaining_owned_processes")
            ):
                if request["operation"] == "campaign_check":
                    record.update(ready=False, checked_identity=None)
                    self.persist_configuration(record)
                if entry is not None:
                    entry.update(
                        last_job=job["id"],
                        verification="verification_failed",
                        report_completeness="unavailable",
                        error=None,
                    )
                    self.persist_entry(entry)
                job["result"] = {
                    "status": "cancelled",
                    "diagnostic": "Cancelled before a bounded worker receipt was available",
                }
                return
            result = read_json(folder / "campaign-result.json")
            common.require(
                isinstance(result, dict)
                and result["schema"] == RESULT
                and result["request_sha256"] == digest(encode(request))
                and result["operation"] == request["operation"]
                and result["configuration_id"] == record["id"]
                and result["campaign_id"] == request["campaign_id"],
                "Campaign worker result does not bind the frozen request",
            )
            common.require(
                result.get("status") in {"completed", "failed", "cancelled"}
                and type(result.get("ready")) is bool
                and (result.get("error") is None or isinstance(result["error"], str)),
                "Invalid campaign worker outcome",
            )
            if result.get("ready"):
                common.require(
                    isinstance(result.get("checked_identity"), str)
                    and common.SHA.fullmatch(result["checked_identity"]),
                    "Missing campaign checked identity",
                )
            job["result"] = result
            prior_error = job.get("error")
            ownership_ok = (
                not prior_error
                and not job.get("cleanup_forced")
                and not job.get("remaining_owned_processes")
            )
            if result.get("error"):
                job["error"] = prior_error or result["error"]
            if request["operation"] == "campaign_check":
                ready = (
                    ownership_ok
                    and job.get("exit_code") == 0
                    and not job.get("cancel_requested")
                    and result.get("status") == "completed"
                    and result.get("error") is None
                    and result.get("ready") is True
                )
                record.update(
                    ready=ready,
                    checked_identity=result.get("checked_identity") if ready else None,
                    check_job=job["id"],
                )
                self.persist_configuration(record)
            elif result.get("readiness_changed"):
                record.update(ready=False, checked_identity=None)
                self.persist_configuration(record)
            if entry is not None:
                entry.update(
                    last_job=job["id"],
                    error=job.get("error") or result["error"],
                    verification=result["verification"],
                    report_completeness=result["report_completeness"],
                    forensic_unsealed=result["forensic_unsealed"],
                )
                if result.get("source_inventory_sha256"):
                    entry["source_inventory_sha256"] = result["source_inventory_sha256"]
                if result["verification"] == "native_reader_verified":
                    common.require(
                        ownership_ok and result["status"] in {"completed", "failed", "cancelled"},
                        "Ownership failure cannot promote a campaign snapshot",
                    )
                    for name in ARTIFACTS:
                        raw = bounded_bytes(folder / "snapshot" / name, MAX_REPORT)
                        common.require(
                            digest(raw) == result["artifacts_sha256"][name],
                            "Campaign snapshot artifact changed",
                        )
                    report = validate_report(
                        read_json(folder / "snapshot/report.json", MAX_REPORT), record
                    )
                    entry.update(
                        snapshot_job=job["id"],
                        artifacts_sha256=result["artifacts_sha256"],
                        **{
                            key: report[key]
                            for key in ("status", "accepted_slots", "accepted_source_scenarios")
                        },
                    )
                self.persist_entry(entry)
        except (OSError, ValueError, KeyError, TypeError) as error:
            job["error"] = job.get("error") or str(error)
            if request["operation"] == "campaign_check":
                record.update(ready=False, checked_identity=None)
                self.persist_configuration(record)
            if entry is not None:
                entry.update(
                    last_job=job["id"],
                    verification="verification_failed",
                    error=job["error"],
                    report_completeness="unavailable",
                )
                self.persist_entry(entry)

    @synchronized
    def get(self, value):
        identity(value, "campaign")
        common.require(value in self.registered, "Unknown own campaign")
        entry = self.registered[value]
        configuration = self.get_configuration(entry["configuration_id"])
        return (
            {
                key: copy.deepcopy(entry[key])
                for key in (
                    "id",
                    "configuration_id",
                    "created_at",
                    "matrix_sha256",
                    "status",
                    "accepted_slots",
                    "accepted_source_scenarios",
                    "verification",
                    "report_completeness",
                    "last_job",
                    "error",
                )
            }
            | {
                key: configuration[key]
                for key in (
                    "cells",
                    "repeats",
                    "timeout_seconds",
                    "planned_slots",
                    "planned_source_scenarios",
                )
            }
            | {
                "can_resume": configuration["ready"]
                and bool(entry.get("source_inventory_sha256"))
                and not entry["forensic_unsealed"],
                "can_view_report": bool(entry.get("snapshot_job")),
                "source_freshness": "not_rechecked_since_worker",
            }
        )

    @synchronized
    def entries(self):
        return [self.get(value) for value in reversed(self.registered)]

    @synchronized
    def report_bytes(self, value, name):
        self.get(value)
        common.require(name in ARTIFACTS, "Campaign artifact must be JSON or Markdown")
        entry = self.registered[value]
        common.require(entry.get("snapshot_job") is not None, "Campaign report is unavailable")
        try:
            folder = self.service.safe_path(
                self.service.data / identity(entry["snapshot_job"], "job") / "snapshot"
            )
            raw = bounded_bytes(folder / name, MAX_REPORT)
            common.require(
                digest(raw) == entry["artifacts_sha256"].get(name),
                "Cached campaign artifact changed",
            )
        except (OSError, ValueError) as error:
            entry.update(
                verification="changed_since_verification", error="Cached campaign artifact changed"
            )
            self.persist_entry(entry)
            raise ValueError("Cached campaign artifact changed") from error
        return raw

    @synchronized
    def report(self, value):
        raw = self.report_bytes(value, "report.json")
        entry = self.registered[value]
        return {
            "campaign_id": value,
            "configuration_id": entry["configuration_id"],
            "verification": entry["verification"],
            "verification_scope": "verified_snapshot",
            "source_freshness": "not_rechecked_since_worker",
            "report_sha256": digest(raw),
            "report_completeness": entry["report_completeness"],
            "report": validate_report(decode_json(raw), self.records[entry["configuration_id"]]),
        }
