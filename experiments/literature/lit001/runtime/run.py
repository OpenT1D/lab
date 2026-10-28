"""Execute a declared synthetic reference and retain reconstructible artifacts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
from datetime import UTC, datetime
from pathlib import Path

import matplotlib
import numpy as np
import scipy
from model import Parameters, analytic, numerical
from report import reconstruct

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
SOURCE_FILES = ("model.py", "run.py", "report.py", "test_model.py", "uv.lock", "pyproject.toml")


def dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    manifest = {
        "status": "started",
        "started_utc": datetime.now(UTC).isoformat(),
        "claim": "synthetic_published_equation_example",
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "matplotlib": matplotlib.__version__,
        },
        "source_code_sha256": {
            filename: hashlib.sha256((HERE / filename).read_bytes()).hexdigest()
            for filename in SOURCE_FILES
        },
        "files": {},
    }
    dump(args.output / "manifest.json", manifest)
    try:
        for filename in SOURCE_FILES:
            (args.output / f"source-{filename}").write_bytes((HERE / filename).read_bytes())
        for filename in ("reference-protocol.json", "parameters.json"):
            target = "protocol.json" if filename == "reference-protocol.json" else filename
            (args.output / target).write_bytes((HERE.parent / filename).read_bytes())
        protocol = json.loads((args.output / "protocol.json").read_text())
        if (
            hashlib.sha256((args.output / "parameters.json").read_bytes()).hexdigest()
            != protocol["parameter_file_sha256_at_specification"]
        ):
            raise ValueError("Parameter record differs from the frozen specification")
        p = Parameters.from_record(json.loads((args.output / "parameters.json").read_text()))
        times = np.unique(
            np.append(np.arange(0, protocol["horizon_min"] + 0.01, protocol["step_min"]), p.tau)
        )
        dose = protocol["dose_U_per_kg"] * 1000
        exact = analytic(times, dose, p)
        numeric = [numerical(times, dose, p, **settings) for settings in protocol["solvers"]]
        with (args.output / "trace.csv").open("w", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(
                [
                    "time_min",
                    "analytic_mU_per_L",
                    "rk45_coarse_mU_per_L",
                    "rk45_tight_mU_per_L",
                    "dop853_mU_per_L",
                    "sc1",
                    "sc2",
                    "plasma",
                    "eliminated",
                    "pending",
                ]
            )
            for i, time_min in enumerate(times):
                writer.writerow(
                    [time_min, exact[i, 2] / p.volume]
                    + [states[i, 2] / p.volume for states in numeric]
                    + list(numeric[-1][i])
                    + [dose if time_min < p.tau else 0]
                )
        with plt.rc_context({"font.family": "DejaVu Sans", "font.size": 11}):
            fig, axes = plt.subplots(1, 2, figsize=(11, 4.1), layout="constrained")
            axes[0].plot(times, exact[:, 2] / p.volume, color="#126a78", label="Closed form")
            axes[0].plot(
                times[::60],
                numeric[-1][::60, 2] / p.volume,
                ".",
                color="#dc7335",
                label="Numerical integration",
            )
            axes[0].set(xlabel="Time after declared bolus (min)", ylabel="Insulin (mU/L)")
            axes[0].legend(frameon=False)
            for i, label in enumerate(("SC depot 1", "SC depot 2", "Plasma", "Eliminated")):
                axes[1].plot(times, numeric[-1][:, i], label=label)
            axes[1].set(xlabel="Time after declared bolus (min)", ylabel="Insulin amount (mU/kg)")
            axes[1].legend(frameon=False)
            for ax in axes:
                ax.grid(alpha=0.2)
                ax.spines[["top", "right"]].set_visible(False)
            fig.suptitle("Published equations • synthetic zero-history example", fontsize=14)
            fig.savefig(args.output / "reference.png", dpi=160)
            fig.savefig(args.output / "reference.svg", metadata={"Date": None})
            plt.close(fig)
        manifest["files"] = {
            name: hashlib.sha256((args.output / name).read_bytes()).hexdigest()
            for name in (
                "protocol.json",
                "parameters.json",
                "trace.csv",
                "reference.png",
                "reference.svg",
                *(f"source-{filename}" for filename in SOURCE_FILES),
            )
        }
        manifest["status"] = "completed"
        manifest["finished_utc"] = datetime.now(UTC).isoformat()
        dump(args.output / "manifest.json", manifest)
        result = reconstruct(args.output)
        dump(args.output / "report.json", result)
        print(json.dumps(result, indent=2))
        if not result["passed_numerical_criteria"]:
            raise RuntimeError("Prespecified numerical criteria failed")
    except Exception as exc:
        manifest.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        dump(args.output / "manifest.json", manifest)
        raise


if __name__ == "__main__":
    main()
