"""Actual Task 2 CLI/notebook agreement, retaining every scientific failure."""

from pathlib import Path

from experiments.catalogue.storage import digest, dump, encoded, fresh, load_sealed, read, seal
from experiments.m3.researcher.intake import read_regular
from experiments.observation_analysis.observations import validate_package

from .notebook import SAMPLING_NOTEBOOK, execute_notebook
from .preflight import development_copy
from .technical import cli

MAX_REPORT = 512 * 1024 * 1024
PROJECTION = "Only top-level native execution journal excluded; all scientific content retained"


def scientific(report):
    """Exclude only the native process journal, never scientific content."""
    if report["schema"] != "opent1d.mmtt-sampling/1":
        raise ValueError("Expected the registered Task 2 scientific report")
    return {key: value for key, value in report.items() if key != "execution"}


def coverage(report, package):
    count = len(package["participants"])
    variants = len(report["plan"]["settings"]["variants"])
    schedules = 1 + len(report["plan"]["design"]["subsets"])
    expected = {
        "planned_people": count,
        "planned_schedules": schedules,
        "planned_visits_per_schedule": 2 * count,
        "planned_variant_pairs": schedules * count * variants,
        "planned_visit_points": 2 * schedules * count * variants,
        "planned_draw_pairs": schedules
        * count
        * variants
        * report["plan"]["settings"]["uncertainty"]["draws"],
    }
    if any(report["coverage"][key] != value for key, value in expected.items()):
        raise ValueError("Task 2 dropped planned participant/schedule/attempt coverage")
    for record in report["schedules"].values():
        if record["report"] is not None and set(record["report"]["people"]) != {
            person["id"] for person in package["participants"]
        }:
            raise ValueError("Task 2 child lost declared participants")


def matched_files(report):
    return {
        "scientific-report.json",
        "report.md",
        *(
            f"studies/{schedule}/{name}"
            for schedule, record in report["schedules"].items()
            if record["report"] is not None
            for name in ("report.json", "report.md", "attempts.json")
        ),
    }


def check_outputs(archive, report):
    """Compare the entire scientific projection and all child attempts exactly."""
    hashes = {}
    projected = encoded(scientific(report))
    if projected != (archive / "notebook/report.json").read_bytes():
        raise ValueError("Task 2 scientific notebook/native reports differ")
    if projected != (archive / "scientific-report.json").read_bytes():
        raise ValueError("Saved Task 2 scientific projection differs")
    for name in matched_files(report):
        native = (
            projected
            if name == "scientific-report.json"
            else (archive / "native" / name).read_bytes()
        )
        notebook_name = "report.json" if name == "scientific-report.json" else name
        if native != (archive / "notebook" / notebook_name).read_bytes():
            raise ValueError(f"Task 2 notebook/native scientific bytes differ: {name}")
        hashes[name] = digest(native)
    for schedule, record in report["schedules"].items():
        if record["report"] is not None and (
            (archive / "native/plans" / schedule / "plan.json").read_bytes()
            != (archive / "notebook/plans" / schedule / "plan.json").read_bytes()
        ):
            raise ValueError("Task 2 child frozen input/settings/source plans differ")
    return hashes


def task2(inputs, settings, output, *, expect_freeze_refusal=False):
    inputs, settings = Path(inputs).absolute(), Path(settings).absolute()
    output = fresh(output, (inputs, settings))
    snapshot = output / "inputs"
    snapshot.mkdir()
    hashes = {}
    for name, source, limit in (
        ("package.json", inputs / "package.json", 1024 * 1024),
        ("observations.csv", inputs / "observations.csv", 16 * 1024 * 1024),
        ("settings.json", settings, 1024 * 1024),
        ("design.json", inputs / "sampling-design.json", 1024 * 1024),
    ):
        raw = read_regular(source, limit, name)
        (snapshot / name).write_bytes(raw)
        hashes[name] = digest(raw)
    development_copy(snapshot, output / "development-inputs")
    imported = cli(
        "experiments.observation_analysis",
        [
            "import",
            "--package",
            output / "development-inputs/package.json",
            "--csv",
            output / "development-inputs/observations.csv",
            "--output",
            output / "development-import",
        ],
        output / "import-log.json",
    )
    if imported != (2 if expect_freeze_refusal else 0):
        raise ValueError("Unexpected development import outcome")
    code = cli(
        "experiments.mmtt_sampling",
        [
            "freeze-study",
            "--package",
            snapshot / "package.json",
            "--csv",
            snapshot / "observations.csv",
            "--settings",
            snapshot / "settings.json",
            "--design",
            snapshot / "design.json",
            "--development-import",
            output / "development-import",
            "--output",
            output / "native-plan",
        ],
        output / "freeze-log.json",
    )
    parameters = {
        "PACKAGE_FILE": str(snapshot / "package.json"),
        "CSV_FILE": str(snapshot / "observations.csv"),
        "SETTINGS_FILE": str(snapshot / "settings.json"),
        "DESIGN_FILE": str(snapshot / "design.json"),
        "DEVELOPMENT_IMPORT": str(output / "development-import"),
    }
    if expect_freeze_refusal:
        if code != 2:
            raise ValueError("Task 2 did not refuse invalid units before estimation")
        try:
            execute_notebook(parameters, output / "notebook", task="task2")
        except ValueError:
            if read(output / "notebook/execution.json")["status"] != "failed":
                raise
        else:
            raise ValueError("Task 2 notebook accepted invalid units")
        record = {"status": "expected-input-refusal"}
    else:
        if code != 0:
            raise ValueError("Unexpected Task 2 study-plan refusal")
        code = cli(
            "experiments.mmtt_sampling",
            ["run", "--config", output / "native-plan", "--output", output / "native"],
            output / "run-log.json",
        )
        if code not in (0, 1):
            raise ValueError("Unexpected Task 2 execution refusal")
        report = read(output / "native/report.json", limit=MAX_REPORT)
        if report["execution_status"] != "completed":
            raise ValueError(
                "Task 2 execution unfinished; retained scientific failures are separate"
            )
        coverage(report, read(snapshot / "package.json"))
        execute_notebook(parameters, output / "notebook", task="task2")
        if (output / "native/frozen/plan.json").read_bytes() != (
            output / "notebook/frozen/plan.json"
        ).read_bytes():
            raise ValueError("Task 2 native/notebook study inputs or frozen identities differ")
        dump(output / "scientific-report.json", scientific(report))
        matched = check_outputs(output, report)
        if (
            cli(
                "experiments.mmtt_sampling",
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
            raise ValueError("Task 2 native reconstruction refused")
        for name in ("report.json", "report.md"):
            if (output / "native" / name).read_bytes() != (
                output / "reconstructed" / name
            ).read_bytes():
                raise ValueError("Task 2 reconstructed parent report differs")
        record = {"status": "matched", "coverage": report["coverage"], "matched_sha256": matched}
    record.update(
        human_sessions=0,
        input_sha256=hashes,
        development_manifest_sha256=digest(
            (output / "development-import/manifest.json").read_bytes()
        ),
        scientific_projection=PROJECTION,
    )
    dump(output / "comparison.json", record)
    seal(output)
    return record


def verify_task2(archive, reconstruction):
    archive = load_sealed(archive)
    record = read(archive / "comparison.json")
    if (
        record["scientific_projection"] != PROJECTION
        or record["human_sessions"] != 0
        or set(record["input_sha256"])
        != {
            "package.json",
            "observations.csv",
            "settings.json",
            "design.json",
        }
    ):
        raise ValueError("Task 2 comparison input or human scope differs")
    for name, sha in record["input_sha256"].items():
        if digest((archive / "inputs" / name).read_bytes()) != sha:
            raise ValueError("Task 2 input snapshot differs")
    if (
        digest((archive / "development-import/manifest.json").read_bytes())
        != record["development_manifest_sha256"]
    ):
        raise ValueError("Task 2 development evidence differs")
    load_sealed(archive / "notebook")
    notebook = read(archive / "notebook/execution.json")
    if (
        notebook["human_sessions"] != 0
        or notebook["task"] != "task2"
        or (notebook["source_sha256"] != digest(SAMPLING_NOTEBOOK.read_bytes()))
    ):
        raise ValueError("Task 2 fixed notebook identity or scope differs")
    if record["status"] == "expected-input-refusal":
        if read(archive / "freeze-log.json")["returncode"] != 2 or notebook["status"] != "failed":
            raise ValueError("Task 2 refusal evidence differs")
        try:
            validate_package(read(archive / "inputs/package.json"))
        except ValueError:
            return record
        raise ValueError("Task 2 metadata refusal is not reproducible")
    if record["status"] != "matched" or notebook["status"] != "executed":
        raise ValueError("Unsupported Task 2 comparison status")
    plan = read(archive / "native/frozen/plan.json")
    if (
        plan["input_sha256"] != record["input_sha256"]
        or (plan["development_manifest_sha256"] != record["development_manifest_sha256"])
        or (archive / "native/frozen/plan.json").read_bytes()
        != (archive / "notebook/frozen/plan.json").read_bytes()
    ):
        raise ValueError("Task 2 input/development/plan binding differs")
    if (
        cli(
            "experiments.mmtt_sampling",
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
        raise ValueError("Relocated Task 2 native reconstruction refused")
    report = read(reconstruction / "report.json", limit=MAX_REPORT)
    coverage(report, read(archive / "inputs/package.json"))
    if (
        record["coverage"] != report["coverage"]
        or check_outputs(archive, report) != record["matched_sha256"]
    ):
        raise ValueError("Task 2 comparison coverage or scientific hashes differ")
    return record
