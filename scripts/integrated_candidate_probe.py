"""Current trusted installed-candidate probes; native execution is explicit, never root CI."""

import argparse
import hashlib
import http.client
import json
import re
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def hashes(root):
    result = {}
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ValueError("Linked qualification entry refused")
        if path.is_file():
            result[path.relative_to(root).as_posix()] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
    return result


def native_acceptance(archive):
    value = json.loads((archive / "report.json").read_bytes())
    assert value["passed"] is True and value["reference"]["accepted"] is True
    assert value["common_controls"]["passed"] is True
    assert value["configuration"]["scenarios"] == ["fasting", "gastric_load_15g"]
    assert set(value["sources"]) == {"dalla_man", "ultradian"}
    assert value["denominators"]["source_scenarios"] == 4
    assert value["denominators"]["accepted_source_scenarios"] == 4
    for name, source in value["sources"].items():
        assert source["accepted"] is True
        for scene, cell in source["scenarios"].items():
            assert cell["accepted"] is True
            path = archive / "children" / name / "primary" / scene / "candidate-reference.json"
            trajectory = json.loads(path.read_bytes())
            assert trajectory["times"] == [i / 4 for i in range(961)]
            assert len(trajectory["states"]) == len(trajectory["source_rates"]) == 961
    return {"passed": True, "sources": 2, "source_scenarios": 4, "points_per_case": 961}


def connected_acceptance(value, missing):
    coverage = value["coverage"]
    assert len(value["rows"]) == coverage["planned_rows"] == 72
    assert coverage["planned_native_variant_pairs"] == 24
    assert coverage["planned_comparison_members"] == 6
    assert coverage["available_point_rows"] == (48 if missing else 72)
    assert coverage["complete_rows"] == (36 if missing else 72)
    assert coverage["unavailable_point_rows"] == (24 if missing else 0)
    assert value["completeness"] == ("incomplete" if missing else "complete")
    assert value["point_recovery"]["planned"] == 6
    assert value["mismatch_controls"]["planned"] == 18
    assert value["point_recovery"]["passed"] == (4 if missing else 6)
    assert value["mismatch_controls"]["passed"] == (12 if missing else 18)
    assert value["point_recovery"]["all_passed"] is (not missing)
    assert value["mismatch_controls"]["all_passed"] is (not missing)
    assert value["numerical_acceptance"]["all_passed"] is (not missing)
    assert value["numerical_acceptance"]["status"] == ("unavailable" if missing else "passed")


class GUI:
    def __init__(self, root, attachment=None):
        self.root, self.attachment = root, attachment
        self.cli = Path(sys.executable).with_name("opent1d-lab")
        self.process, self.log, self.token = None, None, None
        self.serial = 0

    def start(self):
        self.log = (self.root / f"gui-{self.serial}.log").open("w")
        self.serial += 1
        command = [str(self.cli), "gui", "--workspace", str(self.root / "workspace")]
        if self.attachment:
            command += ["--runtime-attachment", str(self.attachment)]
        self.process = subprocess.Popen(command, stdout=self.log, stderr=self.log)
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            text = Path(self.log.name).read_text(errors="replace")
            match = re.search(r"OpenT1D project GUI: http://127\.0\.0\.1:(\d+)", text)
            if match:
                self.port = int(match[1])
                html = self.request("/")
                self.token = re.search(rb'name="opent1d-token" content="([a-f0-9]{64})"', html)[
                    1
                ].decode()
                return self
            if self.process.poll() is not None:
                break
            time.sleep(0.05)
        raise ValueError("Installed GUI did not start; retain its log")

    def request(self, route, body=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        headers = {"X-OpenT1D-Token": self.token} if self.token else {}
        if body is not None:
            headers.update(
                {"Origin": f"http://127.0.0.1:{self.port}", "Content-Type": "application/json"}
            )
        try:
            connection.request(
                "POST" if body is not None else "GET",
                route,
                json.dumps(body) if body is not None else None,
                headers,
            )
            response = connection.getresponse()
            raw = response.read()
            assert response.status in {200, 202}, (response.status, raw[:500])
            return raw
        finally:
            connection.close()

    def submit(self, operation, arguments, project=None):
        return json.loads(
            self.request(
                "/api/actions",
                {
                    "request_id": uuid.uuid4().hex,
                    "operation": operation,
                    "arguments": arguments,
                    "project": project,
                },
            )
        )

    def finish(self, job, *, timeout=600, expected="done"):
        deadline = time.monotonic() + timeout
        while job["status"] == "running" and time.monotonic() < deadline:
            time.sleep(0.2)
            job = json.loads(self.request("/api/jobs/" + job["id"]))
        assert job["status"] == expected, job
        return job["result"] if expected == "done" else job

    def action(self, operation, arguments, project=None, **options):
        return self.finish(self.submit(operation, arguments, project), **options)

    def report(self, result, output):
        output.mkdir()
        for name, expected in result["report_sha256"].items():
            raw = self.request("/api/reports/" + result["report"] + "/" + name)
            assert hashlib.sha256(raw).hexdigest() == expected
            filename = output / name
            filename.parent.mkdir(parents=True, exist_ok=True)
            filename.write_bytes(raw)
        return json.loads((output / "report.json").read_bytes())

    def stop(self):
        try:
            if self.process and self.process.poll() is None:
                self.request("/api/shutdown", {})
                self.process.wait(timeout=60)
                assert self.process.returncode == 0
        finally:
            if self.log:
                self.log.close()
            self.token = None

    def __enter__(self):
        try:
            return self.start()
        except BaseException:
            try:
                self.__exit__()
            except Exception:
                pass  # Keep the startup error; fallback termination still ran.
            raise

    def __exit__(self, *_):
        try:
            self.stop()
        finally:
            if self.process and self.process.poll() is None:
                self.process.terminate()
                self.process.wait(timeout=60)


def attachment(root, roles):
    import opent1d_lab as lab

    destination = root / "attachment.json"
    result = lab.attach_runtimes(roles / "native", roles / "observer", destination)
    assert hashlib.sha256(destination.read_bytes()).hexdigest() == result["sha256"]
    return destination


def direct_prepare(root, roles):
    import opent1d_lab as lab

    root.mkdir()
    attached = attachment(root, roles)
    inputs = lab.example("m4-study-installed", root / "inputs", case="fasting")["inputs"]
    config = Path(inputs["config.json"])
    value = json.loads(config.read_bytes())
    value["scenarios"] = ["fasting", "gastric_load_15g"]
    write(config, value)
    project = lab.create_project(root / "project", "Retrospective direct predecessor M4 evidence")
    plan = project.freeze("m4-study-installed", inputs)["plan"]
    result = {
        "application": lab.installation(),
        "project": project.path,
        "plan": plan,
        "attachment": str(attached),
        "config": str(Path(project.path) / "events/00000002/plan/input/config.json"),
    }
    write(root / "request.json", result)
    return result


def direct_finish(root):
    import opent1d_lab as lab

    request = json.loads((root / "request.json").read_bytes())
    accepted = native_acceptance(root / "archive")
    project = lab.Project(request["project"])
    imported = project.import_attempt(request["plan"], root / "archive")
    assert imported["result"]["completeness"] == "complete"
    assert imported["receipt"]["remaining_owned_processes"] == []
    report = project.reconstruct(imported["attempt"], root / "report")
    result = {
        **request,
        "native": accepted,
        "attempt": imported,
        "report": report,
        "project_files": hashes(Path(project.path)),
        "mode": "retrospective-import-of-owned-direct-execution",
    }
    write(root / "result.json", result)
    return result


def candidate(root, roles):
    import opent1d_lab as lab

    root.mkdir()
    installed = lab.installation()
    assert (
        installed["schema"] == "opent1d.installed-sdk/5" and installed["source"]["dirty"] is False
    )
    attached = attachment(root, roles)
    project = lab.create_project(root / "project", "Prospective integrated candidate study")
    results = {
        "application": installed,
        "attachment_sha256": hashlib.sha256(attached.read_bytes()).hexdigest(),
        "studies": {},
    }
    with GUI(root, attached) as gui:
        handle = gui.action("open", {"path": project.path})["project"]
        complete = gui.action(
            "study_freeze",
            {
                "name": "Known secretion recovery",
                "question": "Does the declared inverse recover its independent synthetic source?",
                "forward_plan": None,
                "observation_case": "complete",
            },
            handle,
        )
        missing = gui.action(
            "study_freeze",
            {
                "name": "Preserved missing evaluation observation",
                "question": "Are all missing cases and denominators preserved?",
                "forward_plan": complete["forward_plan"],
                "observation_case": "missing-evaluation",
            },
            handle,
        )
        forward_plan = complete["forward_plan"]
        members = [
            {
                "id": f"member-{i + 1}",
                "label": source + " / " + scene,
                "plan": forward_plan,
                "selector": {"source": source, "scenario": scene},
            }
            for i, (source, scene) in enumerate(
                (s, c) for c in ("fasting", "gastric_load_15g") for s in ("dalla_man", "ultradian")
            )
        ]
        comparison = gui.action(
            "comparison_freeze",
            {
                "definition": {
                    "schema": "opent1d.plan-comparison/1",
                    "name": "M4 source and initial-load contrast",
                    "question": "What changes under these fixed synthetic source/load conditions?",
                    "baseline": "member-1",
                    "variants": members,
                }
            },
            handle,
        )
        for name, frozen in (("complete", complete), ("missing", missing)):
            initial = gui.action("study_verify", {"study": frozen["study"], "at": None}, handle)
            initial_value = gui.report(initial, root / (name + "-initial"))
            assert initial_value["coverage"]["unavailable_point_rows"] == 72
            results["studies"][name] = {"frozen": frozen, "initial": initial}
        assert gui.action("check", {"plan": forward_plan}, handle)["runtimes_ready"] is True
        print("Executing installed C four-slot native forward through workbench HTTP", flush=True)
        forward = gui.action("run", {"plan": forward_plan, "retry_of": None}, handle, timeout=10830)
        assert forward["result"]["completeness"] == "complete"
        assert list(forward["result"]["slot_statuses"].values()) == ["complete"] * 4
        assert forward["receipt"]["remaining_owned_processes"] == []
        archive = Path(forward["evidence"]) / "native"
        results["forward"] = forward
        results["native_acceptance"] = native_acceptance(archive)
        native_report = gui.action(
            "verify", {"attempt": forward["attempt"], "allow_failed": False}, handle
        )
        gui.report(native_report, root / "native-report")
        results["native_report"] = native_report
        m4_comparison = gui.action(
            "comparison_verify", {"comparison": comparison["comparison"], "at": None}, handle
        )
        value = gui.report(m4_comparison, root / "m4-comparison")
        assert value["completeness"] == "complete"
        assert value["coverage"]["planned_cases"] == value["coverage"]["compared_cases"] == 12
        results["m4_comparison"] = m4_comparison
        for name, item in results["studies"].items():
            frozen = item["frozen"]
            print("Materializing and executing", name, "connected study", flush=True)
            materialized = gui.action("study_materialize", {"study": frozen["study"]}, handle)
            inverse = gui.action(
                "run", {"plan": materialized["sampling_plan"], "retry_of": None}, handle
            )
            assert inverse["result"]["payload"] == "native"
            assert inverse["result"]["completeness"] == (
                "incomplete" if name == "missing" else "complete"
            )
            assert inverse["receipt"]["remaining_owned_processes"] == []
            report = gui.action("study_verify", {"study": frozen["study"], "at": None}, handle)
            value = gui.report(report, root / (name + "-report"))
            connected_acceptance(value, name == "missing")
            companion = gui.action(
                "comparison_verify", {"comparison": materialized["comparison"], "at": None}, handle
            )
            gui.report(companion, root / (name + "-comparison"))
            initial = gui.action(
                "study_verify",
                {"study": frozen["study"], "at": item["initial"]["snapshot"]["tip"]},
                handle,
            )
            assert initial["report_sha256"] == item["initial"]["report_sha256"]
            item.update(
                {
                    "materialized": materialized,
                    "inverse": inverse,
                    "report": report,
                    "comparison": companion,
                    "coverage": value["coverage"],
                    "point_recovery": value["point_recovery"],
                    "mismatch_controls": value["mismatch_controls"],
                }
            )
        gui.stop()
        gui.start()
        gui.action("refresh", {}, handle)
        replay = gui.action(
            "study_verify",
            {
                "study": complete["study"],
                "at": results["studies"]["complete"]["report"]["snapshot"]["tip"],
            },
            handle,
        )
        assert replay["report_sha256"] == results["studies"]["complete"]["report"]["report_sha256"]
        results["relaunch_exact"] = True
    results["project_files"] = hashes(Path(project.path))
    write(root / "result.json", results)
    return results


def adverse(root, roles):
    import opent1d_lab as lab

    root.mkdir()
    attached = attachment(root, roles)
    project = lab.create_project(
        root / "failed-project", "Missing attachment keeps first forward failure"
    )
    frozen = project.freeze_study("No attachment", "Preserve the unavailable downstream chain")
    assert project.check(frozen["forward_plan"])["runtimes_ready"] is False
    failed = project.run(frozen["forward_plan"])
    assert failed["result"]["execution_status"] == "failed"
    assert failed["result"]["payload"] == "forensic"
    assert failed["receipt"]["remaining_owned_processes"] == []
    assert len(failed["result"]["slot_statuses"]) == 4
    assert set(failed["result"]["slot_statuses"].values()) == {"unavailable"}
    assert project.study(frozen["study"])["next"]["action"] == "blocked"
    try:
        project.materialize_study(frozen["study"])
    except ValueError as error:
        assert "incomplete" in str(error)
    else:
        raise AssertionError("Failed forward materialized descendants")
    blocked = project.reconstruct_study(frozen["study"], root / "blocked-report")
    value = json.loads((root / "blocked-report/report.json").read_bytes())
    assert value["coverage"]["unavailable_point_rows"] == 72
    refusals = {}
    for case in ("foreign-application", "altered-role-hash"):
        record = json.loads(attached.read_bytes())
        if case == "foreign-application":
            record["application"]["descriptor_sha256"] = "0" * 64
        else:
            entries = record["roles"]["native"]["files"]
            key = next(k for k in entries if k.endswith(".dist-info/METADATA"))
            entries[key]["sha256"] = "0" * 64
        filename = root / (case + ".json")
        write(filename, record)
        before = hashes(Path(project.path))
        try:
            project.check(frozen["forward_plan"], runtime_attachment=filename)
        except ValueError as error:
            message = str(error)
            assert (
                "different current SDK application" in message
                if case == "foreign-application"
                else "Runtime byte/file roster changed" in message
            )
            refusals[case] = message
        else:
            raise AssertionError("Invalid attachment admitted")
        assert hashes(Path(project.path)) == before
    cancelled = lab.create_project(root / "cancelled-project", "Observed native cancellation")
    inputs = lab.example("m4-study-installed", root / "cancel-inputs", case="fasting")["inputs"]
    plan = cancelled.freeze("m4-study-installed", inputs)["plan"]
    unrelated = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(600)"])
    try:
        with GUI(root, attached) as gui:
            handle = gui.action("open", {"path": cancelled.path})["project"]
            job = gui.submit("run", {"plan": plan, "retry_of": None}, handle)
            deadline, observed = time.monotonic() + 180, None
            while time.monotonic() < deadline and observed is None:
                for filename in (Path(cancelled.path) / "work").glob(
                    "*/native/historical/fasting/*-coarse.json"
                ):
                    try:
                        trajectory = json.loads(filename.read_bytes())
                    except (OSError, ValueError):
                        continue
                    if trajectory.get("status") == "completed" and trajectory.get("states"):
                        observed = filename.relative_to(cancelled.path).as_posix()
                        break
                if observed is None:
                    current = json.loads(gui.request("/api/jobs/" + job["id"]))
                    assert current["status"] == "running", current
                    time.sleep(0.05)
            assert observed is not None, "No actual numerical child was observed"
            gui.request("/api/jobs/" + job["id"] + "/cancel", {})
            result = gui.finish(job, timeout=120)
            assert result["result"]["execution_status"] == "interrupted", result
            assert result["result"]["completeness"] == "incomplete"
            assert result["receipt"]["remaining_owned_processes"] == []
            assert len(result["result"]["slot_statuses"]) == 2
            assert unrelated.poll() is None, "Unrelated process was stopped"
    finally:
        if unrelated.poll() is None:
            unrelated.terminate()
        unrelated.wait(timeout=10)
    value = {
        "failed": failed,
        "blocked": blocked,
        "attachment_refusals": refusals,
        "cancelled": result,
        "observed_numerical_child": observed,
        "unrelated_process_preserved": True,
    }
    write(root / "result.json", value)
    return value


def replay(root, bundle):
    import opent1d_lab as lab

    root.mkdir()
    config = json.loads(bundle.read_bytes())
    receipts = {}
    for name in ("predecessor", "candidate"):
        folder = Path(config[name])
        saved = json.loads((folder / "result.json").read_bytes())
        project = lab.Project(folder / "project")
        before = hashes(Path(project.path))
        assert before == saved["project_files"]
        if name == "predecessor":
            r = project.reconstruct(saved["attempt"]["attempt"], root / "predecessor-native")
            assert r["report_sha256"] == saved["report"]["report_sha256"]
            receipts[name] = r
        else:
            r = project.reconstruct(saved["forward"]["attempt"], root / "candidate-native")
            assert r["report_sha256"] == saved["native_report"]["report_sha256"]
            comparisons = project.reconstruct_comparison(
                saved["m4_comparison"]["comparison"],
                root / "m4-comparison",
                at=saved["m4_comparison"]["snapshot"]["tip"],
            )
            assert comparisons["report_sha256"] == saved["m4_comparison"]["report_sha256"]
            receipts[name] = {"native": r, "comparison": comparisons, "studies": {}}
            for label, item in saved["studies"].items():
                study = item["frozen"]["study"]
                r = project.reconstruct_study(
                    study, root / (label + "-report"), at=item["report"]["snapshot"]["tip"]
                )
                assert r["report_sha256"] == item["report"]["report_sha256"]
                initial = project.reconstruct_study(
                    study, root / (label + "-initial"), at=item["initial"]["snapshot"]["tip"]
                )
                assert initial["report_sha256"] == item["initial"]["report_sha256"]
                companion = project.reconstruct_comparison(
                    item["comparison"]["comparison"],
                    root / (label + "-comparison"),
                    at=item["comparison"]["snapshot"]["tip"],
                )
                assert companion["report_sha256"] == item["comparison"]["report_sha256"]
                receipts[name]["studies"][label] = r
        assert hashes(Path(project.path)) == before
    result = {
        "application": lab.installation(),
        "reports": receipts,
        "original_project_inventories_unchanged": True,
        "runtime_attachment_used": False,
    }
    write(root / "result.json", result)
    return result


def negative(root, bundle):
    """Mutate only disposable copies, then exercise current fixed trusted readers."""
    import opent1d_lab as lab

    root.mkdir()
    lab.installation()  # Validate the current installed payload before importing its reader.
    payload = Path(lab.__file__).parent / "_payload/app"
    sys.path.insert(0, str(payload))
    from experiments.catalogue.storage import seal
    from experiments.m4.initial_load import common as inherited
    from experiments.m4.installed_study import report
    from experiments.shared_services.store import digest, encoded

    folders = json.loads(bundle.read_bytes())
    original = Path(folders["predecessor"]) / "project"
    before = hashes(original)
    copied = root / "unknown-native-reader"
    shutil.copytree(original, copied)
    for folder in (copied / "events").iterdir():
        if int(folder.name) > 2:
            shutil.rmtree(folder)
    event_folder = copied / "events/00000002"
    event = json.loads((event_folder / "event.json").read_bytes())
    event["data"]["descriptor"]["reader"]["compatibility"] = "unknown-native-reader/999"
    (event_folder / "event.json").write_bytes(encoded(event))
    (event_folder / "plan/descriptor.json").write_bytes(encoded(event["data"]["descriptor"]))
    (event_folder / "manifest.json").unlink()
    seal(event_folder)
    (copied / "HEAD.json").write_bytes(
        encoded(
            {
                "schema": "opent1d.project-store/1",
                "count": 2,
                "tip": digest((event_folder / "manifest.json").read_bytes()),
            }
        )
    )
    copy_before = hashes(copied)
    refused = {}
    try:
        lab.Project(copied).info()
    except ValueError as error:
        assert "Unsupported trusted reader version" in str(error), str(error)
        refused["unknown-native-reader"] = str(error)
    else:
        raise AssertionError("Unknown native reader admitted")
    assert hashes(copied) == copy_before and hashes(original) == before
    archive = Path(folders["predecessor"]) / "archive"
    archived_before = hashes(archive)
    for case in ("resealed-grid", "resealed-repeat"):
        destination = root / case
        shutil.copytree(archive, destination)
        if case == "resealed-grid":
            filename = destination / "children/dalla_man/primary/fasting/candidate-reference.json"
            value = json.loads(filename.read_bytes())
            value["times"][10] += 0.01
        else:
            filename = destination / "children/dalla_man/repeat/worker.json"
            value = json.loads(filename.read_bytes())
            value["label"] = "primary"
        write(filename, value)
        manifest = json.loads((destination / "manifest.json").read_bytes())
        manifest["files"] = {
            k: v for k, v in hashes(destination).items() if k not in inherited.ARTIFACTS
        }
        write(destination / "manifest.json", manifest)
        copy_before = hashes(destination)
        try:
            report.reconstruct(destination)
        except ValueError as error:
            message = str(error)
            assert (
                ("grid" in message.lower() or "time" in message.lower())
                if case == "resealed-grid"
                else ("repeat" in message.lower() or "worker" in message.lower())
            ), message
            refused[case] = message
        else:
            raise AssertionError("Resealed altered numerical evidence admitted")
        assert hashes(destination) == copy_before
    assert hashes(archive) == archived_before and hashes(original) == before
    result = {"refusals": refused, "originals_unchanged": True, "fixed_current_reader_only": True}
    write(root / "result.json", result)
    return result


def main():
    if sys.flags.optimize:
        raise ValueError("Qualification requires assertions")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--phase",
        required=True,
        choices=("direct-prepare", "direct-finish", "candidate", "adverse", "replay", "negative"),
    )
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--roles", type=Path)
    parser.add_argument("--bundle", type=Path)
    args = parser.parse_args()
    functions = {
        "direct-prepare": lambda: direct_prepare(args.output, args.roles),
        "direct-finish": lambda: direct_finish(args.output),
        "candidate": lambda: candidate(args.output, args.roles),
        "adverse": lambda: adverse(args.output, args.roles),
        "replay": lambda: replay(args.output, args.bundle),
        "negative": lambda: negative(args.output, args.bundle),
    }
    functions[args.phase]()
    print(json.dumps({"phase": args.phase, "passed": True}), flush=True)


if __name__ == "__main__":
    main()
