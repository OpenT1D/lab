"""Fresh bounded local execution and deterministic saved-analysis verification."""

import shutil
import signal
from pathlib import Path

from experiments.catalogue.storage import decode, dump, encoded, fresh, load_sealed, seal
from experiments.m3.researcher.intake import read_regular

from .analysis import SCHEMA, evaluate, report_from_attempts
from .observations import validate_package
from .plan import load_plan, runtime_identity, source_identity, validate_settings
from .report import render

EXECUTION = "opent1d.observation-analysis-execution/1"
MAX_ATTEMPTS = 128 * 1024 * 1024


def failure_report(plan, package, status):
    """An interrupted calculation cannot invent attempt completion or participants."""
    report = {
        "schema": SCHEMA,
        "task": "mmtt-sensitivity",
        "kind": "synthetic",
        "human_evaluation": False,
        "plan": plan,
        "import_errors": [],
        "execution_status": status,
        "fatal_error": "Execution did not produce complete saved attempts",
        "people": {},
        "coverage": {
            "planned_people": None,
            "planned_visits": None,
            "planned_variant_pairs": None,
            "completed_variant_pairs": 0,
            "complete_people": 0,
            "complete_cohort": False,
        },
    }
    if package is not None:
        count = len(package["participants"])
        report["coverage"].update(
            planned_people=count,
            planned_visits=2 * count,
            planned_variant_pairs=count * len(plan["settings"]["variants"]),
        )
        report["unavailable_participants"] = [
            {
                "id": person["id"],
                "allocation": person["allocation"],
                "status": "attempt_status_unavailable",
            }
            for person in package["participants"]
        ]
    return report


def run(config, output):
    config = Path(config).absolute()
    output = fresh(output, (config,))
    execution = {
        "schema": EXECUTION,
        "status": "started",
        "interruption_signal": None,
        "implementation_sha256": source_identity(),
        "runtime": runtime_identity(),
        "error_type": None,
        "phase": "preflight",
    }
    dump(output / "execution.json", execution)
    plan = package = attempts = None
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
        plan, package, _ = load_plan(config, check_runtime=True)
        dump(output / "admission.json", {"plan": plan, "package": package})
        execution["phase"] = "snapshot"
        dump(output / "execution.json", execution)
        shutil.copytree(config, output / "frozen", symlinks=True)
        copied, package, raw = load_plan(output / "frozen", check_runtime=True)
        if copied != plan:
            raise ValueError("Frozen plan changed during snapshot")
        execution["phase"] = "analysis"
        dump(output / "execution.json", execution)
        attempts = evaluate(plan["settings"], package, raw["observations.csv"])
        dump(output / "attempts.json", attempts)
        report = report_from_attempts(plan, attempts)
        execution["status"] = "completed"
        execution["phase"] = "report"
        report["execution_status"] = "completed"
    except (
        KeyboardInterrupt,
        OSError,
        ValueError,
        TypeError,
        KeyError,
        OverflowError,
        RecursionError,
    ) as error:
        execution.update(
            status="interrupted" if isinstance(error, KeyboardInterrupt) else "failed",
            error_type=type(error).__name__,
        )
        report = failure_report(plan, package, execution["status"])
    finally:
        for number, handler in previous.items():
            signal.signal(number, handler)
    dump(output / "execution.json", execution)
    dump(output / "report.json", report)
    (output / "report.md").write_bytes(render(report))
    seal(output)
    return report


def reconstruct(archive, output, *, allow_failed=False):
    """Replay the same frozen variates and exact algebra, never a new fitted model.

    Only installed trusted code runs. The original archive and its source
    snapshots are read-only. No new seed, user method, R runtime or engine is used.
    """
    archive = load_sealed(archive)
    execution = decode(read_regular(archive / "execution.json", 2 * 1024 * 1024, "execution"))
    if (
        execution.get("schema") != EXECUTION
        or execution.get("implementation_sha256") != source_identity()
        or execution.get("status") not in ("completed", "failed", "interrupted")
    ):
        raise ValueError("Unsupported execution identity or state")
    if execution["status"] == "completed":
        plan, package, raw = load_plan(archive / "frozen")
        attempts = decode(read_regular(archive / "attempts.json", MAX_ATTEMPTS, "attempts"))
        expected = evaluate(plan["settings"], package, raw["observations.csv"])
        if attempts != expected:
            raise ValueError("Saved analysis attempts differ from the frozen input/plan arithmetic")
        report = report_from_attempts(plan, attempts)
        report["execution_status"] = "completed"
    else:
        if not allow_failed:
            raise ValueError("Use --allow-failed to verify a failed/interrupted archive")
        plan = package = None
        if (archive / "admission.json").exists():
            admitted = decode(
                read_regular(archive / "admission.json", 4 * 1024 * 1024, "admission")
            )
            plan, package = admitted["plan"], validate_package(admitted["package"])
            validate_settings(plan["settings"], package)
            if plan["implementation_sha256"] != source_identity():
                raise ValueError("Failed admission source identity differs")
        report = failure_report(plan, package, execution["status"])
    if encoded(report) != read_regular(
        archive / "report.json", MAX_ATTEMPTS, "saved report"
    ) or render(report) != read_regular(archive / "report.md", MAX_ATTEMPTS, "saved report"):
        raise ValueError("Saved report differs from reconstructed analysis")
    if not report["coverage"]["complete_cohort"] and not allow_failed:
        raise ValueError("Use --allow-failed for an incomplete analysis")
    target = fresh(output, (archive,))
    dump(target / "report.json", report)
    (target / "report.md").write_bytes(render(report))
    seal(target)
    return report
