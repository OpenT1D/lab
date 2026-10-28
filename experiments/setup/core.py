"""Task-directed lock plans, read-only readiness checks and explicit installation."""

import json
import os
import shutil
import subprocess
import tempfile
import tomllib
from pathlib import Path

from experiments.catalogue.formats import TASKS
from experiments.catalogue.storage import (
    ROOT,
    digest,
    dump,
    encoded,
    fresh,
    load_sealed,
    read,
    regular,
    require,
    seal,
    source_hashes,
    supervise,
    text,
)
from experiments.desktop.runtime import SOURCE_FILES as RUNTIME_SOURCES
from experiments.desktop.runtime import packaged_manifest, packaged_runtime, verify_packaged_project
from experiments.platform_files import native_absolute
from experiments.setup.publication import check_install

PLAN = "opent1d.task-setup-plan/1"
VERSION = "opent1d.task-setup-receipt/1"
NATIVE = "experiments/m0/simglucose"
SECURE_NATIVE = "experiments/m0/simglucose_secure"
OBSERVER = "experiments/m4/beta_cell/runtime"
SOURCES = (
    "experiments/setup/__init__.py",
    "experiments/setup/__main__.py",
    "experiments/setup/core.py",
    *RUNTIME_SOURCES,
    "experiments/setup/publication.py",
    "publication-security.json",
    "experiments/setup/contract.json",
    "experiments/catalogue/__init__.py",
    "experiments/catalogue/storage.py",
    "experiments/catalogue/formats.py",
    "experiments/p1_external/intake.py",
    "experiments/m1/artifacts.py",
    "experiments/m1/contracts.py",
    "experiments/m1/metrics.py",
    "experiments/m1/validation.py",
    "experiments/m0/simglucose/recording.py",
)


def requirements(task, reconstruction=False, controller=None):
    require(task in TASKS, "Unsupported setup task")
    result = {".": {}}
    if not reconstruction and task in {"p1-controller", "m4-secretion", "m4-compare", "m4-study"}:
        result[NATIVE] = {"simglucose": "0.2.11", "numpy": "1.26.4", "scipy": "1.13.1"}
    if not reconstruction and task == "m4-study-secure":
        result[SECURE_NATIVE] = {
            "simglucose": "0.2.11",
            "numpy": "1.26.4",
            "scipy": "1.13.1",
            "urllib3": "2.8.0",
            "setuptools": "84.0.0",
        }
    if not reconstruction and task.startswith("m4-"):
        result[OBSERVER] = {"numpy": "2.2.6", "scipy": "1.15.3"}
    if controller is not None:
        require(
            task == "p1-controller" and not reconstruction,
            "Controller declaration only applies to P1 execution setup",
        )
        locked = tomllib.loads(regular(ROOT / NATIVE / "uv.lock").read_text())
        packages = {
            (item["name"], item["version"]) for item in locked["package"] if "version" in item
        }
        for package, version in controller["dependencies"].items():
            require(
                (package, version) in packages,
                "Controller dependency is absent from the existing native lock",
            )
            require(
                package not in result[NATIVE] or result[NATIVE][package] == version,
                "Controller dependency conflicts with the native runtime",
            )
            result[NATIVE][package] = version
    return result


def selectors(project):
    paths = ["uv.lock", "pyproject.toml"]
    if (ROOT / project / ".python-version").exists():
        paths.append(".python-version")
    else:
        paths.append(str(Path(os.path.relpath(ROOT / ".python-version", ROOT / project))))
    return {
        name: digest(regular(native_absolute(ROOT / project / name)).read_bytes()) for name in paths
    }


def uv_identity():
    manifest = packaged_manifest(ROOT)
    if manifest is not None:
        return {
            "kind": "bundled-locked-runtimes",
            "build_id": manifest["build_id"],
            "manifest_sha256": digest((ROOT.parent / "package-manifest.json").read_bytes()),
        }
    executable = shutil.which("uv")
    if executable is None:
        return None
    path = Path(executable).resolve()
    version = subprocess.run(
        [str(path), "--version"],
        stdin=subprocess.DEVNULL,
        creationflags=0x00000008 if os.name == "nt" else 0,  # DETACHED_PROCESS
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    return {
        "path": str(path),
        "sha256": digest(regular(path).read_bytes()),
        "version": version.stdout.strip(),
    }


def install_argv(project):
    if packaged_runtime(project, source_root=ROOT) is not None:
        return ["verify-bundled-runtime", project]
    return ["uv", "sync", "--locked", *([] if project == "." else ["--project", project])]


def plan(task, output, reconstruction=False, source=None):
    controller = None
    if source is not None:
        from experiments.p1_external.intake import declaration

        controller = declaration(source)
    required = requirements(task, reconstruction, controller)
    projects = [
        {
            "project": project,
            "python": "CPython 3.12",
            "packages": packages,
            "files": selectors(project),
            "install_argv": install_argv(project),
        }
        for project, packages in required.items()
    ]
    data = {
        "schema": PLAN,
        "task": task,
        "scope": "reconstruct" if reconstruction else "run",
        "controller": controller,
        "projects": projects,
        "source_sha256": source_hashes(SOURCES),
        "uv": uv_identity(),
    }
    output = fresh(output, protected(projects))
    dump(output / "plan.json", data)
    (output / "report.md").write_bytes(markdown(data).encode("utf-8"))
    seal(output)
    return data


def validate(data):
    require(
        isinstance(data, dict)
        and set(data)
        == {"schema", "task", "scope", "controller", "projects", "source_sha256", "uv"}
        and data["schema"] == PLAN
        and data["scope"] in {"run", "reconstruct"},
        "Unsupported setup plan",
    )
    require(data["source_sha256"] == source_hashes(SOURCES), "Setup implementation changed")
    required = requirements(data["task"], data["scope"] == "reconstruct", data["controller"])
    require(len(data["projects"]) == len(required), "Setup project roster differs")
    for item, (project, packages) in zip(data["projects"], required.items(), strict=True):
        expected = {
            "project": project,
            "python": "CPython 3.12",
            "packages": packages,
            "files": selectors(project),
            "install_argv": install_argv(project),
        }
        require(item == expected, "Setup project, lock, Python selector or command changed")
    require(data["uv"] == uv_identity(), "Setup uv executable identity changed; create a new plan")
    return data


def load(directory):
    directory = load_sealed(directory)
    data = validate(read(directory / "plan.json"))
    require(
        (directory / "report.md").read_bytes() == markdown(data).encode(),
        "Setup plan report differs",
    )
    return directory, data


def environment(cache, offline):
    result = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("UV_")
        and key not in {"VIRTUAL_ENV", "PYTHONHOME", "PYTHONPATH", "__PYVENV_LAUNCHER__"}
    }
    result.update(
        UV_NO_CONFIG="1", UV_CACHE_DIR=str(cache), PYTHONNOUSERSITE="1", PYTHONDONTWRITEBYTECODE="1"
    )
    if offline:
        result.update(UV_OFFLINE="1", UV_PYTHON_DOWNLOADS="never")
    return result


def check_project(item, uv, cache):
    project = ROOT / item["project"]
    python = project / ".venv/bin/python"
    result = {
        "project": item["project"],
        "ready": False,
        "reason": None,
        "lock_consistency": "not_checked",
        "actual": None,
    }
    if packaged_runtime(item["project"], source_root=ROOT) is not None:
        try:
            actual = verify_packaged_project(item["project"], source_root=ROOT)
            require(
                all(
                    actual["packages"].get(name) == version
                    for name, version in item["packages"].items()
                ),
                "Bundled distributions differ from the setup plan",
            )
            return dict(result, ready=True, lock_consistency="matched", actual=actual)
        except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
            return dict(result, reason="packaged_runtime_failed: " + str(error)[:200])
    if (
        not (project / ".venv/pyvenv.cfg").is_file()
        or not python.is_file()
        or (project / ".venv").is_symlink()
    ):
        return dict(result, reason="missing_or_aliased_environment")
    if uv is None:
        return dict(result, reason="uv_unavailable")
    script = (
        "import importlib.metadata as m,json,platform,sys; "
        "names=json.loads(sys.argv[1]); versions={};\n"
        "for name in names:\n"
        " try: versions[name]=m.version(name)\n"
        " except m.PackageNotFoundError: versions[name]=None\n"
        "print(json.dumps({'python':platform.python_version(),"
        "'implementation':platform.python_implementation(),'packages':versions}))"
    )
    try:
        probe = subprocess.run(
            [str(python), "-I", "-B", "-c", script, json.dumps(sorted(item["packages"]))],
            cwd=ROOT,
            env=environment(cache, True),
            stdin=subprocess.DEVNULL,
            creationflags=0x00000008 if os.name == "nt" else 0,  # DETACHED_PROCESS
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        actual = json.loads(probe.stdout)
        result["actual"] = actual
        require(
            actual["implementation"] == "CPython"
            and actual["python"].startswith("3.12.")
            and actual["packages"] == item["packages"],
            "Installed interpreter or declared distributions differ",
        )
        args = [uv["path"], *item["install_argv"][1:], "--check"]
        checked = subprocess.run(
            args,
            cwd=ROOT,
            env=environment(cache, True),
            stdin=subprocess.DEVNULL,
            creationflags=0x00000008 if os.name == "nt" else 0,  # DETACHED_PROCESS
            capture_output=True,
            text=True,
            timeout=120,
        )
        result["lock_consistency"] = "matched" if checked.returncode == 0 else "mismatch"
        return dict(
            result,
            ready=checked.returncode == 0,
            reason=None if checked.returncode == 0 else "environment_not_synchronized",
        )
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        return dict(result, reason=type(error).__name__ + ": " + str(error)[:200])


def protected(projects):
    return [
        path
        for item in projects
        for path in [
            ROOT / item["project"] / ".venv",
            *(ROOT / item["project"] / name for name in item["files"]),
        ]
    ]


def install_project(args, logfile, cache, offline):
    return supervise(args, logfile, ROOT, environment(cache, offline), 1800)


def offline_cache(uv):
    env = environment("unused", True)
    env.pop("UV_CACHE_DIR")
    result = subprocess.run(
        [uv["path"], "cache", "dir"],
        stdin=subprocess.DEVNULL,
        creationflags=0x00000008 if os.name == "nt" else 0,  # DETACHED_PROCESS
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    cache = Path(result.stdout.strip())
    require(cache.is_absolute() and not cache.is_symlink(), "Invalid default uv cache path")
    return str(cache)


def execute(plan_directory, output, install=False, offline=False):
    directory, data = load(plan_directory)
    if install:
        check_install(ROOT, [item["project"] for item in data["projects"]])
    output = fresh(output, [directory, *protected(data["projects"])])
    result = {
        "schema": VERSION,
        "operation": "install" if install else "check",
        "task": data["task"],
        "scope": data["scope"],
        "plan_sha256": digest(encoded(data)),
        "projects": [],
        "ready": False,
        "numerical_validation": False,
        "source_or_model_executed": False,
        "interruption_signal": None,
    }
    with tempfile.TemporaryDirectory(prefix="opent1d-task-setup-cache-") as cache:
        install_cache = (
            offline_cache(data["uv"])
            if install
            and offline
            and data["uv"] is not None
            and data["uv"].get("kind") != "bundled-locked-runtimes"
            else cache
        )
        for item in data["projects"]:
            validate(data)
            installed = {"status": "not_requested", "exit_code": None}
            if result["interruption_signal"] is not None:
                result["projects"].append(
                    {
                        "project": item["project"],
                        "ready": False,
                        "reason": "global_interruption",
                        "lock_consistency": "not_checked",
                        "actual": None,
                        "installation": {"status": "not_attempted", "exit_code": None},
                    }
                )
                continue
            if install and packaged_manifest(ROOT) is not None:
                installed = {"status": "bundled_verified", "exit_code": 0}
            elif install:
                require(data["uv"] is not None, "uv unavailable; install uv and create a new plan")
                args = [data["uv"]["path"], *item["install_argv"][1:]]
                logfile = output / (item["project"].replace("/", "_").replace(".", "root") + ".log")
                try:
                    installed = install_project(args, logfile, install_cache, offline)
                except (OSError, subprocess.SubprocessError) as error:
                    installed = {
                        "status": "failed",
                        "exit_code": None,
                        "error_type": type(error).__name__,
                    }
            validate(data)
            if installed["status"] == "interrupted":
                result["interruption_signal"] = installed["signal"]
                result["projects"].append(
                    {
                        "project": item["project"],
                        "ready": False,
                        "reason": "installation_interrupted",
                        "lock_consistency": "not_checked",
                        "actual": None,
                        "installation": installed,
                    }
                )
                continue
            checked = check_project(item, data["uv"], cache)
            if installed["status"] == "bundled_verified" and not checked["ready"]:
                installed = {
                    "status": "failed",
                    "exit_code": 1,
                    "reason": "Rerun this installer to restore its immutable runtime",
                }
            result["projects"].append({**checked, "installation": installed})
    validate(data)
    result["ready"] = all(
        item["ready"] and item["installation"]["status"] != "failed" for item in result["projects"]
    )
    dump(output / "plan.json", data)
    dump(output / "setup.json", result)
    (output / "report.md").write_text(markdown(data, result))
    seal(output)
    return result


def markdown(data, receipt=None):
    lines = [
        "# Task-directed locked setup",
        "",
        f"Task: `{text(data['task'])}`; operation scope: `{data['scope']}`.",
        "",
        "Root tooling is separate from numerical runtimes. Planning and checking do not "
        "execute a model. Installation is explicit and uses the declared existing locks.",
        "",
        "| Project | Python | Locked files | Command |",
        "| --- | --- | --- | --- |",
    ]
    for item in data["projects"]:
        lines.append(
            f"| {text(item['project'])} | {item['python']} | "
            f"{text(', '.join(sorted(item['files'])))} | "
            f"`{text(' '.join(item['install_argv']))}` |"
        )
    if receipt is not None:
        lines.extend(
            [
                "",
                f"Environment readiness: **{receipt['ready']}**.",
                "",
                "| Project | Ready | Lock consistency | Installation | Reason |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for item in receipt["projects"]:
            lines.append(
                f"| {text(item['project'])} | {item['ready']} | {item['lock_consistency']} | "
                f"{item['installation']['status']} | {text(item['reason'])} |"
            )
    lines.extend(
        [
            "",
            "Readiness describes installed environments and lock consistency. It does not "
            "establish numerical acceptance, model validity, source rights or "
            "independent usability.",
            "",
        ]
    )
    return "\n".join(lines)
