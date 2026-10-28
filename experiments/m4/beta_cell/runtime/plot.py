"""Draw the report from saved data only; no model import or solver execution."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
from report import TRACE_COLUMNS, read_table, reconstruct

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402


def render(directory: Path, output: Path, *, allow_pending: bool = False) -> None:
    if not reconstruct(directory, allow_pending=allow_pending)["passed"]:
        raise ValueError("Refusing to plot a run with failed numerical criteria")
    rows = read_table(directory / "trace.csv", TRACE_COLUMNS)
    funcs = read_table(
        directory / "reference-functions.csv",
        ("glucose_mmol_per_L", "rho_per_min", "y_infinity_ug_per_min", "delay_min"),
    )
    p = json.loads((directory / "protocol.json").read_text())
    t = [r["time_min"] for r in rows]
    with plt.rc_context({"font.family": "DejaVu Sans", "font.size": 10, "svg.hashsalt": "BC-001"}):
        fig, axes = plt.subplots(2, 2, figsize=(12, 8), layout="constrained")
        axes[0, 0].plot(t, [r["glucose_mmol_per_L"] for r in rows], color="#206a79")
        axes[0, 0].set(
            title="Prescribed synthetic post-bolus glucose",
            xlabel="Time (min)",
            ylabel="Plasma glucose (mmol/L)",
        )
        for c in p["capacity_values"]:
            axes[0, 1].plot(
                t, [r[f"capacity_{c:g}_ug_per_min"] for r in rows], label=f"Capacity {c:g}"
            )
        axes[0, 1].set(
            title="Evoked secretion · printed initialization",
            xlabel="Time (min)",
            ylabel="Insulin secretion (µg/min)",
        )
        axes[0, 1].legend(frameon=False)
        for key, label in (
            ("secretion_ug_per_min", "Printed equation 4.13"),
            ("alternative_initialization_ug_per_min", "Author X0 = 92.7 µg"),
        ):
            axes[1, 0].plot(t, [r[key] for r in rows], label=label)
        axes[1, 0].set(
            title="Unresolved source initialization difference",
            xlabel="Time (min)",
            ylabel="Insulin secretion (µg/min)",
        )
        axes[1, 0].legend(frameon=False)
        g = [r["glucose_mmol_per_L"] for r in funcs]
        axes[1, 1].plot(g, [r["y_infinity_ug_per_min"] for r in funcs], color="#206a79")
        axes[1, 1].set(
            title="Published provision and delay functions",
            xlabel="Glucose (mmol/L)",
            ylabel="Y∞ (µg/min)",
        )
        twin = axes[1, 1].twinx()
        twin.plot(g, [r["delay_min"] for r in funcs], "--", color="#c77325")
        twin.set_ylabel("Delay 1/ρ (min)", color="#9e581b")
        twin.set_ylim(11.8, 12.8)
        for ax in axes.flat:
            ax.grid(alpha=0.2)
            ax.spines[["top", "right"]].set_visible(False)
        fig.suptitle(
            "BC-001 · Pedersen–Cobelli reduced IVGTT reference\n"
            "Synthetic input; no patient, graft or therapy validation",
            fontsize=14,
        )
        fig.savefig(output, metadata={"Date": None} if output.suffix == ".svg" else {})
        plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Refusing to overwrite figure")
    render(args.directory, args.output)
