"""Explicit durable package pointers and cached evidence under the shared GUI owner."""

import copy
import uuid
from pathlib import Path

from experiments.platform_files import atomic_write_bytes, native_absolute

from .library_paths import directory_identity, resolve_archive, validate_identity
from .service import MAX_REPORT, bounded_bytes, decode_json, digest, encode, read_json, timestamp

ENTRY = "opent1d.gui-durable-entry/1"
REQUEST = "opent1d.gui-durable-request/1"
RESULT = "opent1d.gui-durable-worker/1"
OPERATIONS = frozenset(
    "durable_" + name for name in ("export", "register", "verify", "reconstruct")
)
ARTIFACTS = ("report.json", "report.md", "figure.svg")


def store_identity(workspace, value):
    if value is None:
        return None
    path = native_absolute(value)
    if path != path.resolve(strict=True):
        raise ValueError("Archive store must be canonical and have no symlink components")
    for parent in (*reversed(path.parents), path):
        directory_identity(parent)
    if path == workspace or workspace in path.parents or path in workspace.parents:
        raise ValueError("Archive store must be outside and separate from this checkout")
    return directory_identity(path)


class Durable:
    def __init__(self, service, store=None):
        self.service = service
        self.store = store
        self.data = service.safe_path(service.data / "durable", exists=False)
        self.data.mkdir(exist_ok=True)
        self.registered = {}
        self.load()
        from .forensic import Forensics

        self.forensic = Forensics(self)

    def persist(self, entry):
        target = self.service.safe_path(self.data / (entry["id"] + ".json"), exists=False)
        temporary = target.with_suffix(".tmp")
        self.service.safe_path(temporary, exists=False)
        atomic_write_bytes(target, encode(entry), temporary=temporary)

    def load(self):
        for path in sorted(self.data.glob("durable-*.json"))[:128]:
            try:
                self.service.safe_path(path)
                entry = read_json(path)
                if (
                    not isinstance(entry, dict)
                    or entry.get("schema") != ENTRY
                    or entry.get("id") != path.stem
                    or len(path.stem) != 40
                    or not all(key in entry for key in ("root_id", "path", "root_identity"))
                ):
                    continue
                if entry.get("integrity") in {"verified_snapshot", "checking"}:
                    entry["integrity"] = (
                        "recorded_verification"
                        if entry.get("package_identity")
                        else "not_requested"
                    )
                if entry.get("reconstruction") in {"verified_snapshot", "checking"}:
                    entry["reconstruction"] = (
                        "recorded_verification" if entry.get("snapshot_job") else "not_requested"
                    )
                self.registered[entry["id"]] = entry
                self.refresh(entry)
                self.persist(entry)
            except (OSError, ValueError, KeyError, TypeError):
                continue

    def lookup(self, value):
        if value not in self.registered:
            raise ValueError("Unknown durable package")
        return self.registered[value]

    def resolve(self, entry, *, fresh=False):
        policy = self.service.library.policy
        if policy.identity(entry["root_id"]) != entry["root_identity"]:
            raise ValueError("Durable archive root identity changed")
        if fresh:
            root = validate_identity(entry["root_identity"])
            target = root / entry["path"]
            if target.exists() or target.is_symlink() or target.parent != root:
                raise ValueError("Export requires a fresh opaque package child")
            return target
        path, _ = resolve_archive(
            entry["root_identity"], entry["path"], entry.get("archive_identity")
        )
        if (
            path == self.service.data
            or path in self.service.data.parents
            or self.service.data in path.parents
        ):
            raise ValueError("GUI administration cannot be registered as a durable package")
        return path

    def refresh(self, entry):
        try:
            if (
                entry.get("export_source")
                and entry.get("archive_identity") is None
                and entry.get("integrity") == "checking"
            ):
                target = Path(entry["root_identity"]["path"]) / entry["path"]
                if not target.exists() and not target.is_symlink():
                    self.resolve(entry, fresh=True)
                    entry["availability"] = "awaiting_export"
                    entry.pop("availability_error", None)
                    return
            self.resolve(entry)
            entry["availability"] = "available"
            entry.pop("availability_error", None)
        except (OSError, ValueError, KeyError, TypeError) as error:
            entry["availability"] = "unavailable"
            entry["availability_error"] = str(error)[:300]
            if entry.get("package_identity"):
                entry["integrity"] = "changed_since_verification"
                entry["reconstruction"] = "changed_since_verification"

    def bootstrap(self):
        available = False
        error = None
        if self.store:
            try:
                validate_identity(self.store)
                available = True
            except (OSError, ValueError) as problem:
                error = str(problem)[:300]
        return {
            "store": self.store["path"] if self.store else None,
            "can_export": available,
            "store_error": error,
            "roots": self.service.library.roots(),
            "reader_scope": (
                "current clean checkout or verified installation at the recorded full revision"
            ),
        }

    def sources(self):
        with self.service.lock:
            return self.source_listing()

    def source_listing(self):
        values = []
        for job in list(self.service.jobs.values())[-256:]:
            if job["operation"] == "run" and job["state"] not in {
                "queued",
                "running",
                "cancelling",
            }:
                archive = self.service.safe_path(
                    self.service.data / job["id"] / "archive", exists=False
                )
                if (archive / "manifest.json").is_file():
                    values.append(
                        {
                            "kind": "study",
                            "id": job["id"],
                            "label": "Study · " + job["id"] + " · " + job["state"],
                        }
                    )
        for identity, entry in self.service.campaigns.registered.items():
            archive = self.service.campaigns.archive(identity)
            if (archive / "manifest.json").is_file():
                values.append(
                    {
                        "kind": "campaign",
                        "id": identity,
                        "label": "Campaign · " + identity + " · " + entry["status"],
                    }
                )
        for entry in self.service.library.registered.values():
            if entry["task"] in {"m4-study-secure", "m3-forecast", "m3-compare"}:
                try:
                    self.service.library.resolve(entry)
                    values.append(
                        {
                            "kind": "library",
                            "id": entry["id"],
                            "label": "Library study · " + entry["path"],
                        }
                    )
                except (OSError, ValueError, KeyError, TypeError):
                    continue
        if hasattr(self.service, "m3"):
            for entry in self.service.m3.list():
                if entry["sealed"] and entry["execution_state"] not in {
                    "queued",
                    "running",
                    "cancelling",
                }:
                    values.append(
                        {
                            "kind": "m3",
                            "id": entry["id"],
                            "label": entry["task"]
                            + " · "
                            + entry["id"]
                            + " · "
                            + entry["execution_state"],
                        }
                    )
        return values[-128:]

    def new_entry(self, root_id, relative, identity=None):
        if len(self.registered) >= 128:
            raise ValueError("At most 128 durable pointers are supported")
        root = self.service.library.policy.identity(root_id)
        entry = {
            "schema": ENTRY,
            "id": "durable-" + uuid.uuid4().hex,
            "created_at": timestamp(),
            "root_id": root_id,
            "path": relative,
            "root_identity": root,
            "archive_identity": identity,
            "package_identity": None,
            "task": None,
            "reader_revision": None,
            "integrity": "not_requested",
            "reconstruction": "not_requested",
            "complete": None,
            "snapshot_job": None,
            "artifacts_sha256": {},
            "error": None,
        }
        self.registered[entry["id"]] = entry
        return entry

    def request(self, operation, entry):
        return {
            "schema": REQUEST,
            "operation": operation,
            "entry_id": entry["id"],
            "root_identity": copy.deepcopy(entry["root_identity"]),
            "path": entry["path"],
            "archive_identity": copy.deepcopy(entry.get("archive_identity")),
            "expected_identity": entry.get("package_identity"),
            "source": copy.deepcopy(entry.get("source")) if operation == "durable_export" else None,
            "checkout": str(self.service.source_root),
        }

    def export(self, body):
        if not isinstance(body, dict) or set(body) != {"kind", "id"}:
            raise ValueError("Choose an existing study, campaign, M3 or library ID")
        if not self.bootstrap()["can_export"]:
            raise ValueError("Start the GUI with an existing --archive-store outside this checkout")
        kind, value = body["kind"], body["id"]
        if kind == "study":
            job = self.service.get_job(value)
            if job["operation"] != "run" or job["state"] in {"queued", "running", "cancelling"}:
                raise ValueError("Choose a finished study")
            archive = self.service.safe_path(self.service.data / value / "archive")
            task = "m4-study-secure"
        elif kind == "campaign":
            self.service.campaigns.get(value)
            archive = self.service.campaigns.archive(value, exists=True)
            task = "maintained-campaign"
        elif kind == "m3":
            entry = self.service.m3.get(value)
            if entry["execution_state"] in {"queued", "running", "cancelling"}:
                raise ValueError("Choose a stopped M3 run")
            archive = self.service.m3.archive_path(value)
            task = entry["task"]
        elif kind == "library":
            entry = self.service.library.lookup(value)
            if entry["task"] not in {"m4-study-secure", "m3-forecast", "m3-compare"}:
                raise ValueError("Unsupported durable library task")
            archive = self.service.library.resolve(entry)
            task = entry["task"]
        else:
            raise ValueError("Unsupported durable export source")
        if not (archive / "manifest.json").is_file():
            raise ValueError("Choose a sealed reconstructible archive")
        root_id = next(
            key for key, root in self.service.library.policy.roots.items() if root == self.store
        )
        entry = self.new_entry(root_id, "package-" + uuid.uuid4().hex)
        entry["integrity"] = entry["reconstruction"] = "checking"
        entry["export_source"] = {"kind": kind, "id": value}
        self.resolve(entry, fresh=True)
        entry["source"] = {
            "task": task,
            "path": str(archive),
            "identity": directory_identity(archive),
        }
        self.persist(entry)
        return self.request("durable_export", entry)

    def register(self, body):
        if not isinstance(body, dict) or set(body) != {"root_id", "path"}:
            raise ValueError(
                "Select a durable package using an allowed root and relative directory"
            )
        path, identity = self.service.library.policy.resolve(body["root_id"], body["path"])
        if (
            path == self.service.data
            or path in self.service.data.parents
            or self.service.data in path.parents
        ):
            raise ValueError("GUI administration cannot be registered as a durable package")
        root = self.service.library.policy.identity(body["root_id"])
        relative = path.relative_to(root["path"]).as_posix()
        entry = next(
            (
                value
                for value in self.registered.values()
                if value["root_id"] == body["root_id"] and value["path"] == relative
            ),
            None,
        )
        created = entry is None
        entry = entry or self.new_entry(body["root_id"], relative, identity)
        try:
            self.resolve(entry)
        except (OSError, ValueError, KeyError, TypeError):
            if created:
                self.registered.pop(entry["id"], None)
            raise
        entry["integrity"] = "checking"
        entry["reconstruction"] = "not_requested"
        entry["snapshot_job"] = None
        self.persist(entry)
        return self.request("durable_register", entry)

    def operation(self, operation, identity):
        if operation not in {"durable_verify", "durable_reconstruct"}:
            raise ValueError("Unsupported durable operation")
        entry = self.lookup(identity)
        self.resolve(entry)
        entry["integrity"] = "checking"
        entry["reconstruction"] = (
            "checking" if operation == "durable_reconstruct" else "not_requested"
        )
        entry["snapshot_job"] = None
        entry["error"] = None
        self.persist(entry)
        return self.request(operation, entry)

    def retain_m3(self, identity):
        return self.forensic.prepare(identity)

    def commands(self, job):
        if job["operation"] == "durable_forensic":
            return self.forensic.commands(job)
        request = job["request"]
        entry = self.lookup(request["entry_id"])
        if request != self.request(job["operation"], entry):
            raise ValueError("Frozen durable request no longer matches its registered pointer")
        self.resolve(entry, fresh=job["operation"] == "durable_export")
        folder = self.service.safe_path(self.service.data / job["id"])
        path = folder / "worker-request.json"
        if path.exists():
            raise ValueError("Durable worker request requires a fresh job")
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
                    "experiments.gui.durable_worker",
                    "--request",
                    str(path),
                    "--output",
                    str(folder),
                ],
                900,
            )
        ]

    def finish(self, job):
        with self.service.lock:
            if job["operation"] == "durable_forensic":
                return self.forensic.finish(job)
            entry = self.lookup(job["request"]["entry_id"])
            folder = self.service.safe_path(self.service.data / job["id"])
            if job["cancel_requested"] and not job.get("cleanup_forced") and not job.get("error"):
                entry.update(
                    integrity="recorded_verification"
                    if entry.get("package_identity")
                    else "not_requested",
                    reconstruction="not_requested",
                    snapshot_job=None,
                    error="Operation cancelled; no new verification is granted",
                )
                job["result"] = {"status": "cancelled", "report_completeness": "unavailable"}
                self.persist(entry)
                return
            try:
                result = read_json(folder / "worker-result.json")
                if (
                    result.get("schema") != RESULT
                    or result.get("entry_id") != entry["id"]
                    or result.get("operation") != job["operation"]
                    or result.get("request_sha256") != digest(encode(job["request"]))
                ):
                    raise ValueError("Durable worker result does not bind its frozen request")
                success = (
                    result["status"] == "completed"
                    and job["exit_code"] == 0
                    and not job["cancel_requested"]
                    and not job.get("error")
                )
                native = result.get("native") or {}
                job["result"] = result
                expected = job["request"].get("expected_identity")
                if native and (
                    native.get("schema") != "opent1d.durable-archive-result/1"
                    or native.get("task")
                    not in {"m4-study-secure", "maintained-campaign", "m3-forecast", "m3-compare"}
                    or type(native.get("integrity_verified")) is not bool
                    or type(native.get("reconstruction_verified")) is not bool
                    or type(native.get("complete")) is not bool
                    or not isinstance(native.get("package_identity"), str)
                    or len(native["package_identity"]) != 64
                    or any(c not in "0123456789abcdef" for c in native["package_identity"])
                    or not isinstance(native.get("reader_revision"), str)
                    or len(native["reader_revision"]) != 40
                    or any(c not in "0123456789abcdef" for c in native["reader_revision"])
                    or expected is not None
                    and native["package_identity"] != expected
                ):
                    raise ValueError("Durable worker native identity or result differs")
                current = directory_identity(Path(entry["root_identity"]["path"]) / entry["path"])
                if (
                    job["request"].get("archive_identity") is not None
                    and current != job["request"]["archive_identity"]
                ):
                    raise ValueError("Registered durable package directory was replaced")
                owner_clean = (
                    not job["cancel_requested"]
                    and not job.get("cleanup_forced")
                    and job.get("error") is None
                    and not job.get("remaining_owned_processes")
                )
                if native.get("integrity_verified") and owner_clean:
                    entry.update(
                        package_identity=native["package_identity"],
                        task=native["task"],
                        reader_revision=native["reader_revision"],
                        complete=native["complete"],
                        integrity="verified_snapshot",
                    )
                    entry["archive_identity"] = current
                else:
                    entry["integrity"] = "verification_failed"
                self.resolve(entry)
                fallback = result.get("reconstruction", "not_requested")
                if fallback not in {"not_requested", "reader_mismatch", "verification_failed"}:
                    fallback = "verification_failed"
                entry["reconstruction"] = (
                    "verified_snapshot"
                    if success and owner_clean and native.get("reconstruction_verified")
                    else fallback
                )
                entry["artifacts_sha256"] = {}
                entry["snapshot_job"] = None
                if success and owner_clean and native.get("reconstruction_verified"):
                    artifacts = result.get("artifacts_sha256", {})
                    if not {"report.json", "report.md"}.issubset(artifacts) or set(artifacts) - set(
                        ARTIFACTS
                    ):
                        raise ValueError("Durable reconstruction lacks native report artifacts")
                    for name, expected in artifacts.items():
                        if (
                            digest(bounded_bytes(folder / "native-report" / name, MAX_REPORT))
                            != expected
                        ):
                            raise ValueError("Durable reconstructed snapshot changed")
                    entry.update(snapshot_job=job["id"], artifacts_sha256=artifacts)
                    job["verification"] = "native_reader_verified"
                entry["error"] = result.get("error")
                entry["last_job"] = job["id"]
                entry["checked_at"] = timestamp()
                job["report_completeness"] = (
                    "complete"
                    if native.get("complete") is True
                    else "failed"
                    if native.get("complete") is False
                    else "unavailable"
                )
                if not success:
                    job["error"] = (
                        job.get("error")
                        or result.get("error")
                        or "Durable package operation failed"
                    )
            except (OSError, ValueError, KeyError, TypeError) as error:
                entry.update(
                    integrity="verification_failed",
                    reconstruction="verification_failed",
                    snapshot_job=None,
                    error=str(error)[:300],
                )
                job["error"] = job.get("error") or str(error)[:300]
            self.persist(entry)

    def get(self, identity):
        with self.service.lock:
            entry = self.lookup(identity)
            self.refresh(entry)
            result = {
                key: copy.deepcopy(value)
                for key, value in entry.items()
                if key not in {"root_identity", "archive_identity"}
            }
            result.update(
                directory=str(Path(entry["root_identity"]["path"]) / entry["path"]),
                source_freshness="not_rechecked_since_worker",
                verification_scope="verified_snapshot",
                can_view_report=bool(entry.get("snapshot_job"))
                and entry["availability"] == "available",
                can_verify=entry["availability"] == "available",
                can_reconstruct=entry["availability"] == "available",
            )
            return result

    def entries(self):
        with self.service.lock:
            return [self.get(identity) for identity in reversed(self.registered)]

    def report_bytes(self, identity, name):
        if name not in ARTIFACTS:
            raise ValueError("Unsupported durable report artifact")
        with self.service.lock:
            entry = self.lookup(identity)
            try:
                self.resolve(entry)
                if not entry.get("snapshot_job") or name not in entry["artifacts_sha256"]:
                    raise ValueError(
                        "Reconstruct this durable package before downloading its native reports"
                    )
                path = self.service.safe_path(
                    self.service.data / entry["snapshot_job"] / "native-report" / name
                )
                raw = bounded_bytes(path, MAX_REPORT)
                if digest(raw) != entry["artifacts_sha256"][name]:
                    raise ValueError("Durable reconstructed snapshot changed")
                return raw
            except (OSError, ValueError, KeyError, TypeError):
                entry.update(reconstruction="changed_since_verification", snapshot_job=None)
                self.persist(entry)
                raise

    def report(self, identity):
        raw = self.report_bytes(identity, "report.json")
        data = decode_json(raw)
        if not isinstance(data, dict):
            raise ValueError("Native report must be an object")
        return {"entry": self.get(identity), "native_report": data, "report_sha256": digest(raw)}
