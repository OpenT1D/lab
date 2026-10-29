"""Explicit installed two-route policy and process-proxy request dispatch."""

import sys
import tempfile
from pathlib import Path

from experiments.observation_analysis.plan import runtime_identity
from experiments.shared_contracts.selected import FIXTURES
from experiments.workflows.checks import prepare_check
from experiments.workflows.registry import TASKS

from . import execution, routes, store


class Backend:
    def __init__(self, bootstrap, artifact):
        self.bootstrap = Path(bootstrap)
        self.application = {
            "schema": "opent1d.sdk-application/1",
            "descriptor_sha256": store.digest(store.encoded(artifact)),
            **{
                key: artifact[key] for key in ("source", "build_label", "tasks", "native_execution")
            },
        }

    def check(self, task, args):
        details, issues = prepare_check(task, args)
        return {
            "schema": "opent1d.installed-admission/1",
            "task": task.id,
            "metadata_valid": True,
            "metadata": details,
            "observation_path_issues": issues,
            "runtimes_ready": task.id == "mmtt-sensitivity",
            "coordinator_runtime": runtime_identity(),
            "native_policy": "unavailable-public-policy"
            if task.id == "m4-study-secure"
            else "standard-library-only",
            "setup_performed": False,
        }

    def command_for(self, task, args, *, operation="run"):
        store.require(task.id in routes.TASKS, "Unselected installed task")
        store.require(
            operation == "reconstruct" or task.id == "mmtt-sensitivity",
            "Native runtime not admitted by installed policy",
        )
        command = [
            sys.executable,
            "-I",
            "-B",
            "-S",
            str(self.bootstrap),
            "--native",
            task.id,
            operation,
        ]
        if operation == "run":
            command += ["--config", str(args.config), "--output", str(args.output)]
        else:
            command += ["--archive", str(args.archive), "--output", str(args.output)]
            if args.allow_failed:
                command.append("--allow-failed")
        return command


FIELDS = {
    "installation": set(),
    "create": {"project", "name"},
    "info": {"project"},
    "validate": {"task", "inputs"},
    "example": {"task", "output", "case"},
    "freeze": {"project", "task", "inputs", "parent"},
    "check": {"project", "plan"},
    "run": {"project", "plan", "retry_of", "timeout"},
    "reconstruct": {"project", "attempt", "output", "allow_failed"},
    "import": {"project", "plan", "archive", "retry_of"},
    "recover": {"project", "attempt", "execution_stopped"},
    "relocate": {"project", "output"},
}


def workspace_path(value, bootstrap, *, fresh=False):
    path = store.safe_path(value, fresh=fresh)
    package = bootstrap.parent
    environment = package.parents[3]
    store.require(
        not path.is_relative_to(environment) and not path.is_relative_to(package),
        "Keep projects and reports outside the installed environment",
    )
    if fresh:
        for parent in path.parents:
            store.require(
                not all(
                    (parent / name).exists()
                    for name in ("HEAD.json", "events", "work", "pending", ".lock")
                ),
                "New outputs cannot be placed inside an existing project store",
            )
    return path


def example(task, output, case):
    store.require(task in routes.TASKS, "Unselected installed task")
    store.require(
        case
        in (
            {"complete", "censored"}
            if task == "mmtt-sensitivity"
            else {"fasting", "gastric_load_15g"}
        ),
        "Unselected example case",
    )
    output.mkdir()
    if task == "mmtt-sensitivity":
        store.require(case in {"complete", "censored"}, "Unselected MMTT example")
        inputs = {}
        for name in ("package.json", "observations.csv", "settings.json"):
            source = (
                "mmtt-censored.csv"
                if name == "observations.csv" and case == "censored"
                else "mmtt-" + name
            )
            (output / name).write_bytes((FIXTURES / source).read_bytes())
            inputs[name] = str(output / name)
    else:
        store.require(case in {"fasting", "gastric_load_15g"}, "Unselected M4 example")
        name = "m4-fasting.json" if case == "fasting" else "m4-gastric-15g.json"
        target = output / "experiments/shared_contracts/fixtures" / name
        target.parent.mkdir(parents=True)
        target.write_bytes((FIXTURES / name).read_bytes())
        config = store.read(target)
        for source in config["sources"]:
            for field in ("model", "declaration"):
                relative = (FIXTURES / source[field]).resolve().relative_to(routes.ROOT)
                copied = output / relative
                copied.parent.mkdir(parents=True, exist_ok=True)
                copied.write_bytes((routes.ROOT / relative).read_bytes())
        inputs = {"config.json": str(target)}
    return {"task": task, "inputs": inputs, "scientific_evidence": "synthetic-only"}


def attempt_result(project, attempt):
    data, evidence = project.finishes[attempt]
    return {
        "attempt": attempt,
        "plan": project.attempts[attempt]["plan"],
        "result": data["result"],
        "receipt": data["receipt"],
        "evidence": str(evidence),
    }


def dispatch(request, bootstrap, artifact):
    store.require(isinstance(request, dict), "Structured installed request required")
    action = request.get("action")
    store.require(
        action in FIELDS and set(request) == {"action", *FIELDS[action]},
        "Unsupported installed request fields",
    )
    if action == "installation":
        return {
            key: artifact[key]
            for key in ("schema", "source", "build_label", "tasks", "native_execution")
        }
    if action == "example":
        output = workspace_path(request["output"], bootstrap, fresh=True)
        return example(request["task"], output, request["case"])
    if action == "validate":
        with tempfile.TemporaryDirectory(prefix="opent1d-sdk-validate-") as temporary:
            metadata = routes.capture(
                request["task"], request["inputs"], Path(temporary).resolve() / "plan"
            )
        return {
            "valid": True,
            "task": metadata["task"],
            "planned_slots": metadata["boundary"]["planned_slots"],
            "estimation_performed": False,
        }
    path = workspace_path(request["project"], bootstrap, fresh=action == "create")
    if action == "create":
        return {"project": str(store.create(path, request["name"]))}
    writing = action not in {"info", "check", "relocate"}
    backend = Backend(bootstrap, artifact)
    with store.opened(path, write_access=writing) as project:
        if action == "info":
            return {
                "project": str(path),
                "head": project.head,
                "plans": [
                    {
                        "id": identity,
                        "task": descriptor["task"],
                        "slots": descriptor["boundary"]["planned_slots"],
                    }
                    for identity, (descriptor, _) in project.plans.items()
                ],
                "attempts": [
                    {
                        "id": identity,
                        **record,
                        **(
                            {"outcome": project.finishes[identity][0]["result"]}
                            if identity in project.finishes
                            else {"outcome": "unfinished"}
                        ),
                    }
                    for identity, record in project.attempts.items()
                ],
                "reader_checks": [
                    event["data"]
                    for _, event, _ in project.events
                    if event["kind"] == "reconstruct"
                ],
            }
        if action == "freeze":
            identity = routes.freeze(
                project,
                request["task"],
                request["inputs"],
                parent=request["parent"],
                application={"identity": backend.application, "artifact": artifact},
            )
            return {"plan": identity, "task": request["task"]}
        if action == "check":
            from types import SimpleNamespace

            descriptor, folder = project.plans[request["plan"]]
            routes.validate_freeze(folder, descriptor, current=True)
            return backend.check(
                TASKS[descriptor["task"]],
                SimpleNamespace(
                    config=folder / "input"
                    if descriptor["task"] == "mmtt-sensitivity"
                    else folder / "input/config.json",
                    reference=None,
                ),
            )
        if action == "run":
            attempt = execution.execute(
                project,
                request["plan"],
                retry_of=request["retry_of"],
                timeout=request["timeout"],
                backend=backend,
            )
            return attempt_result(project, attempt)
        if action == "reconstruct":
            output = workspace_path(request["output"], bootstrap, fresh=True)
            result = execution.reconstruct(
                project,
                request["attempt"],
                output,
                allow_failed=request["allow_failed"],
                backend=backend,
            )
            return {**result, "application": backend.application}
        if action == "import":
            attempt = routes.import_attempt(
                project,
                request["plan"],
                request["archive"],
                retry_of=request["retry_of"],
                application=backend.application,
            )
            return attempt_result(project, attempt)
        if action == "recover":
            attempt = execution.recover(
                project, request["attempt"], execution_stopped=request["execution_stopped"]
            )
            return attempt_result(project, attempt)
        output = workspace_path(request["output"], bootstrap, fresh=True)
        return {"project": str(project.relocate(output))}
