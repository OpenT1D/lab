"""Explicit, process-local successor bindings for unchanged engines and assessment.

This context is for a dedicated coordinator, reader or worker process. It is not a
thread-safe in-process service API. Every binding is restored even after failure.
"""

from contextlib import contextmanager

from experiments.m4.causal_secretion import common as causal
from experiments.m4.initial_load import analysis, common, report, run

from . import common as secure
from . import context, locations
from .process import Control, supervise

INHERITED_FREEZE = run.freeze


def freeze(*args, **kwargs):
    output, plan, reference = INHERITED_FREEZE(*args, **kwargs)
    plan["execution_locations"] = locations.capture()
    context.snapshot(output / "runtime-context.json")
    secure.dump(output / "plan.json", plan)
    return output, plan, reference


def worker_args(output, kind, label, source=None):
    role = "observer" if kind == "observer" else "native"
    arguments = [str(output), "--kind", kind, "--label", label]
    if source is not None:
        arguments += ["--source", source]
    return context.command(role, "worker", arguments)


def supervise_stage(args, log_path, timeout, control):
    # Bind the inherited coordinator's baseline stage to the explicit successor.
    baseline = "experiments.m4.feedback.run" in args
    if baseline:
        args[:] = context.command(
            "coordinator",
            "reference",
            [
                "--output",
                str(log_path.parent.parent / "historical"),
                "--timeout-seconds",
                str(int(timeout)),
            ],
        )
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
            "provenance": context.provenance,
            "protocol": secure.protocol,
            "source_paths": secure.source_paths,
            "verify_reference": verify,
        },
        run: {
            "freeze": freeze,
            "Control": Control,
            "provenance": context.provenance,
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
