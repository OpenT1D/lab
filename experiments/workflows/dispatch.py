"""Explicit dispatch, signal forwarding and recorded native-report discovery."""

import json
import signal
import subprocess
from pathlib import Path

from experiments.platform_process import close_tree, handled_signals, signal_tree, spawn

from .checks import check, interpreter, safe_environment, value
from .registry import ROOT, VERSION


def child_environment():
    return safe_environment()


def command_for(task, args, *, operation="run"):
    """Only the explicit registry decides modules and environments."""
    reconstruction = operation == "reconstruct"
    project = "." if reconstruction else task.run_project
    argv = [str(interpreter(project)), "-B", "-E", "-s"]
    if reconstruction:
        argv.append("-S")
    argv.extend(["-m", task.reconstruct_module if reconstruction else task.run_module])
    if reconstruction:
        archive = str(Path(args.archive).absolute())
        if task.id in ("p1-controller", "m3-forecast", "m3-compare"):
            argv.extend(
                [
                    "report" if task.id == "m3-forecast" else "reconstruct",
                    "--study",
                    archive,
                    "--output",
                    str(Path(args.output).absolute()),
                ]
            )
        elif task.id in (
            "m4-compare",
            "m4-study",
            "m4-study-secure",
            "mmtt-sensitivity",
            "mmtt-sampling",
        ):
            argv.extend(
                ["reconstruct", "--archive", archive, "--output", str(Path(args.output).absolute())]
            )
            if args.allow_failed:
                argv.append("--allow-failed")
        elif task.id == "m4-secretion":
            argv.extend([archive, "--output", str(Path(args.output).absolute())])
            if args.allow_failed:
                argv.append("--allow-failed")
        elif task.id == "m5-prognosis":
            argv.extend(["reconstruct", archive])
        return argv
    output = str(Path(args.output).absolute())
    if task.id == "p1-controller":
        argv.extend(
            [
                "run",
                "--source",
                str(Path(args.source).absolute()),
                "--output",
                output,
                "--profile",
                args.profile,
                "--seed",
                str(args.seed),
            ]
        )
    elif task.id == "m3-forecast":
        argv.extend(
            [
                "run",
                "--config",
                str(Path(args.config).absolute()),
                "--output",
                output,
                "--timeout",
                str(args.timeout),
            ]
        )
    elif task.id in ("m3-compare", "mmtt-sensitivity", "mmtt-sampling"):
        argv.extend(["run", "--config", str(Path(args.config).absolute()), "--output", output])
    elif task.id in ("m4-compare", "m4-study", "m4-study-secure"):
        argv.extend(["run", "--config", str(Path(args.config).absolute()), "--output", output])
        if args.reference is not None:
            argv.extend(["--reference", str(Path(args.reference).absolute())])
    elif task.id == "m4-secretion":
        argv.extend(["--config", str(Path(args.config).absolute()), "--output", output])
        if args.reference is not None:
            argv.extend(["--reference", str(Path(args.reference).absolute())])
    elif task.id == "m5-prognosis":
        argv.extend(
            [
                "run",
                str(Path(args.bundle).absolute()),
                output,
                "--timeout-seconds",
                str(args.timeout_seconds),
            ]
        )
    return argv


def run_process(argv, env):
    """Forward signals to the native supervisor and wait for its archive sealing."""
    child = None
    received = None
    previous = {}

    def forward(signum, _frame):
        nonlocal received
        received = signum
        if child is not None and child.poll() is None:
            try:
                # Legacy M3/P1/M4 supervisors handle TERM, while HUP defaults to
                # immediate death and can strand their separately sessioned workers.
                signal_tree(
                    child, signal.SIGTERM if signum == getattr(signal, "SIGHUP", None) else signum
                )
            except ProcessLookupError:
                pass

    try:
        for signum in handled_signals():
            previous[signum] = signal.signal(signum, forward)
        if received is not None:
            return -received, received
        child = spawn(
            argv,
            cwd=ROOT,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if received is not None:
            forward(received, None)
        return child.wait(), received
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)
        if child is not None and child.poll() is None:
            # A non-signal supervisor exception still asks the native owner to clean up.
            signal_tree(child, signal.SIGTERM)
            child.wait()
        if child is not None:
            close_tree(child)


def report_status(task, archive, *, reconstruction_output=None):
    """Read recorded status only; the native reconstruction remains authoritative."""
    directory = Path(reconstruction_output if reconstruction_output is not None else archive)
    if task.id == "p1-controller" and reconstruction_output is None:
        directory /= "report"
    report = directory / "report.json"
    markdown = directory / "report.md"
    result = {"report": str(markdown.absolute()), "report_completeness": "unavailable"}
    try:
        if report.is_symlink() or markdown.is_symlink() or not markdown.is_file():
            return result
        data = json.loads(report.read_bytes())
        if task.id == "p1-controller":
            status = "complete" if data["study_status"] == "completed" else "incomplete"
        elif task.id == "m3-forecast":
            status = "complete" if data["evaluation"]["complete_cohort"] else "incomplete"
        elif task.id == "m3-compare":
            status = "complete" if data["common"]["complete_cohort"] else "incomplete"
        elif task.id in ("mmtt-sensitivity", "mmtt-sampling"):
            status = "complete" if data["coverage"]["complete_cohort"] else "incomplete"
        elif task.id in ("m4-secretion", "m4-compare", "m4-study", "m4-study-secure"):
            status = "complete" if data["passed"] else "failed"
        else:
            status = data["comparison_status"]
            if status not in ("complete", "incomplete"):
                return result
        return dict(result, report_completeness=status)
    except (OSError, ValueError, KeyError, TypeError):
        return result


def execute(task, args, *, operation="run"):
    reconstruction = operation == "reconstruct"
    if value(args, "output") is not None:
        output = Path(args.output)
        if output.exists() or output.is_symlink():
            raise ValueError("Choose a new output directory")
    from experiments.desktop.admission import Admission, requested

    if requested(args, operation=operation):
        with Admission(task, args, operation=operation) as admission:
            readiness = admission.check()
            return _execute_checked(task, args, readiness, operation, admission.run)
    readiness = check(task, args, reconstruction=reconstruction)
    return _execute_checked(task, args, readiness, operation, run_process)


def _execute_checked(task, args, readiness, operation, run):
    # Private call inside the live admission owner; no persisted receipt or public
    # skip option can invoke native execution without its current readiness.
    reconstruction = operation == "reconstruct"
    if not readiness["runtimes_ready"]:
        return dict(
            readiness,
            operation=operation,
            child_exit_code=None,
            entry_error="Installed runtimes unavailable; use the listed setup commands",
            report_completeness="unavailable",
            report=None,
        )
    code, forwarded = run(command_for(task, args, operation=operation), child_environment())
    archive = args.archive if reconstruction else args.output
    reconstructed = value(args, "output") if reconstruction else None
    return {
        "schema": VERSION,
        "operation": operation,
        "task": task.id,
        "child_exit_code": code,
        "forwarded_signal": forwarded,
        "report_status_scope": "native_reader_verified"
        if reconstruction and code == 0
        else "recorded_native_report",
        "observation_path_issues": readiness["observation_path_issues"],
        **report_status(task, archive, reconstruction_output=reconstructed),
    }
