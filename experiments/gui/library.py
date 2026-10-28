"""Pointers and bounded metadata for explicit archives; heavy reads belong to jobs."""

import copy
import uuid

from experiments.catalogue.formats import TASKS
from experiments.platform_files import atomic_write_bytes

from . import library_m5
from .library_paths import ArchiveRoots
from .library_worker import ARTIFACTS_BY_TASK, REQUEST, SCHEMA, file_digest, validate_report
from .service import MAX_REPORT, bounded_bytes, decode_json, digest, encode, read_json, timestamp

VERSION = "opent1d.gui-library-entry/1"
POINTER_KEYS = ("id", "root_id", "path", "task", "tags", "root_identity", "archive_identity")


class Library:
    def __init__(self, service, archive_roots=()):
        self.service = service
        self.policy = ArchiveRoots(service.root, archive_roots)
        self.data = service.safe_path(service.data / "library", exists=False)
        self.data.mkdir(exist_ok=True)
        self.registered = {}
        self.load()

    def roots(self):
        return self.policy.listing()

    def browse(self, root_id, directory=""):
        return self.policy.browse(root_id, directory)

    def persist(self, entry):
        target = self.service.safe_path(self.data / (entry["id"] + ".json"), exists=False)
        temporary = target.with_suffix(".tmp")
        self.service.safe_path(temporary, exists=False)
        atomic_write_bytes(target, encode(entry), temporary=temporary)

    def load(self):
        for path in sorted(self.data.glob("archive-*.json"))[:128]:
            try:
                self.service.safe_path(path)
                entry = read_json(path)
                if (
                    not isinstance(entry, dict)
                    or entry.get("schema") != VERSION
                    or entry.get("id") != path.stem
                    or not path.stem.startswith("archive-")
                    or len(path.stem) != 40
                    or entry.get("task") not in TASKS
                    or type(entry.get("hidden", False)) is not bool
                    or not all(key in entry for key in POINTER_KEYS)
                ):
                    continue
                if entry.get("verification") in {"native_reader_verified", "verifying"}:
                    entry["verification"] = (
                        "recorded_verification" if entry.get("verified_job") else "not_requested"
                    )
                if entry.get("metadata_status") == "indexing":
                    entry["metadata_status"] = "unavailable"
                    entry["metadata_error"] = "Previous index owner stopped; ownership not adopted"
                self.registered[entry["id"]] = entry
                self.refresh_identity(entry)
                self.persist(entry)
            except (OSError, ValueError, KeyError, TypeError):
                continue

    def resolve(self, entry):
        if self.policy.identity(entry["root_id"]) != entry["root_identity"]:
            raise ValueError("Registered archive root identity differs")
        path, _ = self.policy.resolve(entry["root_id"], entry["path"], entry["archive_identity"])
        if path == self.service.data or path in self.service.data.parents:
            raise ValueError("Archive overlaps GUI administration and derived output")
        if self.service.data in path.parents:
            raise ValueError("GUI administration cannot be registered as an archive")
        return path

    def refresh_identity(self, entry):
        try:
            self.resolve(entry)
            entry["availability"] = "available"
            entry.pop("availability_error", None)
        except (OSError, ValueError, KeyError, TypeError) as error:
            entry["availability"] = "unavailable"
            entry["availability_error"] = str(error)[:300]
            if entry.get("verified_job"):
                entry["verification"] = "changed_since_verification"

    def lookup(self, identity):
        if identity not in self.registered:
            raise ValueError("Unknown registered archive")
        return self.registered[identity]

    def get(self, identity):
        with self.service.lock:
            entry = self.lookup(identity)
            self.refresh_identity(entry)
            # Only small cached metadata is read on HTTP paths. No archive scan occurs here.
            result = {k: copy.deepcopy(v) for k, v in entry.items() if k not in POINTER_KEYS[5:]}
            result["verification_scope"] = "verified_snapshot"
            result["source_freshness"] = "not_rechecked_since_worker"
            result["can_verify"] = (
                not entry.get("hidden", False)
                and entry["task"] in ARTIFACTS_BY_TASK
                and entry.get("inventory_sha256") is not None
                and entry["availability"] == "available"
            )
            result["can_view_report"] = (
                not entry.get("hidden", False)
                and entry["task"] in ARTIFACTS_BY_TASK
                and bool(entry.get("verified_job"))
                and entry["verification"] in {"native_reader_verified", "recorded_verification"}
                and entry["availability"] == "available"
            )
            result["reader_scope"] = (
                "current maintained M4 reader"
                if entry["task"] == "m4-study-secure"
                else "current synthetic M3 native reader"
                if entry["task"].startswith("m3-")
                else "current synthetic M5 native reader"
                if entry["task"] == "m5-prognosis"
                else "current fixed-kinetic synthetic observation reader"
                if entry["task"] in {"mmtt-sensitivity", "mmtt-sampling"}
                else "passive metadata; use a separate compatible trusted reader for verification"
            )
            if entry["task"] == "m5-prognosis" and not result["can_view_report"]:
                result.pop("model_declaration", None)
                result.pop("model_declaration_sha256", None)
            return result

    def set_hidden(self, identity, hidden):
        if type(hidden) is not bool:
            raise ValueError("Choose whether to hide this local reference")
        with self.service.lock:
            if self.service.closing or self.service.active is not None:
                raise ValueError("One active operation is allowed; wait or cancel it")
            entry = self.lookup(identity)
            entry["hidden"] = hidden
            self.persist(entry)
            return self.get(identity)

    def entries(self, filters=None):
        filters = filters or {}
        if (
            not isinstance(filters, dict)
            or set(filters) - {"task", "text", "status", "tag", "model", "protocol"}
            or any(not isinstance(v, str) or len(v) > 256 for v in filters.values())
        ):
            raise ValueError("Unsupported archive filter")
        result = []
        with self.service.lock:
            for identity in self.registered:
                entry = self.get(identity)
                meta = entry.get("metadata") or {}
                values = {
                    "task": [entry["task"]],
                    "status": [
                        entry["metadata_status"],
                        entry["verification"],
                        meta.get("recorded_status"),
                        entry["availability"],
                    ],
                    "tag": entry["tags"],
                    "model": [m.get("id") for m in meta.get("models", [])],
                    "protocol": [meta.get("protocol")],
                }
                if (
                    all(
                        not value or value in values[key]
                        for key, value in filters.items()
                        if key != "text"
                    )
                    and filters.get("text", "").lower()
                    in (
                        entry["path"]
                        + " "
                        + entry["task"]
                        + " "
                        + " ".join(entry["tags"])
                        + " "
                        + " ".join(m.get("id", "") for m in meta.get("models", []))
                    ).lower()
                ):
                    result.append(entry)
        return list(reversed(result))

    def request(self, entry, operation):
        self.resolve(entry)
        return {
            "schema": REQUEST,
            "operation": operation,
            "entry": {key: copy.deepcopy(entry[key]) for key in POINTER_KEYS},
            "expected_inventory": entry.get("inventory_sha256"),
        }

    def add(self, body):
        if (
            not isinstance(body, dict)
            or set(body) not in ({"root_id", "path", "task"}, {"root_id", "path", "task", "tags"})
            or body.get("task") not in TASKS
        ):
            raise ValueError("Choose a supported scientific archive task")
        tags = body.get("tags", [])
        if (
            not isinstance(tags, list)
            or len(tags) > 16
            or any(not isinstance(t, str) or not 0 < len(t) <= 128 for t in tags)
            or len(set(tags)) != len(tags)
        ):
            raise ValueError("Invalid local archive tags")
        root_identity = self.policy.identity(body["root_id"])
        path, archive_identity = self.policy.resolve(body["root_id"], body["path"])
        relative = path.relative_to(root_identity["path"]).as_posix()
        relative = "" if relative == "." else relative
        with self.service.lock:
            existing = next(
                (
                    e
                    for e in self.registered.values()
                    if e["root_id"] == body["root_id"]
                    and e["path"] == relative
                    and e["task"] == body["task"]
                ),
                None,
            )
            if existing is None and len(self.registered) >= 128:
                raise ValueError("The local library supports at most 128 explicit pointers")
            entry = existing or {
                "schema": VERSION,
                "id": "archive-" + uuid.uuid4().hex,
                "created_at": timestamp(),
                "metadata": None,
                "metadata_error": None,
                "hash_checks": None,
                "inventory_sha256": None,
                "verified_job": None,
                "artifacts_sha256": {},
                "report_completeness": "unavailable",
            }
            entry.update(
                root_id=body["root_id"],
                path=relative,
                task=body["task"],
                tags=tags,
                root_identity=root_identity,
                archive_identity=archive_identity,
                metadata_status="indexing",
                verification="not_requested",
                availability="available",
                hidden=False,
            )
            request = self.request(entry, "library_index")
            self.registered[entry["id"]] = entry
            self.persist(entry)
            return request

    def verify(self, identity):
        with self.service.lock:
            entry = self.lookup(identity)
            if entry.get("hidden", False):
                raise ValueError("Restore this local reference before verifying it")
            if entry["task"] not in ARTIFACTS_BY_TASK:
                raise ValueError("GUI verification requires a supported fixed native reader")
            if entry.get("inventory_sha256") is None:
                raise ValueError("Index this archive before requesting verification")
            request = self.request(entry, "library_verify")
            entry["verification"] = "verifying"
            self.persist(entry)
            return request

    def commands(self, job):
        request = job["request"]
        entry = self.lookup(request["entry"]["id"])
        if request != self.request(entry, job["operation"]):
            raise ValueError("Frozen library request no longer matches the registered pointer")
        folder = self.service.safe_path(self.service.data / job["id"])
        path = folder / "worker-request.json"
        if path.exists():
            raise ValueError("Library request output must be fresh")
        path.write_bytes(encode(request))
        return [
            (
                [
                    self.service.python,
                    "-B",
                    "-E",
                    "-s",
                    "-S",
                    "-m",
                    "experiments.gui.library_worker",
                    "--request",
                    str(path),
                    "--output",
                    str(folder),
                ],
                300 if job["operation"] == "library_verify" else 180,
            )
        ]

    def finish(self, job):
        with self.service.lock:
            entry = self.lookup(job["request"]["entry"]["id"])
            folder = self.service.safe_path(self.service.data / job["id"])
            if job["cancel_requested"] and not job.get("cleanup_forced") and not job.get("error"):
                entry["verification"] = (
                    "recorded_verification" if entry.get("verified_job") else "not_requested"
                )
                if entry["metadata_status"] == "indexing":
                    entry["metadata_status"] = "unavailable"
                    entry["metadata_error"] = (
                        "Index operation cancelled; available evidence retained"
                    )
                job["result"] = {"status": "cancelled", "report_completeness": "unavailable"}
                self.persist(entry)
                return
            try:
                result = read_json(folder / "worker-result.json")
                if (
                    result["schema"] != SCHEMA
                    or result["entry_id"] != entry["id"]
                    or result["operation"] != job["operation"]
                    or result["request_sha256"] != digest(encode(job["request"]))
                ):
                    raise ValueError("Library result does not bind the frozen request")
                self.resolve(entry)
                job["result"] = result
                success = (
                    result["status"] == "completed"
                    and job["exit_code"] == 0
                    and not job["cancel_requested"]
                    and job.get("error") is None
                )
                item = None
                if result.get("catalogue_sha256"):
                    path = self.service.safe_path(folder / "catalogue" / "catalogue.json")
                    raw = bounded_bytes(path, MAX_REPORT)
                    if digest(raw) != result["catalogue_sha256"]:
                        raise ValueError("Worker metadata bytes changed")
                    item = decode_json(raw)["entries"][0]
                    if item["id"] != entry["id"] or item["task"] != entry["task"]:
                        raise ValueError("Worker metadata pointer differs")
                    entry.update(
                        metadata=item["metadata"],
                        metadata_status=item["metadata_status"],
                        metadata_error=item["metadata_error"],
                        hash_checks=item["hash_checks"],
                        index_job=job["id"],
                    )
                if success:
                    entry["inventory_sha256"] = result["source_inventory_sha256"]
                    entry["indexed_at"] = timestamp()
                if job["operation"] == "library_verify":
                    entry["verification"] = (
                        result["verification"]
                        if success
                        else (
                            "changed_since_verification"
                            if result.get("verification") == "changed_since_verification"
                            else "verification_failed"
                        )
                    )
                    if success and result["verification"] == "native_reader_verified":
                        if set(result["artifacts_sha256"]) != set(ARTIFACTS_BY_TASK[entry["task"]]):
                            raise ValueError("Worker artifact roster differs from registered task")
                        for name in ARTIFACTS_BY_TASK[entry["task"]]:
                            path = self.service.safe_path(folder / "reconstructed" / name)
                            if file_digest(path) != result["artifacts_sha256"].get(name):
                                raise ValueError("Verified reconstructed artifact changed")
                        report = validate_report(
                            entry["task"],
                            decode_json(
                                bounded_bytes(folder / "reconstructed/report.json", MAX_REPORT)
                            ),
                        )
                        if entry["task"] == "m5-prognosis":
                            source_inventory = read_json(folder / "source-inventory.json")
                            source_digest = digest(encode(source_inventory))
                            if (
                                not isinstance(source_inventory, dict)
                                or source_digest != job["request"]["expected_inventory"]
                                or source_digest != result.get("source_inventory_sha256")
                                or any(
                                    result["artifacts_sha256"][name] != source_inventory.get(name)
                                    for name in ARTIFACTS_BY_TASK[entry["task"]]
                                )
                            ):
                                raise ValueError(
                                    "Worker M5 copied artifacts differ from frozen source inventory"
                                )
                            declared = library_m5.validate_declaration(
                                result.get("model_declaration"), report
                            )
                            metadata = (item or {}).get("metadata")
                            models = metadata.get("models") if isinstance(metadata, dict) else None
                            if (
                                not isinstance(models, list)
                                or len(models) != 1
                                or not isinstance(models[0], dict)
                                or declared != models[0].get("declaration")
                            ):
                                raise ValueError(
                                    "Worker M5 declaration differs from verified catalogue"
                                )
                            if library_m5.declaration_digest(declared) != result.get(
                                "model_declaration_sha256"
                            ):
                                raise ValueError("Worker M5 declaration digest differs")
                            if result["report_completeness"] != (
                                "complete" if library_m5.complete(report) else "incomplete"
                            ):
                                raise ValueError("Worker M5 report completeness differs")
                            entry.update(
                                model_declaration=copy.deepcopy(declared),
                                model_declaration_sha256=result["model_declaration_sha256"],
                                model_receipt_sha256=digest(encode(result)),
                            )
                        entry.update(
                            verified_job=job["id"],
                            verified_at=timestamp(),
                            artifacts_sha256=result["artifacts_sha256"],
                            report_completeness=result["report_completeness"],
                        )
                        job["verification"] = "native_reader_verified"
                    entry["verification_error"] = result["error"]
                if not success:
                    job["error"] = result["error"] or job.get("error") or "Archive operation failed"
                    if job["operation"] == "library_index":
                        entry["metadata_status"] = "unavailable"
                        entry["metadata_error"] = job["error"]
                job["report_completeness"] = entry["report_completeness"]
            except (OSError, ValueError, KeyError, TypeError) as error:
                entry["verification"] = "verification_failed"
                entry["metadata_error"] = str(error)[:300]
                if entry["metadata_status"] == "indexing":
                    entry["metadata_status"] = "unavailable"
                job["error"] = job.get("error") or str(error)[:300]
            self.persist(entry)

    def report_file(self, identity, name):
        entry = self.lookup(identity)
        if name not in ARTIFACTS_BY_TASK.get(entry["task"], ()):
            raise ValueError("Unknown report artifact for registered task")
        self.resolve(entry)
        if not entry.get("verified_job") or entry["verification"] not in {
            "native_reader_verified",
            "recorded_verification",
        }:
            raise ValueError("Verify this archive to view its reconstructed report")
        return self.service.safe_path(
            self.service.data / entry["verified_job"] / "reconstructed" / name
        )

    def m5_snapshot(self, entry):
        """Bind cached declarations to owned receipt/report, never reopen source files."""
        folder = self.service.safe_path(self.service.data / entry["verified_job"])
        receipt = read_json(folder / "worker-result.json")
        if digest(encode(receipt)) != entry.get("model_receipt_sha256"):
            raise ValueError("Verified M5 declaration receipt changed")
        declared = entry.get("model_declaration")
        if (
            declared != receipt.get("model_declaration")
            or entry.get("model_declaration_sha256") != receipt.get("model_declaration_sha256")
            or library_m5.declaration_digest(declared) != entry.get("model_declaration_sha256")
        ):
            raise ValueError("Verified M5 declaration snapshot changed")
        if entry["artifacts_sha256"] != receipt.get("artifacts_sha256"):
            raise ValueError("Verified M5 snapshot artifact binding changed")
        snapshots = {}
        for name in ARTIFACTS_BY_TASK[entry["task"]]:
            path = self.service.safe_path(folder / "reconstructed" / name)
            raw = bounded_bytes(path, library_m5.MAX_NATIVE_FILE)
            if digest(raw) != receipt["artifacts_sha256"].get(name):
                raise ValueError("Verified snapshot artifact changed")
            snapshots[name] = raw
        report = validate_report(entry["task"], decode_json(snapshots["report.json"]))
        library_m5.validate_declaration(declared, report)

    def report_bytes(self, identity, name):
        with self.service.lock:
            entry = self.lookup(identity)
            try:
                path = self.report_file(identity, name)
                if entry["task"] == "m5-prognosis":
                    self.m5_snapshot(entry)
                raw = bounded_bytes(
                    path,
                    library_m5.MAX_NATIVE_FILE if entry["task"] == "m5-prognosis" else MAX_REPORT,
                )
                if digest(raw) != entry["artifacts_sha256"].get(name):
                    raise ValueError("Verified snapshot artifact changed")
                if name == "report.json":
                    validate_report(entry["task"], decode_json(raw))
                self.resolve(entry)
                return raw
            except (OSError, ValueError, KeyError, TypeError):
                if entry.get("verified_job") and name in ARTIFACTS_BY_TASK.get(entry["task"], ()):
                    entry["verification"] = "changed_since_verification"
                    self.persist(entry)
                raise

    def report(self, identity):
        with self.service.lock:
            raw = self.report_bytes(identity, "report.json")
            entry = self.get(identity)
            report = validate_report(entry["task"], decode_json(raw))
            if entry["task"].startswith("m3-") or entry["task"] in {
                "m5-prognosis",
                "mmtt-sensitivity",
                "mmtt-sampling",
            }:
                result = {
                    "task": entry["task"],
                    "schema": report["schema"],
                    "native_report": report,
                    "verification": entry["verification"],
                    "verification_scope": "verified_snapshot",
                    "source_freshness": "not_rechecked_since_worker",
                    "report_completeness": entry["report_completeness"],
                    "report_sha256": digest(raw),
                }
                if entry["task"] == "m5-prognosis":
                    result.update(
                        model_declaration=copy.deepcopy(entry["model_declaration"]),
                        model_declaration_sha256=entry["model_declaration_sha256"],
                    )
                return result
            sources = report.get("sources", {})
            pairs = report.get("pairs", [])
            limitations = report.get("limitations", [])
            if not isinstance(sources, dict):
                raise ValueError("Malformed maintained M4 report sources")
            if any(
                not isinstance(item, dict) or not isinstance(item.get("declaration", {}), dict)
                for item in sources.values()
            ):
                raise ValueError("Malformed maintained M4 report source or declaration")
            if not isinstance(pairs, list) or any(not isinstance(item, dict) for item in pairs):
                raise ValueError("Malformed maintained M4 report pairs")
            if not isinstance(limitations, list) or any(
                not isinstance(item, str) for item in limitations
            ):
                raise ValueError("Malformed maintained M4 report limitations")
            entry = self.get(identity)
            return {
                **{
                    key: report.get(key)
                    for key in (
                        "schema",
                        "protocol",
                        "status",
                        "passed",
                        "denominators",
                        "scenarios",
                        "limitations",
                    )
                },
                "sources": {
                    name: {
                        "accepted": item.get("accepted"),
                        "status": item.get("status"),
                        "ancestry": item.get("declaration", {}).get("ancestry"),
                    }
                    for name, item in sources.items()
                },
                "pairs": [
                    {key: item.get(key) for key in ("left", "right", "accepted", "reason")}
                    for item in pairs
                ],
                "verification": entry["verification"],
                "verification_scope": "verified_snapshot",
                "source_freshness": "not_rechecked_since_worker",
                "report_completeness": entry["report_completeness"],
                "report_sha256": digest(raw),
            }
