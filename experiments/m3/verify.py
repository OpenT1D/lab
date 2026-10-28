"""Run the frozen synthetic example, reconstruction and retained failure checks."""

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from .analysis import reconstruct
from .common import ROOT, digest, provenance, read, require, save
from .fixtures import generate
from .workflow import fit_plan, freeze, run_study, supervise


def verify(output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    record = {
        "schema": "opent1d.m3-verification/1",
        "status": "started",
        "provenance": provenance(),
        "checks": {},
    }
    save(output / "verification.json", record)
    try:
        require(
            not record["provenance"]["dirty"], "Commit reviewed implementation before verification"
        )
        generate(output / "data")
        freeze(output / "data/registry.json", output / "plan")
        fit_plan(output / "plan/plan.json", output / "fit")
        first = run_study(output / "plan/plan.json", output / "fit", output / "study")
        require(first == reconstruct(output / "study"), "In-process reconstruction differs")
        subprocess.run(
            [
                sys.executable,
                "-S",
                "-m",
                "experiments.m3",
                "report",
                "--study",
                str(output / "study"),
                "--output",
                str(output / "reconstructed.json"),
            ],
            cwd=ROOT,
            check=True,
        )
        require(
            (output / "reconstructed.json").read_bytes()
            == (output / "study/report.json").read_bytes(),
            "Simulator-free reconstruction bytes differ",
        )
        record["checks"]["reconstruction"] = "exact without sklearn or simulators"
        fit_plan(output / "plan/plan.json", output / "repeat-fit")
        require(
            (output / "repeat-fit/model.json").read_bytes()
            == (output / "fit/model.json").read_bytes(),
            "Fresh-process fit differs",
        )
        repeated = run_study(
            output / "plan/plan.json", output / "repeat-fit", output / "repeat-study", reuse=True
        )
        for key in ("primary", "equal_person_metrics", "people", "validation"):
            require(first[key] == repeated[key], "Fresh-process forecast differs")
        record["checks"]["fresh_process"] = "exact model, forecasts, errors and coverage"
        # An ordinary second evaluation must reject known material and retain its schedule.
        try:
            run_study(output / "plan/plan.json", output / "fit", output / "rejected-reuse")
        except ValueError:
            retained = read(output / "rejected-reuse/study.json")[0]
            require(
                retained["status"] == "failed"
                and all(c["status"] == "not_attempted" for c in retained["cases"]),
                "Reuse rejection lost schedule",
            )
        else:
            raise AssertionError("Missing evaluation reuse gate")
        record["checks"]["reuse"] = "explicit reuse required, rejected attempt retained"
        # Genuine SIGTERM after checkpoint; no assumption about interpreter startup latency.
        command = [
            sys.executable,
            "-c",
            "import sys,time;from pathlib import Path;"
            'p=Path(sys.argv[1]);(p/"trace.jsonl").write_text("checkpoint\\n");time.sleep(30)',
        ]
        harness = output / "cancellation.py"
        harness.write_text(
            "from experiments.m3.workflow import supervise\n"
            + f"supervise({command!r}, {str(output / 'cancelled')!r}, 40)\n"
        )
        environment = dict(os.environ, PYTHONPATH=str(ROOT))
        with (output / "cancelled-supervisor.log").open("wb") as log:
            process = subprocess.Popen(
                [sys.executable, str(harness)],
                cwd=ROOT,
                env=environment,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
            try:
                deadline = time.monotonic() + 15
                while time.monotonic() < deadline:
                    path = output / "cancelled/trace.jsonl"
                    if path.exists() and path.read_bytes() == b"checkpoint\n":
                        break
                    if process.poll() is not None:
                        raise AssertionError("Supervisor ended before checkpoint")
                    time.sleep(0.02)
                else:
                    raise AssertionError("No checkpoint before cancellation test deadline")
                process.send_signal(signal.SIGTERM)
                process.wait(timeout=10)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()
        state, _ = read(output / "cancelled/state.json")
        require(
            state["status"] == "interrupted"
            and (output / "cancelled/trace.jsonl").read_bytes() == b"checkpoint\n",
            "Cancellation lost output",
        )
        record["checks"]["cancellation"] = "SIGTERM after checkpoint retained"
        try:
            supervise(command, output / "timeout", 1)
        except BaseException as error:
            state, _ = read(output / "timeout/state.json")
            require(state["status"] == "interrupted", "Deadline not retained as interruption")
            record["checks"]["deadline"] = {
                "type": type(error).__name__,
                "trace_sha256": digest((output / "timeout/trace.jsonl").read_bytes()),
            }
        else:
            raise AssertionError("Missing deadline")
        record["synthetic_summary"] = {
            k: first[k] for k in ("primary", "equal_person_metrics", "status_counts")
        }
        record["status"] = "completed"
    except BaseException as error:
        from .workflow import failure

        record.update(status="failed", error=failure(error))
        raise
    finally:
        save(output / "verification.json", record)
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps({"status": verify(args.output)["status"]}))
