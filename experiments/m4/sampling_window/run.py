"""Run the frozen BC-015-P4 synthetic sampling experiment in its native lock."""

import argparse
import platform
import shutil
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import scipy

from .analysis import run_analysis
from .plot import render
from .report import PROTOCOL_SHA256, RAW, SOURCES, digest, read_json, summarize, write_json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCE_PATHS = {
    "source-analysis.py": HERE / "analysis.py",
    "source-report.py": HERE / "report.py",
    "source-run.py": HERE / "run.py",
    "source-plot.py": HERE / "plot.py",
    "source-test_numerical.py": HERE / "test_numerical.py",
    "source-cpeptide-model.py": ROOT / "experiments/m4/c_peptide/model.py",
    "source-cpeptide-reference.py": ROOT / "experiments/m4/c_peptide/reference.py",
    "source-forcing.py": ROOT / "experiments/m4/kinetic_inlet/forcing.py",
    "runtime-uv.lock": ROOT / "experiments/m4/beta_cell/runtime/uv.lock",
    "runtime-pyproject.toml": ROOT / "experiments/m4/beta_cell/runtime/pyproject.toml",
}


def execute(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    manifest = {
        "schema": "bc015-sampling-window-archive/1",
        "status": "started",
        "started_utc": datetime.now(UTC).isoformat(),
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
        "files": {},
    }
    write_json(output / "manifest.json", manifest)
    try:
        shutil.copyfile(HERE / "protocol.json", output / "protocol.json")
        if digest(output / "protocol.json") != PROTOCOL_SHA256:
            raise ValueError("BC-015-P4/1 protocol changed; create a new version")
        protocol = read_json(output / "protocol.json")
        expected = protocol["runtime"]
        if not manifest["runtime"]["python"].startswith(expected["python"] + ".") or any(
            manifest["runtime"][key] != expected[key] for key in ("numpy", "scipy")
        ):
            raise ValueError("BC-015-P4 requires its frozen model runtime")
        if set(SOURCE_PATHS) != set(SOURCES):
            raise RuntimeError("Incomplete source inventory")
        for name, path in SOURCE_PATHS.items():
            shutil.copyfile(path, output / name)
        raw = run_analysis(protocol)
        for name in RAW[1:]:
            write_json(output / name, raw[name.removesuffix(".json")])
        report = summarize(
            protocol, raw["checks"], raw["sensitivities"], raw["observations"], raw["cases"]
        )
        write_json(output / "report.json", report)
        render(output, output / "figure.svg", verify=False)
        manifest["files"] = {
            name: digest(output / name) for name in RAW + SOURCES + ("report.json", "figure.svg")
        }
        manifest["status"] = "completed"
        manifest["completed_utc"] = datetime.now(UTC).isoformat()
    except Exception as exc:
        manifest["status"] = "failed"
        manifest["error_type"] = type(exc).__name__
        manifest["error"] = str(exc)
        raise
    finally:
        write_json(output / "manifest.json", manifest)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = execute(args.output)
    print(
        {
            "noisy_results": report["noisy_results"],
            "paired_completed_draws": report["paired_completed_draws"],
        }
    )
