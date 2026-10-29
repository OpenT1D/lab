"""Thin SDK actions and transient browser jobs; no second experiment ledger."""

import json
import threading
import time
import uuid
from datetime import UTC, datetime

from . import api
from ._gui_files import Lease, decode, encoded, outside_projects, path, read, require, sha256, write

TASKS = {"mmtt-sensitivity", "m4-study-installed"}
REPORTS = {
    "report.json": "application/json",
    "report.md": "text/markdown",
    "figure.svg": "image/svg+xml",
}
FIELDS = {
    "create": {"name"},
    "open": {"path"},
    "refresh": set(),
    "prepare": {"task", "case"},
    "freeze": {"draft", "name", "parent"},
    "plan": {"plan"},
    "check": {"plan"},
    "run": {"plan", "retry_of"},
    "verify": {"attempt", "allow_failed"},
    "relocate": {"output"},
    "attach": {"native_site", "observer_site"},
    "select_attachment": {"path"},
    "clear_attachment": set(),
}
GLOBAL = {"create", "open", "attach", "select_attachment", "clear_attachment"}


def now():
    return datetime.now(UTC).isoformat()


class Busy(ValueError):
    pass


class Controller:
    def __init__(self, workspace, *, runtime_attachment=None, sdk=api):
        self.sdk = sdk
        self.root = outside_projects(workspace)
        for name in (
            "projects",
            "inputs",
            "reports",
            "attachments",
            "journal",
            ".gui.lock",
            "catalog.json",
        ):
            outside_projects(self.root / name)
        self.root.mkdir(parents=True, exist_ok=True)
        path(self.root, directory=True)
        self.lease = Lease(self.root / ".gui.lock")
        try:
            self.installation = sdk.installation()
            for name in ("projects", "inputs", "reports", "attachments", "journal"):
                target = self.root / name
                target.mkdir(exist_ok=True)
                outside_projects(target)
                path(target, directory=True)
            self.catalog_file = self.root / "catalog.json"
            self.catalog = (
                decode(read(self.catalog_file))
                if self.catalog_file.exists()
                else {"schema": "opent1d.gui-catalog/1", "projects": {}}
            )
            require(
                set(self.catalog) == {"schema", "projects"}
                and self.catalog["schema"] == "opent1d.gui-catalog/1",
                "Unsupported GUI catalog",
            )
            require(
                isinstance(self.catalog["projects"], dict) and len(self.catalog["projects"]) <= 200,
                "Bounded project catalog required",
            )
            for key, record in self.catalog["projects"].items():
                require(
                    len(key) == 32 and set(record) == {"path", "name", "labels"},
                    "Invalid GUI project handle",
                )
                path(record["path"])
                require(
                    isinstance(record["name"], str) and isinstance(record["labels"], dict),
                    "Invalid project display metadata",
                )
            self.mutex = threading.RLock()
            self.jobs, self.requests, self.infos, self.drafts, self.plans, self.reports = (
                {},
                {},
                {},
                {},
                {},
                {},
            )
            self.active = None
            self.closing = False
            self.runtime_attachment = str(path(runtime_attachment)) if runtime_attachment else None
            self.previous = []
            for filename in sorted((self.root / "journal").glob("*.json"))[-32:]:
                record = decode(read(filename, 65536))
                if record.get("status") == "running":
                    self.previous.append(
                        {
                            "operation": record.get("operation"),
                            "status": "unobserved",
                            "message": "Previous action did not record completion. "
                            "Inspect the SDK project; no process was adopted.",
                        }
                    )
        except BaseException:
            self.lease.close()
            raise

    def state(self):
        with self.mutex:
            return json.loads(
                encoded(
                    {
                        "installation": self.installation,
                        "workspace": str(self.root),
                        "closing": self.closing,
                        "runtime_attachment": self.runtime_attachment,
                        "projects": [
                            {"id": key, **value, "info": self.infos.get(key)}
                            for key, value in self.catalog["projects"].items()
                        ],
                        "jobs": [self.public(value) for value in list(self.jobs.values())[-12:]],
                        "active": self.active["id"] if self.active else None,
                        "reports": [
                            {
                                key: value[key]
                                for key in (
                                    "id",
                                    "project",
                                    "attempt",
                                    "verified_at",
                                    "valid",
                                    "completeness",
                                    "files",
                                )
                            }
                            for value in self.reports.values()
                        ],
                        "previous_actions": self.previous,
                    }
                )
            )

    @staticmethod
    def public(job):
        return {
            key: value for key, value in job.items() if key not in {"thread", "cancel", "clock"}
        } | {
            "elapsed_seconds": round(time.monotonic() - job["clock"], 1)
            if job["status"] == "running"
            else job.get("elapsed_seconds", 0)
        }

    def get_job(self, identity):
        with self.mutex:
            return json.loads(encoded(self.public(self.jobs[identity])))

    def journal(self, job):
        value = {
            key: job.get(key)
            for key in ("id", "operation", "project", "status", "started", "finished", "error")
        }
        write(self.root / "journal" / (job["id"] + ".json"), value)

    def submit(self, request):
        require(
            isinstance(request, dict)
            and set(request) == {"request_id", "operation", "project", "arguments"},
            "Structured action required",
        )
        key, operation, project, arguments = (
            request[name] for name in ("request_id", "operation", "project", "arguments")
        )
        require(
            isinstance(key, str) and len(key) <= 64 and key.replace("-", "").isalnum(),
            "Action request ID required",
        )
        require(
            operation in FIELDS
            and isinstance(arguments, dict)
            and set(arguments) == FIELDS[operation],
            "Unsupported action fields",
        )
        require(
            (operation in GLOBAL and project is None) or project in self.catalog["projects"],
            "Choose a known project",
        )
        identity = sha256(encoded(request))
        with self.mutex:
            if key in self.requests:
                previous, job = self.requests[key]
                require(previous == identity, "Request ID was reused for different content")
                return self.public(self.jobs[job])
            if self.closing or self.active is not None:
                raise Busy("Another action is still running, or this server is closing")
            require(
                len(self.requests) < 512,
                "This session has reached its action limit; restart the GUI",
            )
            job = {
                "id": uuid.uuid4().hex,
                "operation": operation,
                "project": project,
                "arguments": arguments,
                "status": "running",
                "phase": "Calling the installed SDK",
                "started": now(),
                "clock": time.monotonic(),
                "cancel": threading.Event(),
                "cancelable": operation == "run",
                "cancel_requested": False,
            }
            self.jobs[job["id"]] = job
            self.requests[key] = (identity, job["id"])
            self.active = job
            try:
                self.journal(job)
                job["thread"] = threading.Thread(target=self.work, args=(job,), daemon=False)
                job["thread"].start()
            except BaseException:
                self.active = None
                self.jobs.pop(job["id"], None)
                self.requests.pop(key, None)
                raise
            return self.public(job)

    def register(self, project_path, name):
        project_path = path(project_path, directory=True)
        with self.mutex:
            for key, value in self.catalog["projects"].items():
                if value["path"] == str(project_path):
                    return key
            require(len(self.catalog["projects"]) < 200, "Project catalog is full")
            key = uuid.uuid4().hex
            self.catalog["projects"][key] = {"path": str(project_path), "name": name, "labels": {}}
            write(self.catalog_file, self.catalog)
            return key

    def work(self, job):
        try:
            result, project = self.perform(job)
            if project is not None:
                with self.mutex:
                    job.update(
                        project=project, cancelable=False, phase="Reading the saved project ledger"
                    )
                info = self.sdk.Project(self.catalog["projects"][project]["path"]).info()
                with self.mutex:
                    self.infos[project] = info
            with self.mutex:
                job.update(result=result, status="done", phase="Action finished")
        except Exception as error:
            with self.mutex:
                if job["project"] is not None:
                    self.infos.pop(job["project"], None)
                job.update(
                    status="error", phase="Action refused or interrupted", error=str(error)[:1200]
                )
        finally:
            with self.mutex:
                job.update(
                    finished=now(),
                    elapsed_seconds=round(time.monotonic() - job["clock"], 1),
                    cancelable=False,
                )
                try:
                    self.journal(job)
                except (OSError, ValueError) as error:
                    job.update(
                        status="error",
                        phase="SDK action ended; GUI journal unavailable",
                        error="Inspect the retained SDK project. GUI action metadata "
                        "could not be saved: " + str(error)[:500],
                    )
                finally:
                    self.active = None

    def perform(self, job):
        operation, args, handle = job["operation"], job["arguments"], job["project"]
        project = self.sdk.Project(self.catalog["projects"][handle]["path"]) if handle else None
        if operation == "create":
            require(
                isinstance(args["name"], str) and 1 <= len(args["name"].strip()) <= 100,
                "Enter a project name (1–100 characters)",
            )
            created = self.sdk.create_project(
                self.root / "projects" / uuid.uuid4().hex, args["name"].strip()
            )
            handle = self.register(created.path, args["name"].strip())
            return {"project": handle}, handle
        if operation == "open":
            chosen = path(args["path"], directory=True)
            self.sdk.open_project(chosen)
            handle = self.register(chosen, chosen.name)
            return {"project": handle}, handle
        if operation == "refresh":
            return {"project": handle}, handle
        if operation == "prepare":
            require(args["task"] in TASKS, "Choose a supported task")
            result = self.sdk.example(
                args["task"], self.root / "inputs" / uuid.uuid4().hex, case=args["case"]
            )
            validation = self.sdk.validate(args["task"], result["inputs"])
            key = uuid.uuid4().hex
            draft = {
                "id": key,
                "project": handle,
                "task": args["task"],
                "case": args["case"],
                "inputs": result["inputs"],
                "validation": validation,
            }
            self.drafts[key] = draft
            return draft, handle
        if operation == "freeze":
            draft = self.drafts[args["draft"]]
            require(draft["project"] == handle, "Input draft belongs to another project")
            require(
                isinstance(args["name"], str) and 1 <= len(args["name"].strip()) <= 100,
                "Enter a plan name",
            )
            result = project.freeze(draft["task"], draft["inputs"], parent=args["parent"])
            with self.mutex:
                self.catalog["projects"][handle]["labels"][result["plan"]] = args["name"].strip()
                write(self.catalog_file, self.catalog)
            return result, handle
        if operation == "plan":
            result = project.plan(args["plan"])
            self.plans[(handle, args["plan"])] = result
            return result, handle
        if operation == "check":
            result = project.check(args["plan"], runtime_attachment=self.runtime_attachment)
            return {
                key: result[key]
                for key in (
                    "task",
                    "metadata_valid",
                    "runtimes_ready",
                    "native_policy",
                    "setup_performed",
                )
            }, handle
        if operation == "run":
            detail = project.plan(args["plan"])
            require(detail["task"] in TASKS, "This historical task is available for reading only")
            result = project.run(
                args["plan"],
                retry_of=args["retry_of"],
                timeout=10800 if detail["task"] == "m4-study-installed" else 600,
                cancel=job["cancel"],
                runtime_attachment=self.runtime_attachment,
            )
            return result, handle
        if operation == "verify":
            require(
                type(args["allow_failed"]) is bool, "Explicit incomplete-evidence option required"
            )
            key = uuid.uuid4().hex
            destination = self.root / "reports" / key
            result = project.reconstruct(
                args["attempt"], destination, allow_failed=args["allow_failed"]
            )
            require(
                set(result["report_sha256"]) in ({"report.json", "report.md"}, set(REPORTS)),
                "Unsupported authoritative report roster",
            )
            for name, expected in result["report_sha256"].items():
                require(
                    sha256(read(destination / name, 64 * 1024 * 1024)) == expected,
                    "Reconstructed report bytes changed",
                )
            entries = {p.name for p in destination.iterdir()}
            require(
                entries
                in (set(result["report_sha256"]), {*result["report_sha256"], "manifest.json"}),
                "Unsupported reconstructed report directory",
            )
            record = {
                "id": key,
                "project": handle,
                "attempt": args["attempt"],
                "directory": str(destination),
                "verified_at": now(),
                "valid": True,
                "completeness": result["completeness"],
                "hashes": result["report_sha256"],
                "snapshot_hashes": {
                    name: sha256(read(destination / name, 64 * 1024 * 1024)) for name in entries
                },
                "files": sorted(result["report_sha256"]),
            }
            with self.mutex:
                self.reports[key] = record
            return {"report": key, **result}, handle
        if operation == "relocate":
            destination = outside_projects(args["output"])
            path(destination, fresh=True)
            project.relocate(destination)
            copied = self.register(
                destination, self.catalog["projects"][handle]["name"] + " — copy"
            )
            return {"project": copied, "original": handle}, copied
        if operation == "attach":
            result = self.sdk.attach_runtimes(
                args["native_site"],
                args["observer_site"],
                self.root / "attachments" / (uuid.uuid4().hex + ".json"),
            )
            self.runtime_attachment = result["attachment"]
            return result, None
        if operation == "select_attachment":
            filename = outside_projects(args["path"])
            read(filename, 16 * 1024 * 1024)
            self.runtime_attachment = str(filename)
            return {"selected": str(filename), "validated": False}, None
        if operation == "clear_attachment":
            self.runtime_attachment = None
            return {"selected": None}, None
        raise ValueError("Unsupported action")

    def report(self, identity, name):
        require(name in REPORTS, "Unknown report filename")
        with self.mutex:
            record = self.reports[identity]
            require(record["valid"], "Report copy is unavailable; verify again")
            require(name in record["hashes"], "This task has no such report file")
        try:
            directory = path(record["directory"], directory=True)
            require(
                {p.name for p in directory.iterdir()} == set(record["snapshot_hashes"]),
                "Report directory changed",
            )
            if "manifest.json" in record["snapshot_hashes"]:
                require(
                    sha256(read(directory / "manifest.json"))
                    == record["snapshot_hashes"]["manifest.json"],
                    "Report seal changed",
                )
            raw = read(directory / name, 64 * 1024 * 1024)
            require(
                sha256(raw) == record["hashes"][name], "Verified report copy changed; verify again"
            )
            return raw, REPORTS[name]
        except (ValueError, OSError):
            with self.mutex:
                record["valid"] = False
            raise

    def cancel(self, identity):
        with self.mutex:
            require(
                self.active is not None
                and self.active["id"] == identity
                and self.active["cancelable"],
                "No cancellable run is active",
            )
            self.active["cancel"].set()
            self.active["cancel_requested"] = True
            self.active["phase"] = "Stop requested; waiting for SDK cleanup"

    def begin_close(self):
        with self.mutex:
            self.closing = True
            if self.active is not None and self.active["cancelable"]:
                self.active["cancel"].set()
                self.active["cancel_requested"] = True

    def close(self):
        self.begin_close()
        with self.mutex:
            thread = self.active["thread"] if self.active else None
        if thread is not None:
            thread.join()
        self.lease.close()
