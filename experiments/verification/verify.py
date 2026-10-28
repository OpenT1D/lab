"""Native regression checks for IV-001, including a known native stop and process replay."""

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

from experiments.m0.simglucose.recording import write_json
from experiments.m1.artifacts import digest, strict_json
from experiments.m2.run import execute as reference

from .analysis import read_run
from .common import ROOT, configurations, read_lines
from .run import execute


def verify(output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    summary = {"status": "started", "cases": []}
    write_json(output / "verification.json", summary)
    for index in (0, 3, 8, 9):
        cfg = configurations()[index]
        case = output / str(index)
        case.mkdir()
        original = {k: cfg[k] for k in ("engine", "profile", "seed", "controller")} | {
            "condition": "A"
        }
        write_json(case / "reference-config.json", original)
        reference(
            case / "reference-config.json",
            case / "reference",
            _driver="simglucose" if cfg["engine"] == "simglucose" else "cambridge",
        )
        expected = read_lines((case / "reference/trace.jsonl").read_bytes())
        for name in ("first", "repeat"):
            execute(cfg, case / name)
            actual = read_run(case / name)
            if actual["rows"] != expected:
                raise ValueError(f"Native reference differs: {index}/{name}")
            reference_status = strict_json((case / "reference/manifest.json").read_bytes())[
                "status"
            ]
            if actual["status"] != reference_status:
                raise ValueError("Native completion status differs")
        saved = read_run(case / "first")
        write_json(
            case / "replay.json",
            dict(
                config=cfg,
                status=saved["status"],
                trace_sha256=saved["inputs_sha256"]["trace.jsonl"],
                rows=saved["rows"],
            ),
        )
        execute(cfg | {"mode": "replay"}, case / "replay", case / "replay.json")
        replay = read_run(case / "replay")
        if replay["rows"] != saved["rows"] or replay["status"] != saved["status"]:
            raise ValueError("Nominal fixed-input replay differs")
        # Standard-library-only process; both native environments are absent from sys.path.
        command = [
            sys.executable,
            "-S",
            "-c",
            "from experiments.verification.analysis import read_run; "
            "import sys; read_run(sys.argv[1])",
            str(case / "first"),
        ]
        subprocess.run(command, cwd=ROOT, check=True)
        summary["cases"].append(
            dict(
                index=index,
                status=saved["status"],
                exact_reference=True,
                exact_fresh_process=True,
                exact_nominal_replay=True,
                simulator_free_reconstruction=True,
            )
        )
        write_json(output / "verification.json", summary)
    for label, index, group, key, diagnostic in (
        ("sg-parameters", 0, "settings", "parameters", "physiological parameters"),
        ("sg-packages", 0, None, "packages", "packages"),
        ("cambridge-patient", 8, "settings", "patient", "patient"),
        ("mpc-controller", 9, "settings", "controller", "controller"),
        ("cambridge-source", 8, None, "source_sha256", "native source"),
    ):
        target = output / label
        source = output / str(index) / "first"
        read_run(source)
        shutil.copytree(source, target)
        runtime = strict_json((target / "runtime.json").read_bytes())
        container = runtime if group is None else runtime[group]
        del container[key]
        write_json(target / "runtime.json", runtime)
        manifest = strict_json((target / "manifest.json").read_bytes())
        manifest["files_sha256"]["runtime.json"] = digest(target / "runtime.json")
        write_json(target / "manifest.json", manifest)
        try:
            read_run(target)
        except ValueError as error:
            if diagnostic not in str(error):
                raise
        else:
            raise ValueError(f"Missing native provenance accepted: {label}")
    summary["missing_runtime_provenance_detected"] = True
    # Start with a genuinely complete, validated artifact; preserve other guards.
    altered = output / "false-completion"
    shutil.copytree(output / "8/first", altered)
    trace = altered / "trace.jsonl"
    trace.write_bytes(b"\n".join(trace.read_bytes().splitlines()[:-1]) + b"\n")
    manifest = strict_json((altered / "manifest.json").read_bytes())
    manifest["files_sha256"]["trace.jsonl"] = digest(trace)
    write_json(altered / "manifest.json", manifest)
    try:
        read_run(altered)
    except ValueError as error:
        if "False completion" not in str(error):
            raise
    else:
        raise ValueError("Truncated artifact accepted as complete")
    changed = output / "changed-input"
    shutil.copytree(output / "8/first", changed)
    with (changed / "config.json").open("ab") as stream:
        stream.write(b" ")
    try:
        read_run(changed)
    except ValueError as error:
        if "Artifact changed: config.json" not in str(error):
            raise
    else:
        raise ValueError("Changed input bytes accepted")
    summary.update(false_completion_detected=True, changed_input_detected=True)
    cfg = configurations()[-1]
    execute(cfg, output / "timeout", timeout=0.01)
    if read_run(output / "timeout")["status"] != "interrupted":
        raise ValueError("Timeout lost")
    write_json(output / "cancel-config.json", cfg)
    for command, trace in (
        (
            [
                sys.executable,
                "-m",
                "experiments.verification.run",
                "--config",
                str(output / "cancel-config.json"),
                "--output",
                str(output / "cancelled"),
            ],
            output / "cancelled/trace.jsonl",
        ),
        (
            [
                sys.executable,
                "-m",
                "experiments.verification.campaign",
                "pilot",
                "--output",
                str(output / "cancelled-campaign"),
            ],
            output / "cancelled-campaign/00-feedback-1/trace.jsonl",
        ),
    ):
        child = subprocess.Popen(command, cwd=ROOT)
        try:
            deadline = time.monotonic() + 60
            while not trace.exists() or not trace.stat().st_size:
                if child.poll() is not None or time.monotonic() > deadline:
                    raise RuntimeError("No cancellable progress")
                time.sleep(0.01)
            os.kill(child.pid, signal.SIGTERM)
            if child.wait(timeout=15) == 0:
                raise ValueError("Cancelled process succeeded")
        finally:
            if child.poll() is None:
                child.kill()
                child.wait()
        if read_run(trace.parent)["status"] != "interrupted":
            raise ValueError("Cancellation lost")
    cancelled = strict_json((output / "cancelled-campaign/report.json").read_bytes())
    if cancelled["status"] != "failed" or len(cancelled["cases"]) != 12:
        raise ValueError("Cancelled campaign lost its planning")
    summary["campaign_cancellation"] = True
    execute(configurations()[0] | {"profile": "invalid"}, output / "invalid")
    bad = read_run(output / "invalid")
    if bad["status"] != "failed" or bad["rows"]:
        raise ValueError("Failed initialization leaked output")
    shim = output / "node-shim"
    shim.mkdir()
    executable = shim / "node"
    executable.write_text("#!/bin/sh\nexit 23\n")
    executable.chmod(0o755)
    environment = dict(os.environ, PATH=str(shim) + os.pathsep + os.environ["PATH"])
    with (output / "injected-campaign.log").open("wb") as log:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "experiments.verification.campaign",
                "pilot",
                "--output",
                str(output / "injected-campaign"),
            ],
            cwd=ROOT,
            env=environment,
            stdout=log,
            stderr=subprocess.STDOUT,
            timeout=180,
        )
    report = strict_json((output / "injected-campaign/report.json").read_bytes())
    if result.returncode == 0 or report["status"] != "failed":
        raise ValueError("Failed native campaign returned success")
    statuses = [c["status"] for c in report["cases"]]
    if statuses.count("failed") != 6 or statuses.count("completed") != 6:
        raise ValueError("Injected failures disappeared from planned accounting")
    summary.update(
        status="completed",
        timeout=True,
        cancellation=True,
        invalid_initialization=True,
        injected_campaign_failure_detected=True,
    )
    write_json(output / "verification.json", summary)
    print(json.dumps(summary))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    verify(parser.parse_args().output)
