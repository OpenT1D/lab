"""Combined synthetic acceptance; human sessions and product acceptance stay open."""

import csv
import io
import json
import shutil
import tempfile
from copy import deepcopy
from pathlib import Path

from experiments.catalogue.storage import (
    digest,
    dump,
    fresh,
    inventory,
    load_sealed,
    read,
    seal,
    source_hashes,
)
from experiments.mmtt_sampling.fixtures import export_example
from experiments.observation_analysis.fixtures import csv_bytes

from .cases import check_main_report
from .leakage import omitted_cell_controls, schedule_gap_control
from .sampling import MAX_REPORT, task2, verify_task2
from .technical import check_reference_report, cli, task1_phase, verify_task1_phase

SOURCES = tuple(
    f"experiments/ot056_pilot/{name}"
    for name in (
        "__main__.py",
        "cases.py",
        "leakage.py",
        "notebook.py",
        "preflight.py",
        "references.py",
        "rehearsal.py",
        "sampling.py",
        "technical.py",
        "same-estimator.ipynb",
        "same-estimator-sampling.ipynb",
    )
)
IDS = {
    "task2-A",
    "task2-B",
    "task2-C",
    "bad-units",
    "missing-endpoint",
    "duplicate-time",
    "reference",
    "information-loss",
    "invalid-omitted-cells",
    "extreme-omitted-cells",
    "missing-interior-time",
}
SCOPE = (
    "Internal synthetic native CLI/notebook verification; "
    "no human, empirical, vendor-equivalence or product-value acceptance"
)


def prepare_inputs(task1_archive, output):
    """Derive only declared synthetic traps; keep development evidence untouched."""
    output = fresh(output)
    case = task1_archive / "input-preflight/cases/task2-B"
    package = read(case / "package.json")
    rows = list(csv.reader(io.StringIO((case / "observations.csv").read_text())))[1:]
    person = next(p for p in package["participants"] if p["allocation"] == "evaluation")
    identity = (person["id"], person["visits"][0]["id"])

    def write(name, observations, source=case):
        target = output / name
        target.mkdir()
        for filename in ("package.json", "sampling-design.json"):
            shutil.copyfile(source / filename, target / filename)
        (target / "observations.csv").write_bytes(observations)

    missing = [row for row in rows if not (tuple(row[:2]) == identity and float(row[3]) == 120)]
    write("missing-endpoint", csv_bytes(missing))
    duplicate = next(row for row in rows if tuple(row[:2]) == identity and float(row[3]) == 0)
    write("duplicate-time", csv_bytes(rows + [deepcopy(duplicate)]))
    omitted_cell_controls(case, output / "omitted-controls")
    for name in ("invalid-omitted-cells", "extreme-omitted-cells"):
        write(name, (output / "omitted-controls" / f"{name}.csv").read_bytes())
    schedule_gap_control(task1_archive / "reference-inputs", output / "missing-interior-time")
    export_example(output / "information-loss", case="information-loss")
    seal(output)
    return output


def source_map(task1_archive, auxiliary):
    settings = task1_archive / "settings.json"
    return {
        **{
            f"task2-{label}": (task1_archive / f"input-preflight/cases/task2-{label}", settings)
            for label in "ABC"
        },
        "bad-units": (task1_archive / "input-preflight/cases/bad-units", settings),
        "reference": (
            task1_archive / "reference-inputs",
            task1_archive / "reference-settings.json",
        ),
        "missing-interior-time": (
            auxiliary / "missing-interior-time",
            task1_archive / "reference-settings.json",
        ),
        **{
            name: (auxiliary / name, settings)
            for name in (
                "missing-endpoint",
                "duplicate-time",
                "invalid-omitted-cells",
                "extreme-omitted-cells",
                "information-loss",
            )
        },
    }


def read_report(root, case):
    return read(root / case / "native/report.json", limit=MAX_REPORT)


def check_answers(root, expected):
    checks = {}
    for label in "ABC":
        report = read_report(root, f"task2-{label}")
        checks[f"task2-{label}"] = {
            name: check_main_report(record["report"], name)
            for name, record in report["schedules"].items()
        }
    reference = read_report(root, "reference")
    checks["analytical_references"] = {
        name: check_reference_report(record["report"], expected)
        for name, record in reference["schedules"].items()
    }
    loss = read_report(root, "information-loss")
    if not loss["coverage"]["complete_cohort"]:
        raise ValueError("Controlled information-loss case unexpectedly incomplete")
    for name, record in loss["schedules"].items():
        direction = "decrease" if name == "three-times" else "increase"
        for person in record["report"]["people"].values():
            if any(
                v["direction"] != direction or v["status"] != "complete"
                for v in person["variants"].values()
            ):
                raise ValueError("Controlled sampling direction reversal was not reproduced")
    checks["information_loss"] = (
        "full/five/four increase; three decreases in every required variant"
    )
    original = read_report(root, "task2-B")
    for control in ("invalid-omitted-cells", "extreme-omitted-cells"):
        altered = read_report(root, control)
        for schedule in original["plan"]["design"]["subsets"]:
            if (
                altered["schedules"][schedule]["report"]
                != original["schedules"][schedule]["report"]
            ):
                raise ValueError(
                    "Omitted evaluation values leaked into reduced native calculations"
                )
            for filename in ("attempts.json", "report.json", "report.md"):
                relative = Path("native/studies") / schedule / filename
                if (root / control / relative).read_bytes() != (
                    root / "task2-B" / relative
                ).read_bytes():
                    raise ValueError("Omitted values changed retained native attempts or reports")
        if control == "invalid-omitted-cells":
            target = next(
                row
                for row in altered["visit_comparisons"]
                if row["participant_id"] == "invented-evaluation-01"
                and row["schedule"] == "five-times"
                and row["variant"] == "nominal"
                and row["visit"] == "before"
            )
            if (
                target["reference_pmol"] is not None
                or target["reduced_pmol"] is None
                or target["difference_pmol"] is not None
            ):
                raise ValueError(
                    "Unavailable full reference was replaced by zero or hid reduced work"
                )
        checks[control] = "all reduced native reports and perturbations equal the unpoisoned case"
    gap = read_report(root, "missing-interior-time")
    answer = next(a for a in expected["answers"] if a["participant_id"] == "reference-linear-rise")
    for schedule, record in gap["schedules"].items():
        variant = record["report"]["people"][answer["participant_id"]]["variants"]["nominal"]
        before, after = (variant["point"]["visits"][visit] for visit in ("before", "after"))
        if after["status"] != "completed":
            raise ValueError("Missing-time control lost the unaffected visit")
        if schedule in ("full", "five-times"):
            if (
                before["status"] != "failed"
                or before["estimate"] is not None
                or variant["attempted_draws"] != 0
            ):
                raise ValueError("Missing requested time reached the estimator or perturbations")
        elif before["status"] != "completed" or abs(
            before["estimate"]["total_pmol"] - float(answer["before_total_pmol"])
        ) > float(expected["tolerance_pmol"]):
            raise ValueError("Schedule not requesting missing time lost its known valid result")
    checks["missing_interior_time"] = (
        "full/five blocked before estimation; four/three known totals retained; other visit visible"
    )
    missing = read_report(root, "missing-endpoint")
    for record in missing["schedules"].values():
        person = record["report"]["people"]["invented-evaluation-01"]
        for variant in person["variants"].values():
            if (
                variant["point"]["visits"]["before"]["estimate"] is not None
                or variant["point"]["visits"]["after"]["status"] != "completed"
            ):
                raise ValueError("Missing endpoint did not preserve its visit-level failure")
    duplicate = read_report(root, "duplicate-time")
    if any(
        r["status"] != "mask_failed" or r["report"] is not None
        for r in duplicate["schedules"].values()
    ):
        raise ValueError("Duplicate-time structure was not refused before masking/calculation")
    checks["faults"] = (
        "bad units refused; missing endpoints retained; "
        "duplicate times unattempted with full coverage"
    )
    return checks


def common_checks(task1_archive, task2_archive, output):
    output.mkdir()
    result = {}
    for task, config in (
        ("mmtt-sensitivity", task1_archive / "control-increase/native-plan"),
        ("mmtt-sampling", task2_archive / "information-loss/native-plan"),
    ):
        log = output / f"{task}.json"
        if cli("experiments.workflows", ["check", task, "--config", config], log) != 0:
            raise ValueError("Combined task registration/readiness check failed")
        readiness = json.loads(read(log)["stdout"])
        if readiness["ready"] is not True:
            raise ValueError("Registered task did not admit the verified source-bound plan")
        result[task] = True
    return result


def rehearse(output):
    output = fresh(output)
    task1_result = task1_phase(output / "task1")
    prepare_inputs(output / "task1", output / "task2-inputs")
    task2_root = output / "task2"
    task2_root.mkdir()
    records = {
        name: task2(source, settings, task2_root / name, expect_freeze_refusal=name == "bad-units")
        for name, (source, settings) in source_map(
            output / "task1", output / "task2-inputs"
        ).items()
    }
    checks = check_answers(task2_root, read(output / "task1/reference-inputs/expected.json"))
    readiness = common_checks(output / "task1", task2_root, output / "common-checks")
    result = {
        "schema": "ot056-two-task-technical/1",
        "status": "internal-synthetic-two-task-verified",
        "technical_complete": True,
        "source_sha256": source_hashes(SOURCES),
        "human_sessions": 0,
        "human_pilot": "open",
        "product_decision": None,
        "task1_cases": len(task1_result["comparisons"]),
        "task1_manifest_sha256": digest((output / "task1/manifest.json").read_bytes()),
        "task2_comparisons": records,
        "scientific_checks": checks,
        "registered_tasks_ready": readiness,
        "scope": SCOPE,
    }
    dump(output / "technical.json", result)
    seal(output)
    return result


def verify(archive, output):
    archive = load_sealed(archive)
    result = read(archive / "technical.json")
    if result["schema"] != "ot056-two-task-technical/1" or result["source_sha256"] != source_hashes(
        SOURCES
    ):
        raise ValueError("Combined technical source identity differs")
    if (
        result["status"] != "internal-synthetic-two-task-verified"
        or result["technical_complete"] is not True
        or result["human_sessions"] != 0
        or result["human_pilot"] != "open"
        or result["product_decision"] is not None
        or result["scope"] != SCOPE
    ):
        raise ValueError("Combined technical scope cannot supply human or product acceptance")
    if set(result["task2_comparisons"]) != IDS or result["task1_cases"] != 11:
        raise ValueError("Combined technical case coverage differs")
    if result["task1_manifest_sha256"] != digest((archive / "task1/manifest.json").read_bytes()):
        raise ValueError("Task 1 component identity differs")
    output = fresh(output, (archive,))
    verify_task1_phase(archive / "task1", output / "task1")
    with tempfile.TemporaryDirectory() as temporary:
        canonical = prepare_inputs(archive / "task1", Path(temporary) / "inputs")
        if inventory(canonical) != inventory(archive / "task2-inputs"):
            raise ValueError("Task 2 trap inputs differ from trusted synthetic construction")
    for name, (source, settings) in source_map(archive / "task1", archive / "task2-inputs").items():
        for filename, expected in (
            ("package.json", source / "package.json"),
            ("observations.csv", source / "observations.csv"),
            ("design.json", source / "sampling-design.json"),
            ("settings.json", settings),
        ):
            if (
                expected.read_bytes()
                != (archive / "task2" / name / "inputs" / filename).read_bytes()
            ):
                raise ValueError("Task 2 comparison inputs differ from the named canonical case")
        actual = verify_task2(archive / "task2" / name, output / name)
        if actual != result["task2_comparisons"][name]:
            raise ValueError("Task 2 comparison receipt differs")
    if (
        check_answers(archive / "task2", read(archive / "task1/reference-inputs/expected.json"))
        != result["scientific_checks"]
    ):
        raise ValueError("Combined expected-answer checks differ")
    if (
        common_checks(archive / "task1", archive / "task2", output / "common-checks")
        != result["registered_tasks_ready"]
    ):
        raise ValueError("Combined registered-task readiness differs")
    dump(
        output / "verification.json",
        {
            "schema": result["schema"],
            "task1_cases": 11,
            "task2_cases": 11,
            "human_sessions": 0,
            "product_decision": None,
        },
    )
    seal(output)
    return result
