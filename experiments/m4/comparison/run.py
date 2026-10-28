"""Sequential source supervision around unchanged M4 execution and retained archives."""

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from experiments.m4.researcher_workflow.report import reconstruct as reconstruct_child

from .common import (
    ROOT,
    VERSION,
    digest,
    dump,
    encoded,
    intake,
    protocol,
    provenance,
    read,
    require,
    seal,
    sha256,
    source_snapshots,
    verify_reference,
)


def attempt():
    return {
        "status": "not_attempted",
        "error_type": None,
        "exit_code": None,
        "manifest_sha256": None,
    }


def separate(output, path):
    require(
        output != path and output not in path.parents and path not in output.parents,
        "Output and supplied input/reference must be separate",
    )


def freeze(config_path, output, reference_path=None):
    config, bundles = intake(config_path)
    p = protocol()
    output = Path(output).absolute()
    require(not output.is_symlink(), "Output cannot be a symlink")
    output = output.resolve()
    separate(output, Path(config_path).resolve())
    for bundle in bundles.values():
        for name in ("model", "declaration"):
            separate(output, bundle[name])
    if reference_path is not None:
        reference_path = Path(reference_path).absolute()
        require(not reference_path.is_symlink(), "Reference cannot be a symlink")
        reference_path = reference_path.resolve()
        separate(output, reference_path)
        verify_reference(reference_path)
    snapshots = source_snapshots()
    identity = provenance(snapshots)
    output.mkdir(parents=True, exist_ok=False)
    for name in ("frozen", "children", "logs", "sources"):
        (output / name).mkdir()
    raw_config = next(iter(bundles.values()))["config_raw"]
    (output / "config.json").write_bytes(raw_config)
    frozen = {}
    for item in config["sources"]:
        name, bundle = item["id"], bundles[item["id"]]
        folder = output / "frozen" / name
        folder.mkdir()
        (folder / "model.py").write_bytes(bundle["model_raw"])
        (folder / "model.json").write_bytes(bundle["declaration_raw"])
        effective = {
            "schema": "m4-researcher-config/1",
            "model": "model.py",
            "declaration": "model.json",
            "timeout_seconds": config["timeout_seconds"],
        }
        dump(folder / "config.json", effective)
        frozen[name] = {
            "declaration": bundle["declared"],
            "source_sha256": digest(bundle["model_raw"]),
            "declaration_sha256": digest(bundle["declaration_raw"]),
            "effective_config": effective,
        }
    for name, raw in snapshots.items():
        path = output / "sources" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    plan = {
        "schema": VERSION,
        "protocol": p,
        "config": config,
        "config_sha256": digest(raw_config),
        "sources": frozen,
        "provenance": identity,
    }
    dump(output / "plan.json", plan)
    return output, plan, reference_path


def verify_frozen(output, plan):
    require(sha256(output / "config.json") == plan["config_sha256"], "Frozen config changed")
    require(read(output / "plan.json") == plan, "Frozen plan changed")
    for name, expected in plan["provenance"]["sources"].items():
        require(
            sha256(output / "sources" / name) == expected and sha256(ROOT / name) == expected,
            f"Frozen coordinator/condition source changed: {name}",
        )
    for name, item in plan["sources"].items():
        folder = output / "frozen" / name
        require(sha256(folder / "model.py") == item["source_sha256"], "Frozen model changed")
        require(
            sha256(folder / "model.json") == item["declaration_sha256"],
            "Frozen declaration changed",
        )
        require(
            encoded(read(folder / "config.json")) == encoded(item["effective_config"]),
            "Frozen child config changed",
        )


class Control:
    def __init__(self):
        self.signal = None
        self.cancelled_at = None
        self.active = None

    def stop(self, signum, _frame=None):
        if self.signal is None:
            self.signal, self.cancelled_at = int(signum), time.monotonic()
        self.send(signum)

    def send(self, signum):
        if self.active is not None and self.active.poll() is None:
            try:
                os.killpg(self.active.pid, signum)
            except ProcessLookupError:
                pass


def worker_environment():
    """Use installed checkout locks without active-Python or inherited uv selectors."""
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
        UV_CACHE_DIR=str(Path(tempfile.gettempdir()) / "opent1d-m4-comparison-uv-cache"),
        PYTHONNOUSERSITE="1",
        PYTHONDONTWRITEBYTECODE="1",
    )
    return env


def supervise(args, log_path, timeout, control):
    """Soft cancellation lets the old supervisor reap its separate numerical sessions."""
    deadline = time.monotonic() + timeout
    expired_at = None
    code, error = None, None
    with log_path.open("x") as log:
        log.write(json.dumps({"argv": args, "timeout_seconds": timeout}, sort_keys=True) + "\n")
        log.flush()
        control.active = subprocess.Popen(
            args,
            cwd=ROOT,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            env=worker_environment(),
        )
        try:
            if control.signal is not None:
                control.send(control.signal)
            while control.active.poll() is None:
                now = time.monotonic()
                if control.signal is None and expired_at is None and now >= deadline:
                    expired_at, error = now, "WorkerDeadline"
                    control.send(signal.SIGTERM)
                stopped_at = control.cancelled_at if control.signal is not None else expired_at
                if stopped_at is not None and now - stopped_at >= 10:
                    control.send(signal.SIGKILL)
                time.sleep(0.02)
            code = control.active.wait()
            if control.signal is not None:
                error = "GlobalInterruption"
            elif code and error is None:
                error = "WorkerExit"
        finally:
            if control.active.poll() is None:
                control.send(signal.SIGTERM)
                try:
                    control.active.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    control.send(signal.SIGKILL)
                    control.active.wait()
            control.active = None
    return code, error


def worker_args(output, *, config=None, reference=None):
    args = [sys.executable, "-B", "-S", "-m", "experiments.m4.comparison.run", "--worker"]
    args.extend(["--output", str(output)])
    if config is not None:
        args.extend(["--config", str(config), "--reference", str(reference)])
    return args


def run_study(config_path, output, reference_path=None):
    require(os.name == "posix", "M4 comparison process supervision requires POSIX")
    output, plan, reference_path = freeze(config_path, output, reference_path)
    order = [item["id"] for item in plan["config"]["sources"]]
    state = {
        "status": "started",
        "interruption_signal": None,
        "reference": attempt(),
        "sources": {identity: attempt() for identity in order},
    }
    dump(output / "state.json", state)
    control = Control()
    handled = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)
    previous = {signum: signal.signal(signum, control.stop) for signum in handled}

    def invoke(item, args, archive, logfile, budget, reference=False):
        if control.signal is not None:
            return
        item["status"] = "started"
        dump(output / "state.json", state)
        try:
            verify_frozen(output, plan)
            if control.signal is not None:
                item.update(attempt())
                return
            if args is None:
                shutil.copytree(reference_path, archive)
                (output / "logs" / logfile).write_text(
                    json.dumps(
                        {
                            "operation": "reuse_verified_reference",
                            "source": str(reference_path),
                            "manifest_sha256": sha256(archive / "manifest.json"),
                        },
                        sort_keys=True,
                    )
                    + "\n"
                )
                code, error = 0, None
            else:
                code, error = supervise(args, output / "logs" / logfile, budget, control)
            item["exit_code"] = code
            manifest = archive / "manifest.json"
            if manifest.is_file():
                item["manifest_sha256"] = sha256(manifest)
            if control.signal is not None:
                item.update(status="interrupted", error_type="GlobalInterruption")
            elif error is not None:
                item.update(status="failed", error_type=error)
            else:
                result = verify_reference(archive) if reference else reconstruct_child(archive)
                if not reference:
                    require(result["passed"], "Complete child numerical checks failed")
                item.update(status="completed", error_type=None)
            verify_frozen(output, plan)
        except BaseException as exc:
            if isinstance(exc, KeyboardInterrupt):
                control.stop(signal.SIGINT)
            item.update(
                status="interrupted" if control.signal is not None else "failed",
                error_type="GlobalInterruption"
                if control.signal is not None
                else type(exc).__name__,
            )
            manifest = archive / "manifest.json"
            if manifest.is_file() and not manifest.is_symlink():
                item["manifest_sha256"] = sha256(manifest)
        finally:
            dump(output / "state.json", state)

    try:
        if control.signal is None:
            invoke(
                state["reference"],
                None if reference_path is not None else worker_args(output / "reference"),
                output / "reference",
                "reference.log",
                plan["config"]["timeout_seconds"],
                reference=True,
            )
        if state["reference"]["status"] == "completed":
            for identity in order:
                if control.signal is not None:
                    break
                try:
                    verify_reference(output / "reference")
                    require(
                        sha256(output / "reference/manifest.json")
                        == state["reference"]["manifest_sha256"],
                        "Common reference manifest changed",
                    )
                except Exception as exc:
                    state["reference"].update(status="failed", error_type=type(exc).__name__)
                    break
                if control.signal is not None:
                    break
                invoke(
                    state["sources"][identity],
                    worker_args(
                        output / "children" / identity,
                        config=output / "frozen" / identity / "config.json",
                        reference=output / "reference",
                    ),
                    output / "children" / identity,
                    identity + ".log",
                    plan["config"]["source_timeout_seconds"],
                )
        state["status"] = (
            "interrupted"
            if control.signal is not None
            else "completed"
            if state["reference"]["status"] == "completed"
            and all(item["status"] == "completed" for item in state["sources"].values())
            else "failed"
        )
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)
        if control.signal is not None:
            state.update(status="interrupted", interruption_signal=control.signal)
        if state["status"] == "started":
            state["status"] = "failed"
        for item in (state["reference"], *state["sources"].values()):
            if item["status"] == "started":
                item.update(
                    status="interrupted" if control.signal is not None else "failed",
                    error_type="GlobalInterruption"
                    if control.signal is not None
                    else "UncommittedWorker",
                )
        dump(output / "state.json", state)
        seal(output)
    from .report import reconstruct

    return reconstruct(output, write_to=output, allow_failed=True)


execute = run_study


def main():
    """Private subprocess entry; supplied callbacks only execute in inherited workers."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", action="store_true", required=True)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reference", type=Path)
    args = parser.parse_args()
    cancelled = False

    def stop(_signum, _frame):
        nonlocal cancelled
        if not cancelled:
            cancelled = True
            raise KeyboardInterrupt("M4 comparison worker interrupted")

    for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(signum, stop)
    try:
        if args.config is None:
            from experiments.m4.feedback.run import execute as execute_reference

            execute_reference(args.output)
        else:
            from experiments.m4.researcher_workflow.run import execute as execute_source

            execute_source(args.output, args.config, args.reference)
        return 0
    except BaseException as exc:
        print(f"M4 worker failed ({type(exc).__name__}).", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
