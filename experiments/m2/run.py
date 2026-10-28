"""Bounded LT1 process lifecycle. Root tooling needs no simulation dependency."""

import argparse
import platform
import subprocess
import sys
import time
import traceback
from pathlib import Path

from experiments.m0.simglucose.recording import RunInterrupted, interruption, write_json
from experiments.m1.artifacts import digest, strict_json
from experiments.m1.contracts import number

ROOT = Path(__file__).resolve().parents[2]


def source_hashes():
    paths = sorted((ROOT / "experiments/m2").glob("*.py"))
    paths += sorted((ROOT / "experiments/m2").glob("*.mjs"))
    paths += [ROOT / "experiments/m0/lt1" / n for n in ("setup.mjs", "record.mjs")]
    paths += sorted((ROOT / "experiments/m1").glob("*.py"))
    paths.append(ROOT / "experiments/m0/simglucose/recording.py")
    paths.append(ROOT / "experiments/platform_files.py")
    return {str(p.relative_to(ROOT)): digest(p) for p in paths}


def validate_config(value):
    if not isinstance(value, dict) or set(value) != {
        "engine",
        "profile",
        "controller",
        "condition",
        "seed",
    }:
        raise ValueError("Require engine, profile, controller, condition and seed only")
    if (
        value["engine"] != "lt1_cambridge"
        or value["profile"] != "reference"
        or value["controller"] not in ("lt1_pid", "lt1_mpc")
    ):
        raise ValueError("Cambridge supports reference with lt1_pid/lt1_mpc; no bolus or cohort")
    if value["condition"] not in ("A", "B", "C", "D"):
        raise ValueError("Expected condition A, B, C or D")
    if type(value["seed"]) is not int or value["seed"] != 101:
        raise ValueError("Cambridge structural demonstration uses seed 101")
    return value


def execute(config_path, output, timeout=300, *, _driver="cambridge", evaluation_plan=None):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    manifest = {
        "schema": "opent1d.cambridge/1" if _driver == "cambridge" else "opent1d.simglucose-m2/1",
        "status": "started",
        "config": None,
        "files_sha256": {},
        "completed_rows": 0,
    }
    write_json(output / "manifest.json", manifest)
    for name in ("trace.jsonl", "native.jsonl", "run.log"):
        (output / name).touch()
    started = time.monotonic()
    child = None
    try:
        number(timeout, "timeout_seconds", 0)
        raw = Path(config_path).read_bytes()
        (output / "config.json").write_bytes(raw)
        if _driver == "cambridge":
            cfg = validate_config(strict_json(raw))
        elif _driver == "simglucose":
            from .simglucose import evaluation_gate
            from .simglucose import validate_config as sg_config

            cfg = sg_config(strict_json(raw))
            evaluation_gate(cfg, evaluation_plan)
            if evaluation_plan is not None:
                (output / "evaluation-plan.json").write_bytes(Path(evaluation_plan).read_bytes())
        else:
            raise ValueError("Unsupported process driver")
        manifest.update(
            config=cfg,
            source_sha256=source_hashes(),
            timeout_seconds=timeout,
            revision=subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            worktree_dirty=bool(
                subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT)
            ),
            command=sys.argv,
            supervisor_python=sys.version,
            supervisor_platform=platform.platform(),
        )
        for name, path in {
            "protocol.md": ROOT / "docs/research/m2-protocol.md",
            "package-lock.json": ROOT / "experiments/m0/lt1/package-lock.json",
            "package.json": ROOT / "experiments/m0/lt1/package.json",
            "baseline.json": ROOT / "experiments/m0/lt1/baseline.json",
        }.items():
            (output / name).write_bytes(path.read_bytes())
        if _driver == "simglucose":
            for name in ("uv.lock", "protocol-settings.json", "baseline.json"):
                (output / ("simglucose-" + name)).write_bytes(
                    (ROOT / "experiments/m0/simglucose" / name).read_bytes()
                )
        write_json(output / "manifest.json", manifest)
        import os

        environment = dict(
            os.environ,
            OPENT1D_PARENT_PID=str(os.getpid()),
            TS_NODE_PROJECT=str(ROOT / "experiments/m0/lt1/tsconfig.json"),
        )
        with interruption(timeout), (output / "run.log").open("wb") as log:
            command = [
                "node",
                "--loader",
                str(ROOT / "experiments/m0/lt1/node_modules/ts-node/esm.mjs"),
                str(ROOT / "experiments/m2/worker.mjs"),
                str(output),
            ]
            if _driver == "simglucose":
                command = [
                    str(ROOT / "experiments/m0/simglucose/.venv/bin/python"),
                    "-m",
                    "experiments.m2.simglucose_worker",
                    str(output),
                ]
            child = subprocess.Popen(
                command,
                cwd=ROOT,
                env=environment,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
            returncode = child.wait(timeout=timeout)
        result = strict_json((output / "result.json").read_bytes())
        if result.get("status") not in ("completed", "terminated") or returncode:
            raise RuntimeError(result.get("error", "Native worker failed"))
        manifest["status"] = result["status"]
        if result["status"] == "terminated":
            manifest["error"] = "Native simglucose interval glucose below 10 or above 600 mg/dL"
    except BaseException as error:
        if child is not None and child.poll() is None:
            child.kill()
            child.wait()
        interrupted = isinstance(
            error, (RunInterrupted, KeyboardInterrupt, subprocess.TimeoutExpired)
        )
        manifest.update(
            status="interrupted" if interrupted else "failed",
            error=f"{type(error).__name__}: {error}",
        )
        (output / "supervisor-error.log").write_text(traceback.format_exc())
        raise
    finally:
        manifest.update(
            elapsed_seconds=time.monotonic() - started,
            completed_rows=(output / "trace.jsonl").read_bytes().count(b"\n"),
        )
        manifest["files_sha256"] = {
            p.name: digest(p)
            for p in sorted(output.iterdir())
            if p.is_file() and p.name != "manifest.json" and not p.name.endswith(".tmp")
        }
        write_json(output / "manifest.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=float, default=300)
    args = parser.parse_args()
    execute(args.config, args.output, args.timeout_seconds)


if __name__ == "__main__":
    main()
