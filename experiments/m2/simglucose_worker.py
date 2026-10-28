"""Run unchanged M1 physiology/control with a separately gated M2 population."""

import json
import platform
import sys
import traceback
import warnings
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

from experiments.m0.simglucose.recording import write_json
from experiments.m1.artifacts import strict_json


class NativeArtifacts:
    """Route M1's metadata file to runtime.json; the supervisor owns manifest.json."""

    def __init__(self, root):
        self.root = root

    def __truediv__(self, name):
        return self.root / ("runtime.json" if name == "manifest.json" else name)


def main(output):
    native = {
        "python": sys.version,
        "platform": platform.platform(),
        "architecture": platform.machine(),
    }
    caught = []
    try:
        from .simglucose import evaluation_gate, validate_config

        cfg = validate_config(strict_json((output / "config.json").read_bytes()))
        evaluation_gate(cfg, output / "evaluation-plan.json")
        native["config"] = cfg
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            from experiments.m1.runtime import native_run

            def initial(snapshot):
                write_json(output / "initial.json", asdict(snapshot))

            with (output / "trace.jsonl").open("a") as trace:
                previous = 0

                def checkpoint(row):
                    nonlocal previous
                    if row.start_min != previous:
                        raise ValueError("Noncontiguous native checkpoint")
                    trace.write(json.dumps(asdict(row), allow_nan=False) + "\n")
                    trace.flush()
                    previous = row.end_min

                status = native_run(
                    SimpleNamespace(**cfg), checkpoint, initial, NativeArtifacts(output), native
                )
            if status not in ("completed", "terminated"):
                raise ValueError("Unsupported native completion")
            write_json(output / "result.json", {"status": status})
    except BaseException as error:
        write_json(
            output / "result.json",
            {"status": "failed", "error": f"{type(error).__name__}: {error}"},
        )
        (output / "failure.log").write_text(traceback.format_exc())
        raise
    finally:
        write_json(output / "runtime.json", native)
        write_json(
            output / "warnings.json",
            [
                {
                    "category": w.category.__name__,
                    "message": str(w.message),
                    "filename": w.filename,
                    "line": w.lineno,
                }
                for w in caught
            ],
        )


if __name__ == "__main__":
    main(Path(sys.argv[1]))
