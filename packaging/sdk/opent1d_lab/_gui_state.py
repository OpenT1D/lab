"""Thin SDK actions and transient browser jobs; no second experiment ledger."""

import json
import re
import threading
import time
import uuid
from datetime import UTC, datetime

from . import api
from ._gui_drafts import Drafts
from ._gui_files import Lease, decode, encoded, outside_projects, path, read, require, sha256, write
from ._gui_inputs import materialize, texts

TASKS = {"mmtt-sensitivity", "mmtt-sampling", "m4-study-installed"}
REPORTS = {
    "report.json": "application/json",
    "report.md": "text/markdown",
    "figure.svg": "image/svg+xml",
    "comparison.csv": "text/csv; charset=utf-8",
}
FIELDS = {
    "create": {"name"},
    "open": {"path"},
    "refresh": set(),
    "prepare": {"task", "case"},
    "draft_create": {"task", "name", "parent", "files"},
    "draft_save": {"draft", "revision", "name", "parent", "files"},
    "draft_validate": {"draft", "revision"},
    "draft_restore": {"draft", "revision", "selected"},
    "derive": {"plan"},
    "freeze": {"draft", "revision", "name", "parent"},
    "plan": {"plan"},
    "comparison_options": {"plan"},
    "comparison_freeze": {"definition"},
    "comparison_open": {"comparison", "at"},
    "comparison_verify": {"comparison", "at"},
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


def report_mime(name):
    require(isinstance(name, str), "Unknown report filename")
    if name in REPORTS:
        return REPORTS[name]
    require(
        re.fullmatch(r"studies/[a-z][a-z0-9_-]{0,63}/report\.(json|md)", name) is not None,
        "Unknown report filename",
    )
    return REPORTS[name.rsplit("/", 1)[-1]]


def report_snapshot(directory):
    """Retain a bounded regular report tree, including native child copies."""
    directory = path(directory, directory=True)
    files, directories = {}, set()
    for index, item in enumerate(directory.rglob("*")):
        require(index < 64, "Report copy entry limit exceeded")
        name = item.relative_to(directory).as_posix()
        if item.is_dir():
            path(item, directory=True)
            directories.add(name)
        else:
            files[name] = sha256(read(item, 64 * 1024 * 1024))
    expected = {parent for name in files for parent in (name.rsplit("/", 1)[0],) if "/" in name}
    expected |= {"studies"} if any(name.startswith("studies/") for name in files) else set()
    require(directories == expected, "Unexpected report directory")
    return files


class Busy(ValueError):
    pass


class Controller:
    def __init__(self, workspace, *, runtime_attachment=None, sdk=api):
        self.sdk = sdk
        self.root = outside_projects(workspace)
        for name in (
            "projects",
            "inputs",
            "drafts",
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
            for name in ("projects", "inputs", "drafts", "reports", "attachments", "journal"):
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
            self.draft_store = Drafts(self.root / "drafts")
            self.jobs, self.requests, self.infos, self.plans, self.reports = (
                {},
                {},
                {},
                {},
                {},
            )
            self.active = None
            self.closing = False
            self.runtime_attachment = str(path(runtime_attachment)) if runtime_attachment else None
            self.runtime_revision = 0
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
                        "runtime_revision": self.runtime_revision,
                        "projects": [
                            {"id": key, **value, "info": self.infos.get(key)}
                            for key, value in self.catalog["projects"].items()
                        ],
                        "jobs": [self.public(value) for value in list(self.jobs.values())[-12:]],
                        "active": self.active["id"] if self.active else None,
                        "reports": [
                            {
                                key: value.get(key)
                                for key in (
                                    "id",
                                    "project",
                                    "attempt",
                                    "comparison",
                                    "snapshot",
                                    "verified_at",
                                    "valid",
                                    "completeness",
                                    "files",
                                )
                            }
                            for value in self.reports.values()
                        ],
                        "drafts": self.draft_store.summaries(),
                        "draft_issues": self.draft_store.issues,
                        "previous_actions": self.previous,
                    }
                )
            )

    @staticmethod
    def compact_result(operation, result):
        if operation == "prepare" or operation == "derive" or operation.startswith("draft_"):
            return {
                key: value
                for key, value in result.items()
                if key
                in {"id", "project", "task", "name", "parent", "revision", "case", "frozen_plan"}
            }
        return result

    def public(self, job, *, draft_content=False):
        result = job.get("result")
        if draft_content and isinstance(result, dict) and "id" in result and "revision" in result:
            result = {**self.draft_store.get(result["id"], result["revision"]), **result}
        value = {
            key: value for key, value in job.items() if key not in {"thread", "cancel", "clock"}
        } | {
            "elapsed_seconds": round(time.monotonic() - job["clock"], 1)
            if job["status"] == "running"
            else job.get("elapsed_seconds", 0)
        }
        value["arguments"] = {key: item for key, item in job["arguments"].items() if key != "files"}
        if result is not None:
            value["result"] = result
        return value

    def get_job(self, identity):
        with self.mutex:
            return json.loads(encoded(self.public(self.jobs[identity], draft_content=True)))

    def get_draft(self, identity):
        with self.mutex:
            result = self.draft_store.get(identity)
            require(result["project"] in self.catalog["projects"], "Concept project is unavailable")
            result["current_application"] = self.application_id()
            return result

    def application_id(self):
        return self.installation.get("descriptor_sha256") or sha256(encoded(self.installation))

    def inspect_draft(self, draft):
        inputs = materialize(self.sdk, draft["task"], draft["files"], self.root / "inputs")
        if draft["parent"] is not None:
            project = self.sdk.Project(self.catalog["projects"][draft["project"]]["path"])
            require(
                project.plan(draft["parent"])["task"] == draft["task"],
                "Parent plan belongs to another task",
            )
        return inputs, self.sdk.inspect_inputs(draft["task"], inputs)

    def validate_draft(self, draft):
        stamp = {
            "application": self.application_id(),
            "valid": False,
            "result": None,
            "error": None,
        }
        try:
            _, stamp["result"] = self.inspect_draft(draft)
            stamp["valid"] = True
        except (ValueError, OSError, KeyError, TypeError, RuntimeError) as error:
            stamp["error"] = str(error)[:1200]
        with self.mutex:
            return self.draft_store.annotate(
                draft["id"],
                draft["revision"],
                draft["project"],
                stamp,
                frozen_plan=draft["frozen_plan"],
            )

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
            if operation == "check":
                job["check_context"] = {
                    "project": project,
                    "plan": arguments["plan"],
                    "runtime_attachment": self.runtime_attachment,
                    "runtime_revision": self.runtime_revision,
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
            if project is not None and job["operation"] not in {
                "draft_create",
                "draft_save",
                "draft_validate",
                "draft_restore",
            }:
                with self.mutex:
                    job.update(
                        project=project, cancelable=False, phase="Reading the saved project ledger"
                    )
                info = self.sdk.Project(self.catalog["projects"][project]["path"]).info()
                with self.mutex:
                    self.infos[project] = info
            with self.mutex:
                job.update(
                    result=self.compact_result(job["operation"], result),
                    status="done",
                    phase="Action finished",
                )
        except Exception as error:
            with self.mutex:
                if job["project"] is not None:
                    self.infos.pop(job["project"], None)
                job.update(
                    status="error", phase="Action refused or interrupted", error=str(error)[:1200]
                )
        finally:
            with self.mutex:
                job["arguments"] = {
                    key: item for key, item in job["arguments"].items() if key != "files"
                }
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
            with self.mutex:
                draft = self.draft_store.create(
                    handle,
                    args["task"],
                    "Supplied " + args["case"],
                    texts(args["task"], result["inputs"]),
                    origin={"kind": "example", "case": args["case"]},
                )
            draft = self.validate_draft(draft)
            # Preserve the supplied-case hint for the original M4 parent suggestion.
            draft["case"] = args["case"]
            return draft, handle
        if operation == "draft_create":
            if args["parent"] is not None:
                require(
                    project.plan(args["parent"])["task"] == args["task"],
                    "Parent plan belongs to another task",
                )
            with self.mutex:
                return self.draft_store.create(
                    handle, args["task"], args["name"], args["files"], parent=args["parent"]
                ), handle
        if operation == "draft_save":
            with self.mutex:
                return self.draft_store.save(
                    args["draft"],
                    args["revision"],
                    handle,
                    args["name"],
                    args["parent"],
                    args["files"],
                ), handle
        if operation == "draft_restore":
            with self.mutex:
                return self.draft_store.restore(
                    args["draft"], args["revision"], handle, args["selected"]
                ), handle
        if operation == "draft_validate":
            draft = self.draft_store.current(args["draft"], args["revision"], handle)
            return self.validate_draft(draft), handle
        if operation == "derive":
            result = project.export_inputs(args["plan"], self.root / "inputs" / uuid.uuid4().hex)
            require(result["task"] in TASKS, "Unsupported editable task")
            with self.mutex:
                draft = self.draft_store.create(
                    handle,
                    result["task"],
                    "Derived study",
                    texts(result["task"], result["inputs"]),
                    parent=args["plan"],
                    origin={"kind": "plan", "plan": args["plan"]},
                )
            return draft, handle
        if operation == "freeze":
            draft = self.draft_store.current(args["draft"], args["revision"], handle)
            stamp = draft["validation"]
            require(
                isinstance(stamp, dict)
                and stamp.get("valid") is True
                and stamp.get("revision") == draft["revision"]
                and stamp.get("content_sha256") == draft["content_sha256"]
                and stamp.get("application") == self.application_id(),
                "Validate this exact saved concept revision before freezing",
            )
            require(
                draft["frozen_plan"] is None,
                "This concept is already frozen; edit to derive a plan",
            )
            require(
                args["parent"] == draft["parent"],
                "Parent selection changed; save and validate again",
            )
            require(
                isinstance(args["name"], str) and 1 <= len(args["name"].strip()) <= 100,
                "Enter a plan name",
            )
            inputs, inspected = self.inspect_draft(draft)
            require(inspected == stamp["result"], "Concept inputs changed after validation")
            result = project.freeze(draft["task"], inputs, parent=draft["parent"])
            with self.mutex:
                self.catalog["projects"][handle]["labels"][result["plan"]] = args["name"].strip()
                write(self.catalog_file, self.catalog)
                self.draft_store.annotate(
                    draft["id"], draft["revision"], handle, stamp, result["plan"]
                )
            return result, handle
        if operation == "comparison_options":
            return project.comparison_options(args["plan"]), handle
        if operation == "comparison_freeze":
            return project.freeze_comparison(args["definition"]), handle
        if operation == "comparison_open":
            return project.comparison(args["comparison"], at=args["at"]), handle
        if operation == "plan":
            result = project.plan(args["plan"])
            self.plans[(handle, args["plan"])] = result
            if "scientific_input" in result:
                result = {
                    **result,
                    "scientific_input_text": json.dumps(
                        result["scientific_input"], indent=2, sort_keys=True, allow_nan=False
                    ),
                }
            return result, handle
        if operation == "check":
            result = project.check(
                args["plan"], runtime_attachment=job["check_context"]["runtime_attachment"]
            )
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
        if operation in {"verify", "comparison_verify"}:
            key = uuid.uuid4().hex
            destination = self.root / "reports" / key
            if operation == "verify":
                require(
                    type(args["allow_failed"]) is bool,
                    "Explicit incomplete-evidence option required",
                )
                result = project.reconstruct(
                    args["attempt"], destination, allow_failed=args["allow_failed"]
                )
            else:
                result = project.reconstruct_comparison(
                    args["comparison"], destination, at=args["at"]
                )
            names = set(result["report_sha256"])
            require({"report.json", "report.md"} <= names, "Report roster")
            require(len(names) <= 10, "Unsupported authoritative report roster")
            require(
                ("comparison.csv" in names) == (operation == "comparison_verify"),
                "Comparison/native report families differ",
            )
            for name in names:
                report_mime(name)
            children = {name for name in names if name.startswith("studies/")}
            require(not children or "figure.svg" not in names, "Mixed report families")
            require(
                all(
                    name.rsplit(".", 1)[0] + ".json" in names
                    and name.rsplit(".", 1)[0] + ".md" in names
                    for name in children
                ),
                "Incomplete child report roster",
            )
            for name, expected in result["report_sha256"].items():
                require(
                    sha256(read(destination / name, 64 * 1024 * 1024)) == expected,
                    "Reconstructed report bytes changed",
                )
            entries = report_snapshot(destination)
            require(
                set(entries) in (names, names | {"manifest.json"}),
                "Unsupported reconstructed report directory",
            )
            record = {
                "id": key,
                "project": handle,
                "attempt": args.get("attempt"),
                "comparison": args.get("comparison"),
                "snapshot": result.get("snapshot"),
                "directory": str(destination),
                "verified_at": now(),
                "valid": True,
                "completeness": result["completeness"],
                "hashes": result["report_sha256"],
                "snapshot_hashes": entries,
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
            with self.mutex:
                self.draft_store.clone_project(handle, copied)
            return {"project": copied, "original": handle}, copied
        if operation == "attach":
            result = self.sdk.attach_runtimes(
                args["native_site"],
                args["observer_site"],
                self.root / "attachments" / (uuid.uuid4().hex + ".json"),
            )
            self.select_runtime(result["attachment"])
            return result, None
        if operation == "select_attachment":
            filename = outside_projects(args["path"])
            read(filename, 16 * 1024 * 1024)
            self.select_runtime(str(filename))
            return {"selected": str(filename), "validated": False}, None
        if operation == "clear_attachment":
            self.select_runtime(None)
            return {"selected": None}, None
        raise ValueError("Unsupported action")

    def select_runtime(self, attachment):
        with self.mutex:
            self.runtime_attachment = attachment
            self.runtime_revision += 1

    def report(self, identity, name):
        mime = report_mime(name)
        with self.mutex:
            record = self.reports[identity]
            require(record["valid"], "Report copy is unavailable; verify again")
            require(name in record["hashes"], "This task has no such report file")
        try:
            directory = path(record["directory"], directory=True)
            require(
                report_snapshot(directory) == record["snapshot_hashes"],
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
            return raw, mime
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
