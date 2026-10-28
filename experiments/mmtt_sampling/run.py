"""Run isolated native plans, preserve all outcomes and reconstruct through OT-054."""

import shutil
import signal
import tempfile
from copy import deepcopy
from pathlib import Path

from experiments.catalogue.storage import decode, dump, encoded, fresh, load_sealed, seal
from experiments.m3.researcher.intake import read_regular
from experiments.observation_analysis.observations import fields
from experiments.observation_analysis.plan import freeze as freeze_native
from experiments.observation_analysis.plan import load_plan as load_native_plan
from experiments.observation_analysis.run import reconstruct as reconstruct_native
from experiments.observation_analysis.run import run as run_native

from .masking import mask_csv
from .plan import load_plan, runtime_identity, source_identity
from .report import build, render

EXECUTION = "opent1d.mmtt-sampling-execution/1"
MAX_REPORT = 512 * 1024 * 1024


def schedule_map(plan):
    design = plan["design"]
    return {"full": design["full_times_minutes"], **design["subsets"]}


def project(raw, package, plan, times):
    masked, inventory = mask_csv(raw["observations.csv"], package, times)
    if any(
        time not in plan["design"]["full_times_minutes"]
        for visit in inventory
        for time in visit["actual_times_minutes"]
    ):
        raise ValueError("Unexpected actual time outside full schedule; freeze a matching design")
    return masked, inventory


def initial_records(plan):
    return {
        name: {
            "times_min": times,
            "status": "not_attempted",
            "report": None,
            "inventory": None,
            "error": None,
            "error_type": None,
        }
        for name, times in schedule_map(plan).items()
    }


def run(config, output):
    config = Path(config).absolute()
    plan, package, _ = load_plan(config, check_runtime=True)
    output = fresh(output, (config,))
    execution = {
        "schema": EXECUTION,
        "status": "started",
        "phase": "snapshot",
        "interruption_signal": None,
        "implementation_sha256": source_identity(),
        "runtime": runtime_identity(),
        "error_type": None,
        "error": None,
        "schedules": {},
    }
    dump(output / "execution.json", execution)
    records = initial_records(plan)
    previous = {}

    def stop(signum, _frame):
        execution["interruption_signal"] = signum
        raise KeyboardInterrupt

    try:
        numbers = (signal.SIGINT, signal.SIGTERM)
        if hasattr(signal, "SIGHUP"):
            numbers += (signal.SIGHUP,)
        for number in numbers:
            previous[number] = signal.signal(number, stop)
        shutil.copytree(config, output / "frozen", symlinks=True)
        copied, package, raw = load_plan(output / "frozen", check_runtime=True)
        if copied != plan:
            raise ValueError("Sampling plan changed during snapshot")
        for name, times in schedule_map(plan).items():
            record = records[name]
            execution["phase"] = name
            execution["schedules"][name] = "masking"
            dump(output / "execution.json", execution)
            try:
                masked, inventory = project(raw, package, plan, times)
            except (ValueError, OSError) as error:
                record.update(
                    status="mask_failed", error=str(error), error_type=type(error).__name__
                )
                execution["schedules"][name] = "mask_failed"
                continue
            record["inventory"] = inventory
            source = output / "inputs" / name
            source.mkdir(parents=True)
            (source / "package.json").write_bytes(raw["package.json"])
            (source / "observations.csv").write_bytes(masked)
            settings = {**deepcopy(plan["settings"]), "required_times_min": list(times)}
            dump(source / "settings.json", settings)
            try:
                if source_identity() != plan["implementation_sha256"]:
                    raise ValueError("Trusted implementation changed during sampling execution")
                freeze_native(
                    source / "package.json",
                    source / "observations.csv",
                    source / "settings.json",
                    output / "plans" / name,
                )
            except (ValueError, OSError, TypeError, KeyError, OverflowError) as error:
                record.update(
                    status="plan_failed", error=str(error), error_type=type(error).__name__
                )
                execution["schedules"][name] = "plan_failed"
                continue
            record["status"] = "running"
            execution["schedules"][name] = "analysis"
            dump(output / "execution.json", execution)
            child = run_native(output / "plans" / name, output / "studies" / name)
            record.update(status=child["execution_status"], report=child)
            execution["schedules"][name] = record["status"]
            dump(output / "execution.json", execution)
            if child["execution_status"] == "interrupted":
                child_execution = decode(
                    (output / "studies" / name / "execution.json").read_bytes()
                )
                execution.update(
                    status="interrupted", interruption_signal=child_execution["interruption_signal"]
                )
                break
        else:
            execution["status"] = "completed"
        if source_identity() != plan["implementation_sha256"]:
            raise ValueError("Trusted implementation changed during sampling execution")
    except (KeyboardInterrupt, OSError, ValueError, TypeError, KeyError, OverflowError) as error:
        execution.update(
            status="interrupted" if isinstance(error, KeyboardInterrupt) else "failed",
            error_type=type(error).__name__,
            error="Interrupted" if isinstance(error, KeyboardInterrupt) else str(error),
        )
        for record in records.values():
            if record["status"] == "running":
                record.update(
                    status="attempt_status_unavailable",
                    error=type(error).__name__,
                    error_type=type(error).__name__,
                )
    finally:
        for number, handler in previous.items():
            signal.signal(number, handler)
    execution["last_phase"] = execution["phase"]
    execution["phase"] = "finished"
    report = build(plan, package, records, execution["status"])
    report["execution"] = execution
    dump(output / "execution.json", execution)
    # The journal contains statuses only; native reports remain authoritative child bytes.
    dump(
        output / "schedules.json",
        {
            name: {key: value for key, value in record.items() if key != "report"}
            for name, record in records.items()
        },
    )
    dump(output / "report.json", report)
    (output / "report.md").write_bytes(render(report))
    seal(output)
    return report


def reconstruct(archive, output, *, allow_failed=False):
    archive = load_sealed(archive)
    plan, package, raw = load_plan(archive / "frozen")
    execution = decode(read_regular(archive / "execution.json", 2 * 1024 * 1024, "execution"))
    if (
        execution.get("schema") != EXECUTION
        or execution.get("implementation_sha256") != plan["implementation_sha256"]
        or execution.get("status") not in ("completed", "failed", "interrupted")
    ):
        raise ValueError("Unsupported sampling execution identity or state")
    journal = decode(read_regular(archive / "schedules.json", 8 * 1024 * 1024, "schedules"))
    if set(journal) != set(schedule_map(plan)):
        raise ValueError("Planned sampling schedules were dropped or added")
    records = initial_records(plan)
    with tempfile.TemporaryDirectory(prefix="opent1d-sampling-reader-") as temporary:
        for name, times in schedule_map(plan).items():
            saved = journal[name]
            fields(
                saved,
                ("times_min", "status", "inventory", "error", "error_type"),
                "sampling schedule journal",
            )
            if saved["status"] not in {
                "not_attempted",
                "mask_failed",
                "plan_failed",
                "attempt_status_unavailable",
                "completed",
                "failed",
                "interrupted",
            }:
                raise ValueError("Unsupported terminal sampling schedule state")
            if saved["times_min"] != times:
                raise ValueError("Saved schedule differs from the frozen design")
            record = records[name]
            record.update(saved)
            try:
                masked, inventory = project(raw, package, plan, times)
            except (ValueError, OSError) as error:
                if (
                    saved["status"] != "mask_failed"
                    or saved["error"] != str(error)
                    or saved["error_type"] != type(error).__name__
                ):
                    raise ValueError("Saved masking failure differs") from error
                continue
            child = archive / "studies" / name
            if saved["inventory"] is not None and saved["inventory"] != inventory:
                raise ValueError("Saved raw-mask inventory differs")
            if (child / "manifest.json").exists():
                if saved["inventory"] != inventory:
                    raise ValueError("Native result lacks its exact raw-mask inventory")
                if saved["status"] not in ("completed", "failed", "interrupted"):
                    raise ValueError("Unattempted schedule has an unexpected native result")
                child_plan, _, child_raw = load_native_plan(archive / "plans" / name)
                if (child / "frozen").exists():
                    copied, _, _ = load_native_plan(child / "frozen")
                    if copied != child_plan:
                        raise ValueError("Native execution snapshot differs from its intended plan")
                expected_settings = {**plan["settings"], "required_times_min": list(times)}
                if (
                    child_raw["observations.csv"] != masked
                    or child_raw["package.json"] != raw["package.json"]
                    or child_plan["settings"] != expected_settings
                ):
                    raise ValueError("Native child observations or fixed assumptions differ")
                record["report"] = reconstruct_native(
                    child, Path(temporary) / name, allow_failed=True
                )
                if record["report"]["execution_status"] != saved["status"]:
                    raise ValueError("Saved native schedule execution state differs")
            elif saved["status"] in ("completed", "failed", "interrupted"):
                raise ValueError("Recorded native result is missing its sealed child archive")
            elif saved["status"] == "mask_failed":
                raise ValueError("Recorded masking failure is not reproducible")
            elif execution["status"] == "completed" and saved["status"] not in ("plan_failed",):
                raise ValueError("Completed sampling execution has an unattempted schedule")
    report = build(plan, package, records, execution["status"])
    report["execution"] = execution
    if encoded(report) != read_regular(
        archive / "report.json", MAX_REPORT, "saved comparison"
    ) or render(report) != read_regular(archive / "report.md", MAX_REPORT, "saved Markdown"):
        raise ValueError("Saved sampling report differs from native reconstruction")
    if not report["coverage"]["complete_cohort"] and not allow_failed:
        raise ValueError("Use --allow-failed to verify incomplete or interrupted sampling")
    target = fresh(output, (archive,))
    dump(target / "report.json", report)
    (target / "report.md").write_bytes(render(report))
    # Relative native-report links remain usable in the reconstructed report.
    for name in schedule_map(plan):
        child = archive / "studies" / name
        if records[name]["report"] is not None:
            destination = target / "studies" / name
            destination.mkdir(parents=True)
            for filename in ("report.md", "report.json"):
                shutil.copyfile(child / filename, destination / filename)
    seal(target)
    return report
