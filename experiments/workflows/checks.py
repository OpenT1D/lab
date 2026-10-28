"""Passive declarations and installed metadata; no candidate or observation execution."""

import json
import math
import os
import re
import shutil
import stat
import subprocess
from pathlib import Path

from experiments.desktop.runtime import (
    interpreter as runtime_interpreter,
)
from experiments.desktop.runtime import (
    packaged_manifest,
    packaged_runtime,
    verify_packaged_project,
)

from .registry import NATIVE_PROJECT, OBSERVER_PROJECT, ROOT, SECURE_NATIVE_PROJECT, VERSION

NATIVE_VERSIONS = {"simglucose": "0.2.11", "numpy": "1.26.4", "scipy": "1.13.1"}
OBSERVER_VERSIONS = {"numpy": "2.2.6", "scipy": "1.15.3"}


def value(args, name, default=None):
    return getattr(args, name, default)


def safe_environment():
    """Select checkout environments, without inherited uv/active-Python overrides."""
    env = {
        key: val
        for key, val in os.environ.items()
        if not key.startswith("UV_")
        and key not in ("VIRTUAL_ENV", "PYTHONHOME", "PYTHONPATH", "__PYVENV_LAUNCHER__")
    }
    env.update(
        UV_NO_SYNC="1",
        UV_PYTHON_DOWNLOADS="never",
        UV_OFFLINE="1",
        UV_NO_CONFIG="1",
        PYTHONNOUSERSITE="1",
    )
    return env


def validate_options(args):
    for name in ("timeout", "timeout_seconds"):
        budget = value(args, name)
        if budget is not None and (
            type(budget) not in (int, float)
            or not math.isfinite(budget)
            or budget <= 0
            or (name == "timeout_seconds" and budget > 60)
        ):
            raise ValueError("Worker timeout must be finite and positive; M5 maximum is 60 seconds")


def observation_path_issues(config):
    """Only stat planned observation paths; their content belongs to the runner."""
    issues = []
    for person in config["people"]:
        path = Path(person["input"]["file"])
        try:
            if (
                path.is_symlink()
                or path.parent.is_symlink()
                or not stat.S_ISREG(path.stat().st_mode)
            ):
                issues.append({"person": person["id"], "reason": "nonregular_input"})
        except OSError:
            issues.append({"person": person["id"], "reason": "unavailable_input"})
    return issues


def metadata(task, args):
    """Reuse the route's admission rules without importing supplied Python."""
    observation_issues = []
    if task.id == "p1-controller":
        from experiments.p1.__main__ import plan
        from experiments.p1_external.intake import declaration

        declared = declaration(value(args, "source"))
        plan(value(args, "profile", "adult#001"), value(args, "seed", 101))
        details = {"model_id": declared["name"], "dependencies": declared["dependencies"]}
    elif task.id == "m3-forecast":
        from experiments.m3.researcher.common import read, validate_config
        from experiments.m3.researcher.intake import load_declaration

        config, _ = read(value(args, "config"))
        validate_config(config)
        declared, _, _ = load_declaration(config["predictor"])
        observation_issues = observation_path_issues(config)
        details = {
            "model_id": declared["id"],
            "planned_people": len(config["people"]),
            "planned_origins": sum(len(person["origins_us"]) for person in config["people"]),
            "observation_bytes_verified": False,
        }
    elif task.id == "m3-compare":
        from experiments.m3.comparison.common import metadata as comparison_metadata

        config, bundles = comparison_metadata(value(args, "config"))
        observation_issues = observation_path_issues(config)
        details = {
            "candidate_order": [candidate["id"] for candidate in config["candidates"]],
            "planned_people": len(config["people"]),
            "planned_origins": {
                person["id"]: len(person["origins_us"]) for person in config["people"]
            },
            "timeout_seconds": config["timeout_seconds"],
            "candidate_source_sha256": {
                identity: bundle["declaration"]["source"]["sha256"]
                for identity, bundle in bundles.items()
            },
            "observation_bytes_verified": False,
            "candidate_executed": False,
        }
    elif task.id == "m4-secretion":
        from experiments.m4.researcher_workflow.common import intake

        config, _, declared = intake(value(args, "config"))
        details = {
            "model_id": declared["model_id"],
            "timeout_seconds": config["timeout_seconds"],
        }
        if value(args, "reference") is not None:
            from experiments.m4.causal_secretion.common import reference
            from experiments.m4.researcher_workflow.common import verify_reference_sources

            archive = Path(args.reference)
            if archive.is_symlink() or any(path.is_symlink() for path in archive.rglob("*")):
                raise ValueError("Reference cannot contain symlinks")
            reference(archive)
            verify_reference_sources(archive)
            details["reference_checked"] = True
    elif task.id in ("m4-compare", "m4-study", "m4-study-secure"):
        if task.id == "m4-study-secure":
            from experiments.m4.secure_study.common import intake
            from experiments.m4.secure_study.reference import verify as verify_reference
        elif task.id == "m4-study":
            from experiments.m4.initial_load.common import intake, verify_reference
        else:
            from experiments.m4.comparison.common import intake, verify_reference

        config, bundles = intake(value(args, "config"))
        details = {
            "source_order": [source["id"] for source in config["sources"]],
            "source_sha256": {
                identity: bundle["declared"]["source_sha256"]
                for identity, bundle in bundles.items()
            },
            "timeout_seconds": config["timeout_seconds"],
            "source_timeout_seconds": config["source_timeout_seconds"],
            "source_executed": False,
        }
        if task.id in ("m4-study", "m4-study-secure"):
            details["scenario_order"] = config["scenarios"]
        if value(args, "reference") is not None:
            verify_reference(args.reference)
            details["reference_checked"] = True
    elif task.id == "m5-prognosis":
        from experiments.m5.researcher_workflow.contract import (
            BUNDLE_FILES,
            declaration,
            decode,
            snapshot,
        )

        bundle = snapshot(value(args, "bundle"), BUNDLE_FILES)
        declared = declaration(
            decode(bundle["model.json"]), bundle["model.py"], bundle["state.json"]
        )
        details = {"model_id": declared["model_id"]}
    elif task.id in ("mmtt-sensitivity", "mmtt-sampling"):
        if task.id == "mmtt-sampling":
            from experiments.mmtt_sampling.plan import load_plan
        else:
            from experiments.observation_analysis.plan import load_plan

        plan, package, _ = load_plan(value(args, "config"), check_runtime=True)
        details = {
            "method": plan["method"],
            "planned_people": len(package["participants"]),
            "planned_variants": len(plan["settings"]["variants"]),
            "source_executed": False,
            "estimation_performed": False,
            "frozen_input_bytes_verified": True,
        }
    else:
        raise ValueError("Unsupported task")
    return details, observation_issues


def runtime_requirements(task, details=None, *, reconstruction=False):
    if reconstruction:
        return {".": {}}
    requirements = {".": {}}
    if task.id in ("p1-controller", "m4-secretion", "m4-compare", "m4-study"):
        requirements[NATIVE_PROJECT] = dict(NATIVE_VERSIONS)
    if task.id == "m4-study-secure":
        requirements[SECURE_NATIVE_PROJECT] = {
            **NATIVE_VERSIONS,
            "urllib3": "2.8.0",
            "setuptools": "84.0.0",
        }
    if task.id == "p1-controller":
        for package, version in (details or {}).get("dependencies", {}).items():
            existing = requirements[NATIVE_PROJECT].get(package)
            if existing is not None and existing != version:
                raise ValueError(f"Declared {package} conflicts with the locked native task")
            requirements[NATIVE_PROJECT][package] = version
    if task.id in ("m4-secretion", "m4-compare", "m4-study", "m4-study-secure"):
        requirements[OBSERVER_PROJECT] = dict(OBSERVER_VERSIONS)
    return requirements


def interpreter(project):
    return runtime_interpreter(project, source_root=ROOT)


def probe_runtime(project, packages):
    """Ask the installed interpreter for metadata, without importing distributions."""
    project_path = ROOT / project
    result = {
        "project": project,
        "python": str(interpreter(project)),
        "setup": "uv sync --locked" + (f" --project {project}" if project != "." else ""),
        "expected_python": "3.12",
        "expected_packages": packages,
        "ready": False,
    }
    bundled = packaged_runtime(project, source_root=ROOT)
    if bundled is not None:
        result["setup"] = "Verify bundled runtime; rerun this installer if repair is needed"
        try:
            actual = verify_packaged_project(project, source_root=ROOT)
            ready = all(
                actual["packages"].get(name) == version for name, version in packages.items()
            )
            return dict(
                result, ready=ready, actual=actual, reason=None if ready else "runtime_mismatch"
            )
        except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
            return dict(result, reason="packaged_runtime_failed: " + str(error)[:200])
    if not all((project_path / name).is_file() for name in ("uv.lock", "pyproject.toml")):
        return dict(result, reason="missing_project_or_lock")
    python = interpreter(project)
    if not (project_path / ".venv" / "pyvenv.cfg").is_file() or not python.is_file():
        return dict(result, reason="missing_environment")
    script = (
        "import importlib.metadata as m,json,platform,sys; "
        "names=json.loads(sys.argv[1]); versions={}; "
        "\nfor name in names:\n"
        " try: versions[name]=m.version(name)\n"
        " except m.PackageNotFoundError: versions[name]=None\n"
        "print(json.dumps({'python':platform.python_version(),"
        "'implementation':platform.python_implementation(),'packages':versions}))"
    )
    try:
        probe = subprocess.run(
            [str(python), "-I", "-c", script, json.dumps(sorted(packages))],
            cwd=ROOT,
            env=safe_environment(),
            stdin=subprocess.DEVNULL,
            creationflags=0x00000008 if os.name == "nt" else 0,  # DETACHED_PROCESS
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        actual = json.loads(probe.stdout)
        ready = (
            actual["implementation"] == "CPython"
            and actual["python"].startswith("3.12.")
            and actual["packages"] == packages
        )
        return dict(
            result, ready=ready, actual=actual, reason=None if ready else "runtime_mismatch"
        )
    except (OSError, subprocess.SubprocessError, ValueError, KeyError):
        return dict(result, reason="metadata_probe_failed")


def uv_ready():
    if packaged_manifest(ROOT) is not None:
        return {"ready": True, "reason": "bundled_locked_runtimes_no_uv_required"}
    executable = shutil.which("uv")
    if executable is None:
        return {"ready": False, "reason": "uv_unavailable"}
    try:
        result = subprocess.run(
            [executable, "--version"],
            stdin=subprocess.DEVNULL,
            creationflags=0x00000008 if os.name == "nt" else 0,  # DETACHED_PROCESS
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
            env=safe_environment(),
        )
        match = re.match(r"uv (\d+)\.(\d+)\.(\d+)", result.stdout)
        ready = match is not None and tuple(map(int, match.groups())) >= (0, 11, 16)
        return {"ready": ready, "reason": None if ready else "unsupported_uv_version"}
    except (OSError, subprocess.SubprocessError):
        return {"ready": False, "reason": "uv_probe_failed"}


def prepare_check(task, args, *, reconstruction=False):
    """Passive intake reused inside a bounded packaged preparation child."""
    validate_options(args)
    return ({}, []) if reconstruction else metadata(task, args)


def check(task, args, *, reconstruction=False):
    from experiments.desktop.admission import Admission, requested

    if requested(args, operation="check"):
        with Admission(task, args) as admission:
            result = admission.check()
            if result["runtimes_ready"]:
                admission.finish("complete")
            return result
    details, observation_issues = prepare_check(task, args, reconstruction=reconstruction)
    runtimes = [
        probe_runtime(project, packages)
        for project, packages in runtime_requirements(
            task, details, reconstruction=reconstruction
        ).items()
    ]
    return assemble_check(task, details, observation_issues, runtimes)


def assemble_check(task, details, observation_issues, runtimes):
    """Keep readiness/provenance fields independent of phase timing telemetry."""
    uv = uv_ready()
    # These two source routes use the shared Windows Job/control-pipe worker
    # and stdlib runtime. Other source tasks retain their POSIX-only boundary;
    # installed Windows-v1 runtimes retain their existing manifest admission.
    windows_source = os.name == "nt" and task.id in {"mmtt-sensitivity", "mmtt-sampling"}
    runtime_ready = (
        (os.name == "posix" or windows_source or packaged_manifest(ROOT) is not None)
        and all(item["ready"] for item in runtimes)
        and uv["ready"]
    )
    return {
        "schema": VERSION,
        "operation": "check",
        "task": task.id,
        "metadata_valid": True,
        "metadata": details,
        "runtimes": runtimes,
        "uv": uv,
        "posix_host": os.name == "posix",
        "runtimes_ready": runtime_ready,
        "observation_path_issues": observation_issues,
        "observation_bytes_verified": (
            True
            if task.id in ("mmtt-sensitivity", "mmtt-sampling")
            else False
            if task.id in ("m3-forecast", "m3-compare")
            else None
        ),
        "ready": runtime_ready and not observation_issues,
        "scope": (
            "frozen plan/source/input identities and installed metadata; estimation unexecuted"
            if task.id in ("mmtt-sensitivity", "mmtt-sampling")
            else "declaration identities and installed metadata; "
            "candidate behavior and observation bytes unverified"
        ),
    }
