"""Explicit, process-local successor bindings for unchanged engines and assessment.

This context is for a dedicated coordinator, reader or worker process. It is not a
thread-safe in-process service API. Every binding is restored even after failure.
"""

from contextlib import contextmanager

from experiments.desktop.runtime import interpreter
from experiments.m4.causal_secretion import common as causal
from experiments.m4.initial_load import analysis, common, report, run
from experiments.m4.initial_load.process import supervise

from . import common as secure
from . import locations

INHERITED_FREEZE = run.freeze


def freeze(*args, **kwargs):
    output, plan, reference = INHERITED_FREEZE(*args, **kwargs)
    plan["execution_locations"] = locations.capture()
    secure.dump(output / "plan.json", plan)
    return output, plan, reference


def worker_args(output, kind, label, source=None):
    project = secure.OBSERVER_PROJECT if kind == "observer" else secure.NATIVE_PROJECT
    args = [
        str(interpreter(project)),
        "-B",
        "-E",
        "-s",
        "-m",
        "experiments.m4.secure_study.worker",
        str(output),
        "--kind",
        kind,
        "--label",
        label,
    ]
    if source is not None:
        args += ["--source", source]
    return args


def supervise_stage(args, log_path, timeout, control):
    # Bind the inherited coordinator's baseline stage to the explicit successor.
    baseline = "experiments.m4.feedback.run" in args
    if baseline:
        args[args.index("experiments.m4.feedback.run")] = "experiments.m4.secure_study.reference"
        args += ["--timeout-seconds", str(int(timeout))]
        state_path = log_path.parent.parent / "state.json"
        if state_path.is_file():
            state = secure.read(state_path)
            attempt = state["reference"]["attempts"][-1]
            secure.require(
                attempt["stage"] == "historical" and attempt["status"] == "started",
                "Reference dispatch ledger changed before launch",
            )
            attempt["argv"] = args
            secure.dump(state_path, state)
    return supervise(args, log_path, timeout, control, grace_seconds=20 if baseline else 10)


@contextmanager
def activate():
    from .reference import verify
    from .report import assessment, expected_stage, validate_frozen

    bindings = {
        common: {
            "VERSION": secure.VERSION,
            "protocol": secure.protocol,
            "source_paths": secure.source_paths,
            "verify_reference": verify,
        },
        run: {
            "freeze": freeze,
            "VERSION": secure.VERSION,
            "intake": secure.intake,
            "protocol": secure.protocol,
            "source_snapshots": secure.source_snapshots,
            "verify_reference": verify,
            "worker_args": worker_args,
            "supervise": supervise_stage,
        },
        report: {
            "VERSION": secure.VERSION,
            "REPORT_SCHEMA": secure.REPORT_SCHEMA,
            "source_paths": secure.source_paths,
            "validate_config": secure.validate_config,
            "validate_frozen": validate_frozen,
            "expected_stage": expected_stage,
            "assessment": assessment,
        },
        analysis: {"verify_reference": verify},
        causal: {"reference": verify},
    }
    saved = [
        (module, key, getattr(module, key)) for module, values in bindings.items() for key in values
    ]
    try:
        for module, values in bindings.items():
            for key, value in values.items():
                setattr(module, key, value)
        yield
    finally:
        for module, key, value in reversed(saved):
            setattr(module, key, value)
