"""Fixed passive preparation or complete runtime audit; never scientific dispatch."""

import argparse
from pathlib import Path
from types import SimpleNamespace

from experiments.desktop.admission import (
    ARGUMENTS,
    ROOT,
    _manifest_identity,
    _read_json,
    _write_json,
)
from experiments.workflows.checks import prepare_check, probe_runtime, runtime_requirements
from experiments.workflows.registry import TASKS


def execute(request):
    if not isinstance(request, dict) or set(request) != {"identity", "payload"}:
        raise ValueError("Invalid admission request")
    identity, payload = request["identity"], request["payload"]
    if not isinstance(identity, dict) or set(identity) != {
        "task",
        "operation",
        "mode",
        "project",
        "source_root",
        "manifest",
        "sequence",
    }:
        raise ValueError("Invalid admission identity")
    if identity["source_root"] != str(ROOT) or identity["manifest"] != _manifest_identity(ROOT):
        raise ValueError("Installed admission source differs")
    task = TASKS[identity["task"]]
    if identity["operation"] not in {"check", "run", "reconstruct"}:
        raise ValueError("Unsupported admission operation")
    reconstruction = identity["operation"] == "reconstruct"
    if identity["mode"] == "prepare":
        if (
            identity["project"] is not None
            or not isinstance(payload, dict)
            or not set(payload) <= ARGUMENTS
        ):
            raise ValueError("Invalid passive preparation")
        details, issues = prepare_check(
            task, SimpleNamespace(**payload), reconstruction=reconstruction
        )
        result = {"metadata": details, "observation_path_issues": issues}
    elif identity["mode"] == "audit":
        if not isinstance(payload, dict) or set(payload) != {"metadata"}:
            raise ValueError("Invalid runtime audit")
        requirements = runtime_requirements(
            task, payload["metadata"], reconstruction=reconstruction
        )
        project = identity["project"]
        if project not in requirements:
            raise ValueError("Runtime is outside the task roster")
        result = probe_runtime(project, requirements[project])
    else:
        raise ValueError("Unsupported admission phase")
    if identity["manifest"] != _manifest_identity(ROOT):
        raise ValueError("Installed manifest changed during admission")
    return {"identity": identity, "result": result}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args(argv)
    request = _read_json(args.request)
    try:
        response = execute(request)
    except (OSError, ValueError, KeyError, TypeError, OverflowError) as error:
        # Preserve a bounded failure class, without dumping configuration or
        # observation data. This receipt never authorizes native execution.
        _write_json(
            args.result, {"identity": request.get("identity"), "error_type": type(error).__name__}
        )
        return 2
    _write_json(args.result, response)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
