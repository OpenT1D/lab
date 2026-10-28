"""Explicit synthetic preparation and owned M3 pointers outside native archives."""

import copy
import functools
import math
import os
import re
import time
import uuid
from pathlib import Path

from experiments.durable_archives import storage
from experiments.m3.comparison import common as comparison
from experiments.m3.researcher import common as forecast
from experiments.m3.researcher.intake import validate_bundle, validate_declaration
from experiments.platform_files import is_link

from .campaigns import atomic
from .library_paths import relative_path, validate_identity
from .packaged_phases import m3_extra
from .service import MAX_REPORT, bounded_bytes, decode_json, digest, encode, read_json, timestamp

TASKS = ("m3-forecast", "m3-compare")
OPERATIONS = frozenset("m3_" + name for name in ("fixture", "check", "run", "reconstruct"))
INPUT = "opent1d.gui-m3-input/1"
CONFIGURATION = "opent1d.gui-m3-configuration/1"
FREEZE = "opent1d.gui-m3-freeze/1"
ENTRY = "opent1d.gui-m3-entry/1"
REQUEST = "opent1d.gui-m3-request/1"
RESULT = "opent1d.gui-m3-worker/1"
ARTIFACTS = ("report.json", "report.md")
MAX_CONFIG = 16 * 1024 * 1024
MAX_INPUT = 64 * 1024 * 1024
PREFIXES = {
    "input": "m3-input-",
    "configuration": "m3-config-",
    "entry": "m3-study-",
    "job": "job-",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def identity(value, kind):
    require(
        isinstance(value, str) and re.fullmatch(PREFIXES[kind] + r"[0-9a-f]{32}", value),
        "Invalid opaque M3 " + kind + " ID",
    )
    return value


def synchronized(method):
    @functools.wraps(method)
    def locked(self, *args, **kwargs):
        with self.service.lock:
            return method(self, *args, **kwargs)

    return locked


def budget(seconds=30):
    result = storage.Budget()
    result.deadline = time.monotonic() + seconds
    return result


def validate_request(request):
    require(
        isinstance(request, dict)
        and set(request)
        == {
            "schema",
            "operation",
            "task",
            "input_id",
            "configuration_id",
            "entry_id",
            "config_sha256",
            "freeze_sha256",
            "checked_identity",
            "expected_inventory",
        }
        and request["schema"] == REQUEST
        and request["operation"] in OPERATIONS
        and request["task"] in TASKS,
        "Unsupported M3 worker request",
    )
    fixture = request["operation"] == "m3_fixture"
    require((request["input_id"] is not None) == fixture, "M3 fixture target differs")
    if fixture:
        identity(request["input_id"], "input")
        require(request["task"] == "m3-compare", "Fixture prepares the fixed comparison")
    else:
        identity(request["configuration_id"], "configuration")
    for key in ("config_sha256", "freeze_sha256"):
        value = request[key]
        require(
            value is None if fixture else isinstance(value, str) and forecast.SHA.fullmatch(value),
            "Invalid M3 frozen identity",
        )
    require((request["configuration_id"] is None) == fixture, "M3 configuration target differs")
    for key in ("checked_identity", "expected_inventory"):
        value = request[key]
        require(
            value is None or isinstance(value, str) and forecast.SHA.fullmatch(value),
            "Invalid M3 readiness/snapshot identity",
        )
    requires_entry = request["operation"] in {"m3_run", "m3_reconstruct"}
    require((request["entry_id"] is not None) == requires_entry, "M3 archive target differs")
    if requires_entry:
        identity(request["entry_id"], "entry")
    require(
        request["operation"] != "m3_run" or request["checked_identity"] is not None,
        "Check this M3 configuration before running",
    )
    return request


def validate_freeze(folder, request):
    timer = budget()
    raw = storage.read_file(folder, "manifest.json", timer, limit=8 * 1024 * 1024)
    require(digest(raw) == request["freeze_sha256"], "Frozen M3 manifest changed")
    manifest = decode_json(raw)
    require(
        isinstance(manifest, dict)
        and set(manifest) == {"schema", "inventory"}
        and manifest["schema"] == FREEZE,
        "Invalid M3 preparation freeze",
    )
    actual, _ = storage.inventory(folder, timer, exclude_manifest=True)
    require(actual == manifest["inventory"], "Frozen M3 configuration or input bytes changed")
    config_raw = storage.read_file(folder, "config.json", timer, limit=MAX_CONFIG)
    require(digest(config_raw) == request["config_sha256"], "Frozen M3 configuration changed")
    config = decode_json(config_raw)
    (forecast.validate_config if request["task"] == "m3-forecast" else comparison.validate_config)(
        config
    )
    return config


def validate_report(report, record):
    task = record["task"]
    require(
        isinstance(report, dict)
        and report.get("schema")
        == (forecast.SCHEMA if task == "m3-forecast" else comparison.SCHEMA)
        and report.get("kind") == "synthetic"
        and report.get("human_evaluation") is False,
        "Wrong synthetic M3 report shape",
    )
    evaluation = report["evaluation"] if task == "m3-forecast" else report["common"]
    require(
        isinstance(evaluation, dict)
        and type(evaluation.get("complete_cohort")) is bool
        and evaluation.get("planned_people") == record["planned_people"]
        and isinstance(evaluation.get("people"), dict)
        and set(evaluation["people"]) == set(record["planned_origins"]),
        "M3 report planned cohort differs",
    )
    if task == "m3-forecast":
        require(
            report["predictor"]["id"] == record["candidate_ids"][0], "M3 forecast predictor differs"
        )
    else:
        require(
            report["candidate_order"] == record["candidate_ids"]
            and set(report["candidates"]) == set(record["candidate_ids"]),
            "M3 comparison frozen candidate order differs",
        )
    for person, count in record["planned_origins"].items():
        detail = evaluation["people"][person]
        require(
            isinstance(detail, dict)
            and detail.get("planned" if task == "m3-forecast" else "planned_origins") == count,
            "M3 report registered origin denominator differs",
        )
    return report


class M3:
    def __init__(self, service):
        self.service = service
        self.policy = service.library.policy
        self.data = service.safe_path(service.data / "m3", exists=False)
        for name in ("inputs", "configurations", "entries", "archives", "pointers"):
            service.safe_path(self.data / name, exists=False).mkdir(parents=True, exist_ok=True)
        self.inputs, self.records, self.registered = {}, {}, {}
        self.load()

    def load(self):
        for kind, folder, schema, target in (
            ("input", "pointers", INPUT, self.inputs),
            ("configuration", "configurations", CONFIGURATION, self.records),
            ("entry", "entries", ENTRY, self.registered),
        ):
            paths = (self.data / folder).glob(
                "*.json" if kind != "configuration" else "*/record.json"
            )
            for path in sorted(paths):
                try:
                    self.service.safe_path(path)
                    value = read_json(path)
                    identity(value["id"], kind)
                    require(
                        value["schema"] == schema and value["task"] in TASKS,
                        "Unsupported saved M3 pointer",
                    )
                    if kind == "configuration":
                        value.update(ready=False, checked_identity=None)
                        atomic(path, value)
                    elif kind == "entry":
                        identity(value["configuration_id"], "configuration")
                        require(
                            value["configuration_id"] in self.records,
                            "M3 entry has no registered configuration",
                        )
                        if value.get("verification") == "native_reader_verified":
                            value["verification"] = "recorded_verification"
                        job = self.service.jobs.get(value.get("last_job"))
                        if (
                            job
                            and job["state"] == "failed"
                            and job.get("operation") == "m3_run"
                            and job.get("task") == value["task"]
                            and job.get("request", {}).get("entry_id") == value["id"]
                        ):
                            value["execution_state"] = "failed"
                        atomic(path, value)
                    target[value["id"]] = value
                except (OSError, ValueError, KeyError, TypeError):
                    continue

    def idle(self):
        require(
            not self.service.closing and self.service.active is None,
            "One active operation is allowed; wait or cancel it",
        )

    def read_allowed(self, path, limit, timer):
        path = Path(path)
        require(
            path.is_absolute() and str(path) == os.path.abspath(path),
            "Input paths must be canonical absolute paths under an enabled root",
        )
        matches = [
            (Path(value["path"]), value)
            for value in self.policy.roots.values()
            if path.is_relative_to(Path(value["path"]))
        ]
        require(matches, "M3 input is outside the enabled read-only roots")
        root, declared = max(matches, key=lambda item: len(item[0].parts))
        validate_identity(declared)
        relative = relative_path(path.relative_to(root).as_posix())
        raw = storage.read_file(root, relative, timer, limit=limit)
        validate_identity(declared)
        return raw

    def intake(self, path):
        timer = budget()
        raw = self.read_allowed(path, MAX_CONFIG, timer)
        config = decode_json(raw)
        require(isinstance(config, dict), "M3 configuration must be a JSON object")
        task = {forecast.SCHEMA: "m3-forecast", comparison.SCHEMA: "m3-compare"}.get(
            config.get("schema")
        )
        require(task in TASKS, "Choose an existing synthetic M3 forecast/comparison configuration")
        (forecast.validate_config if task == "m3-forecast" else comparison.validate_config)(config)
        require(1 <= len(config["people"]) <= 128, "M3 GUI supports 1–128 planned participants")
        selected = (
            [{"id": None, "declaration": config["predictor"]}]
            if task == "m3-forecast"
            else config["candidates"]
        )
        require(1 <= len(selected) <= 8, "M3 GUI supports at most eight frozen candidates")
        candidates, bundles = [], {}
        for item in selected:
            declaration_raw = self.read_allowed(item["declaration"], 65536, timer)
            declaration = decode_json(declaration_raw)
            validate_declaration(declaration)
            require(
                item["id"] is None or item["id"] == declaration["id"],
                "Candidate identity differs from declaration",
            )
            source = self.read_allowed(declaration["source"]["file"], 1048576, timer)
            settings = self.read_allowed(declaration["settings"]["file"], 1048576, timer)
            validate_bundle(declaration, source, settings)
            identity_value = declaration["id"]
            bundles[identity_value] = {
                "declaration": declaration,
                "declaration_raw": declaration_raw,
                "source": source,
                "settings": settings,
            }
            candidates.append(
                {
                    "id": identity_value,
                    "reference": declaration["reference"],
                    "rights": declaration["rights"],
                    "training": declaration["training"],
                    "source_sha256": digest(source),
                    "settings_sha256": digest(settings),
                    "declaration_sha256": digest(declaration_raw),
                }
            )
        return raw, config, task, candidates, bundles

    @synchronized
    def inspect(self, body):
        self.idle()
        require(
            isinstance(body, dict) and set(body) == {"root_id", "path"},
            "Inspect requires an enabled root ID and relative configuration path",
        )
        root = self.policy.identity(body["root_id"])
        relative = relative_path(body["path"])
        require(relative and relative.endswith(".json"), "Choose a JSON M3 configuration")
        path = Path(root["path"]) / relative
        raw, config, task, candidates, _ = self.intake(path)
        value = next(
            (
                v
                for v in self.inputs.values()
                if v["root_id"] == body["root_id"]
                and v["path"] == relative
                and v["config_sha256"] == digest(raw)
                and v["candidates"] == candidates
            ),
            None,
        )
        if value is None:
            require(len(self.inputs) < 128, "At most 128 inspected M3 inputs supported")
            value = {
                "schema": INPUT,
                "id": "m3-input-" + uuid.uuid4().hex,
                "task": task,
                "root_id": body["root_id"],
                "path": relative,
                "root_identity": root,
                "config_sha256": digest(raw),
                "candidates": candidates,
                "planned_people": len(config["people"]),
                "planned_origins": {p["id"]: len(p["origins_us"]) for p in config["people"]},
                "source": config["source"],
                "prior_access": config["prior_access"],
                "created_at": timestamp(),
            }
            self.inputs[value["id"]] = value
            atomic(self.data / "pointers" / (value["id"] + ".json"), value)
        return self.get_input(value["id"])

    @synchronized
    def get_input(self, value):
        identity(value, "input")
        require(value in self.inputs, "Unknown inspected M3 input")
        record = self.inputs[value]
        return {
            key: copy.deepcopy(record[key])
            for key in (
                "id",
                "task",
                "root_id",
                "path",
                "config_sha256",
                "candidates",
                "planned_people",
                "planned_origins",
                "source",
                "prior_access",
                "created_at",
            )
        } | {"input_id": value}

    @synchronized
    def input_list(self):
        return [self.get_input(value) for value in reversed(self.inputs)]

    @synchronized
    def bootstrap(self):
        return {
            "schema": "opent1d.gui-m3/1",
            "scope": "synthetic",
            "tasks": [
                {"id": "m3-forecast", "title": "One frozen forecast against persistence"},
                {"id": "m3-compare", "title": "Frozen forecasts on shared support"},
            ],
            "roots": self.policy.listing(),
            "limits": {"candidates": [1, 8], "people": [1, 128], "timeout_seconds": [1, 1800]},
            "inputs": self.input_list(),
            "configurations": self.configurations(),
            "entries": self.list(),
        }

    @synchronized
    def browse(self, root_id, directory=""):
        root = self.policy.identity(root_id)
        folder, _ = self.policy.resolve(root_id, directory)
        result = self.policy.browse(root_id, directory)
        entries, inspected = result["entries"], 0
        with os.scandir(folder) as children:
            for child in children:
                inspected += 1
                require(inspected <= 2000, "Directory exceeds the bounded M3 input browser")
                if child.name.startswith(".") or is_link(child.path):
                    continue
                if child.is_file(follow_symlinks=False) and child.name.endswith(".json"):
                    relative = Path(child.path).relative_to(root["path"]).as_posix()
                    entries.append({"name": child.name, "path": relative, "kind": "configuration"})
                    require(len(entries) <= 500, "Directory exceeds the M3 browser entry limit")
        result["entries"] = sorted(
            entries, key=lambda item: (item["kind"] != "directory", item["name"])
        )
        return result

    @synchronized
    def configure(self, body):
        self.idle()
        require(
            isinstance(body, dict)
            and set(body) == {"input_id", "task", "candidate_ids", "timeout_seconds"},
            "Unsupported M3 preparation fields",
        )
        original = self.get_input(body["input_id"])
        source = self.inputs[body["input_id"]]
        validate_identity(source["root_identity"])
        raw, config, _, candidates, bundles = self.intake(
            Path(source["root_identity"]["path"]) / source["path"]
        )
        require(
            digest(raw) == source["config_sha256"] and candidates == original["candidates"],
            "Inspected M3 configuration/predictor changed; inspect again",
        )
        task, selected, timeout = body["task"], body["candidate_ids"], body["timeout_seconds"]
        require(
            task in TASKS
            and isinstance(selected, list)
            and all(isinstance(item, str) for item in selected)
            and len(set(selected)) == len(selected)
            and all(item in bundles for item in selected)
            and (len(selected) == 1 if task == "m3-forecast" else 2 <= len(selected) <= 8),
            "Choose one frozen predictor for a forecast or at least two for comparison",
        )
        require(
            type(timeout) in (int, float) and math.isfinite(timeout) and 1 <= timeout <= 1800,
            "M3 participant worker timeout must be 1–1800 seconds",
        )
        require(len(self.records) < 128, "At most 128 M3 preparations supported")
        value = "m3-config-" + uuid.uuid4().hex
        folder = self.service.safe_path(self.data / "configurations" / value, exists=False)
        frozen = folder / "frozen"
        frozen.mkdir(parents=True)
        timer, total = budget(), len(raw)
        (frozen / "original-config.json").write_bytes(raw)
        effective = {
            key: copy.deepcopy(config[key]) for key in ("kind", "source", "prior_access", "people")
        }
        for item in selected:
            target = frozen / "predictors" / item
            target.mkdir(parents=True)
            bundle = bundles[item]
            for name, data in (
                ("original-declaration.json", bundle["declaration_raw"]),
                ("source.py", bundle["source"]),
                ("settings.json", bundle["settings"]),
            ):
                total += len(data)
                require(total <= 2147483648, "M3 preparation exceeds the total byte limit")
                (target / name).write_bytes(data)
            declaration = copy.deepcopy(bundle["declaration"])
            declaration["source"]["file"] = str(target / "source.py")
            declaration["settings"]["file"] = str(target / "settings.json")
            (target / "declaration.json").write_bytes(encode(declaration))
        receipts = []
        for person in effective["people"]:
            timer.check()
            target = frozen / "observations" / (person["id"] + ".json")
            target.parent.mkdir(exist_ok=True)
            receipt = {
                "person": person["id"],
                "event": "before_synthetic_preparation_read",
                "original_file": person["input"]["file"],
                "planned_sha256": person["input"]["sha256"],
                "at": timestamp(),
            }
            receipts.append(receipt)
            (frozen / "preparation-access.json").write_bytes(encode(receipts))
            observed = self.read_allowed(person["input"]["file"], MAX_INPUT, timer)
            require(
                digest(observed) == person["input"]["sha256"], "Synthetic observation hash mismatch"
            )
            total += len(observed)
            require(total <= 2147483648, "M3 preparation exceeds the total byte limit")
            target.write_bytes(observed)
            person["input"]["file"] = str(target)
            receipt.update(copied_sha256=digest(observed), copied_bytes=len(observed))
            (frozen / "preparation-access.json").write_bytes(encode(receipts))
        if task == "m3-forecast":
            effective.update(
                schema=forecast.SCHEMA,
                predictor=str(frozen / "predictors" / selected[0] / "declaration.json"),
            )
        else:
            effective.update(
                schema=comparison.SCHEMA,
                candidates=[
                    {
                        "id": item,
                        "declaration": str(frozen / "predictors" / item / "declaration.json"),
                    }
                    for item in selected
                ],
                timeout_seconds=timeout,
            )
        config_bytes = encode(effective)
        (frozen / "config.json").write_bytes(config_bytes)
        (frozen / "preparation.json").write_bytes(
            encode(
                {
                    "schema": "opent1d.gui-m3-preparation/1",
                    "input_id": source["id"],
                    "original_task": source["task"],
                    "task": task,
                    "candidate_ids": selected,
                    "timeout_seconds": timeout,
                    "changes": [
                        "task schema",
                        "candidate selection/order",
                        "absolute owned paths",
                        "worker budget",
                    ],
                    "scope": (
                        "Explicit synthetic preparation access and byte identity; "
                        "native observation validation remains execution-only"
                    ),
                }
            )
        )
        tree, _ = storage.inventory(frozen, timer)
        manifest = encode({"schema": FREEZE, "inventory": tree})
        (frozen / "manifest.json").write_bytes(manifest)
        record = {
            "schema": CONFIGURATION,
            "id": value,
            "input_id": source["id"],
            "task": task,
            "candidate_ids": list(selected),
            "timeout_seconds": timeout,
            "planned_people": len(effective["people"]),
            "planned_origins": {p["id"]: len(p["origins_us"]) for p in effective["people"]},
            "config_sha256": digest(config_bytes),
            "freeze_sha256": digest(manifest),
            "ready": False,
            "checked_identity": None,
            "check_job": None,
            "created_at": timestamp(),
        }
        self.records[value] = record
        atomic(folder / "record.json", record)
        return self.get_configuration(value)

    @synchronized
    def configuration_path(self, value):
        identity(value, "configuration")
        require(value in self.records, "Unknown M3 configuration")
        return self.service.safe_path(self.data / "configurations" / value / "frozen")

    @synchronized
    def get_configuration(self, value):
        identity(value, "configuration")
        require(value in self.records, "Unknown M3 configuration")
        record = self.records[value]
        return {
            key: copy.deepcopy(record[key])
            for key in (
                "id",
                "input_id",
                "task",
                "candidate_ids",
                "timeout_seconds",
                "planned_people",
                "planned_origins",
                "config_sha256",
                "freeze_sha256",
                "ready",
                "check_job",
                "created_at",
            )
        } | {
            "preparation_scope": "synthetic observation copy/hash; not native validation",
            "readiness_scope": "recorded native metadata/runtime check",
        }

    @synchronized
    def configurations(self):
        return [self.get_configuration(value) for value in reversed(self.records)]

    @synchronized
    def invalidate_readiness(self):
        for record in self.records.values():
            record.update(ready=False, checked_identity=None)
            atomic(self.data / "configurations" / record["id"] / "record.json", record)

    @synchronized
    def request(self, operation, *, configuration_id=None, entry_id=None):
        require(operation in OPERATIONS, "Unsupported M3 operation")
        if operation == "m3_fixture":
            request = {
                "schema": REQUEST,
                "operation": operation,
                "task": "m3-compare",
                "input_id": "m3-input-" + uuid.uuid4().hex,
                "configuration_id": None,
                "entry_id": None,
                "config_sha256": None,
                "freeze_sha256": None,
                "checked_identity": None,
                "expected_inventory": None,
            }
            return validate_request(request)
        if operation == "m3_reconstruct":
            self.get(entry_id)
            original = self.registered[entry_id]
            configuration_id = original["configuration_id"]
        else:
            require(entry_id is None, "New M3 operation cannot supply an archive ID")
        self.get_configuration(configuration_id)
        record = self.records[configuration_id]
        if operation == "m3_run":
            require(record["ready"], "Check this M3 configuration before running")
            require(len(self.registered) < 128, "At most 128 own M3 studies supported")
            entry_id = "m3-study-" + uuid.uuid4().hex
        request = {
            "schema": REQUEST,
            "operation": operation,
            "task": record["task"],
            "input_id": None,
            "configuration_id": configuration_id,
            "entry_id": entry_id,
            "config_sha256": record["config_sha256"],
            "freeze_sha256": record["freeze_sha256"],
            "checked_identity": record["checked_identity"] if record["ready"] else None,
            "expected_inventory": self.registered[entry_id].get("source_inventory_sha256")
            if operation == "m3_reconstruct"
            else None,
        }
        if operation != "m3_reconstruct":
            try:
                validate_freeze(self.configuration_path(configuration_id), request)
            except (OSError, ValueError):
                record.update(ready=False, checked_identity=None)
                atomic(self.data / "configurations" / record["id"] / "record.json", record)
                raise
        return validate_request(request)

    @synchronized
    def started(self, job):
        request = validate_request(job["request"])
        require(job["operation"] == request["operation"], "M3 job operation differs")
        job.update(
            task=request["task"],
            m3_configuration_id=request["configuration_id"],
            m3_entry_id=request["entry_id"],
        )
        if request["operation"] == "m3_run":
            value = request["entry_id"]
            self.registered[value] = {
                "schema": ENTRY,
                "id": value,
                "task": request["task"],
                "configuration_id": request["configuration_id"],
                "creator_job": job["id"],
                "last_job": job["id"],
                "created_at": timestamp(),
                "updated_at": timestamp(),
                "execution_state": "queued",
                "verification": "not_requested",
                "complete": None,
                "report_completeness": "unavailable",
                "snapshot_job": None,
                "source_inventory_sha256": None,
                "artifacts_sha256": {},
                "forensic_unsealed": False,
                "error": None,
            }
            self.persist_entry(self.registered[value])
        elif request["entry_id"] is not None:
            entry = self.registered[request["entry_id"]]
            entry.update(last_job=job["id"], updated_at=timestamp(), error=None)
            if entry["verification"] == "native_reader_verified":
                entry["verification"] = "recorded_verification"
            self.persist_entry(entry)

    def persist_entry(self, entry):
        atomic(self.data / "entries" / (entry["id"] + ".json"), entry)

    @synchronized
    def commands(self, job):
        request = validate_request(job["request"])
        folder = self.service.safe_path(self.service.data / identity(job["id"], "job"))
        path = folder / "m3-request.json"
        require(not path.exists() and not is_link(path), "M3 request must be fresh")
        path.write_bytes(encode(request))
        if request["operation"] == "m3_fixture":
            timeout = 120
        else:
            record = self.records[request["configuration_id"]]
            timeout = (
                300
                if request["operation"] != "m3_run"
                else (
                    600
                    + record["planned_people"]
                    * len(record["candidate_ids"])
                    * (record["timeout_seconds"] + 10)
                )
            )
            native_seconds = 120 + record["planned_people"] * len(record["candidate_ids"]) * (
                record["timeout_seconds"] + 10
            )
            timeout += m3_extra(
                request["task"],
                request["operation"],
                native_seconds,
                source_root=self.service.source_root,
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
                    "experiments.gui.m3_worker",
                    "--request",
                    str(path),
                    "--output",
                    str(folder),
                ],
                timeout,
            )
        ]

    @synchronized
    def finish(self, job):
        request = validate_request(job["request"])
        folder = self.service.safe_path(self.service.data / job["id"])
        record = self.records.get(request["configuration_id"])
        entry = self.registered.get(request["entry_id"])
        try:
            result = read_json(folder / "m3-result.json")
            require(
                isinstance(result, dict)
                and result["schema"] == RESULT
                and result["request_sha256"] == digest(encode(request))
                and all(
                    result[key] == request[key]
                    for key in ("operation", "task", "configuration_id", "entry_id")
                )
                and result["status"] in {"completed", "failed", "cancelled"},
                "M3 worker result does not bind its own frozen request",
            )
            job["result"] = result
            ownership_ok = not (
                job.get("error")
                or job.get("cleanup_forced")
                or job.get("remaining_owned_processes")
            )
            if result.get("error"):
                job["error"] = job.get("error") or result["error"]
            if request["operation"] == "m3_fixture" and ownership_ok and job.get("exit_code") == 0:
                relative = (
                    (self.data / "inputs" / request["input_id"] / "comparison.json")
                    .relative_to(self.service.root)
                    .as_posix()
                )
                own_root = next(
                    key
                    for key, value in self.policy.roots.items()
                    if Path(value["path"]) == self.service.root
                )
                # The live job still owns the global slot; use the already checked fixture bytes.
                active = self.service.active
                self.service.active = None
                try:
                    inspected = self.inspect({"root_id": own_root, "path": relative})
                finally:
                    self.service.active = active
                result["input_id"] = inspected["id"]
            if request["operation"] == "m3_check":
                ready = bool(
                    ownership_ok
                    and job.get("exit_code") == 0
                    and not job.get("cancel_requested")
                    and result.get("ready") is True
                    and result["status"] == "completed"
                )
                record.update(
                    ready=ready,
                    checked_identity=result.get("checked_identity") if ready else None,
                    check_job=job["id"],
                )
                atomic(self.data / "configurations" / record["id"] / "record.json", record)
            elif record is not None and result.get("readiness_changed"):
                record.update(ready=False, checked_identity=None)
                atomic(self.data / "configurations" / record["id"] / "record.json", record)
            if entry is not None:
                entry.update(
                    last_job=job["id"],
                    updated_at=timestamp(),
                    error=job.get("error"),
                    verification=result["verification"],
                    forensic_unsealed=result.get("forensic_unsealed", False),
                    source_inventory_sha256=result.get("source_inventory_sha256"),
                    report_completeness=result["report_completeness"],
                )
                if request["operation"] == "m3_run":
                    entry["execution_state"] = result["status"]
                if result["verification"] == "native_reader_verified":
                    require(ownership_ok, "Ownership failure cannot promote an M3 report")
                    report = validate_report(
                        read_json(folder / "snapshot/report.json", MAX_REPORT), record
                    )
                    for name in ARTIFACTS:
                        require(
                            digest(bounded_bytes(folder / "snapshot" / name, MAX_REPORT))
                            == result["artifacts_sha256"][name],
                            "Cached M3 report artifact changed",
                        )
                    evaluation = (
                        report["evaluation"]
                        if record["task"] == "m3-forecast"
                        else report["common"]
                    )
                    entry.update(
                        snapshot_job=job["id"],
                        artifacts_sha256=result["artifacts_sha256"],
                        complete=evaluation["complete_cohort"],
                    )
                else:
                    entry.update(snapshot_job=None, artifacts_sha256={}, complete=None)
                self.persist_entry(entry)
        except (OSError, ValueError, KeyError, TypeError) as error:
            if job.get("cancel_requested") and not (
                job.get("error")
                or job.get("cleanup_forced")
                or job.get("remaining_owned_processes")
            ):
                job["result"] = {
                    "status": "cancelled",
                    "diagnostic": "Cancelled before an M3 worker receipt was available",
                }
            else:
                job["error"] = job.get("error") or str(error)
            if record is not None and request["operation"] == "m3_check":
                record.update(ready=False, checked_identity=None)
                atomic(self.data / "configurations" / record["id"] / "record.json", record)
            if entry is not None:
                entry.update(
                    verification="verification_failed",
                    error=job.get("error"),
                    complete=None,
                    snapshot_job=None,
                    artifacts_sha256={},
                    report_completeness="unavailable",
                    forensic_unsealed=self.archive_path(entry["id"], exists=False).is_dir(),
                    updated_at=timestamp(),
                )
                if request["operation"] == "m3_run":
                    entry["execution_state"] = (
                        "cancelled" if job.get("cancel_requested") else "failed"
                    )
                self.persist_entry(entry)

    @synchronized
    def archive_path(self, value, *, exists=True):
        identity(value, "entry")
        require(value in self.registered, "Unknown own M3 study")
        return self.service.safe_path(self.data / "archives" / value / "archive", exists=exists)

    def progress(self, entry, archive):
        result = {
            "candidate_order": self.records[entry["configuration_id"]]["candidate_ids"],
            "coordinator_status": None,
            "candidates": {},
            "people": {},
        }
        if not archive.is_dir():
            return result
        try:
            if entry["task"] == "m3-compare":
                state = read_json(self.service.safe_path(archive / "state.json"), 65536)
                result["coordinator_status"] = state["status"]
                result["candidates"] = {
                    key: value["status"] for key, value in state["candidates"].items()
                }
                bases = {key: archive / "children" / key for key in result["candidate_order"]}
            else:
                bases = {result["candidate_order"][0]: archive}
            for candidate, base in bases.items():
                people = {}
                for person in self.records[entry["configuration_id"]]["planned_origins"]:
                    path = base / "cases" / person / "state.json"
                    if path.exists():
                        people[person] = read_json(self.service.safe_path(path), 65536)["status"]
                    else:
                        people[person] = "not_attempted"
                result["people"][candidate] = people
        except (OSError, ValueError, KeyError, TypeError):
            result["observation"] = "native progress unavailable while being written"
        return result

    @synchronized
    def get(self, value):
        identity(value, "entry")
        require(value in self.registered, "Unknown own M3 study")
        entry = self.registered[value]
        archive = self.archive_path(value, exists=False)
        last = self.service.jobs.get(entry["last_job"], {})
        running = last.get("state") in {"queued", "running", "cancelling"}
        sealed = (archive / "manifest.json").is_file() and not is_link(archive / "manifest.json")
        available = bool(
            entry.get("snapshot_job")
            and entry["verification"] in {"native_reader_verified", "recorded_verification"}
        )
        return {
            key: copy.deepcopy(entry[key])
            for key in (
                "id",
                "task",
                "configuration_id",
                "execution_state",
                "verification",
                "complete",
                "report_completeness",
                "last_job",
                "snapshot_job",
                "artifacts_sha256",
                "error",
                "created_at",
                "updated_at",
                "forensic_unsealed",
            )
        } | {
            "archive": archive.relative_to(self.service.root).as_posix(),
            "sealed": sealed,
            "execution_state": last["state"]
            if running and last.get("operation") == "m3_run"
            else entry["execution_state"],
            "report_available": available,
            "can_view_report": available,
            "can_reconstruct": sealed and not running,
            "progress": self.progress(entry, archive),
            "source_freshness": "not_rechecked_since_worker",
        }

    @synchronized
    def list(self):
        return [self.get(value) for value in reversed(self.registered)]

    @synchronized
    def report_bytes(self, value, name):
        self.get(value)
        require(name in ARTIFACTS, "M3 artifacts are native JSON or Markdown")
        entry = self.registered[value]
        require(
            entry.get("snapshot_job") is not None
            and entry["verification"] in {"native_reader_verified", "recorded_verification"},
            "M3 report is unavailable",
        )
        try:
            folder = self.service.safe_path(
                self.service.data / identity(entry["snapshot_job"], "job") / "snapshot"
            )
            retained = {
                artifact: bounded_bytes(folder / artifact, MAX_REPORT) for artifact in ARTIFACTS
            }
            require(
                all(
                    digest(raw) == entry["artifacts_sha256"].get(artifact)
                    for artifact, raw in retained.items()
                ),
                "Cached M3 report changed",
            )
            validate_report(
                decode_json(retained["report.json"]), self.records[entry["configuration_id"]]
            )
            return retained[name]
        except (OSError, ValueError, KeyError, TypeError) as error:
            entry.update(
                verification="changed_since_verification",
                error="Cached M3 report changed",
                snapshot_job=None,
                artifacts_sha256={},
                complete=None,
                report_completeness="unavailable",
                updated_at=timestamp(),
            )
            self.persist_entry(entry)
            raise ValueError("Cached M3 report changed; reconstruct explicitly") from error

    @synchronized
    def report(self, value):
        raw = self.report_bytes(value, "report.json")
        entry = self.registered[value]
        return {
            "entry_id": value,
            "task": entry["task"],
            "configuration_id": entry["configuration_id"],
            "snapshot_job": entry["snapshot_job"],
            "verification": entry["verification"],
            "report_sha256": digest(raw),
            "artifacts_sha256": copy.deepcopy(entry["artifacts_sha256"]),
            "complete": entry["complete"],
            "report_completeness": entry["report_completeness"],
            "source_freshness": "not_rechecked_since_worker",
            "report": decode_json(raw),
        }
