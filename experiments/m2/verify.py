"""Verify process replay, reconstruction and catchable cancellation with native LT1."""

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from experiments.m0.simglucose.recording import write_json
from experiments.m1.artifacts import digest

from .analysis import read_run
from .run import ROOT, execute


def verify(output):
    output.mkdir(parents=True, exist_ok=False)
    summary = {"status": "started"}
    write_json(output / "verification.json", summary)
    try:
        config = ROOT / "experiments/m2/example.json"
        for name in ("first", "fresh-process"):
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "experiments.m2.run",
                    "--config",
                    str(config),
                    "--output",
                    str(output / name),
                ],
                cwd=ROOT,
                check=True,
            )
        for name in ("trace.jsonl", "native.jsonl", "runtime.json"):
            if (output / "first" / name).read_bytes() != (
                output / "fresh-process" / name
            ).read_bytes():
                raise ValueError(f"New-process replay differs: {name}")
        result = read_run(output / "first")
        rebuilt = subprocess.check_output(
            [
                sys.executable,
                "-S",
                "-c",
                "import json,sys; from experiments.m2.analysis import read_run; "
                "print(json.dumps(read_run(sys.argv[1]),sort_keys=True))",
                str(output / "first"),
            ],
            cwd=ROOT,
        )
        if json.loads(rebuilt) != result:
            raise ValueError("Simulator-free reconstruction differs")
        for sig in (signal.SIGINT, signal.SIGTERM):
            target = output / sig.name
            child = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "experiments.m2.run",
                    "--config",
                    str(config),
                    "--output",
                    str(target),
                ],
                cwd=ROOT,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            deadline = time.monotonic() + 30
            try:
                while time.monotonic() < deadline:
                    trace = target / "trace.jsonl"
                    if trace.exists() and trace.stat().st_size > 1000:
                        break
                    if child.poll() is not None:
                        raise ValueError("Worker ended before interruption test")
                    time.sleep(0.05)
                else:
                    raise TimeoutError("No native checkpoint before interruption")
                os.kill(child.pid, sig)
                child.wait(timeout=10)
                interrupted = read_run(target)
                if (
                    interrupted["manifest"]["status"] != "interrupted"
                    or not interrupted["manifest"]["completed_rows"]
                ):
                    raise ValueError("Lost interruption/partial trace")
            finally:
                if child.poll() is None:
                    child.kill()
                    child.wait()
        try:
            execute(config, output / "timeout", timeout=0.01)
        except BaseException:
            if read_run(output / "timeout")["manifest"]["status"] != "interrupted":
                raise
        else:
            raise ValueError("Deadline did not interrupt")
        summary.update(
            status="completed",
            exact_process_replay=True,
            simulator_free_reconstruction=True,
            catchable_signals=["SIGINT", "SIGTERM"],
            deadline=True,
            trace_sha256=digest(output / "first/trace.jsonl"),
            metrics=result["metrics"],
        )
    except BaseException as error:
        summary.update(status="failed", error=f"{type(error).__name__}: {error}")
        raise
    finally:
        write_json(output / "verification.json", summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    verify(parser.parse_args().output.resolve())
