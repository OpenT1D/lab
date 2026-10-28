"""Freeze inputs and supervise known CLI operations outside scientific archives."""

import hashlib
import json
import os
import re
import signal
import stat
import subprocess
import sys
import threading
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

from experiments.platform_files import atomic_write_bytes, is_link, native_absolute, open_regular
from experiments.workflows.checks import safe_environment

from .locking import WorkspaceLock
from .ownership import Ownership
from .packaged_phases import cleanup_seconds as phased_cleanup
from .packaged_phases import command as phased_command
from .packaged_phases import public_phase

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CONTRACT = json.loads((HERE / "contract.json").read_text())
TASK = CONTRACT["task"]
ID = re.compile(r"[a-z][a-z0-9_-]{0,63}\Z")
MAX_JSON = 65536
CLEANUP_SECONDS = 30
CAMPAIGN_CLEANUP_SECONDS = 90
CAMPAIGN_OPERATIONS = frozenset(
    {
        "campaign_check",
        "campaign_install",
        "campaign_run",
        "campaign_resume",
        "campaign_reconstruct",
    }
)
DURABLE_OPERATIONS = frozenset(
    "durable_" + name for name in ("export", "register", "verify", "reconstruct", "forensic")
)
M3_OPERATIONS = frozenset("m3_" + name for name in ("fixture", "check", "run", "reconstruct"))
M3_TASKS = frozenset({"m3-forecast", "m3-compare"})
OBSERVATION_OPERATIONS = frozenset(
    prefix + name
    for prefix in ("observation_", "sampling_")
    for name in ("example", "freeze", "run", "reconstruct")
)
LIBRARY_OPERATIONS = frozenset({"library_index", "library_verify"})
MAX_JOURNAL = 8388608
MAX_REPORT = 67108864
MAX_ARCHIVE_BYTES = 2147483648
INVENTORY_SECONDS = 30


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    return json.dumps(value, sort_keys=True, indent=2, allow_nan=False).encode() + b"\n"


def timestamp():
    return datetime.now(UTC).isoformat()


def decode_json(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result

    def nonfinite(_value):
        raise ValueError("Nonfinite JSON value")

    try:
        return json.loads(raw, object_pairs_hook=unique, parse_constant=nonfinite)
    except RecursionError as error:
        raise ValueError("JSON nesting exceeds the supported reader") from error


def read_json(path, maximum=MAX_JOURNAL):
    return decode_json(bounded_bytes(path, maximum))


def bounded_bytes(path, maximum):
    descriptor = open_regular(path)
    with os.fdopen(descriptor, "rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > maximum:
            raise ValueError("File is nonregular or exceeds the task byte limit")
        raw = stream.read(maximum + 1)
        after = os.fstat(stream.fileno())
    current = path.stat()

    def identity(value):
        return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns

    if identity(before) != identity(after) or identity(after) != identity(current):
        raise ValueError("File changed while reading")
    if len(raw) > maximum:
        raise ValueError("File exceeds the task byte limit")
    return raw


def inventory(folder, *, files=False):
    """Hash regular archive bytes without executing or following archived links."""
    entries, total, inspected = {}, 0, 0
    deadline = time.monotonic() + INVENTORY_SECONDS
    if is_link(folder) or not folder.is_dir():
        raise ValueError("Choose a regular archive directory")
    for path in folder.rglob("*"):
        inspected += 1
        if inspected > 100000 or time.monotonic() >= deadline:
            raise ValueError("Archive inventory exceeds its bounded reader")
        if is_link(path):
            raise ValueError("Symlink archive entries are unavailable")
        if path.is_dir():
            continue
        if not path.is_file() or len(entries) >= 50000:
            raise ValueError("Unsupported archive inventory")
        before = path.stat()
        total += before.st_size
        if total > MAX_ARCHIVE_BYTES:
            raise ValueError("Archive inventory exceeds its byte limit")
        sha = hashlib.sha256()
        descriptor = open_regular(path)
        with os.fdopen(descriptor, "rb") as stream:
            opened = os.fstat(stream.fileno())
            if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (
                before.st_dev,
                before.st_ino,
            ):
                raise ValueError("Archive entry changed or became nonregular")
            consumed = 0
            while chunk := stream.read(1048576):
                consumed += len(chunk)
                if consumed > before.st_size or time.monotonic() >= deadline:
                    raise ValueError("Archive changed or exceeds its bounded reader")
                sha.update(chunk)
        after = path.stat()
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        ):
            raise ValueError("Archive changed while reading")
        entries[path.relative_to(folder).as_posix()] = sha.hexdigest()
    return entries if files else digest(encode(entries))


class Service:
    def __init__(
        self,
        root=ROOT,
        *,
        python=None,
        archive_roots=(),
        archive_store=None,
        profile="checkout",
        source_root=None,
    ):
        if profile not in {"checkout", "desktop"}:
            raise ValueError("Unknown application capability profile")
        self.profile = profile
        self.root = native_absolute(root).resolve(strict=True)
        self.source_root = Path(source_root or self.root).resolve(strict=True)
        self.python = str(Path(python or sys.executable).absolute())
        self.data = self.root / "results" / "gui"
        self.safe_path("results/gui", exists=False)
        self.data.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.configurations = {}
        self.jobs = {}
        self.verification_checks = {}
        self.active = None
        self.process = None
        self.thread = None
        self.closing = False
        self.manager = WorkspaceLock(self.data / ".manager.lock")
        try:
            self.example_prefix = ""
            if self.profile == "desktop":
                from experiments.desktop.examples import prepare

                self.example_prefix = prepare(self.source_root, self.root) + "/"
            self.load_journals()
            from .durable import Durable, store_identity
            from .library import Library

            store = store_identity(self.root, archive_store)
            roots = (*archive_roots, *((store["path"],) if store else ()))
            self.library = Library(self, roots)
            from .campaigns import Campaigns

            self.campaigns = Campaigns(self)
            self.durable = Durable(self, store)
            from .m3 import M3

            self.m3 = M3(self)
            from .observations import Observations

            self.observations = Observations(self)
            from .sampling import Sampling

            self.sampling = Sampling(self)
        except BaseException:
            self.manager.close()
            raise

    def load_journals(self):
        # A restart cannot adopt a persisted PID: it may now belong to another process.
        for directory in sorted(self.data.glob("job-*")):
            if is_link(directory) or not (directory / "job.json").is_file():
                continue
            try:
                self.safe_path(directory.relative_to(self.root))
                journal = self.safe_path(directory / "job.json", suffix=".json")
                job = read_json(journal)
                if not isinstance(job, dict):
                    continue
                if job.get("id") != directory.name or job.get("schema") != "opent1d.gui-job/1":
                    continue
                if job.get("operation") in LIBRARY_OPERATIONS:
                    from experiments.catalogue.formats import TASKS as CATALOGUE_TASKS

                    from .library_worker import REQUEST

                    request = job.get("request")
                    if (
                        not isinstance(request, dict)
                        or request.get("schema") != REQUEST
                        or request.get("operation") != job["operation"]
                        or not isinstance(request.get("entry"), dict)
                        or request["entry"].get("task") not in CATALOGUE_TASKS
                        or job.get("task") not in {TASK, request["entry"]["task"]}
                    ):
                        continue
                    # Older library journals used the M4 label for every task.
                    job["task"] = request["entry"]["task"]
                if (
                    (
                        job.get("task") not in CATALOGUE_TASKS
                        if job.get("operation") in LIBRARY_OPERATIONS
                        else job.get("task") not in M3_TASKS
                        if job.get("operation") in M3_OPERATIONS
                        else job.get("task") not in {"mmtt-sensitivity", "mmtt-sampling"}
                        if job.get("operation") in OBSERVATION_OPERATIONS
                        else job.get("task") != TASK
                    )
                    or job.get("operation") not in CONTRACT["operations"]
                    or job.get("state") not in CONTRACT["job_states"]
                ):
                    continue
                if (
                    not isinstance(job.get("commands", []), list)
                    or job.get("result") is not None
                    and not isinstance(job["result"], dict)
                ):
                    continue
                if job["operation"] in M3_OPERATIONS:
                    from .m3 import validate_request

                    request = validate_request(job.get("request"))
                    if request["task"] != job["task"] or request["operation"] != job["operation"]:
                        continue
                if job["operation"] in OBSERVATION_OPERATIONS:
                    from .observations import validate_request as validate_observation_request

                    if job["operation"].startswith("sampling_"):
                        from .sampling import Sampling

                        request = validate_observation_request(
                            job.get("request"),
                            task=Sampling.task,
                            operations=Sampling.operations,
                            request_schema=Sampling.request_schema,
                            cases=Sampling.cases,
                            operation_prefix=Sampling.operation_prefix,
                            id_prefix=Sampling.id_prefix,
                        )
                    else:
                        request = validate_observation_request(job.get("request"))
                    if request["task"] != job["task"] or request["operation"] != job["operation"]:
                        continue
                # Persisted markers are historical accounting, not a new live attestation.
                if job.get("verification") == "native_reader_verified":
                    job["verification"] = "recorded_verification"
                    self.persist(job)
                if job.get("state") in {"queued", "running", "cancelling"}:
                    job.update(
                        state="failed", error="Previous server stopped; ownership not adopted"
                    )
                    job["finished_at"] = timestamp()
                    self.persist(job)
                self.jobs[job["id"]] = job
            except (OSError, ValueError, TypeError):
                continue

    def safe_path(self, value, *, exists=True, suffix=None):
        path = Path(value)
        if not path.is_absolute():
            path = self.root / path
        path = native_absolute(path)
        if not path.is_relative_to(self.root) or path == self.root and suffix:
            raise ValueError("Choose a path inside the workspace")
        relative = path.relative_to(self.root)
        if any(part.startswith(".") for part in relative.parts):
            raise ValueError("Hidden workspace paths are unavailable")
        current = self.root
        for part in relative.parts:
            current /= part
            if is_link(current):
                raise ValueError("Symlink paths are unavailable")
        if exists and not path.exists():
            raise ValueError("Workspace path does not exist")
        if suffix is not None and (not path.is_file() or path.suffix != suffix):
            raise ValueError("Choose a regular " + suffix + " file")
        return path

    def defaults(self):
        return {
            "schema": CONTRACT["config_schema"],
            "sources": [
                {
                    "id": "dalla_man",
                    "model": self.example_prefix
                    + "experiments/m4/causal_secretion/example_model.py",
                    "declaration": self.example_prefix
                    + "experiments/m4/causal_secretion/example_model.json",
                },
                {
                    "id": "ultradian",
                    "model": self.example_prefix + "experiments/m4/ultradian_secretion/model.py",
                    "declaration": self.example_prefix
                    + "experiments/m4/ultradian_secretion/model.json",
                },
            ],
            "scenarios": list(CONTRACT["scenarios"]),
            "timeout_seconds": 600,
            "source_timeout_seconds": 3600,
        }

    def bootstrap(self):
        return {
            "schema": "opent1d.gui-session/1",
            "profile": self.profile,
            "task": TASK,
            "workspace": self.root.name,
            "draft_scope": digest(str(self.root).encode()),
            "defaults": self.defaults(),
            "contract": CONTRACT,
            "jobs": self.list_jobs(),
        }

    def browse(self, directory="experiments/m4", kind="model"):
        if kind not in {"model", "declaration"}:
            raise ValueError("Unknown file kind")
        if self.profile == "desktop" and directory == "experiments/m4":
            directory = self.example_prefix + directory
        folder = self.safe_path(directory)
        if not folder.is_dir():
            raise ValueError("Choose a workspace directory")
        suffix = ".py" if kind == "model" else ".json"
        entries = []
        for path in sorted(folder.iterdir(), key=lambda p: (not p.is_dir(), p.name)):
            if path.name.startswith(".") or is_link(path):
                continue
            if path.is_dir() or path.is_file() and path.suffix == suffix:
                entries.append(
                    {
                        "name": path.name,
                        "path": path.relative_to(self.root).as_posix(),
                        "kind": "directory" if path.is_dir() else "file",
                    }
                )
            if len(entries) >= 500:
                break
        parent = folder.parent.relative_to(self.root).as_posix() if folder != self.root else None
        return {
            "directory": folder.relative_to(self.root).as_posix(),
            "parent": parent,
            "entries": entries,
        }

    def configure(self, config):
        required = {"schema", "sources", "scenarios", "timeout_seconds", "source_timeout_seconds"}
        if not isinstance(config, dict) or set(config) != required:
            raise ValueError("Configuration fields differ from the supported task")
        if config["schema"] != CONTRACT["config_schema"]:
            raise ValueError("Unsupported configuration schema")
        sources = config["sources"]
        if not isinstance(sources, list) or not 2 <= len(sources) <= 8:
            raise ValueError("Choose two to eight sources")
        seen, frozen, files, snapshots = set(), [], {}, {}
        for source in sources:
            if not isinstance(source, dict) or set(source) != {"id", "model", "declaration"}:
                raise ValueError("Each source needs id, model and declaration")
            name = source["id"]
            if not isinstance(name, str) or not ID.fullmatch(name) or name in seen:
                raise ValueError("Source IDs must be unique lowercase names")
            seen.add(name)
            item = {"id": name}
            for key, suffix, maximum in (
                ("model", ".py", 1048576),
                ("declaration", ".json", MAX_JSON),
            ):
                if not isinstance(source[key], str) or not source[key] or "\0" in source[key]:
                    raise ValueError("Invalid source path")
                path = self.safe_path(source[key], suffix=suffix)
                raw = bounded_bytes(path, maximum)
                item[key] = str(path)
                files[str(path)] = digest(raw)
                snapshots[(name, key)] = raw
            frozen.append(item)
        scenes = config["scenarios"]
        if (
            not isinstance(scenes, list)
            or not 1 <= len(scenes) <= 3
            or any(not isinstance(s, str) or s not in CONTRACT["scenarios"] for s in scenes)
            or len(set(scenes)) != len(scenes)
        ):
            raise ValueError("Choose a unique nonempty scenario subset")
        for key, (minimum, maximum) in CONTRACT["budgets"].items():
            if type(config[key]) is not int or not minimum <= config[key] <= maximum:
                raise ValueError("Invalid " + key)
        config = {**config, "sources": frozen}
        with self.lock:
            identity = "config-" + uuid.uuid4().hex
            folder = self.data / identity
            folder.mkdir()
            for source in frozen:
                bundle = folder / "sources" / source["id"]
                bundle.mkdir(parents=True)
                for key, filename in (("model", "model.py"), ("declaration", "model.json")):
                    path = bundle / filename
                    raw = snapshots[(source["id"], key)]
                    path.write_bytes(raw)
                    source[key] = str(path)
                    files[str(path)] = digest(raw)
            raw = encode(config)
            (folder / "config.json").write_bytes(raw)
            record = {
                "id": identity,
                "config": config,
                "sha256": digest(raw),
                "source_sha256": files,
                "ready": False,
                "created_at": timestamp(),
            }
            (folder / "frozen.json").write_bytes(encode(record))
            self.configurations[identity] = record
            return record.copy()

    def resolve_configuration(self, identity):
        """Read only this checkout's frozen study inputs; never adopt saved readiness."""
        if not isinstance(identity, str) or re.fullmatch(r"config-[0-9a-f]{32}", identity) is None:
            raise ValueError("Unknown frozen study configuration")
        with self.lock:
            if identity not in self.configurations:
                folder = self.safe_path(self.data / identity)
                record = read_json(self.safe_path(folder / "frozen.json", suffix=".json"), MAX_JSON)
                if (
                    not isinstance(record, dict)
                    or set(record)
                    != {"id", "config", "sha256", "source_sha256", "ready", "created_at"}
                    or record["id"] != identity
                    or not isinstance(record["config"], dict)
                    or record["config"].get("schema") != CONTRACT["config_schema"]
                    or not isinstance(record["source_sha256"], dict)
                    or not isinstance(record["sha256"], str)
                    or re.fullmatch(r"[0-9a-f]{64}", record["sha256"]) is None
                ):
                    raise ValueError("Malformed frozen study configuration")
                sources = record["config"].get("sources")
                if not isinstance(sources, list) or not 2 <= len(sources) <= 8:
                    raise ValueError("Malformed frozen source roster")
                names = set()
                for source in sources:
                    if (
                        not isinstance(source, dict)
                        or set(source) != {"id", "model", "declaration"}
                        or not isinstance(source["id"], str)
                        or not ID.fullmatch(source["id"])
                        or source["id"] in names
                    ):
                        raise ValueError("Malformed frozen source")
                    names.add(source["id"])
                    for key, name in (("model", "model.py"), ("declaration", "model.json")):
                        expected = str(folder / "sources" / source["id"] / name)
                        if source[key] != expected or expected not in record["source_sha256"]:
                            raise ValueError("Frozen source does not belong to its configuration")
                if any(
                    not isinstance(name, str)
                    or not isinstance(sha, str)
                    or re.fullmatch(r"[0-9a-f]{64}", sha) is None
                    for name, sha in record["source_sha256"].items()
                ):
                    raise ValueError("Malformed frozen source identities")
                path = self.safe_path(folder / "config.json", suffix=".json")
                if read_json(path, MAX_JSON) != record["config"]:
                    raise ValueError("Frozen configuration record differs from its bytes")
                record["ready"] = False
                self.unchanged(record)
                self.configurations[identity] = record
            configuration = self.configurations[identity]
            self.unchanged(configuration)
            return configuration

    def invalidate_readiness(self):
        """Any attempted shared-runtime installation invalidates every prior check."""
        for configuration in self.configurations.values():
            configuration["ready"] = False
        self.campaigns.invalidate_readiness()
        self.m3.invalidate_readiness()

    def configure_campaign(self, body):
        with self.lock:
            if self.closing or self.active is not None:
                raise ValueError("One active operation is allowed; wait or cancel it")
            return self.campaigns.configure(body)

    def start_campaign(self, operation, *, configuration_id=None, campaign_id=None):
        with self.lock:
            if self.closing or self.active is not None:
                raise ValueError("One active operation is allowed; wait or cancel it")
            request = self.campaigns.request(
                operation, configuration_id=configuration_id, campaign_id=campaign_id
            )
            return self.start_owned(operation, request)

    def unchanged(self, configuration):
        path = self.safe_path(self.data / configuration["id"] / "config.json", suffix=".json")
        if digest(bounded_bytes(path, MAX_JSON)) != configuration["sha256"]:
            raise ValueError("Frozen configuration changed; save a new configuration")
        for name, expected in configuration["source_sha256"].items():
            path = self.safe_path(name)
            if not path.is_file() or digest(bounded_bytes(path, 1048576)) != expected:
                raise ValueError("Frozen source changed; save a new configuration")
        return path

    def persist(self, job):
        path = self.data / job["id"] / "job.json"
        temporary = path.with_suffix(".tmp")
        atomic_write_bytes(path, encode(job), temporary=temporary)

    def list_jobs(self):
        for identity in tuple(self.jobs):
            self.refresh_verification(identity, force=False)
        with self.lock:
            return [self.public(job) for job in reversed(list(self.jobs.values()))]

    def public(self, job):
        result = {**json.loads(json.dumps(job)), "verification_scope": "recorded_job_receipt"}
        phase = public_phase(job, self.data / job["id"])
        if phase is not None:
            result["phase"] = phase
        return result

    def get_job(self, identity, *, validate=False):
        if validate:
            self.refresh_verification(identity, force=False)
        with self.lock:
            if identity not in self.jobs:
                raise ValueError("Unknown local job")
            return self.public(self.jobs[identity])

    def start(self, operation, configuration_id=None, archive_job=None):
        if operation not in {"check", "install", "run", "reconstruct"}:
            raise ValueError("Unsupported operation")
        with self.lock:
            if self.closing or self.active is not None:
                raise ValueError("One active operation is allowed; wait or cancel it")
            configuration, archive = None, None
            if operation == "reconstruct":
                original = self.get_job(archive_job)
                if original["operation"] != "run" or original["state"] in {
                    "queued",
                    "running",
                    "cancelling",
                }:
                    raise ValueError("Choose a finished study")
                archive = self.safe_path(self.data / archive_job / "archive", exists=False)
                if not (archive / "manifest.json").is_file():
                    raise ValueError("The study has no sealed archive to reconstruct")
            else:
                if configuration_id not in self.configurations:
                    raise ValueError("Save this configuration first")
                configuration = self.configurations[configuration_id]
                self.unchanged(configuration)
                if operation == "run" and not configuration["ready"]:
                    raise ValueError("Check this configuration and its runtimes before starting")
            if operation == "install":
                self.invalidate_readiness()
            identity = "job-" + uuid.uuid4().hex
            folder = self.data / identity
            folder.mkdir()
            job = {
                "schema": "opent1d.gui-job/1",
                "id": identity,
                "task": TASK,
                "operation": operation,
                "state": "queued",
                "created_at": timestamp(),
                "configuration": configuration_id,
                "archive_job": archive_job,
                "exit_code": None,
                "result": None,
                "error": None,
                "verification": "not_requested",
                "report_completeness": "unavailable",
                "cancel_requested": False,
                "cleanup_forced": False,
                "pid": None,
                "commands": [],
                "archive": str(folder / "archive") if operation == "run" else None,
            }
            self.jobs[identity] = job
            self.active = identity
            self.persist(job)
            self.thread = threading.Thread(
                target=self.work, args=(identity, configuration, archive), daemon=True
            )
            self.thread.start()
            return self.public(job)

    def start_owned(self, operation, request):
        """Start a fixed archive operation under the existing workspace owner."""
        if (
            operation
            not in {"library_index", "library_verify"}
            | CAMPAIGN_OPERATIONS
            | DURABLE_OPERATIONS
            | M3_OPERATIONS
            | OBSERVATION_OPERATIONS
        ):
            raise ValueError("Unsupported owned operation")
        with self.lock:
            if self.closing or self.active is not None:
                raise ValueError("One active operation is allowed; wait or cancel it")
            if operation == "campaign_install":
                self.invalidate_readiness()
            identity = "job-" + uuid.uuid4().hex
            folder = self.data / identity
            folder.mkdir()
            job = {
                "schema": "opent1d.gui-job/1",
                "id": identity,
                "task": TASK,
                "operation": operation,
                "request": request,
                "state": "queued",
                "created_at": timestamp(),
                "configuration": None,
                "archive_job": None,
                "archive": None,
                "exit_code": None,
                "result": None,
                "error": None,
                "verification": "not_requested",
                "report_completeness": "unavailable",
                "cancel_requested": False,
                "cleanup_forced": False,
                "pid": None,
                "commands": [],
            }
            if operation in LIBRARY_OPERATIONS:
                job["task"] = request["entry"]["task"]
            if operation in CAMPAIGN_OPERATIONS:
                self.campaigns.started(job)
            if operation in M3_OPERATIONS:
                self.m3.started(job)
            if operation in OBSERVATION_OPERATIONS:
                self.observation_controller(operation).started(job)
            self.jobs[identity] = job
            self.active = identity
            self.persist(job)
            self.thread = threading.Thread(
                target=self.work, args=(identity, None, None), daemon=True
            )
            self.thread.start()
            return self.public(job)

    def add_archive(self, body):
        with self.lock:
            if self.closing or self.active is not None:
                raise ValueError("One active operation is allowed; wait or cancel it")
            return self.start_owned("library_index", self.library.add(body))

    def verify_archive(self, identity):
        with self.lock:
            if self.closing or self.active is not None:
                raise ValueError("One active operation is allowed; wait or cancel it")
            return self.start_owned("library_verify", self.library.verify(identity))

    def start_durable(self, operation, body=None, identity=None):
        with self.lock:
            if self.closing or self.active is not None:
                raise ValueError("One active operation is allowed; wait or cancel it")
            if operation == "durable_export":
                request = self.durable.export(body)
            elif operation == "durable_register":
                request = self.durable.register(body)
            elif operation == "durable_forensic":
                request = self.durable.retain_m3(identity)
            else:
                request = self.durable.operation(operation, identity)
            return self.start_owned(operation, request)

    def configure_m3(self, body):
        with self.lock:
            return self.m3.configure(body)

    def start_m3(self, operation, *, configuration_id=None, entry_id=None):
        with self.lock:
            if self.closing or self.active is not None:
                raise ValueError("One active operation is allowed; wait or cancel it")
            request = self.m3.request(
                operation, configuration_id=configuration_id, entry_id=entry_id
            )
            return self.start_owned(operation, request)

    def observation_controller(self, operation):
        return self.sampling if operation.startswith("sampling_") else self.observations

    def start_observations(self, operation, *, configuration_id=None, entry_id=None, case=None):
        with self.lock:
            controller = self.observation_controller(operation)
            controller.idle()
            request = controller.request(
                operation, configuration_id=configuration_id, entry_id=entry_id, case=case
            )
            return self.start_owned(operation, request)

    def commands(self, job, configuration, archive):
        if job["operation"] in OBSERVATION_OPERATIONS:
            return self.observation_controller(job["operation"]).commands(job)
        if job["operation"] in M3_OPERATIONS:
            return self.m3.commands(job)
        if job["operation"] in DURABLE_OPERATIONS:
            return self.durable.commands(job)
        if job["operation"] in CAMPAIGN_OPERATIONS:
            return self.campaigns.commands(job)
        if job["operation"] in {"library_index", "library_verify"}:
            return self.library.commands(job)
        base = [self.python, "-B", "-E", "-s"]
        folder = self.data / job["id"]
        operation = job["operation"]
        if operation == "install":
            return [
                (
                    base
                    + [
                        "-m",
                        "experiments.setup",
                        "plan",
                        TASK,
                        "--output",
                        str(folder / "setup-plan"),
                    ],
                    30,
                ),
                (
                    base
                    + [
                        "-m",
                        "experiments.setup",
                        "install",
                        "--plan",
                        str(folder / "setup-plan"),
                        "--output",
                        str(folder / "setup-receipt"),
                    ],
                    1800,
                ),
            ]
        if operation == "reconstruct":
            return [
                phased_command(
                    base
                    + [
                        "-S",
                        "-m",
                        "experiments.workflows",
                        "reconstruct",
                        TASK,
                        "--archive",
                        str(archive),
                        "--output",
                        str(folder / "reconstructed"),
                        "--allow-failed",
                    ],
                    TASK,
                    folder,
                    30,
                    600,
                    reconstruction=True,
                    source_root=self.source_root,
                )
            ]
        path = self.data / configuration["id"] / "config.json"
        args = base + ["-m", "experiments.workflows", operation, TASK, "--config", str(path)]
        budget = 30
        if operation == "run":
            args.extend(["--output", str(folder / "archive")])
            budget = (
                7200
                + len(configuration["config"]["sources"])
                * configuration["config"]["source_timeout_seconds"]
            )
        return [
            phased_command(
                args,
                TASK,
                folder,
                30,
                budget if operation == "run" else None,
                source_root=self.source_root,
            )
        ]

    def work(self, identity, configuration, archive):
        job = self.jobs[identity]
        folder = self.data / identity
        library_finished = False
        campaign_finished = False
        durable_finished = False
        m3_finished = False
        observations_finished = False
        cleanup_seconds = (
            CAMPAIGN_CLEANUP_SECONDS if job["operation"] in CAMPAIGN_OPERATIONS else CLEANUP_SECONDS
        )
        try:
            before_files = inventory(archive, files=True) if archive is not None else None
            before_inventory = digest(encode(before_files)) if before_files is not None else None
            for index, (argv, budget) in enumerate(self.commands(job, configuration, archive)):
                cleanup_seconds = phased_cleanup(
                    argv,
                    job["task"],
                    job["operation"],
                    cleanup_seconds,
                    source_root=self.source_root,
                )
                if configuration is not None:
                    self.unchanged(configuration)
                with self.lock:
                    if job["cancel_requested"]:
                        break
                    job.update(state="running", started_at=timestamp())
                    job["commands"].append(
                        {
                            "argv": argv,
                            "timeout_seconds": budget,
                            "cleanup_seconds": cleanup_seconds,
                        }
                    )
                    self.persist(job)
                    log_path = folder / f"command-{index + 1}.log"
                    log = log_path.open("xb")
                    ownership = None
                    try:
                        options = {
                            "cwd": self.source_root,
                            "env": safe_environment(),
                            "stdout": log,
                            "stderr": subprocess.STDOUT,
                        }
                        if os.name == "nt":
                            from .windows_process import spawn_owned

                            self.process, ownership = spawn_owned(argv, **options)
                        else:
                            self.process = subprocess.Popen(argv, start_new_session=True, **options)
                    except BaseException:
                        log.close()
                        raise
                    job["pid"] = self.process.pid
                deadline, stopped = time.monotonic() + budget, None
                try:
                    if ownership is None:
                        ownership = Ownership(self.process)
                    # Admission has already released the child. Journal failure
                    # must enter the same owned cleanup as a monitoring failure.
                    with self.lock:
                        self.persist(job)
                    while self.process.poll() is None:
                        ownership.observe()
                        with self.lock:
                            job["owned_processes"] = ownership.receipt()
                            now = time.monotonic()
                            if stopped is None and (job["cancel_requested"] or now >= deadline):
                                if not job["cancel_requested"]:
                                    job["error"] = "Operation deadline exceeded"
                                try:
                                    self.process.send_signal(signal.SIGTERM)
                                except ProcessLookupError:
                                    pass
                                stopped = now
                            if stopped is not None and now - stopped >= cleanup_seconds:
                                job["cleanup_forced"] = True
                                try:
                                    if os.name == "nt":
                                        self.process.kill()
                                    else:
                                        os.killpg(self.process.pid, signal.SIGKILL)
                                except ProcessLookupError:
                                    pass
                        time.sleep(0.05)
                    job["exit_code"] = self.process.wait()
                finally:
                    log.close()
                    with self.lock:
                        if self.process.poll() is None:
                            self.process.terminate()
                    if ownership is not None:
                        try:
                            leftovers = ownership.observe()
                            if (
                                leftovers
                                and job["exit_code"] == 0
                                and stopped is None
                                and not job["cancel_requested"]
                            ):
                                job["error"] = "Entry owner exited with live descendants"
                            grace = (
                                cleanup_seconds
                                if stopped is None
                                else max(0, stopped + cleanup_seconds - time.monotonic())
                            )
                            forced, remaining = ownership.cleanup(grace)
                            job["cleanup_forced"] = job["cleanup_forced"] or forced
                            job["remaining_owned_processes"] = remaining
                            if remaining:
                                job["error"] = (
                                    "Owned descendants remain alive after bounded cleanup"
                                )
                                self.closing = True
                        except (OSError, ValueError):
                            # Metadata failure must not abandon already observed live ownership.
                            ownership.signal(getattr(signal, "SIGKILL", 9))
                            self.closing = True
                            raise
                        finally:
                            job["owned_processes"] = ownership.receipt()
                            if os.name == "nt":
                                ownership.close()
                    elif self.process.poll() is None:
                        # Still the direct live Popen child; never a persisted PID.
                        if os.name == "nt":
                            self.process.kill()
                        else:
                            os.killpg(self.process.pid, signal.SIGKILL)
                    self.process.wait(timeout=2)
                    with self.lock:
                        self.process = None
                # Full log hash uses streaming; only its bounded tail is parsed.
                log_digest = hashlib.sha256()
                with log_path.open("rb") as stream:
                    while chunk := stream.read(1048576):
                        log_digest.update(chunk)
                    stream.seek(max(0, stream.tell() - 8388608))
                    raw = stream.read(8388608)
                if len(raw) <= 8388608:
                    for line in reversed(raw.splitlines()):
                        try:
                            result = decode_json(line)
                            if isinstance(result, dict):
                                job["result"] = result
                                break
                        except (ValueError, UnicodeDecodeError):
                            continue
                job["commands"][-1]["exit_code"] = job["exit_code"]
                job["commands"][-1]["log_sha256"] = log_digest.hexdigest()
                if job["exit_code"] or job["cancel_requested"]:
                    break
            if job["operation"] in {"library_index", "library_verify"}:
                library_finished = True
                self.library.finish(job)
            if job["operation"] in CAMPAIGN_OPERATIONS:
                campaign_finished = True
                self.campaigns.finish(job)
            if job["operation"] in DURABLE_OPERATIONS:
                durable_finished = True
                self.durable.finish(job)
            if job["operation"] in M3_OPERATIONS:
                m3_finished = True
                self.m3.finish(job)
            if job["operation"] in OBSERVATION_OPERATIONS:
                observations_finished = True
                self.observation_controller(job["operation"]).finish(job)
            result = job["result"] or {}
            if configuration is not None and job["operation"] == "check":
                configuration["ready"] = job["exit_code"] == 0 and result.get("ready") is True
            elif configuration is not None and job["operation"] == "install":
                # Installed environments do not validate the scientific configuration.
                configuration["ready"] = False
            job["report_completeness"] = result.get("report_completeness", "unavailable")
            if archive is not None and inventory(archive) != before_inventory:
                raise ValueError("Source archive changed during reconstruction")
            if job["operation"] == "reconstruct" and job["exit_code"] == 0 and job["error"] is None:
                rebuilt_files = inventory(folder / "reconstructed", files=True)
                rebuilt_inventory = digest(encode(rebuilt_files))
                artifacts = {"report.json", "report.md", "figure.svg"}
                source_artifacts = {
                    name: before_files[name] for name in artifacts if name in before_files
                }
                rebuilt_artifacts = {
                    name: rebuilt_files[name] for name in artifacts if name in rebuilt_files
                }
                if rebuilt_artifacts != source_artifacts or "report.json" not in source_artifacts:
                    raise ValueError(
                        "Reconstructed artifacts differ from the verified source reports"
                    )
                job["verification"] = "native_reader_verified"
                job["verified_inventory"] = rebuilt_inventory
                job["verified_artifacts_sha256"] = rebuilt_artifacts
                job["verified_source_inventory"] = before_inventory
                original = self.jobs[job["archive_job"]]
                original["verification"] = "native_reader_verified"
                original["verified_at"] = timestamp()
                original["verified_inventory"] = before_inventory
                original["verified_artifacts_sha256"] = source_artifacts
                self.persist(original)
        except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
            job["error"] = str(error)
        finally:
            if job["operation"] in {"library_index", "library_verify"} and not library_finished:
                try:
                    self.library.finish(job)
                except (OSError, ValueError, KeyError, TypeError) as error:
                    job["error"] = job["error"] or str(error)
            if job["operation"] in CAMPAIGN_OPERATIONS and not campaign_finished:
                try:
                    self.campaigns.finish(job)
                except (OSError, ValueError, KeyError, TypeError) as error:
                    job["error"] = job["error"] or str(error)
            if job["operation"] in DURABLE_OPERATIONS and not durable_finished:
                try:
                    self.durable.finish(job)
                except (OSError, ValueError, KeyError, TypeError) as error:
                    job["error"] = job["error"] or str(error)
            if job["operation"] in M3_OPERATIONS and not m3_finished:
                try:
                    self.m3.finish(job)
                except (OSError, ValueError, KeyError, TypeError) as error:
                    job["error"] = job["error"] or str(error)
            if job["operation"] in OBSERVATION_OPERATIONS and not observations_finished:
                try:
                    self.observation_controller(job["operation"]).finish(job)
                except (OSError, ValueError, KeyError, TypeError) as error:
                    job["error"] = job["error"] or str(error)
            with self.lock:
                if job["cancel_requested"] and not job["cleanup_forced"] and job["error"] is None:
                    job["state"] = "cancelled"
                else:
                    job["state"] = (
                        "completed" if job["exit_code"] == 0 and not job["error"] else "failed"
                    )
                job["finished_at"] = timestamp()
                job["pid"] = None
                try:
                    self.persist(job)
                except (OSError, ValueError, TypeError) as error:
                    # A failed journal cannot grant another operation admission.
                    # The live child is already reaped; allow shutdown to release
                    # the manager lock without retrying this failed persistence.
                    job.update(state="failed", error=job["error"] or str(error))
                    self.closing = True
                finally:
                    self.active = None

    def cancel(self, identity):
        with self.lock:
            if identity != self.active:
                raise ValueError("This job is not active")
            job = self.jobs[identity]
            job.update(cancel_requested=True, state="cancelling")
            self.persist(job)
            # The live work loop signals the entry owner exactly once. Sending
            # here too can interrupt its cooperative report/sealing cleanup.
            return self.public(job)

    def report_file(self, identity, name):
        if name not in {"report.json", "report.md", "figure.svg"}:
            raise ValueError("Unknown report artifact")
        self.refresh_verification(identity)
        job = self.get_job(identity)
        folder = "reconstructed" if job["operation"] == "reconstruct" else "archive"
        path = self.safe_path(self.data / identity / folder / name)
        if not path.is_file() or path.stat().st_size > MAX_REPORT:
            raise ValueError("Report artifact is unavailable or exceeds the display limit")
        return path

    def refresh_verification(self, identity, *, force=True):
        job = self.get_job(identity)
        if (
            job["operation"]
            in {"library_index", "library_verify"}
            | CAMPAIGN_OPERATIONS
            | DURABLE_OPERATIONS
            | M3_OPERATIONS
            | OBSERVATION_OPERATIONS
        ):
            # Owned extension receipts attest worker snapshots, not study job archives.
            return
        if job.get("verification") != "native_reader_verified":
            return
        if not force and time.monotonic() - self.verification_checks.get(identity, 0) < 5:
            return
        changed = False
        try:
            folder = "reconstructed" if job["operation"] == "reconstruct" else "archive"
            changed = inventory(self.safe_path(self.data / identity / folder)) != job.get(
                "verified_inventory"
            )
            if job["operation"] == "reconstruct":
                source = self.safe_path(self.data / job["archive_job"] / "archive")
                changed = changed or inventory(source) != job.get("verified_source_inventory")
        except (OSError, ValueError):
            changed = True
        if changed:
            with self.lock:
                self.jobs[identity]["verification"] = "changed_since_verification"
                self.persist(self.jobs[identity])
        self.verification_checks[identity] = time.monotonic()

    def report_bytes(self, identity, name):
        path = self.report_file(identity, name)
        raw = bounded_bytes(path, MAX_REPORT)
        job = self.get_job(identity)
        if job.get("verification") == "native_reader_verified" and job.get(
            "verified_artifacts_sha256", {}
        ).get(name) != digest(raw):
            with self.lock:
                self.jobs[identity]["verification"] = "changed_since_verification"
                self.persist(self.jobs[identity])
        self.refresh_verification(identity)
        return raw

    def report(self, identity):
        raw = self.report_bytes(identity, "report.json")
        data = decode_json(raw)
        if not isinstance(data, dict) or not isinstance(data.get("sources", {}), dict):
            raise ValueError("Native report must contain object metadata")
        for item in data.get("sources", {}).values():
            if not isinstance(item, dict) or not isinstance(item.get("declaration", {}), dict):
                raise ValueError("Native source metadata must be an object")
        view = {
            key: data.get(key)
            for key in (
                "schema",
                "protocol",
                "status",
                "passed",
                "denominators",
                "scenarios",
                "limitations",
            )
        }
        view["sources"] = {
            name: {
                "accepted": item.get("accepted"),
                "status": item.get("status"),
                "ancestry": item.get("declaration", {}).get("ancestry"),
            }
            for name, item in data.get("sources", {}).items()
        }
        view["verification"] = self.get_job(identity)["verification"]
        view["verification_scope"] = "current_source_and_displayed_bytes_checked"
        view["report_sha256"] = digest(raw)
        return view

    def close(self):
        with self.lock:
            self.closing = True
            if self.active is not None:
                self.cancel(self.active)
            thread = self.thread
            cleanup_seconds = (
                CAMPAIGN_CLEANUP_SECONDS
                if self.active is not None
                and self.jobs[self.active]["operation"] in CAMPAIGN_OPERATIONS
                else CLEANUP_SECONDS
            )
            if self.active is not None:
                commands = self.jobs[self.active]["commands"]
                if commands:
                    # Only the current in-memory operation owns a process.
                    # Journals are never adopted as live jobs on restart.
                    recorded = commands[-1].get("cleanup_seconds", cleanup_seconds)
                    if type(recorded) is int and recorded in {30, 60, 90}:
                        cleanup_seconds = max(cleanup_seconds, recorded)
        if thread is not None:
            thread.join(cleanup_seconds + 10)
            if thread.is_alive():
                raise ValueError("Owned operation has not finished; GUI manager lock retained")
        self.manager.close()
