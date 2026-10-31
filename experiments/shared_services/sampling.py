"""Sampling service binding; native scientific files and readers stay unchanged."""

from pathlib import Path

from experiments.catalogue.storage import decode, digest, load_sealed
from experiments.m3.researcher.intake import read_regular
from experiments.mmtt_sampling import plan as native
from experiments.mmtt_sampling import report as reporting
from experiments.mmtt_sampling import run as runner
from experiments.observation_analysis import plan as paired
from experiments.observation_analysis.analysis import report_from_attempts
from experiments.setup.core import requirements, selectors
from experiments.shared_contracts.inventory import reader_source_inventory
from experiments.shared_contracts.selected import boundary as paired_boundary
from experiments.shared_contracts.selected import outcome as paired_outcome

from .store import Budget, inventory, read, require, snapshot, write

TASK = "mmtt-sampling"
MODULE = "experiments.mmtt_sampling"
FILES = {"package.json", "observations.csv", "settings.json", "design.json"}
ROOT = Path(__file__).resolve().parents[2]


def reader():
    return {
        "module": MODULE,
        "report_schema": reporting.SCHEMA,
        "trusted_sources_sha256": native.source_identity(),
        "archived_code_execution": False,
    }


def binding():
    return {
        "implementation_sha256": native.source_identity(),
        "runtime_files_sha256": {project: selectors(project) for project in requirements(TASK)},
        "protocol_sha256": digest(native.PROTOCOL.read_bytes()),
        "shared_protocol_sha256": digest(native.SHARED_PROTOCOL.read_bytes()),
        "method": native.VERSION,
        "ancestry_sha256": native.ancestry_identity(),
    }


def boundary(plan, package):
    return {
        "family": "offline-sampling-comparison/1-provisional",
        "binding": binding(),
        "planned_slots": [
            f"{schedule}/{person['id']}/{variant['id']}"
            for schedule in runner.schedule_map(plan)
            for person in package["participants"]
            for variant in plan["settings"]["variants"]
        ],
    }


def hashes(folder):
    files, _ = inventory(folder, Budget())
    return {
        name: digest(read_regular(folder / name, 32 * 1024 * 1024, "sampling input snapshot"))
        for name in files["files"]
    }


def trusted_sources(plan):
    from .routes import runtime_paths

    identity = {**reader(), **reader_source_inventory(MODULE)}
    names = (
        set(identity["trusted_sources_sha256"])
        | set(identity["reader_static_dependencies_sha256"])
        | set(plan["ancestry_sha256"])
        | runtime_paths(binding())
    )
    return identity | {"compatibility": "exact-trusted-reader/1"}, {
        name: digest(read_regular(ROOT / name, 4 * 1024 * 1024, "trusted sampling source"))
        for name in sorted(names)
    }


def capture(inputs, target):
    require(set(inputs) == FILES | {"development"}, "Sampling raw files and development required")
    target.mkdir()
    original = target / "original"
    original.mkdir()
    for name in sorted(FILES):
        (original / name).write_bytes(read_regular(inputs[name], native.RAW_LIMITS[name], name))
    snapshot(inputs["development"], original / "development")
    plan = native.freeze(
        original / "package.json",
        original / "observations.csv",
        original / "settings.json",
        original / "design.json",
        original / "development",
        target / "input",
    )
    package = read(original / "package.json")
    reader_identity, sources = trusted_sources(plan)
    for name in sources:
        path = target / "trusted" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(read_regular(ROOT / name, 4 * 1024 * 1024, "trusted snapshot"))
    descriptor = {
        "schema": "opent1d.service-freeze/1",
        "task": TASK,
        "boundary": boundary(plan, package),
        "reader": reader_identity,
        "original_sha256": hashes(original),
        "trusted_sha256": sources,
    }
    write(target / "descriptor.json", descriptor)
    validate_freeze(target, descriptor, current=True)
    return descriptor


def validate_freeze(folder, descriptor, *, current):
    require(
        isinstance(descriptor, dict)
        and set(descriptor)
        == {"schema", "task", "boundary", "reader", "original_sha256", "trusted_sha256"}
        and descriptor["schema"] == "opent1d.service-freeze/1"
        and descriptor["task"] == TASK
        and read(folder / "descriptor.json") == descriptor,
        "Unsupported sampling service freeze",
    )
    plan, package, raw = native.load_plan(folder / "input", check_runtime=current)
    require(descriptor["boundary"] == boundary(plan, package), "Sampling boundary differs")
    require(
        hashes(folder / "original") == descriptor["original_sha256"], "Sampling originals differ"
    )
    original = folder / "original"
    require(
        {path.name for path in original.iterdir()} == FILES | {"development"}
        and all((original / name).read_bytes() == value for name, value in raw.items())
        and hashes(original / "development") == hashes(folder / "input/development"),
        "Sampling effective inputs or development evidence differ",
    )
    identity, expected = trusted_sources(plan)
    require(descriptor["reader"] == identity, "Unsupported trusted sampling reader")
    require(descriptor["trusted_sha256"] == expected, "Sampling source/ancestry/runtime differs")
    require(hashes(folder / "trusted") == expected, "Sampling trusted snapshots differ")


def child_result(archive, plan_folder, expected_raw, settings):
    from .routes import validate_draw_ledger

    load_sealed(archive)
    plan, package, raw = paired.load_plan(plan_folder)
    require(
        raw["package.json"] == expected_raw["package.json"]
        and raw["observations.csv"] == expected_raw["observations.csv"]
        and plan["settings"] == settings,
        "Sampling child inputs or settings differ",
    )
    if (archive / "frozen").exists():
        copied, _, _ = paired.load_plan(archive / "frozen")
        require(copied == plan, "Sampling child execution freeze differs")
    report, execution = read(archive / "report.json"), read(archive / "execution.json")
    require(report["plan"] == plan, "Sampling child report plan differs")
    if execution.get("status") == "completed":
        attempts = decode(read_regular(archive / "attempts.json", 128 * 1024 * 1024, "draw ledger"))
        require(
            attempts.get("schema") == report.get("schema")
            and set(attempts["people"]) == {p["id"] for p in package["participants"]},
            "Sampling child draw roster differs",
        )
        validate_draw_ledger(attempts, plan, package)
        summary = report_from_attempts(plan, attempts)
        summary["execution_status"] = "completed"
        require(summary == report, "Sampling child draw ledger differs from report")
    else:
        require(
            read(archive / "admission.json") == {"plan": plan, "package": package},
            "Sampling child failed admission differs",
        )
    _, _, slots = paired_outcome(
        "mmtt-sensitivity",
        report,
        execution,
        raw,
        paired_boundary("mmtt-sensitivity", raw)["binding"],
    )
    return report, slots


def native_result(archive, descriptor, service_plan):
    load_sealed(archive)
    saved_plan, package, raw = native.load_plan(archive / "frozen")
    expected_plan, _, _ = native.load_plan(service_plan / "input")
    require(saved_plan == expected_plan, "Sampling archive belongs to another frozen study")
    report = decode(
        read_regular(archive / "report.json", runner.MAX_REPORT, "native sampling report")
    )
    execution, journal = (read(archive / name) for name in ("execution.json", "schedules.json"))
    status = execution.get("status")
    require(
        execution.get("schema") == runner.EXECUTION
        and status in {"completed", "failed", "interrupted"}
        and execution.get("runtime") == saved_plan["runtime"]
        and execution.get("implementation_sha256") == saved_plan["implementation_sha256"],
        "Sampling native execution differs",
    )
    schedules = runner.schedule_map(saved_plan)
    require(set(journal) == set(schedules), "Sampling schedule roster differs")
    if (archive / "studies").exists():
        require(
            {p.name for p in (archive / "studies").iterdir()} <= set(schedules),
            "Unexpected sampling child study",
        )
    records, slots, reports = runner.initial_records(saved_plan), {}, ["report.json", "report.md"]
    for name, times in schedules.items():
        saved = journal[name]
        require(
            set(saved) == {"times_min", "status", "inventory", "error", "error_type"}
            and saved["times_min"] == times
            and saved["status"]
            in {
                "not_attempted",
                "mask_failed",
                "plan_failed",
                "attempt_status_unavailable",
                "completed",
                "failed",
                "interrupted",
            },
            "Unsupported sampling journal",
        )
        records[name].update(saved)
        child_slots = {}
        try:
            masked, mask_inventory = runner.project(raw, package, saved_plan, times)
        except (ValueError, OSError) as error:
            require(
                saved["status"] == "mask_failed"
                and saved["error"] == str(error)
                and saved["error_type"] == type(error).__name__,
                "Sampling masking failure differs",
            )
        else:
            require(
                saved["inventory"] is None or saved["inventory"] == mask_inventory,
                "Sampling mask inventory differs",
            )
            child = archive / "studies" / name
            if (child / "manifest.json").exists():
                require(
                    saved["inventory"] == mask_inventory
                    and saved["status"] in {"completed", "failed", "interrupted"},
                    "Sampling child lacks matching native status/inventory",
                )
                child_report, child_slots = child_result(
                    child,
                    archive / "plans" / name,
                    {"package.json": raw["package.json"], "observations.csv": masked},
                    {**saved_plan["settings"], "required_times_min": list(times)},
                )
                require(child_report["execution_status"] == saved["status"], "Child status differs")
                records[name]["report"] = child_report
                reports.extend(f"studies/{name}/{file}" for file in ("report.json", "report.md"))
            else:
                require(
                    saved["status"] not in {"completed", "failed", "interrupted", "mask_failed"}
                    and (status != "completed" or saved["status"] == "plan_failed"),
                    "Sampling native child report is missing",
                )
        for person in package["participants"]:
            for variant in saved_plan["settings"]["variants"]:
                key = f"{person['id']}/{variant['id']}"
                slots[f"{name}/{key}"] = child_slots.get(
                    key,
                    "failed"
                    if saved["status"] in {"mask_failed", "plan_failed"}
                    else "unavailable",
                )
    rebuilt = reporting.build(saved_plan, package, records, status)
    rebuilt["execution"] = execution
    require(
        report == rebuilt
        and (archive / "report.md").read_bytes() == reporting.render(rebuilt)
        and set(slots) == set(descriptor["boundary"]["planned_slots"]),
        "Sampling parent report or planned slots differ",
    )
    return {
        "payload": "native",
        "execution_status": status,
        "completeness": "complete" if report["coverage"]["complete_cohort"] else "incomplete",
        "slot_statuses": slots,
        "reconstruction": "unchecked",
        "scientific_evidence": "synthetic-only",
        "report_sha256": {
            name: digest(read_regular(archive / name, 128 * 1024 * 1024, "sampling report"))
            for name in reports
        },
    }
