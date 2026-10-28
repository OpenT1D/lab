"""Run the real CLI and same-estimator notebook; audit scientific output equality."""

import subprocess
import sys
import tempfile
from pathlib import Path

from experiments.catalogue.storage import (
    ROOT,
    digest,
    dump,
    fresh,
    load_sealed,
    read,
    seal,
    source_hashes,
)
from experiments.m3.researcher.intake import read_regular
from experiments.observation_analysis.fixtures import CASES, analysis_settings, export_example

from .cases import check_main_report
from .notebook import NOTEBOOK, execute_notebook
from .preflight import preflight, verify_preflight
from .references import export_references, verify_references

TECHNICAL_SOURCES = (
    "experiments/ot056_pilot/technical.py",
    "experiments/ot056_pilot/notebook.py",
    "experiments/ot056_pilot/same-estimator.ipynb",
)
CONTROL_CLASSIFICATIONS = {
    "increase": "consistent within investigated assumptions",
    "assumption-dependent": "assumption-dependent",
    "unresolved": "insufficiently determined",
    "censored": "insufficiently determined",
}
COMPONENT_SCOPE = (
    "Internal synthetic Task 1 component; Task 2 and human acceptance need separate evidence"
)


def cli(module, arguments, log):
    if module not in (
        "experiments.observation_analysis",
        "experiments.mmtt_sampling",
        "experiments.workflows",
    ):
        raise ValueError("Unregistered technical CLI")
    command = [sys.executable, "-S", "-m", module, *map(str, arguments)]
    try:
        completed = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=120)
    except subprocess.TimeoutExpired as error:
        dump(
            log,
            {
                "status": "timeout",
                "stdout": (error.stdout or b"").decode(errors="replace"),
                "stderr": (error.stderr or b"").decode(errors="replace"),
            },
        )
        raise ValueError("Technical CLI timed out; retained log identifies the attempt") from error
    record = {
        "returncode": completed.returncode,
        "stdout": completed.stdout.decode(),
        "stderr": completed.stderr.decode(),
    }
    dump(log, record)
    return completed.returncode


def task1(inputs, settings, output, *, expect_freeze_refusal=False):
    inputs, settings = Path(inputs).absolute(), Path(settings).absolute()
    output = fresh(output, (inputs, settings))
    source_files = {
        "package.json": (inputs / "package.json", 1024 * 1024),
        "observations.csv": (inputs / "observations.csv", 16 * 1024 * 1024),
        "settings.json": (settings, 1024 * 1024),
    }
    snapshot = output / "inputs"
    snapshot.mkdir()
    input_hashes = {}
    for name, (source, limit) in source_files.items():
        raw = read_regular(source, limit, name)
        (snapshot / name).write_bytes(raw)
        input_hashes[name] = digest(raw)
    inputs, settings = snapshot, snapshot / "settings.json"
    code = cli(
        "experiments.observation_analysis",
        [
            "freeze",
            "--package",
            inputs / "package.json",
            "--csv",
            inputs / "observations.csv",
            "--settings",
            settings,
            "--output",
            output / "native-plan",
        ],
        output / "freeze-log.json",
    )
    parameters = {
        "PACKAGE_FILE": str(inputs / "package.json"),
        "CSV_FILE": str(inputs / "observations.csv"),
        "SETTINGS_FILE": str(settings),
    }
    if expect_freeze_refusal:
        if code != 2:
            raise ValueError("Invalid-unit case was not refused by the actual plan freezer")
        try:
            execute_notebook(parameters, output / "notebook")
        except ValueError:
            if read(output / "notebook/execution.json")["status"] != "failed":
                raise
        else:
            raise ValueError("Notebook did not refuse the same invalid-unit input")
        record = {"status": "expected-input-refusal", "human_sessions": 0}
    else:
        if code != 0:
            raise ValueError("Unexpected Task 1 plan refusal; inspect retained freeze log")
        code = cli(
            "experiments.observation_analysis",
            [
                "run",
                "--config",
                output / "native-plan",
                "--output",
                output / "native",
            ],
            output / "run-log.json",
        )
        if code not in (0, 1):
            raise ValueError("Unexpected Task 1 execution refusal")
        report = read(output / "native/report.json", limit=128 * 1024 * 1024)
        if report["execution_status"] != "completed":
            raise ValueError(
                "Technical execution did not finish; scientific failures remain distinct"
            )
        execute_notebook(parameters, output / "notebook")
        matched = {}
        for name in ("report.json", "report.md", "attempts.json"):
            native = (output / "native" / name).read_bytes()
            if native != (output / "notebook" / name).read_bytes():
                raise ValueError(f"Same-estimator notebook differs: {name}")
            matched[name] = digest(native)
        if (output / "native/frozen/plan.json").read_bytes() != (
            output / "notebook/frozen/plan.json"
        ).read_bytes():
            raise ValueError("Native and notebook input/plan/source identities differ")
        package = read(inputs / "package.json")
        if set(report["people"]) != {p["id"] for p in package["participants"]} or (
            report["coverage"]["planned_visits"] != 2 * len(package["participants"])
        ):
            raise ValueError("Task 1 lost declared participant/visit coverage")
        if (
            cli(
                "experiments.observation_analysis",
                [
                    "reconstruct",
                    "--archive",
                    output / "native",
                    "--output",
                    output / "reconstructed",
                    "--allow-failed",
                ],
                output / "reconstruct-log.json",
            )
            != 0
        ):
            raise ValueError("Task 1 reconstruction refused")
        for name in ("report.json", "report.md"):
            if (output / "native" / name).read_bytes() != (
                output / "reconstructed" / name
            ).read_bytes():
                raise ValueError("Task 1 reconstructed report differs")
        record = {
            "status": "matched",
            "matched_sha256": matched,
            "coverage": report["coverage"],
            "human_sessions": 0,
        }
    record["input_sha256"] = input_hashes
    dump(output / "comparison.json", record)
    seal(output)
    return record


def reference_settings(expected):
    settings = analysis_settings()
    kinetics = expected["kinetics"]
    nominal = {
        **settings["variants"][0],
        **{
            key: float(kinetics[key])
            for key in ("k1_per_min", "k2_per_min", "k3_per_min", "volume_l")
        },
        "initial_peripheral_factor": 1.0,
        "rationale": "OT-055 manufactured fixed-kinetic software references; no human defaults",
    }
    settings["variants"] = [
        nominal,
        {
            **nominal,
            "id": "volume-120",
            "volume_l": nominal["volume_l"] * 1.2,
            "rationale": "Declared synthetic volume stress; no empirical parameter range",
        },
        {
            **nominal,
            "id": "peripheral-075",
            "initial_peripheral_factor": 0.75,
            "rationale": "Declared synthetic initial-stock stress; no human prehistory inference",
        },
    ]
    settings["uncertainty"].update(independent_sd_pmol_l=0.001, paired_offset_sd_pmol_l=0.0)
    return settings


def check_reference_report(report, expected):
    tolerance = float(expected["tolerance_pmol"])
    checks = []
    for answer in expected["answers"]:
        person = report["people"][answer["participant_id"]]
        variant = person["variants"]["nominal"]
        point = variant["point"]
        for visit, key in (("before", "before_total_pmol"), ("after", "after_total_pmol")):
            actual = point["visits"][visit]["estimate"]["total_pmol"]
            if abs(actual - float(answer[key])) > tolerance:
                raise ValueError(
                    "Whole-body endpoint disagrees with independent analytical reference"
                )
        if abs(variant["paired_change_pmol"] - float(answer["paired_change_pmol"])) > tolerance:
            raise ValueError("Visit order or paired secretion change disagrees with reference")
        auc = person["references"]["before"]["cpeptide_auc_pmol_min_l"]
        # Independent software tolerance in pmol min/L; not an empirical margin.
        if abs(auc - float(answer["before_auc_pmol_min_l"])) > 1e-7:
            raise ValueError("Separate C-peptide AUC disagrees with reference")
        if answer["negative_terminal_rate_expected"]:
            estimate = point["visits"]["before"]["estimate"]
            terminal = estimate["intervals"][-1]["end_rate_pmol_min"]
            if abs(terminal - float(answer["terminal_rate_pmol_min"])) > 1e-7 or (
                estimate["status"] != "boundary_failed" or variant["status"] != "incomplete"
            ):
                raise ValueError("Negative-rate control was clipped or treated as reliable")
        checks.append(
            {
                "participant_id": answer["participant_id"],
                "status": "passed",
                "nominal_summary_status": variant["status"],
            }
        )
    return {
        "status": "passed",
        "endpoint_tolerance_pmol": tolerance,
        "auc_tolerance_pmol_min_l": 1e-7,
        "rate_tolerance_pmol_min": 1e-7,
        "checks": checks,
    }


def verify_task1(archive, reconstruction):
    archive = load_sealed(archive)
    record = read(archive / "comparison.json")
    if record.get("human_sessions") != 0 or set(record["input_sha256"]) != {
        "package.json",
        "observations.csv",
        "settings.json",
    }:
        raise ValueError("Technical input identity or human-session scope differs")
    for name, sha in record["input_sha256"].items():
        if digest((archive / "inputs" / name).read_bytes()) != sha:
            raise ValueError("Technical input snapshot differs")
    load_sealed(archive / "notebook")
    notebook_execution = read(archive / "notebook/execution.json")
    if notebook_execution["source_sha256"] != digest(NOTEBOOK.read_bytes()) or (
        notebook_execution["human_sessions"] != 0
    ):
        raise ValueError("Notebook source or human-session scope differs")
    if record["status"] == "expected-input-refusal":
        if read(archive / "freeze-log.json")["returncode"] != 2 or (
            read(archive / "notebook/execution.json")["status"] != "failed"
        ):
            raise ValueError("Expected refusal evidence differs")
        load_sealed(archive / "notebook")
        return record
    if record["status"] != "matched" or record["human_sessions"] != 0:
        raise ValueError("Unsupported technical comparison status")
    if notebook_execution["status"] != "executed" or (
        notebook_execution["source_sha256"] != digest(NOTEBOOK.read_bytes())
    ):
        raise ValueError("Notebook source or execution scope differs")
    if set(record["matched_sha256"]) != {"report.json", "report.md", "attempts.json"}:
        raise ValueError("Scientific output coverage differs")
    native_plan = read(archive / "native/frozen/plan.json")
    if native_plan["input_sha256"] != record["input_sha256"] or (
        (archive / "native/frozen/plan.json").read_bytes()
        != (archive / "notebook/frozen/plan.json").read_bytes()
    ):
        raise ValueError("Matched native/notebook plan identities differ")
    if (
        cli(
            "experiments.observation_analysis",
            [
                "reconstruct",
                "--archive",
                archive / "native",
                "--output",
                reconstruction,
                "--allow-failed",
            ],
            reconstruction.parent / f"{reconstruction.name}-log.json",
        )
        != 0
    ):
        raise ValueError("Relocated Task 1 reconstruction failed")
    for name, expected_hash in record["matched_sha256"].items():
        raw = (archive / "native" / name).read_bytes()
        if digest(raw) != expected_hash or raw != (archive / "notebook" / name).read_bytes():
            raise ValueError("Scientific notebook/native evidence differs")
    reconstructed = read(reconstruction / "report.json")
    if record["coverage"] != reconstructed["coverage"]:
        raise ValueError("Comparison coverage differs from trusted reconstruction")
    return record


def task1_phase(output):
    output = fresh(output)
    inputs = preflight(output / "input-preflight")
    settings = output / "settings.json"
    dump(settings, analysis_settings())
    records = {}
    for item in inputs["records"]:
        case_id = item["case"]
        if case_id.startswith("task2-"):
            continue
        records[case_id] = task1(
            output / "input-preflight/cases" / case_id,
            settings,
            output / case_id,
            expect_freeze_refusal=case_id == "bad-units",
        )
        if case_id.startswith("task1-"):
            check_main_report(read(output / case_id / "native/report.json"))
        if item["import_status"] == "invalid" and case_id != "bad-units":
            report = read(output / case_id / "native/report.json")
            if report["coverage"]["complete_cohort"] or all(
                person["status"] == "complete" for person in report["people"].values()
            ):
                raise ValueError("Invalid input control lost its analysis failure")
    expected = export_references(output / "reference-inputs")
    dump(output / "reference-settings.json", reference_settings(expected))
    records["reference"] = task1(
        output / "reference-inputs", output / "reference-settings.json", output / "reference"
    )
    checks = check_reference_report(read(output / "reference/native/report.json"), expected)
    for case in CASES:
        case_id = f"control-{case}"
        export_example(output / f"{case_id}-inputs", case)
        records[case_id] = task1(
            output / f"{case_id}-inputs",
            output / f"{case_id}-inputs/settings.json",
            output / case_id,
        )
        report = read(output / case_id / "native/report.json")
        if report["people"]["invented-01"]["classification"] != CONTROL_CLASSIFICATIONS[case]:
            raise ValueError(
                "Controlled interpretation case differs from its frozen expected answer"
            )
    result = {
        "schema": "ot056-task1-technical/1",
        "status": "task1-component-verified",
        "source_sha256": source_hashes(TECHNICAL_SOURCES),
        "human_sessions": 0,
        "product_decision": None,
        "comparisons": records,
        "reference_checks": checks,
        "scope": COMPONENT_SCOPE,
    }
    dump(output / "technical.json", result)
    seal(output)
    return result


def verify_task1_phase(archive, output):
    archive = load_sealed(archive)
    result = read(archive / "technical.json")
    if result["schema"] != "ot056-task1-technical/1" or (
        result["source_sha256"] != source_hashes(TECHNICAL_SOURCES)
    ):
        raise ValueError("Unsupported technical source identity")
    if (
        result["status"] != "task1-component-verified"
        or result["product_decision"] is not None
        or result["scope"] != COMPONENT_SCOPE
    ):
        raise ValueError(
            "Task 1 rehearsal cannot supply full technical or human product acceptance"
        )
    expected_ids = {
        "task1-A",
        "task1-B",
        "task1-C",
        "bad-units",
        "missing-endpoint",
        "duplicate-time",
        "reference",
        *(f"control-{case}" for case in CASES),
    }
    if set(result["comparisons"]) != expected_ids or result["human_sessions"] != 0:
        raise ValueError("Technical case coverage differs")
    verify_preflight(archive / "input-preflight")
    with tempfile.TemporaryDirectory() as temporary:
        for case in CASES:
            canonical = Path(temporary) / case
            export_example(canonical, case)
            for name in ("package.json", "observations.csv", "settings.json"):
                if (canonical / name).read_bytes() != (
                    archive / f"control-{case}-inputs" / name
                ).read_bytes():
                    raise ValueError(
                        "Named control inputs differ from trusted synthetic construction"
                    )
    expected = verify_references(archive / "reference-inputs")
    if (
        check_reference_report(read(archive / "reference/native/report.json"), expected)
        != (result["reference_checks"])
    ):
        raise ValueError("Independent reference comparison differs")
    output = fresh(output, (archive,))
    for case_id in sorted(expected_ids):
        source = (
            archive / "reference-inputs"
            if case_id == "reference"
            else archive / f"{case_id}-inputs"
            if case_id.startswith("control-")
            else archive / "input-preflight/cases" / case_id
        )
        settings = (
            archive / "reference-settings.json"
            if case_id == "reference"
            else source / "settings.json"
            if case_id.startswith("control-")
            else archive / "settings.json"
        )
        for name, path in {
            "package.json": source / "package.json",
            "observations.csv": source / "observations.csv",
            "settings.json": settings,
        }.items():
            if path.read_bytes() != (archive / case_id / "inputs" / name).read_bytes():
                raise ValueError("Comparison inputs differ from the named source case")
        actual = verify_task1(archive / case_id, output / case_id)
        if case_id.startswith("task1-"):
            check_main_report(read(output / case_id / "report.json"))
        if case_id.startswith("control-"):
            report = read(output / case_id / "report.json")
            if (
                report["people"]["invented-01"]["classification"]
                != CONTROL_CLASSIFICATIONS[case_id.removeprefix("control-")]
            ):
                raise ValueError("Reconstructed control interpretation differs")
        if actual != result["comparisons"][case_id]:
            raise ValueError("Saved technical comparison differs")
    dump(
        output / "verification.json",
        {"schema": result["schema"], "verified_cases": len(expected_ids), "human_sessions": 0},
    )
    seal(output)
    return result
