"""Render paired saved trajectories; never execute a model to reconstruct a figure."""

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .common import read
from .report import reconstruct


def render(directory, output, *, allow_pending=False):
    directory, output = Path(directory), Path(output)
    if output.exists():
        raise FileExistsError(output)
    report = reconstruct(directory, allow_pending=allow_pending)
    if not report["passed"]:
        raise ValueError("Cannot render a failed numerical experiment")
    p = read(directory / "protocol.json")
    with plt.rc_context({"svg.hashsalt": "bc005", "font.size": 10}):
        fig, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
        colors = {
            "pulse_increment": "#186a8b",
            "pulse_synthetic_total": "#a34f21",
            "basal_only": "#777777",
        }
        labels = {
            "pulse_increment": "Incremental pulse",
            "pulse_synthetic_total": "Pulse + synthetic basal",
            "basal_only": "Basal only",
        }
        for name in ("pulse_increment", "pulse_synthetic_total", "basal_only"):
            a = read(directory / f"insulin/{name}.json")
            # Plot forcing segments directly to preserve explicit jumps.
            forcing = a["input"]
            xs, ys = [], []
            for lo, hi, left, right in zip(
                forcing["edges"], forcing["edges"][1:], forcing["left"], forcing["right"]
            ):
                xs.extend([lo, hi])
                ys.extend([left, right])
            style = ":" if name == "basal_only" else "-"
            axes[0, 0].plot(xs, ys, style, color=colors[name], label=labels[name])
            for branch, ax in (("insulin", axes[0, 1]), ("cpeptide", axes[1, 0])):
                d = read(directory / f"{branch}/{name}.json")
                ax.plot(
                    d["times_min"],
                    [r[0] / d["volume_l_kg"] for r in d["states"]["reference"]],
                    style,
                    color=colors[name],
                    label=labels[name],
                )
        axes[0, 0].set(
            title="One declared molar input to both branches", ylabel="Appearance [pmol/(kg min)]"
        )
        axes[0, 1].set(
            title="Insulin: native liver/plasma kinetics", ylabel="Plasma insulin [pmol/L]"
        )
        axes[1, 0].set(
            title="C-peptide: nominal two-compartment kinetics", ylabel="C-peptide [pmol/L]"
        )
        for ax in (axes[0, 0], axes[0, 1], axes[1, 0]):
            ax.set_xlabel("Time [min]")
            ax.legend(fontsize=8)
            ax.grid(alpha=0.2)
        for branch, color in (("insulin", "#186a8b"), ("cpeptide", "#a34f21")):
            axes[1, 1].loglog(
                p["communication_intervals_min"],
                report["branches"][branch]["communication_errors_pmol_l"],
                "o-",
                label=branch,
                color=color,
            )
        axes[1, 1].axhline(
            p["criteria"]["fine_communication_error_pmol_l"],
            color="#777777",
            linestyle=":",
            label="Finest-step limit",
        )
        axes[1, 1].set(
            title="Ramp: input communication refinement",
            xlabel="Communication interval [min]",
            ylabel="Maximum concentration difference [pmol/L]",
        )
        axes[1, 1].legend(fontsize=8)
        axes[1, 1].grid(alpha=0.2)
        fig.suptitle(
            "BC-005 · Shared synthetic secretion, separate kinetic branches\n"
            "No glucose feedback or human/therapy validation",
            fontsize=13,
        )
        fig.savefig(output, metadata={"Date": None})
        plt.close(fig)
    if output.suffix == ".svg":
        output.write_text(
            "\n".join(line.rstrip() for line in output.read_text().splitlines()) + "\n"
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--allow-pending", action="store_true")
    args = parser.parse_args()
    render(args.directory, args.output, allow_pending=args.allow_pending)


if __name__ == "__main__":
    main()
