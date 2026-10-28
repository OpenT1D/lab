"""Separate packaged integrity work from the GUI operation's original allowance."""

from experiments.desktop.admission import admission_allowance, coordinator_budget, read_phase


def command(
    argv,
    task,
    folder,
    prepare_seconds,
    operation_seconds=None,
    *,
    reconstruction=False,
    phase_name="admission-phase.json",
    source_root=None,
):
    budget = coordinator_budget(
        task,
        prepare_seconds,
        operation_seconds,
        reconstruction=reconstruction,
        source_root=source_root,
    )
    original = prepare_seconds if operation_seconds is None else operation_seconds
    if budget == original:
        return argv, original
    flags = [
        "--admission-prepare-seconds",
        str(prepare_seconds),
        "--phase-state",
        str(folder / phase_name),
    ]
    if operation_seconds is not None:
        flags.extend(["--operation-seconds", str(operation_seconds)])
    return argv + flags, budget


def m3_extra(task, operation, native_seconds=None, *, source_root=None):
    """Retain the outer worker's existing slack around each separate CLI owner."""
    if operation == "m3_fixture":
        return 0
    options = {"source_root": source_root}
    check = coordinator_budget(task, 120, **options) - 120
    reader = coordinator_budget(task, 120, 120, reconstruction=True, **options) - 120
    if operation == "m3_check":
        return check
    if operation == "m3_reconstruct":
        return reader
    if operation == "m3_run" and native_seconds is not None:
        return (
            check
            + coordinator_budget(task, 120, native_seconds, **options)
            - native_seconds
            + reader
        )
    raise ValueError("Unsupported M3 phase operation")


def public_phase(job, folder):
    """Optional bounded display data; never readiness or deadline authority."""
    if job.get("state") != "running":
        return None
    operation = job.get("operation")
    if operation in {"check", "run", "reconstruct"}:
        candidates = [("admission-phase.json", operation)]
    elif operation == "m3_check":
        candidates = [("m3-check-phase.json", "check")]
    elif operation == "m3_reconstruct":
        candidates = [("m3-reconstruct-phase.json", "reconstruct")]
    elif operation == "m3_run":
        candidates = [
            ("m3-reconstruct-phase.json", "reconstruct"),
            ("m3-run-phase.json", "run"),
            ("m3-check-phase.json", "check"),
        ]
    else:
        return None
    for name, expected in candidates:
        try:
            phase = read_phase(folder / name)
        except (OSError, ValueError, TypeError, KeyError):
            continue
        if phase["task"] == job.get("task") and phase["operation"] == expected:
            return phase
    return None


def cleanup_seconds(argv, task, operation, original, *, source_root=None):
    """Allow the 30-second child cleanup and the intermediate owner's receipt."""
    if "--admission-prepare-seconds" in argv:
        return 60
    if operation in {"m3_check", "m3_run", "m3_reconstruct"} and admission_allowance(
        task,
        reconstruction=operation == "m3_reconstruct",
        source_root=source_root,
    ):
        return 60
    return original
