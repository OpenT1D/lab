"""Rebuild the BC-002 figure from validated archives, without executing a model."""

import argparse
import json
from pathlib import Path

import matplotlib

from .report import COLUMNS, reconstruct, table

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402


def render(directory, output, *, allow_pending=False):
    result = reconstruct(directory, allow_pending=allow_pending)
    if not result["passed"]:
        raise ValueError("Refusing to plot failed numerical criteria")
    directory, output = Path(directory), Path(output)
    source = table(
        directory / "source-input.csv", ("time_min", "secretion_ug_per_min", "q_pmol_kg_min")
    )
    cases = {name: table(directory / f"{name}.csv", COLUMNS) for name in result["cases"]}
    with plt.rc_context({"font.family": "DejaVu Sans", "font.size": 10, "svg.hashsalt": "BC-002"}):
        fig, axes = plt.subplots(2, 2, figsize=(12, 8), layout="constrained")
        ax = axes[0, 0]
        ax.plot(
            [r["time_min"] for r in source], [r["q_pmol_kg_min"] for r in source], color="#206a79"
        )
        ax.set(
            title="BC-001 evoked output · nominal mass conversion",
            xlabel="Time (min)",
            ylabel="Added insulin (pmol/kg/min)",
        )
        ax = axes[0, 1]
        for name, label in (
            ("source-liver", "Liver inlet"),
            ("source-peripheral", "Peripheral inlet"),
            ("matched-constant-liver", "Equal-amount constant · liver"),
            ("zero-liver", "No added insulin"),
        ):
            rows = cases[name]
            ax.plot([r["time_min"] for r in rows], [r["plasma_pmol_l"] for r in rows], label=label)
        ax.set(
            title="Incremental plasma insulin · fixed native kinetics",
            xlabel="Time (min)",
            ylabel="Insulin above zero baseline (pmol/L)",
        )
        ax.legend(frameon=False, fontsize=8)
        ax = axes[1, 0]
        rows = cases["source-liver"]
        for key, label in (
            ("input_pmol_kg", "Input"),
            ("hepatic_loss_pmol_kg", "Hepatic loss"),
            ("peripheral_loss_pmol_kg", "Peripheral loss"),
        ):
            ax.plot([r["time_min"] for r in rows], [r[key] for r in rows], label=label)
        ax.plot(
            [r["time_min"] for r in rows],
            [r["Ip_pmol_kg"] + r["Il_pmol_kg"] for r in rows],
            label="Remaining inventory",
        )
        ax.set(
            title="Mass ledger · liver inlet",
            xlabel="Time (min)",
            ylabel="Cumulative amount / inventory (pmol/kg)",
        )
        ax.legend(frameon=False, fontsize=8)
        ax = axes[1, 1]
        for route in ("liver", "peripheral"):
            rows = result["verification"]["communication"][route]["intervals"]
            ax.loglog(
                [r["interval_min"] for r in rows],
                [r["max_plasma_error_pmol_l"] for r in rows],
                "o-",
                label=route.capitalize(),
            )
        protocol = json.loads((directory / "protocol.json").read_text())
        ax.axhline(
            protocol["criteria"]["fine_communication_plasma_error_pmol_l"],
            color="grey",
            linestyle=":",
            label="Finest-step acceptance limit",
        )
        ax.set(
            title="Interval-average transfer vs continuous input",
            xlabel="Communication interval (min)",
            ylabel="Maximum sampled difference (pmol/L)",
        )
        ax.legend(frameon=False)
        for ax in axes.flat:
            ax.grid(alpha=0.2)
            ax.spines[["top", "right"]].set_visible(False)
        fig.suptitle(
            "BC-002 · Native insulin kinetics with an explicit inlet\n"
            "Synthetic incremental input; no glucose, patient or therapy evaluation",
            fontsize=14,
        )
        fig.savefig(output, metadata={"Date": None} if output.suffix == ".svg" else {})
        plt.close(fig)
    if output.suffix == ".svg":
        output.write_text(
            "\n".join(line.rstrip() for line in output.read_text().splitlines()) + "\n"
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Refusing to overwrite figure")
    render(args.directory, args.output)


if __name__ == "__main__":
    main()
