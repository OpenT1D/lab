"""Qualify an exact two-MMTT wheel against a retained clean PR-43 predecessor.

Runs only standard-library tasks. Retain the fresh output directory, both wheels
and receipts. This internal, actual-host exercise is not release or user approval.
"""

import argparse
import csv
import hashlib
import io
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import threading
import time
import zipfile
from pathlib import Path

PREDECESSOR = "fc041c6e51463ae640d97c55719e742253e453e0"
TASKS = ["mmtt-sensitivity", "mmtt-sampling"]
LEGACY_POLICY = "opent1d.comparison-reader-transition/1"
CURRENT_POLICY = "opent1d.comparison-reader-transition/2"


def canonical(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def transition_identity(result, reader_policy=LEGACY_POLICY, packet_raw=None):
    if reader_policy == LEGACY_POLICY:
        # Preserve the original qualification's literal historical assertion.
        assert result["reader_transition"]["policy"] == "opent1d.comparison-reader-transition/1"
        return
    assert reader_policy == CURRENT_POLICY and packet_raw is not None
    packet = json.loads(packet_raw)
    assert packet["schema"] == CURRENT_POLICY and packet["tasks"] == TASKS
    assert packet["historical_registry_sha256"] == (
        "6b50b5b97f9888e55f2fdddd86388a35963ce090291f37850cffb4863ed6f0e0"
    )
    assert packet["m3_predecessor_revision"] == "6e77f7b86d3418ac5702dfb1efdd0edf68cabd90"
    assert hashlib.sha256(canonical(packet["m3_predecessor"])).hexdigest() == (
        "b6fb575b6bf5532a53f0fb2fd20a3efad5bfadc162dae9f010a2e0d6442e24ec"
    )
    expected = {"schema": CURRENT_POLICY, "registry_sha256": hashlib.sha256(packet_raw).hexdigest()}
    assert result["reader_transition"]["policy"] == CURRENT_POLICY
    assert result["reader_transition"]["registry_sha256"] == expected["registry_sha256"]
    assert canonical(result["reader"]["compatibility"]) == canonical(expected)
    assert canonical(
        {key: value for key, value in result["reader"].items() if key != "compatibility"}
    ) == canonical(packet["successor"])


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def inventory(path):
    result = {}
    for item in path.rglob("*"):
        if item.is_symlink():
            raise ValueError("Linked qualification evidence refused")
        if item.is_file():
            result[item.relative_to(path).as_posix()] = hashlib.sha256(
                item.read_bytes()
            ).hexdigest()
    return result


def artifact_identity(label, receipt, actual):
    """The installed descriptor, not an editable external receipt, owns scope."""
    assert actual["source"] == receipt["source"]
    assert actual["source"]["dirty"] is False and receipt["source"]["dirty"] is False
    assert set(actual["source"]) == {"revision", "dirty"}
    assert re.fullmatch(r"[0-9a-f]{40}", actual["source"]["revision"])
    assert actual["build_label"] == receipt["build_label"]
    if label == "a":
        assert actual["source"]["revision"] == PREDECESSOR
        assert actual["schema"] == "opent1d.installed-sdk/3"
        assert actual["tasks"] == [
            "mmtt-sensitivity",
            "m4-study-secure",
            "m4-study-installed",
            "mmtt-sampling",
        ]
        assert actual["native_execution"] == "explicit-reviewed-attachment/1"
    else:
        assert actual["schema"] == receipt["descriptor_schema"] == "opent1d.installed-sdk/4"
        assert actual["descriptor_sha256"] == receipt["descriptor_sha256"]
        assert actual["tasks"] == receipt["tasks"] == TASKS
        assert (
            actual["native_execution"] == receipt["native_execution"] == "unavailable-public-policy"
        )


def expected_outcome(name, attempt):
    result = attempt["result"]
    assert attempt["receipt"]["remaining_owned_processes"] == []
    if name in {"paired", "sampling", "missing"}:
        assert result["payload"] == "native" and result["execution_status"] == "completed", attempt
        assert result["completeness"] == ("incomplete" if name == "missing" else "complete"), (
            attempt
        )
        slots = list(result["slot_statuses"].values())
        assert len(slots) == (3 if name == "paired" else 60), attempt
        assert slots.count("complete") == (36 if name == "missing" else len(slots)), attempt
        if name == "missing":
            assert slots.count("failed") == 24 and slots.count("unavailable") == 0, attempt


def materials(root, qualification, reference):
    """Keep unanswered participant goals apart from actual technical reference answers."""
    (root / "participant").mkdir(parents=True)
    (root / "facilitator").mkdir()
    (root / "participant/Tasks.md").write_text(
        "# Invented meal-test research exercise\n\n"
        "Use only invented data. Explain your reasoning; ask for help when needed.\n\n"
        "1. Create a project and inspect the supplied paired meal-test inputs.\n"
        "2. Prepare a related analysis with one changed assumption. Preserve both plans, "
        "freeze their comparison before execution and explain the result and its limits.\n"
        "3. Investigate the full and reduced measurement schedules on the supplied "
        "synthetic sampling task. Explain what is estimated and which cases remain missing.\n"
        "4. Recover from the supplied unsuccessful attempt, preserving its first outcome.\n"
        "5. Move the complete project, reopen it with the declared replacement application "
        "and reproduce a saved report. Explain what has been verified.\n\n"
        "Keep your first answers, including unsuccessful work. Do not use health records "
        "or make clinical decisions.\n"
    )
    shutil.copytree(reference / "recovery-project", root / "participant/recovery-project")
    candidate = qualification["artifacts"]["b"]
    (root / "participant/Start.md").write_text(
        "# Prepared local exercise\n\n"
        "Your facilitator supplies the installed candidate and its guide. "
        "The recovery-project folder contains an actual retained unsuccessful synthetic "
        "attempt. Open that whole folder for the recovery task. Keep all attempts.\n\n"
        + "Candidate source: `"
        + candidate["source"]["revision"]
        + "`. "
        + "Wheel SHA-256: `"
        + candidate["wheel_sha256"]
        + "`.\n\n"
        + "Guide: https://github.com/OpenT1D/lab/blob/"
        + candidate["source"]["revision"]
        + "/docs/internal-mmtt-candidate.md\n"
    )
    (root / "facilitator/Key.md").write_text(
        "# Facilitator key — keep separate from participant materials\n\n"
        "Technical preparation only; no human session or usability finding is recorded. "
        "Freeze candidate, host, guide, task order and references before observing an "
        "actual intended analyst. Record assistance, first answers, critical errors, "
        "blocked tasks and retries separately. A distinct recipient is required for an "
        "independent handoff claim. Directory separation is not access control.\n\n"
        "MMTT estimates whole-body total secretion including basal over 0–120 minutes "
        "in pmol; paired change is follow-up minus baseline. C-peptide concentration and "
        "AUC are different quantities. Perturbations describe conditional engineering "
        "uncertainty, not biological validity or assay performance. Sampling selection "
        "uses development evidence only. Preserve every planned and missing case.\n\n"
        "A comparison must precede its selected plans' execution. Its first attempts "
        "remain selected after retries. Reading is not rerunning the physiological model. "
        "The supported upgrade is the exact pinned PR-43 MMTT comparison reader to this "
        "candidate; other reader changes and native/connected projects are unsupported. "
        "Rollback means reopening preserved A evidence in A, not reading new B comparisons.\n\n"
        "Use the actual copied reference reports below; do not invent reference values. "
        "Mark wrong units/window/direction, missing-as-zero, passing-subset reasoning, "
        "lost evidence and success-as-validity as critical errors. Keep active work, "
        "unattended compute and elapsed time separate. Leave unobserved fields null.\n"
    )
    for name in ("paired", "sampling", "missing", "failed", "cancelled"):
        shutil.copytree(reference / (name + "-report"), root / "facilitator" / name)
    write(
        root / "facilitator/observations.template.json",
        {
            "human_sessions": "not_recorded",
            "participant_code": None,
            "recipient_code": None,
            "consent_record": None,
            "tasks": [
                {
                    "id": name,
                    "status": None,
                    "first_answer": None,
                    "active_seconds": None,
                    "compute_seconds": None,
                    "elapsed_seconds": None,
                    "assistance": [],
                    "critical_errors": [],
                    "retests": [],
                }
                for name in ("inputs", "assumptions", "sampling", "recovery", "handoff")
            ],
        },
    )
    write(
        root / "packet.json",
        {
            "schema": "opent1d.internal-mmtt-formative-packet/1",
            "evidence_kind": "preparation",
            "candidate": qualification["artifacts"]["b"],
            "host": qualification["host"],
            "human_sessions": "not_recorded",
            "files": inventory(root),
        },
    )


def prepare(root):
    import opent1d_lab as lab

    root.mkdir()
    project = lab.create_project(root / "project", "Invented reader transition controls")
    record = {
        "application": lab.installation(),
        "plans": {},
        "comparisons": {},
        "attempts": {},
        "reports": {},
    }
    for name, task, case in (
        ("paired", "mmtt-sensitivity", "complete"),
        ("sampling", "mmtt-sampling", "information-loss"),
        ("missing", "mmtt-sampling", "incomplete"),
        ("failed", "mmtt-sensitivity", "complete"),
        ("cancelled", "mmtt-sampling", "information-loss"),
    ):
        inputs = lab.example(task, root / (name + "-inputs"), case=case)["inputs"]
        plan = project.freeze(task, inputs)["plan"]
        record["plans"][name] = plan
        sampling = task == "mmtt-sampling"
        members = [
            {
                "id": "base",
                "label": "Nominal",
                "plan": plan,
                "selector": {"variant": "nominal", **({"schedule": "full"} if sampling else {})},
            },
            {
                "id": "changed",
                "label": "Declared contrast",
                "plan": plan,
                "selector": {
                    "variant": "nominal" if sampling else "volume-120",
                    **({"schedule": "three-times"} if sampling else {}),
                },
            },
        ]
        comparison = project.freeze_comparison(
            {
                "schema": "opent1d.plan-comparison/1",
                "name": name,
                "question": "What changes under the frozen synthetic assumptions?",
                "baseline": "base",
                "variants": members,
            }
        )["comparison"]
        record["comparisons"][name] = comparison
        record["reports"][name + "-initial"] = project.reconstruct_comparison(
            comparison, root / (name + "-initial")
        )
        cancel, observed = threading.Event(), threading.Event()
        watcher = None
        if name == "cancelled":

            def stop():
                deadline = time.monotonic() + 40
                while time.monotonic() < deadline and not cancel.is_set():
                    for filename in (Path(project.path) / "work").glob(
                        "*/native/studies/*/execution.json"
                    ):
                        try:
                            state = json.loads(filename.read_bytes())
                        except (OSError, ValueError):
                            continue
                        if state.get("phase") == "analysis" and state.get("status") == "started":
                            observed.set()
                            cancel.set()
                            return
                    time.sleep(0.005)

            watcher = threading.Thread(target=stop)
            watcher.start()
        try:
            attempt = project.run(
                plan, timeout=0.000001 if name == "failed" else 600, cancel=cancel
            )
        finally:
            cancel.set()
            if watcher:
                watcher.join(timeout=45)
        if name == "cancelled":
            assert observed.is_set() and not watcher.is_alive(), (
                "Actual analysis cancellation was not observed"
            )
            assert attempt["result"]["execution_status"] == "interrupted", attempt
        if name == "failed":
            assert attempt["result"]["execution_status"] == "failed", attempt
        expected_outcome(name, attempt)
        record["attempts"][name] = attempt
        record["reports"][name] = project.reconstruct_comparison(
            comparison, root / (name + "-report")
        )
        if attempt["result"]["payload"] == "native":
            record["reports"][name + "-native"] = project.reconstruct(
                attempt["attempt"], root / (name + "-native"), allow_failed=True
            )
        write(root / "progress.json", record)
    for name in ("failed", "cancelled"):
        record["attempts"][name + "-retry"] = project.run(
            record["plans"][name], retry_of=record["attempts"][name]["attempt"]
        )
        assert record["attempts"][name + "-retry"]["result"]["completeness"] == "complete"
    # Independent analytic control through this actual installed artifact.
    inputs = lab.example("mmtt-sensitivity", root / "constant-inputs")["inputs"]
    csv_path = Path(inputs["observations.csv"])
    reader = csv.DictReader(io.StringIO(csv_path.read_text()))
    target = io.StringIO(newline="")
    writer = csv.DictWriter(target, fieldnames=reader.fieldnames, lineterminator="\n")
    writer.writeheader()
    for row in reader:
        row["cpeptide_nmol_l"] = "0.2" if row["visit_id"] == "before" else "0.3"
        writer.writerow(row)
    csv_path.write_text(target.getvalue())
    plan = project.freeze("mmtt-sensitivity", inputs)["plan"]
    run = project.run(plan)
    project.reconstruct(run["attempt"], root / "constant-report")
    report = json.loads((root / "constant-report/report.json").read_bytes())
    for person in report["people"].values():
        variant = person["variants"]["nominal"]
        for visit, concentration in (("before", 200), ("after", 300)):
            expected = concentration * 4.585 * 0.052 * 120
            actual = variant["point"]["visits"][visit]["estimate"]["total_pmol"]
            assert abs(actual - expected) <= 1e-8, (actual, expected)
    record["constant_reference"] = "passed; independent basal-inclusive amount, 1e-8 pmol"
    recovery = lab.create_project(root / "recovery-project", "Invented unsuccessful attempt")
    recovery_plan = recovery.freeze("mmtt-sensitivity", inputs)["plan"]
    recovery_attempt = recovery.run(recovery_plan, timeout=0.000001)
    assert recovery_attempt["result"]["execution_status"] == "failed"
    assert recovery_attempt["receipt"]["remaining_owned_processes"] == []
    record["recovery_exercise"] = recovery_attempt
    record["head"] = project.info()["head"]
    record["project_files"] = inventory(Path(project.path))
    write(root / "record.json", record)
    return record


def replay(root, source, reader_policy=LEGACY_POLICY, packet_raw=None):
    import opent1d_lab as lab

    root.mkdir()
    record = json.loads((source / "record.json").read_bytes())
    project = lab.Project(source / "project")
    before = inventory(Path(project.path))
    assert before == record["project_files"]
    assert project.info()["head"] == record["head"]
    results = {}
    for name, original in record["reports"].items():
        if name.endswith("-native"):
            role = name.removesuffix("-native")
            results[name] = project.reconstruct(
                record["attempts"][role]["attempt"], root / name, allow_failed=True
            )
        else:
            role = name.removesuffix("-initial")
            results[name] = project.reconstruct_comparison(
                record["comparisons"][role], root / name, at=original["snapshot"]["tip"]
            )
        assert results[name]["report_sha256"] == original["report_sha256"], name
        if not name.endswith("-native"):
            transition_identity(results[name], reader_policy, packet_raw)
    assert inventory(Path(project.path)) == before, "Reading changed the original project"
    # Retrying must never replace the frozen first failure/cancellation.
    for name in ("failed", "cancelled"):
        view = project.comparison(record["comparisons"][name])
        assert (
            view["attempts"][record["plans"][name]]["attempt"]
            == record["attempts"][name]["attempt"]
        )
    receipt = {
        "application": lab.installation(),
        "source_application": record["application"],
        "results": results,
        "project_unchanged": True,
    }
    write(root / "receipt.json", receipt)
    return receipt


def orchestrate(args):
    root = args.output.absolute()
    root.mkdir(exist_ok=False)
    if not (
        platform.system() == "Darwin"
        and platform.machine() == "arm64"
        and sys.version_info[:2] == (3, 12)
    ):
        raise ValueError("This qualification selects Apple Silicon macOS CPython 3.12")
    probe = root / "qualification.py"
    shutil.copyfile(__file__, probe)
    artifacts = {}
    packet_path = None
    env = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
    env["UV_CACHE_DIR"] = str(root / "cache")
    for label in ("a", "b"):
        receipt_path = getattr(args, label + "_receipt")
        receipt = json.loads(receipt_path.read_bytes())
        wheel = getattr(args, label + "_wheel").absolute()
        assert not receipt["source"]["dirty"], "Use clean source artifacts"
        assert hashlib.sha256(wheel.read_bytes()).hexdigest() == receipt["wheel_sha256"]
        if label == "a":
            assert receipt["source"]["revision"] == PREDECESSOR
        else:
            assert receipt["source"]["revision"] != PREDECESSOR
            assert receipt["tasks"] == TASKS
            if args.reader_policy == CURRENT_POLICY:
                with zipfile.ZipFile(wheel) as payload:
                    prefix = "opent1d_lab/_payload/app/experiments/shared_services/"
                    legacy = payload.read(prefix + "reader_compatibility.json")
                    assert hashlib.sha256(legacy).hexdigest() == (
                        "6b50b5b97f9888e55f2fdddd86388a35963ce090291f37850cffb4863ed6f0e0"
                    )
                    packet_path = root / "qualified-reader-packet.json"
                    packet_path.write_bytes(payload.read(prefix + "reader_compatibility_m3.json"))
        destination = root / ("artifact-" + label)
        destination.mkdir()
        shutil.copyfile(wheel, destination / wheel.name)
        shutil.copyfile(receipt_path, destination / "receipt.json")
        environment = root / ("environment-" + label)
        for command in (
            ["uv", "venv", "--offline", "--python", sys.executable, str(environment)],
            [
                "uv",
                "pip",
                "install",
                "--offline",
                "--no-deps",
                "--link-mode=copy",
                "--python",
                str(environment / "bin/python"),
                str(destination / wheel.name),
            ],
        ):
            subprocess.run(command, env=env, check=True, capture_output=True)
        artifacts[label] = {"receipt": receipt, "python": environment / "bin/python"}
        installed = subprocess.run(
            [str(environment / "bin/opent1d-lab"), "installation"],
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
        actual = json.loads(installed.stdout)
        artifact_identity(label, receipt, actual)
        artifacts[label]["installation"] = actual

    def run(label, mode, output, source=None):
        command = [
            str(artifacts[label]["python"]),
            "-I",
            "-B",
            str(probe),
            "--probe",
            mode,
            "--output",
            str(output),
        ]
        if source:
            command += ["--source", str(source)]
        if mode == "replay":
            command += ["--reader-policy", args.reader_policy]
            if packet_path:
                command += ["--qualification-packet", str(packet_path)]
        with (root / (label + "-" + mode + ".log")).open("xb") as log:
            subprocess.run(
                command,
                cwd=root,
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=True,
                timeout=900,
            )

    run("a", "prepare", root / "predecessor")
    moved = root / "relocated"
    shutil.copytree(root / "predecessor", moved)
    (root / "predecessor").rename(root / "original-unavailable")
    (root / "environment-a").rename(root / "application-a-unavailable")
    run("b", "replay", root / "upgrade", moved)
    # Restore the exact predecessor installation for rollback, not a new build.
    (root / "application-a-unavailable").rename(root / "environment-a")
    preserved = json.loads((moved / "record.json").read_bytes())
    code = (
        "import opent1d_lab as lab,json\n"
        + "p=lab.open_project("
        + repr(str(moved / "project"))
        + ")\n"
        + "r=p.reconstruct_comparison("
        + repr(preserved["comparisons"]["paired"])
        + ","
        + repr(str(root / "rollback-report"))
        + ",at="
        + repr(preserved["reports"]["paired"]["snapshot"]["tip"])
        + ")\n"
        + "print(json.dumps({'head':p.info()['head'],'report_sha256':r['report_sha256']}))"
    )
    rollback = subprocess.run(
        [str(artifacts["a"]["python"]), "-I", "-B", "-c", code],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    )
    rollback_result = json.loads(rollback.stdout)
    assert rollback_result["head"] == preserved["head"]
    assert rollback_result["report_sha256"] == preserved["reports"]["paired"]["report_sha256"]
    assert (
        inventory(moved / "project")
        == json.loads((moved / "record.json").read_bytes())["project_files"]
    )
    run("b", "prepare", root / "current-workflows")
    result = {
        "schema": "opent1d.internal-mmtt-candidate-qualification/1",
        "host": {
            "system": platform.system(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "artifacts": {label: value["receipt"] for label, value in artifacts.items()},
        "upgrade": "passed",
        "rollback": "passed",
        "current_workflows": "passed",
        "native_packaging": "excluded",
        "human_sessions": "not_recorded",
        "public_release": False,
    }
    if args.reader_policy == CURRENT_POLICY:
        result["schema"] = "opent1d.internal-mmtt-candidate-qualification/2"
        result["reader_policy"] = CURRENT_POLICY
        result["reader_packet_sha256"] = hashlib.sha256(packet_path.read_bytes()).hexdigest()
    materials(root / "formative-packet", result, root / "current-workflows")
    result["formative_packet_sha256"] = hashlib.sha256(
        (root / "formative-packet/packet.json").read_bytes()
    ).hexdigest()
    write(root / "qualification.json", result)
    print(json.dumps(result, sort_keys=True))


def main():
    if sys.flags.optimize:
        raise ValueError("Run candidate qualification with assertions enabled")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", choices=("prepare", "replay"))
    parser.add_argument("--source", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--reader-policy", choices=(LEGACY_POLICY, CURRENT_POLICY), default=LEGACY_POLICY
    )
    parser.add_argument(
        "--qualification-packet",
        type=Path,
        help="internal replay probe; exact packet extracted from the verified successor wheel",
    )
    for label in ("a", "b"):
        parser.add_argument("--" + label + "-wheel", type=Path)
        parser.add_argument("--" + label + "-receipt", type=Path)
    args = parser.parse_args()
    if args.probe:
        result = (
            prepare(args.output)
            if args.probe == "prepare"
            else replay(
                args.output,
                args.source,
                args.reader_policy,
                args.qualification_packet.read_bytes() if args.qualification_packet else None,
            )
        )
        print(
            json.dumps(
                {"probe": args.probe, "passed": True, "application": result.get("application")},
                sort_keys=True,
            )
        )
    else:
        orchestrate(args)


if __name__ == "__main__":
    main()
