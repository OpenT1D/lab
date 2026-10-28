"""Exercise the installed desktop profile; retain internal, platform-specific evidence."""

import argparse
import copy
import hashlib
import http.client
import io
import json
import math
import os
import platform
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from urllib.parse import urlsplit

TERMINAL = {"completed", "failed", "cancelled"}
SCOPE = "Internal synthetic desktop execution; no human usability or empirical validation"


def require(value, message):
    if not value:
        raise ValueError(message)


def workflow_observation_seconds(
    task, operation, legacy, *, source_root=None, source_rehearsal=False
):
    """Only pure installed readiness checks gain an integrity observation ceiling.

    Every existing smoke limit for a model run, reader, install or campaign stays
    unchanged, even though product commands may now own separate integrity work.
    A check reserves its declared command ceiling, GUI cleanup and 30 seconds for
    HTTP observation. No phase/progress response grants or renews time.
    """
    if source_rehearsal or operation != "check":
        return legacy
    from experiments.desktop.admission import admission_allowance, coordinator_budget
    from experiments.gui.packaged_phases import cleanup_seconds, m3_extra

    options = {"source_root": source_root}
    if not admission_allowance(task, **options):
        return legacy
    if task in {"m3-forecast", "m3-compare"}:
        product = 300 + m3_extra(task, "m3_check", **options)
        cleanup = cleanup_seconds([], task, "m3_check", 30, **options)
    else:
        require(task == "m4-study-secure", "Unsupported observed readiness check")
        product = coordinator_budget(task, 30, **options)
        cleanup = cleanup_seconds(["--admission-prepare-seconds"], task, "check", 30, **options)
    return max(legacy, product + cleanup + 30)


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def isolated_environment():
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("UV_", "PYTHON"))
        and key not in {"VIRTUAL_ENV", "__PYVENV_LAUNCHER__"}
    }
    # All executable paths in the desktop must be application-owned absolutes.
    env.update(PATH="", PYTHONNOUSERSITE="1", UV_OFFLINE="1", UV_PYTHON_DOWNLOADS="never")
    return env


def read_state(path, process):
    value = json.loads(path.read_text(encoding="utf-8"))
    target = urlsplit(value["url"])
    require(
        target.scheme == "http"
        and target.hostname == "127.0.0.1"
        and target.port is not None
        and 0 < target.port <= 65535
        and target.path in {"", "/"}
        and not target.query
        and not target.fragment
        and target.username is None
        and target.password is None,
        "Desktop readiness must identify an HTTP IPv4 loopback origin",
    )
    require(type(value["pid"]) is int and value["pid"] == process.pid, "Readiness PID differs")
    token = value["token"]
    require(
        isinstance(token, str) and len(token) >= 16 and token.isascii() and token.isalnum(),
        "Desktop readiness token is malformed",
    )
    return {"url": f"http://127.0.0.1:{target.port}", "token": token, "pid": value["pid"]}


class Desktop:
    def __init__(self, python, source, data, output, *, source_rehearsal=False):
        self.python, self.source, self.data, self.output = python, source, data, output
        self.cwd = source if source_rehearsal else output
        self.source_rehearsal = source_rehearsal
        self.env = isolated_environment()
        if source_rehearsal:
            # Checkout readiness deliberately verifies developer uv installation.
            self.env["PATH"] = os.environ.get("PATH", "")
        self.process = None
        self.state = None
        self.sequence = 0
        self.log = None
        self.jobs = []
        self.shutdowns = []
        self.observations = []

    def start(self):
        self.sequence += 1
        state_file = self.output / f"session-{self.sequence}.json"
        self.log = (self.output / f"launcher-{self.sequence}.log").open("xb")
        self.process = subprocess.Popen(
            [
                str(self.python),
                "-B",
                "-m",
                "experiments.desktop",
                "--data-dir",
                str(self.data),
                "--no-browser",
                "--state-file",
                str(state_file),
            ],
            cwd=self.cwd,
            env=self.env,
            stdout=self.log,
            stderr=subprocess.STDOUT,
        )
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            require(self.process.poll() is None, "Desktop exited before readiness; inspect log")
            if state_file.is_file():
                try:
                    self.state = read_state(state_file, self.process)
                    break
                except json.JSONDecodeError:
                    pass
            time.sleep(0.05)
        require(self.state is not None, "Desktop readiness timed out; inspect log")
        self.request("GET", "/api/v1/observations/bootstrap")
        # Session credentials are transient and never included in evidence output.
        state_file.unlink(missing_ok=True)

    def request(self, method, path, body=None, *, expected=200, raw=False):
        require(path.startswith("/api/"), "Only bounded desktop API paths are allowed")
        target = urlsplit(self.state["url"])
        headers = {"X-OpenT1D-Token": self.state["token"], "Origin": self.state["url"]}
        content = None
        if body is not None:
            content = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        connection = http.client.HTTPConnection(target.hostname, target.port, timeout=20)
        try:
            connection.request(method, path, content, headers)
            response = connection.getresponse()
            value = response.read()
            require(
                response.status == expected,
                f"{method} {path} returned {response.status}: {value[:500]!r}",
            )
            return value if raw else json.loads(value)
        finally:
            connection.close()

    def wait(self, job, *, state="completed", timeout=200, started_at=None):
        require(
            type(timeout) in (int, float) and math.isfinite(timeout) and timeout > 0,
            "Observation ceiling must be finite and positive",
        )
        deadline = (time.monotonic() if started_at is None else started_at) + timeout
        self.observations.append(
            {
                "job_id": job["id"],
                "ceiling_seconds": timeout,
                "policy": "fixed-from-wait-start"
                if started_at is None
                else "fixed-from-operation-start",
            }
        )
        while time.monotonic() < deadline:
            job = self.request("GET", "/api/v1/jobs/" + job["id"])
            if job["state"] in TERMINAL:
                record = {
                    key: job.get(key)
                    for key in (
                        "id",
                        "operation",
                        "state",
                        "exit_code",
                        "cleanup_forced",
                        "remaining_owned_processes",
                    )
                }
                self.jobs.append(record)
                require(job["state"] == state, f"Job {job['id']} ended as {job['state']}")
                require(not job.get("cleanup_forced"), "Job required forced process cleanup")
                require(not job.get("remaining_owned_processes"), "Owned processes remain alive")
                require(job.get("pid") is None, "Finished job still has an active process")
                return job
            time.sleep(0.05)
        raise ValueError("Desktop operation exceeded smoke-test deadline")

    def operation(self, path, body=None, *, timeout=900):
        started = time.monotonic()
        return self.wait(
            self.request("POST", "/api/v1/" + path, body or {}, expected=202),
            timeout=timeout,
            started_at=started,
        )

    def workflow_operation(self, path, task, operation, *, legacy=900):
        seconds = workflow_observation_seconds(
            task,
            operation,
            legacy,
            source_root=self.source,
            source_rehearsal=self.source_rehearsal,
        )
        return self.operation(path, timeout=seconds)

    def reopen(self):
        state_file = self.output / f"reopen-{self.sequence}.json"
        subprocess.run(
            [
                str(self.python),
                "-B",
                "-m",
                "experiments.desktop",
                "--data-dir",
                str(self.data),
                "--no-browser",
                "--state-file",
                str(state_file),
            ],
            cwd=self.cwd,
            env=self.env,
            capture_output=True,
            check=True,
            timeout=30,
        )
        try:
            require(
                read_state(state_file, self.process) == self.state,
                "Repeated launch started a new session",
            )
        finally:
            state_file.unlink(missing_ok=True)
        require(self.process.poll() is None, "Repeated launch stopped the existing session")

    def stop(self, *, cli=False):
        if self.process is None:
            return
        process, state = self.process, self.state
        clean = False
        try:
            if process.poll() is None and state:
                if cli:
                    subprocess.run(
                        [
                            str(self.python),
                            "-B",
                            "-m",
                            "experiments.desktop",
                            "--data-dir",
                            str(self.data),
                            "--no-browser",
                            "--stop",
                        ],
                        cwd=self.cwd,
                        env=isolated_environment(),
                        capture_output=True,
                        check=True,
                        timeout=50,
                    )
                else:
                    self.request("POST", "/api/desktop/shutdown", {}, expected=202)
                require(process.wait(timeout=45) == 0, "Desktop shutdown returned an error")
                target = urlsplit(state["url"])
                connection = http.client.HTTPConnection(target.hostname, target.port, timeout=2)
                try:
                    connection.request("GET", "/")
                    connection.getresponse()
                except OSError:
                    clean = True
                finally:
                    connection.close()
                require(clean, "Desktop HTTP listener remains after shutdown")
            else:
                require(False, "Desktop exited before requested shutdown")
        finally:
            # Only the directly owned live Popen is terminated on harness failure.
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)
            self.shutdowns.append(
                {
                    "clean": clean,
                    "returncode": process.returncode,
                    "method": "launcher-stop" if cli else "authenticated-api",
                }
            )
            self.log.close()
            self.process, self.state = None, None


def configure(desktop, route, case, *, draws=32):
    prepared = desktop.operation(route + "/example", {"case": case})
    paths = prepared["result"]["input_paths"]
    inspected = desktop.request("POST", "/api/v1/" + route + "/inspect", paths, expected=201)
    settings = copy.deepcopy(inspected["settings"])
    settings["uncertainty"]["draws"] = draws
    config = desktop.request(
        "POST",
        "/api/v1/" + route + "/configurations",
        {**paths, "settings": settings, "input_sha256": inspected["input_sha256"]},
        expected=201,
    )
    desktop.operation(f"{route}/configurations/{config['id']}/freeze")
    frozen = desktop.request("GET", f"/api/v1/{route}/configurations/{config['id']}")
    require(frozen["ready"], "Supplied example is not ready after freezing")
    return frozen


def report_bytes(desktop, route, entry):
    return {
        name: desktop.request("GET", f"/api/v1/{route}/entries/{entry}/artifacts/{name}", raw=True)
        for name in ("report.json", "report.md")
    }


def compare_reports(actual, expected):
    require(set(actual) == set(expected), "Report artifact names differ")
    require(all(actual[name] == expected[name] for name in expected), "Report bytes differ")
    return {name: hashlib.sha256(raw).hexdigest() for name, raw in actual.items()}


def reconstruct(desktop, route, entry, expected):
    job = desktop.operation(f"{route}/entries/{entry}/reconstruct")
    require(job["verification"] == "native_reader_verified", "Native reader did not verify")
    argv = job["commands"][-1]["argv"]
    rebuilt = Path(argv[argv.index("--output") + 1]).resolve()
    require(rebuilt.is_relative_to(desktop.data.resolve()), "Reader output escapes desktop data")
    compare_reports({name: (rebuilt / name).read_bytes() for name in expected}, expected)
    return compare_reports(report_bytes(desktop, route, entry), expected)


def running_analysis(job, data):
    for command in job.get("commands", []):
        argv = command.get("argv", [])
        if "--output" not in argv:
            continue
        archive = Path(argv[argv.index("--output") + 1]).resolve()
        require(archive.is_relative_to(data.resolve()), "Job output escapes desktop data")
        try:
            journal = json.loads((archive / "execution.json").read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            continue
        if (
            journal.get("phase") == "analysis"
            or "analysis" in journal.get("schedules", {}).values()
        ):
            return True
    return False


def cancellation(desktop):
    config = configure(desktop, "sampling", "information-loss", draws=1024)
    job = desktop.request(
        "POST", f"/api/v1/sampling/configurations/{config['id']}/run", {}, expected=202
    )
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        job = desktop.request("GET", "/api/v1/jobs/" + job["id"])
        require(job["state"] not in TERMINAL, "Cancellation run ended before analysis was observed")
        if running_analysis(job, desktop.data):
            break
        time.sleep(0.01)
    else:
        raise ValueError("Cancellation test did not observe native analysis")
    desktop.request("POST", f"/api/v1/jobs/{job['id']}/cancel", {}, expected=202)
    stopped = desktop.wait(job, state="cancelled")
    entry = stopped["request"]["entry_id"]
    artifacts = report_bytes(desktop, "sampling", entry)
    report = json.loads(artifacts["report.json"])
    require(report["execution_status"] == "interrupted", "Cancelled report lost interruption")
    require(not report["coverage"]["complete_cohort"], "Cancelled report claims full completion")
    hashes = reconstruct(desktop, "sampling", entry, artifacts)
    return {"entry": entry, "status": "interrupted", "artifacts_sha256": hashes}


def artifacts_at(desktop, prefix, names=("report.json", "report.md")):
    return {name: desktop.request("GET", "/api/v1/" + prefix + name, raw=True) for name in names}


def retain_case(desktop, name, artifacts):
    folder = desktop.output / name
    folder.mkdir()
    for filename, raw in artifacts.items():
        (folder / filename).write_bytes(raw)
    return compare_reports(artifacts, artifacts)


def exercise_m3(desktop):
    bootstrap = desktop.request("GET", "/api/v1/m3/bootstrap")
    require(
        {item["id"] for item in bootstrap["tasks"]} == {"m3-forecast", "m3-compare"},
        "M3 routes missing",
    )
    fixture = desktop.operation("m3/fixture")
    inputs = desktop.request("GET", "/api/v1/m3/inputs")["inputs"]
    prepared = next(item for item in inputs if item["id"] == fixture["result"]["input_id"])
    inspected = desktop.request(
        "POST",
        "/api/v1/m3/inspect",
        {key: prepared[key] for key in ("root_id", "path")},
        expected=201,
    )
    require(inspected["id"] == prepared["id"], "Repeated M3 intake changed identity")
    cases = []
    for task in ("m3-forecast", "m3-compare"):
        candidates = [item["id"] for item in prepared["candidates"]]
        selected = candidates[:1] if task == "m3-forecast" else candidates
        config = desktop.request(
            "POST",
            "/api/v1/m3/configurations",
            {
                "input_id": prepared["id"],
                "task": task,
                "candidate_ids": selected,
                "timeout_seconds": 120,
            },
            expected=201,
        )
        desktop.workflow_operation(f"m3/configurations/{config['id']}/check", task, "check")
        job = desktop.workflow_operation(f"m3/configurations/{config['id']}/run", task, "run")
        entry = job["request"]["entry_id"]
        artifacts = report_bytes(desktop, "m3", entry)
        report = json.loads(artifacts["report.json"])
        coverage = report["evaluation" if task == "m3-forecast" else "common"]
        require(
            report["kind"] == "synthetic" and report["human_evaluation"] is False,
            "M3 synthetic scope changed",
        )
        require(
            coverage["complete_cohort"]
            and coverage["planned_people"] == prepared["planned_people"],
            "M3 planned cohort changed",
        )
        desktop.workflow_operation(f"m3/entries/{entry}/reconstruct", task, "reconstruct")
        compare_reports(report_bytes(desktop, "m3", entry), artifacts)
        pointer = desktop.request("GET", f"/api/v1/m3/entries/{entry}")
        require(
            pointer["verification"] == "native_reader_verified", "M3 saved reader did not verify"
        )
        cases.append(
            {
                "task": task,
                "kind": "m3",
                "id": entry,
                "archive": pointer["archive"],
                "artifacts_sha256": retain_case(desktop, task, artifacts),
            }
        )
    desktop.request("POST", "/api/v1/m3/configurations", {}, expected=400)
    return cases


def exercise_study(desktop):
    bootstrap = desktop.request("GET", "/api/v1/bootstrap")
    require(bootstrap["profile"] == "desktop", "The complete desktop profile is not active")
    config = copy.deepcopy(bootstrap["defaults"])
    config["scenarios"] = ["fasting"]
    frozen = desktop.request("POST", "/api/v1/configurations", config, expected=201)
    if not desktop.source_rehearsal:
        desktop.operation(f"configurations/{frozen['id']}/install")
    desktop.workflow_operation(f"configurations/{frozen['id']}/check", "m4-study-secure", "check")
    job = desktop.workflow_operation(
        f"configurations/{frozen['id']}/run", "m4-study-secure", "run", legacy=1800
    )
    artifacts = artifacts_at(
        desktop, f"jobs/{job['id']}/", ("report.json", "report.md", "figure.svg")
    )
    report = json.loads(artifacts["report.json"])
    require(report["passed"] and report["status"] == "completed", "M4 known synthetic study failed")
    require(
        report["denominators"]
        == {
            "sources": 2,
            "accepted_sources": 2,
            "source_scenarios": 2,
            "accepted_source_scenarios": 2,
            "pairs": 1,
            "accepted_pairs": 1,
        },
        "M4 source/scenario denominator changed",
    )
    reconstructed = desktop.workflow_operation(
        f"jobs/{job['id']}/reconstruct", "m4-study-secure", "reconstruct"
    )
    compare_reports(
        artifacts_at(desktop, f"jobs/{reconstructed['id']}/", tuple(artifacts)), artifacts
    )
    desktop.request("POST", "/api/v1/configurations", {}, expected=400)
    return frozen, {
        "task": "m4-study-secure",
        "kind": "study",
        "id": job["id"],
        "archive": f"results/gui/{job['id']}/archive",
        "artifacts_sha256": retain_case(desktop, "m4-study-secure", artifacts),
    }


def exercise_campaign(desktop, study):
    config = desktop.request(
        "POST",
        "/api/v1/campaigns/configurations",
        {
            "cells": [
                {"id": "first", "configuration_id": study["id"]},
                {"id": "second", "configuration_id": study["id"]},
            ],
            "repeats": 1,
            "timeout_seconds": 1800,
        },
        expected=201,
    )
    if not desktop.source_rehearsal:
        desktop.operation(f"campaigns/configurations/{config['id']}/install")
    desktop.operation(f"campaigns/configurations/{config['id']}/check")
    job = desktop.request(
        "POST", f"/api/v1/campaigns/configurations/{config['id']}/run", {}, expected=202
    )
    entry = job["request"]["campaign_id"]
    relative = f"results/gui/campaigns/archives/{entry}/campaign"
    journal_path = desktop.data / relative / "sessions/session-0001/state.json"
    deadline = time.monotonic() + 1800
    while time.monotonic() < deadline:
        current = desktop.request("GET", f"/api/v1/jobs/{job['id']}")
        require(
            current["state"] not in TERMINAL,
            "Campaign ended before the controlled cancellation point",
        )
        try:
            state = json.loads(journal_path.read_bytes())
        except (FileNotFoundError, json.JSONDecodeError):
            state = {}
        attempts = state.get("attempts", {})
        if (
            attempts.get("first--r001", {}).get("status") == "completed"
            and attempts.get("second--r001", {}).get("status") == "started"
        ):
            break
        time.sleep(0.05)
    else:
        raise ValueError("Campaign cancellation point timed out")
    desktop.request("POST", f"/api/v1/jobs/{job['id']}/cancel", {}, expected=202)
    desktop.wait(job, state="cancelled", timeout=90)
    prefix = f"campaigns/{entry}/artifacts/"
    interrupted_bytes = artifacts_at(desktop, prefix)
    interrupted = json.loads(interrupted_bytes["report.json"])
    require(
        interrupted["status"] == "interrupted" and interrupted["accepted_slots"] == 1,
        "Campaign cancellation lost accepted first slot",
    )
    retain_case(desktop, "campaign-interrupted", interrupted_bytes)
    desktop.operation(f"campaigns/{entry}/reconstruct")
    compare_reports(artifacts_at(desktop, prefix), interrupted_bytes)
    desktop.operation(f"campaigns/configurations/{config['id']}/check")
    desktop.operation(f"campaigns/{entry}/resume", timeout=1800)
    artifacts = artifacts_at(desktop, prefix)
    report = json.loads(artifacts["report.json"])
    require(
        report["passed"] and report["accepted_slots"] == report["planned_slots"] == 2,
        "Resumed campaign incomplete",
    )
    require(
        report["slots"][0] == interrupted["slots"][0],
        "Campaign resume reran the accepted first slot",
    )
    require(
        report["slots"][1]["attempts"][0] == interrupted["slots"][1]["attempts"][0],
        "Campaign resume changed interrupted evidence",
    )
    require(len(report["slots"][1]["attempts"]) == 2, "Campaign resume lost retry history")
    desktop.operation(f"campaigns/{entry}/reconstruct")
    compare_reports(artifacts_at(desktop, prefix), artifacts)
    desktop.request("POST", "/api/v1/campaigns/configurations", {}, expected=400)
    return {
        "task": "maintained-campaign",
        "kind": "campaign",
        "id": entry,
        "archive": relative,
        "artifacts_sha256": retain_case(desktop, "campaign-resumed", artifacts),
        "cancelled_then_resumed": True,
    }


def extract_report_fixture(fixtures, output):
    """Copy bounded, hash-bound M5 fixture bytes; never execute archived snapshots."""
    with (fixtures / "m5-report-only.json").open("rb") as stream:
        raw = stream.read(65537)
    require(len(raw) <= 65536, "Fixture metadata exceeds limit")
    manifest = json.loads(raw)
    require(
        isinstance(manifest, dict)
        and manifest.get("schema") == "opent1d.synthetic-report-fixture/1",
        "Unsupported report fixture",
    )
    descriptor = manifest["archive"]
    require(
        isinstance(descriptor, dict) and descriptor.get("path") == "m5-report-only.zip",
        "Unexpected fixture archive",
    )
    with (fixtures / descriptor["path"]).open("rb") as stream:
        raw = stream.read(2 * 1024 * 1024 + 1)
    require(
        len(raw) <= 2 * 1024 * 1024
        and len(raw) == descriptor["bytes"]
        and hashlib.sha256(raw).hexdigest() == descriptor["sha256"],
        "Fixture ZIP identity differs",
    )
    expected = manifest["files"]
    require(
        isinstance(expected, dict) and 0 < len(expected) <= 100,
        "Fixture member count exceeds limit",
    )
    for name, value in expected.items():
        require(
            isinstance(name, str)
            and name
            and name not in {".", ".."}
            and not any(char in name for char in ("/", "\\", ":", "\0"))
            and not name.startswith("."),
            "Unsafe fixture member path",
        )
        require(
            isinstance(value, dict)
            and set(value) == {"sha256", "bytes"}
            and type(value["bytes"]) is int
            and 0 <= value["bytes"] <= 500000,
            "Fixture member exceeds limit",
        )
    require(
        sum(value["bytes"] for value in expected.values()) <= 8 * 1024 * 1024,
        "Fixture total exceeds limit",
    )
    output.mkdir(exist_ok=False)
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            members = archive.infolist()
            require(
                len(members) == len(expected)
                and {item.filename for item in members} == set(expected),
                "Fixture ZIP member inventory differs",
            )
            for item in members:
                value = expected[item.filename]
                require(
                    not item.is_dir()
                    and item.file_size == value["bytes"]
                    and (item.external_attr >> 16) & 0o170000 in {0, 0o100000},
                    "Linked or inconsistent fixture member",
                )
                with archive.open(item) as stream:
                    content = stream.read(value["bytes"] + 1)
                require(
                    len(content) == value["bytes"]
                    and hashlib.sha256(content).hexdigest() == value["sha256"],
                    "Fixture member identity differs",
                )
                with (output / item.filename).open("xb") as stream:
                    stream.write(content)
    except BaseException as error:
        shutil.rmtree(output)
        if isinstance(error, (zipfile.BadZipFile, RuntimeError, NotImplementedError)):
            raise ValueError("Unsupported or corrupt report fixture ZIP") from error
        raise
    return manifest


def exercise_library(desktop, cases):
    roots = desktop.request("GET", "/api/v1/library/roots")["roots"]
    root = next(
        item["id"] for item in roots if Path(item["directory"]).resolve() == desktop.data.resolve()
    )
    external = desktop.data / "acceptance-imports"
    external.mkdir()
    # The archive records a genuine earlier macOS execution; this acceptance
    # step verifies only the current GUI's existing saved-report capability.
    extract_report_fixture(desktop.source / "tests/fixtures", external / "m5-prognosis")
    m5 = json.loads((external / "m5-prognosis/report.json").read_bytes())
    require(
        m5["roster_count"] == 32
        and m5["paired_count"] == 7
        and m5["candidate_coverage"] == 1
        and m5["human_execution_authorized"] is False,
        "M5 known synthetic fixture differs",
    )
    registrations = []
    for case in [*cases, {"task": "m5-prognosis", "archive": "acceptance-imports/m5-prognosis"}]:
        if case["task"] == "maintained-campaign":
            continue  # Campaigns have their dedicated native GUI report route.
        relative = "acceptance-imports/" + case["task"]
        if case["task"] != "m5-prognosis":
            shutil.copytree(desktop.data / case["archive"], desktop.data / relative)
        indexed = desktop.operation(
            "library/entries", {"root_id": root, "path": relative, "task": case["task"]}
        )
        entry = indexed["request"]["entry"]["id"]
        desktop.operation(f"library/entries/{entry}/verify")
        names = (
            ("report.json", "report.md", "figure.svg")
            if case["task"] == "m4-study-secure"
            else ("report.json", "report.md")
        )
        artifacts = artifacts_at(desktop, f"library/entries/{entry}/artifacts/", names)
        expected = {name: (desktop.data / relative / name).read_bytes() for name in names}
        compare_reports(artifacts, expected)
        desktop.request("POST", f"/api/v1/library/entries/{entry}/visibility", {"hidden": True})
        desktop.request("POST", f"/api/v1/library/entries/{entry}/visibility", {"hidden": False})
        registrations.append(
            {
                "task": case["task"],
                "id": entry,
                "artifacts_sha256": retain_case(desktop, "library-" + case["task"], artifacts),
            }
        )
    return registrations


def exercise_durable(desktop, cases):
    require(
        desktop.request("GET", "/api/v1/durable/bootstrap")["can_export"],
        "Desktop durable archive store unavailable",
    )
    values = []
    for case in cases:
        if case.get("kind") not in {"study", "campaign", "m3"}:
            continue
        job = desktop.operation("durable/export", {"kind": case["kind"], "id": case["id"]})
        entry = job["request"]["entry_id"]
        pointer = desktop.request("GET", f"/api/v1/durable/entries/{entry}")
        names = tuple(case["artifacts_sha256"])
        artifacts = artifacts_at(desktop, f"durable/entries/{entry}/artifacts/", names)
        require(
            compare_reports(artifacts, artifacts) == case["artifacts_sha256"],
            "Durable export report differs",
        )
        desktop.operation(
            "durable/register", {"root_id": pointer["root_id"], "path": pointer["path"]}
        )
        desktop.operation(f"durable/entries/{entry}/verify")
        desktop.operation(f"durable/entries/{entry}/reconstruct")
        compare_reports(
            artifacts_at(desktop, f"durable/entries/{entry}/artifacts/", names), artifacts
        )
        values.append(
            {
                "task": case["task"],
                "id": entry,
                "artifacts_sha256": retain_case(desktop, "durable-" + case["task"], artifacts),
            }
        )
    return values


def exercise_mmtt(desktop):
    """Run both existing MMTT examples with their unchanged coverage assertions."""
    saved, cases, native_cases = [], [], []
    for route, case in (("observations", "increase"), ("sampling", "information-loss")):
        config = configure(desktop, route, case)
        completed = desktop.operation(f"{route}/configurations/{config['id']}/run")
        entry = completed["request"]["entry_id"]
        artifacts = report_bytes(desktop, route, entry)
        report = json.loads(artifacts["report.json"])
        require(report["coverage"]["complete_cohort"], "Supplied example report is incomplete")
        if route == "observations":
            require(
                report["people"]["invented-01"]["classification"]
                == "consistent within investigated assumptions",
                "Task 1 known synthetic classification differs",
            )
        else:
            require(report["coverage"]["planned_variant_pairs"] == 60, "Task 2 coverage differs")
            require(
                report["comparisons"]["evaluation"]["three-times"]["nominal"]["directions"][
                    "direction_reversal"
                ]
                == 3,
                "Task 2 known synthetic direction reversals differ",
            )
        folder = desktop.output / route
        folder.mkdir()
        for name, raw in artifacts.items():
            (folder / name).write_bytes(raw)
        hashes = reconstruct(desktop, route, entry, artifacts)
        cases.append({"route": route, "case": case, "entry": entry, "artifacts_sha256": hashes})
        native_cases.append(
            {
                "task": "mmtt-sensitivity" if route == "observations" else "mmtt-sampling",
                "id": entry,
                "archive": f"results/gui/{route}/archives/{entry}/archive",
                "artifacts_sha256": hashes,
            }
        )
        saved.append((route, entry, artifacts))
    return saved, cases, native_cases


def reopen_mmtt(desktop, saved):
    for route, entry, artifacts in saved:
        entries = desktop.request("GET", f"/api/v1/{route}/entries")["entries"]
        require(entry in {item["id"] for item in entries}, "Saved entry missing after restart")
        compare_reports(report_bytes(desktop, route, entry), artifacts)
        reconstruct(desktop, route, entry, artifacts)


def reopen_library(desktop, library):
    for case in library:
        desktop.operation(f"library/entries/{case['id']}/verify")
        current = artifacts_at(
            desktop, f"library/entries/{case['id']}/artifacts/", tuple(case["artifacts_sha256"])
        )
        require(
            compare_reports(current, current) == case["artifacts_sha256"],
            "Library restart changed report bytes",
        )


def reopen_durable(desktop, durable):
    for case in durable:
        desktop.operation(f"durable/entries/{case['id']}/reconstruct")
        current = artifacts_at(
            desktop, f"durable/entries/{case['id']}/artifacts/", tuple(case["artifacts_sha256"])
        )
        require(
            compare_reports(current, current) == case["artifacts_sha256"],
            "Durable restart changed report bytes",
        )


def exercise(desktop, *, skip_durable=False):
    desktop.reopen()
    native_cases = exercise_m3(desktop)
    study, study_case = exercise_study(desktop)
    native_cases.append(study_case)
    native_cases.append(exercise_campaign(desktop, study))
    saved, cases, mmtt_cases = exercise_mmtt(desktop)
    native_cases.extend(mmtt_cases)
    desktop.request("POST", "/api/v1/observations/example", {"case": "not-a-case"}, expected=400)
    desktop.request("POST", "/api/v1/sampling/inspect", {}, expected=400)
    cancelled = cancellation(desktop)
    library = exercise_library(desktop, native_cases)
    durable = [] if skip_durable else exercise_durable(desktop, native_cases)
    desktop.stop()
    desktop.start()
    reopen_mmtt(desktop, saved)
    reopen_library(desktop, library)
    reopen_durable(desktop, durable)
    return {
        "cases": cases,
        "native_cases": native_cases,
        "library": library,
        "durable": durable,
        "durable_skipped_for_dirty_source_rehearsal": skip_durable,
        "bundled_setup_install_verified": not desktop.source_rehearsal,
        "repeated_launch_reused_session": True,
        "malformed_input_refused": True,
        "cancellation": cancelled,
        "restart_reopened_and_reconstructed": True,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    sources = parser.add_mutually_exclusive_group(required=True)
    sources.add_argument("--source", type=Path, help="Installed package source directory")
    sources.add_argument("--source-root", type=Path, help="Checkout for local rehearsal only")
    parser.add_argument(
        "--skip-durable",
        action="store_true",
        help="Only for a dirty source rehearsal; records incomplete acceptance",
    )
    parser.add_argument(
        "--output", type=Path, required=True, help="New retained evidence directory"
    )
    args = parser.parse_args(argv)
    if args.skip_durable and not args.source_root:
        parser.error("--skip-durable is only allowed with --source-root")
    source = (args.source or args.source_root).resolve(strict=True)
    python = args.python.resolve(strict=True)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    data = output / "user data"
    mode = "installed-payload" if args.source else "source-rehearsal"
    record = {
        "schema": "opent1d.desktop-smoke/1",
        "scope": SCOPE,
        "mode": mode,
        "host": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "status": "failed",
        "actual_windows_execution": False,
        "independent_clean_windows_installation": False,
        "human_sessions": 0,
        "launcher_path_empty": bool(args.source),
    }
    desktop = Desktop(python, source, data, output, source_rehearsal=bool(args.source_root))
    try:
        if args.source:
            require(not (source / ".git").exists(), "Payload contains Git metadata")
            require(not (source / ".venv").exists(), "Payload contains a checkout environment")
        runtime = subprocess.run(
            [
                str(python),
                "-I",
                "-S",
                "-B",
                "-c",
                "import json,platform,sys; print(json.dumps({"
                "'python':sys.version,'executable':sys.executable,'platform':sys.platform,"
                "'implementation':platform.python_implementation(),'machine':platform.machine()}))",
            ],
            cwd=source,
            env=isolated_environment(),
            capture_output=True,
            check=True,
            text=True,
            timeout=20,
        )
        record["runtime"] = json.loads(runtime.stdout)
        desktop.start()
        record.update(exercise(desktop, skip_durable=args.skip_durable))
        desktop.stop(cli=True)
        record["status"] = "passed_partial" if args.skip_durable else "passed"
        record["actual_windows_execution"] = (
            record["runtime"]["platform"] == "win32" and not args.skip_durable
        )
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        record["failure"] = str(error)
    finally:
        if desktop.process is not None:
            try:
                desktop.stop()
            except (OSError, ValueError, subprocess.SubprocessError) as error:
                record["cleanup_failure"] = str(error)
        record["jobs"] = desktop.jobs
        record["shutdowns"] = desktop.shutdowns
        record["observation_limits"] = desktop.observations
        write_json(output / "evidence.json", record)
    print(json.dumps({"status": record["status"], "evidence": str(output / "evidence.json")}))
    return 0 if record["status"] in {"passed", "passed_partial"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
