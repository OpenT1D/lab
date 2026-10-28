"""Bounded isolated IV-001 worker execution, preserving every attempt."""

import argparse
import json
import os
import subprocess
import sys
import time
import traceback
from pathlib import Path

from experiments.m0.simglucose.recording import RunInterrupted, interruption, write_json
from experiments.m1.artifacts import digest, strict_json
from experiments.m1.contracts import number

from .common import PROTOCOL, ROOT, identity, meals, validate
from .conditions import boundary


def execute(config, output, replay=None, timeout=600, *, config_path=None):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    manifest = {"schema": "iv001.run/1", "status": "started", "files_sha256": {}}
    write_json(output / "manifest.json", manifest)
    (output / "trace.jsonl").touch()
    (output / "native.jsonl").touch()
    (output / "run.log").touch()
    child = None
    started = time.monotonic()
    try:
        number(timeout, "timeout", 0)
        if config_path is not None:
            (output / "config-source.txt").write_text(str(config_path))
            raw = Path(config_path).read_bytes()
        else:
            raw = (json.dumps(config, allow_nan=True) + "\n").encode()
        (output / "config.json").write_bytes(raw)
        cfg = validate(strict_json(raw))
        manifest.update(identity())
        if cfg.get("variant") is not None:
            write_json(output / "boundary.json", boundary(cfg, meals(cfg)))
        manifest["timeout_seconds"] = timeout
        (output / "protocol.md").write_bytes(PROTOCOL.read_bytes())
        for name in manifest["locks_sha256"]:
            (output / (name.replace("/", "_"))).write_bytes((ROOT / name).read_bytes())
        if cfg["mode"] == "replay":
            if replay is None:
                raise ValueError("Replay requires an archived nominal input")
            (output / "replay.json").write_bytes(Path(replay).read_bytes())
        elif replay is not None:
            raise ValueError("Feedback cannot receive replay input")
        write_json(output / "manifest.json", manifest)
        cmd = [
            str(ROOT / "experiments/m0/simglucose/.venv/bin/python"),
            "-m",
            "experiments.verification.simglucose_worker",
            str(output),
        ]
        if cfg["engine"] == "lt1_cambridge":
            cmd = [
                "node",
                "--loader",
                str(ROOT / "experiments/m0/lt1/node_modules/ts-node/esm.mjs"),
                str(ROOT / "experiments/verification/cambridge_worker.mjs"),
                str(output),
            ]
        environment = dict(
            os.environ,
            TS_NODE_PROJECT=str(ROOT / "experiments/m0/lt1/tsconfig.json"),
            OPENT1D_PARENT_PID=str(os.getpid()),
            MPLCONFIGDIR=str(output / "mpl-cache"),
        )
        # Native caches are outside the evidence directory and do not become scientific inputs.
        environment["MPLCONFIGDIR"] = (
            "/private/tmp/opent1d-iv-mpl" if sys.platform == "darwin" else "/tmp/opent1d-iv-mpl"
        )
        with interruption(timeout), (output / "run.log").open("wb") as log:
            child = subprocess.Popen(
                cmd, cwd=ROOT, env=environment, stdout=log, stderr=subprocess.STDOUT
            )
            code = child.wait(timeout=timeout)
        manifest["returncode"] = code
        result = strict_json((output / "result.json").read_bytes())
        if code != 0 or result.get("status") not in ("completed", "terminated", "input_exhausted"):
            raise RuntimeError(result.get("error", "Native process failed"))
        manifest["status"] = result["status"]
    except BaseException as error:
        if child is not None and child.poll() is None:
            child.kill()
            child.wait()
        if child is not None:
            manifest["returncode"] = child.returncode
        manifest.update(
            status="interrupted"
            if isinstance(error, (RunInterrupted, KeyboardInterrupt, subprocess.TimeoutExpired))
            else "failed",
            error=f"{type(error).__name__}: {error}",
        )
        (output / "supervisor-error.log").write_text(traceback.format_exc())
    finally:
        manifest["elapsed_seconds"] = time.monotonic() - started
        manifest["files_sha256"] = {
            p.name: digest(p)
            for p in sorted(output.iterdir())
            if p.is_file() and p.name != "manifest.json"
        }
        write_json(output / "manifest.json", manifest)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--replay", type=Path)
    parser.add_argument("--timeout", type=float, default=600)
    args = parser.parse_args()
    outcome = execute(None, args.output, args.replay, args.timeout, config_path=args.config)
    sys.exit(0 if outcome["status"] in ("completed", "terminated", "input_exhausted") else 1)
