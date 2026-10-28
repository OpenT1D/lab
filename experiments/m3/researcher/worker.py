"""One supervised person; candidate subprocess receives target-free requests."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

from experiments.m1.artifacts import strict_json
from experiments.m3.azt1d.common import MINUTE
from experiments.m3.azt1d.data import history, target, validate_observations

from .common import ROOT, finite, read, require, save
from .intake import validate_bundle
from .predictor import validate_request


class CandidateFailure(Exception):
    """Carry only a source exception's type, never its potentially private message."""

    def __init__(self, error_type):
        self.error_type = error_type
        super().__init__(error_type)


def evaluate(study, pid):
    study = Path(study)
    plan, _ = read(study / "plan.json")
    person = next(p for p in plan["config"]["people"] if p["id"] == pid)
    folder = study / "cases" / pid
    declaration, _ = read(study / "predictor/declaration.json")
    validate_bundle(
        declaration,
        (study / "predictor/source.py").read_bytes(),
        (study / "predictor/settings.json").read_bytes(),
    )
    document, sha = read(folder / "observations.json")
    require(sha == person["input"]["sha256"], "Observation identity changed")
    start, end = person["bounds_us"]
    rows = validate_observations(document, pid, start, end)
    require(sorted(rows) == person["origins_us"], "Observation schedule changed")
    child = subprocess.Popen(
        [
            sys.executable,
            "-B",
            "-S",
            "-m",
            "experiments.m3.researcher.predictor",
            str(study / "predictor/source.py"),
            str(study / "predictor/settings.json"),
        ],
        cwd=ROOT,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        creationflags=0x00000008 if os.name == "nt" else 0,  # DETACHED_PROCESS
    )
    try:
        with (folder / "trace.jsonl").open("x") as stream:
            for origin in person["origins_us"]:
                features, reason = history(rows, origin, start, "evaluation")
                candidate = persistence = None
                if features is not None:
                    request = {
                        "origin_us": origin,
                        "times_us": [origin - offset * MINUTE for offset in (25, 20, 15, 10, 5, 0)],
                        "values_mg_dl": features,
                    }
                    validate_request(request)
                    child.stdin.write(json.dumps(request, allow_nan=False) + "\n")
                    child.stdin.flush()
                    response = child.stdout.readline(16385)
                    require(
                        response.endswith("\n") and len(response) <= 16384,
                        "Predictor response missing or too large",
                    )
                    response = strict_json(response.encode())
                    if isinstance(response, dict) and set(response) == {"error_type"}:
                        error_type = response["error_type"]
                        require(
                            isinstance(error_type, str)
                            and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,127}", error_type),
                            "Invalid source failure type",
                        )
                        raise CandidateFailure(error_type)
                    require(
                        isinstance(response, dict) and set(response) == {"prediction"},
                        "Invalid predictor response",
                    )
                    candidate = finite(response["prediction"], "candidate prediction")
                    persistence = features[-1]
                # Read the target only after a causal request has been answered.
                outcome = target(rows, origin, end)
                if features is not None and outcome["status"] == "measured":
                    finite(candidate - outcome["value"], "candidate scoring error")
                    finite(persistence - outcome["value"], "persistence scoring error")
                row = {
                    "origin_us": origin,
                    "features": features,
                    "reason": reason,
                    "candidate": candidate,
                    "persistence": persistence,
                    "target": outcome,
                }
                stream.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
                stream.flush()
        child.stdin.close()
        require(child.wait(timeout=5) == 0, "Predictor did not finish cleanly")
        save(
            folder / "result.json",
            {
                "person": pid,
                "status": "completed",
                "rows": len(person["origins_us"]),
                "input_sha256": sha,
            },
        )
    finally:
        if child.poll() is None:
            child.kill()
            child.wait()
        for pipe in (child.stdin, child.stdout):
            if pipe is not None:
                pipe.close()


def main():
    require(len(sys.argv) == 3, "Worker requires study and person")
    folder = Path(sys.argv[1]) / "cases" / sys.argv[2]
    try:
        state, _ = read(folder / "state.json")
        require(
            state["status"] == "started" and state["stage"] == "execution",
            "Worker attempt is not new",
        )
        with (folder / "worker-claim.json").open("x") as stream:
            json.dump({"person": sys.argv[2]}, stream)
    except BaseException:
        return 1
    try:
        evaluate(*sys.argv[1:])
    except BaseException as error:
        save(
            folder / "worker-error.json",
            {
                "type": error.error_type
                if isinstance(error, CandidateFailure)
                else type(error).__name__
            },
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
