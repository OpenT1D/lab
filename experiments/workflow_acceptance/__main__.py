"""Run four synthetic researcher routes through the local entry from a clean commit."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TASKS = ("p1-controller", "m3-forecast", "m4-secretion", "m5-prognosis")
REPORTS = {
    "p1-controller": ("report/report.json", "report/report.md"),
    "m3-forecast": ("report.json", "report.md"),
    "m4-secretion": ("report.json", "report.md", "figure.svg"),
    "m5-prognosis": ("report.json", "report.md"),
}
CONTROLS = {"UV_NO_SYNC": "1", "UV_PYTHON_DOWNLOADS": "never", "UV_OFFLINE": "1"}


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save(path, value):
    Path(path).write_text(
        json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )


def require(condition, message):
    if not condition:
        raise ValueError(message)


def inventory(directory):
    """Snapshot every child byte without following symlinks."""
    directory = Path(directory)
    require(directory.is_dir() and not directory.is_symlink(), "Archive must be a directory")
    files = {}
    for path in sorted(directory.rglob("*")):
        require(not path.is_symlink(), "Archive symlink refused")
        if path.is_file():
            files[str(path.relative_to(directory))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return files


def unchanged(directory, before):
    require(inventory(directory) == before, "Acceptance or reconstruction modified child archive")


def reports_equal(task, archive, rebuilt):
    for name in REPORTS[task]:
        counterpart = Path(name).name if task == "p1-controller" else name
        require(
            (archive / name).read_bytes() == (rebuilt / counterpart).read_bytes(),
            f"Reconstructed report differs: {name}",
        )


def native_complete(task, report):
    """Check native accounting independently of the child's exit status."""
    if task == "p1-controller":
        cases = report.get("cases", [])
        complete = (
            report.get("study_status") == "completed"
            and len(cases) == 4
            and {case.get("condition") for case in cases} == {"A", "B", "C", "D"}
            and all(case.get("status") == "completed" for case in cases)
        )
    elif task == "m3-forecast":
        evaluation = report.get("evaluation", {})
        people = evaluation.get("people", {})
        complete = (
            evaluation.get("complete_cohort") is True
            and evaluation.get("planned_people") == len(people) == 2
            and all(
                person.get("execution_status") == "completed"
                and person.get("eligible_for_primary") is True
                and person.get("attempted") == person.get("planned")
                for person in people.values()
            )
        )
    elif task == "m4-secretion":
        accounting = report.get("case_accounting", {})
        complete = (
            report.get("passed") is True
            and report.get("status") == "completed"
            and report.get("accepted_observation_cases") == 6
            and set(accounting) == {"primary", "repeat"}
            and all(
                len(cases) == 6 and all(status == "completed" for status in cases.values())
                for cases in accounting.values()
            )
        )
    elif task == "m5-prognosis":
        complete = (
            report.get("comparison_status") == "complete"
            and report.get("roster_count") == len(report.get("people", [])) == 32
            and report.get("evaluation_eligible_count") == report.get("paired_count") == 7
        )
    else:
        raise ValueError("Unsupported acceptance task")
    require(complete, f"Native {task} report is incomplete")


def provenance():
    require(
        not subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT),
        "Definitive acceptance requires a clean execution commit",
    )
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    paths = [ROOT / ".github/workflows/checks.yml", ROOT / "uv.lock"]
    for package in ("experiments/workflows", "experiments/workflow_acceptance"):
        paths.extend((ROOT / package).glob("*.py"))
    require((ROOT / "experiments/workflows/__main__.py").is_file(), "Local entry is unavailable")
    return {
        "git_revision": revision,
        "git_dirty": False,
        "python": sys.version,
        "sources": {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(paths)
        },
    }


class Commands:
    """Store receipts beside archives; never add administration to child inventories."""

    def __init__(self, output):
        self.directory = output / "commands"
        self.directory.mkdir()
        self.receipts = []

    def run(self, label, arguments, *, expected=0, launcher=False):
        environment = dict(os.environ)
        environment.update(CONTROLS)
        command = [sys.executable, "-B", "-S", "-m", *map(str, arguments)]
        stdout_path, stderr_path = [self.directory / f"{label}.{s}" for s in ("stdout", "stderr")]
        with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
            result = subprocess.run(
                command, cwd=ROOT, env=environment, stdout=stdout, stderr=stderr, check=False
            )
        receipt = {
            "label": label,
            "command": command,
            "exit_code": result.returncode,
            "uv_controls": CONTROLS,
            "stdout": str(stdout_path.relative_to(self.directory.parent)),
            "stderr": str(stderr_path.relative_to(self.directory.parent)),
        }
        self.receipts.append(receipt)
        save(self.directory / f"{label}.json", receipt)
        require(
            result.returncode != 0 if expected == "nonzero" else result.returncode == expected,
            f"Unexpected command exit: {label}; inspect command receipts",
        )
        if launcher:
            summary = read(stdout_path)
            require(summary.get("schema") == "opent1d.workflow-entry/1", "Missing entry result")
            return summary
        return None

    def entry(self, label, operation, task, *arguments, expected=0):
        return self.run(
            label,
            ["experiments.workflows", operation, task, *arguments],
            expected=expected,
            launcher=True,
        )


def prepare(task, inputs, commands):
    folder = inputs / task
    if task == "p1-controller":
        folder.mkdir()
        for name in ("controller.py", "controller.json"):
            shutil.copy2(ROOT / "experiments/p1_external/example" / name, folder / name)
        return ["--source", folder]
    if task == "m3-forecast":
        commands.run("m3-fixture", ["experiments.m3.researcher", "fixture", "--output", folder])
        return ["--config", folder / "config.json"]
    if task == "m4-secretion":
        folder.mkdir()
        parent = ROOT / "experiments/m4/causal_secretion"
        shutil.copy2(parent / "example_model.py", folder / "model.py")
        shutil.copy2(parent / "example_model.json", folder / "model.json")
        save(
            folder / "config.json",
            {
                "schema": "m4-researcher-config/1",
                "model": str(folder / "model.py"),
                "declaration": str(folder / "model.json"),
                "timeout_seconds": 600,
            },
        )
        return ["--config", folder / "config.json"]
    commands.run("m5-export", ["experiments.m5.researcher_workflow.run", "export-example", folder])
    return ["--bundle", folder]


def failure_config(fixture, inputs, name, body):
    folder = inputs / name
    folder.mkdir()
    source, marker = folder / "source.py", folder / "imported-marker"
    source.write_text(
        "from pathlib import Path\n"
        f"Path({str(marker)!r}).write_text('explicit candidate execution')\n"
        "def predict(request, settings):\n" + body,
        encoding="utf-8",
    )
    shutil.copy2(fixture / "trend/settings.json", folder / "settings.json")
    declaration = read(fixture / "trend/declaration.json")
    declaration.update(
        id=name, reference="Invented acceptance failure probe, no quality assessment"
    )
    declaration["training"]["reference"] = "Self-authored synthetic failure probe; no fitting"
    for key, path in (("source", source), ("settings", folder / "settings.json")):
        declaration[key] = {
            "file": str(path),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    save(folder / "declaration.json", declaration)
    config = read(fixture / "config.json")
    config["predictor"] = str(folder / "declaration.json")
    save(folder / "config.json", config)
    return folder / "config.json", marker


def failed_m3(output, inputs, commands):
    evidence = {}
    for name, body, timeout, expected_state in (
        ("m3-failed", "    raise RuntimeError('invented failure probe')\n", "120", "failed"),
        (
            "m3-timeout",
            "    import time\n    time.sleep(10)\n    return 100.0\n",
            "1",
            "interrupted",
        ),
    ):
        config, marker = failure_config(inputs / "m3-forecast", inputs, name, body)
        checked = commands.entry(name + "-check", "check", "m3-forecast", "--config", config)
        require(checked.get("ready") is True and not marker.exists(), "Passive check ran candidate")
        archive = output / name
        summary = commands.entry(
            name + "-run",
            "run",
            "m3-forecast",
            "--config",
            config,
            "--output",
            archive,
            "--timeout",
            timeout,
            expected="nonzero",
        )
        require(marker.is_file(), "Failure probe was not explicitly executed")
        require(summary.get("report_completeness") != "complete", "Failure falsely complete")
        evaluation = read(archive / "report.json")["evaluation"]
        require(evaluation["planned_people"] == 2, "Failure erased planned people")
        require(evaluation["complete_cohort"] is False, "Failed cohort falsely complete")
        require(evaluation["contributing_people"] == 0, "Failed prefix became primary evidence")
        require(
            all(
                person["execution_status"] == expected_state
                and person["planned"] == person["attempted"] + person["not_attempted"]
                and person["not_attempted"] > 0
                for person in evaluation["people"].values()
            ),
            "Failure or timeout accounting differs",
        )
        evidence[name] = {"archive": archive, "inventory": inventory(archive)}
    return evidence


def verify(output, tasks=TASKS, *, m4_reference=None):
    tasks = tuple(tasks)
    require(bool(tasks) and len(set(tasks)) == len(tasks), "Select unique acceptance tasks")
    require(set(tasks) <= set(TASKS), "Unsupported acceptance task")
    identity = provenance()
    output = Path(output).absolute()
    require(not output.is_symlink(), "Acceptance output cannot be a symlink")
    output.mkdir(parents=True, exist_ok=False)
    inputs = output / "inputs"
    inputs.mkdir()
    commands = Commands(output)
    plan = {
        "schema": "opent1d.workflow-acceptance/1",
        "claim": "internal_synthetic_verification_only",
        "selected_tasks": list(tasks),
        "provenance": identity,
        "uv_controls": CONTROLS,
        "running_in_github_actions": os.environ.get("GITHUB_ACTIONS") == "true",
        "m4_reference": str(Path(m4_reference).absolute()) if m4_reference else None,
    }
    save(output / "plan.json", plan)
    receipts = {}
    try:
        listed = commands.run("entry-list", ["experiments.workflows", "list"], launcher=True)
        require(set(TASKS) <= {task["task"] for task in listed["tasks"]}, "Missing entry task")
        for task in tasks:
            arguments = prepare(task, inputs, commands)
            checked = commands.entry(task + "-check", "check", task, *arguments)
            require(checked.get("ready") is True, f"Task requirements are not ready: {task}")
            archive = output / task
            extra = (
                ["--reference", str(m4_reference)]
                if task == "m4-secretion" and m4_reference
                else []
            )
            summary = commands.entry(
                task + "-run", "run", task, *arguments, "--output", archive, *extra
            )
            require(summary.get("report_completeness") == "complete", "Entry report is incomplete")
            native_complete(task, read(archive / REPORTS[task][0]))
            receipts[task] = {"archive": archive, "inventory": inventory(archive)}
        failures = failed_m3(output, inputs, commands) if "m3-forecast" in tasks else {}
        shutil.rmtree(inputs)
        for task, receipt in {**receipts, **failures}.items():
            route = "m3-forecast" if task in failures else task
            rebuilt = output / (task + "-reconstructed")
            arguments = [] if route == "m5-prognosis" else ["--output", rebuilt]
            summary = commands.entry(
                task + "-reconstruct",
                "reconstruct",
                route,
                "--archive",
                receipt["archive"],
                *arguments,
            )
            require(summary["child_exit_code"] == 0, "Native reconstruction failed")
            unchanged(receipt["archive"], receipt["inventory"])
            if route != "m5-prognosis":
                reports_equal(route, receipt["archive"], rebuilt)
            receipt["reports_reconstructed"] = True
        require(provenance() == identity, "Acceptance source identity changed during execution")
        result = {
            **plan,
            "status": "passed",
            "original_synthetic_inputs_removed": True,
            "child_archives_unchanged": True,
            "tasks": {
                task: {
                    "archive": str(receipt["archive"].relative_to(output)),
                    "reports_reconstructed": receipt["reports_reconstructed"],
                    "report_hashes": {
                        Path(name).name: receipt["inventory"][name]
                        for name in REPORTS["m3-forecast" if task in failures else task]
                    },
                }
                for task, receipt in {**receipts, **failures}.items()
            },
            "commands": commands.receipts,
            "limitations": [
                "Self-run synthetic software verification; no independent user or human evidence.",
                "No unrelated historical M0–M2 or C1 campaigns were rerun; "
                "configured M4 executes or reuses its declared native BC-008 prerequisite.",
                "Hashes establish consistency, not authenticated execution.",
                "Arbitrary M3/M5 predictions are recorded; "
                "P1 reconstruction replays its source actions.",
                "This receipt alone does not establish the final hosted CI job outcome.",
            ],
        }
        save(output / "acceptance.json", result)
        return result
    except BaseException as error:
        save(
            output / "acceptance.json",
            {
                **plan,
                "status": "failed",
                "error_type": type(error).__name__,
                "commands": commands.receipts,
            },
        )
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--task", choices=TASKS, action="append")
    parser.add_argument("--m4-reference", type=Path)
    args = parser.parse_args()
    result = verify(args.output, args.task or TASKS, m4_reference=args.m4_reference)
    print(
        json.dumps({"status": result["status"], "evidence": str(args.output / "acceptance.json")})
    )


if __name__ == "__main__":
    main()
