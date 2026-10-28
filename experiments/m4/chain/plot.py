"""Regenerate the complete synthetic chain figure from verified saved artifacts."""

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .common import load_source, read
from .report import reconstruct


def render(directory, output, *, allow_pending=False):
    directory, output = Path(directory), Path(output)
    if output.exists():
        raise FileExistsError(output)
    report = reconstruct(directory, allow_pending=allow_pending)
    if not report["passed"]:
        raise ValueError("Cannot render a passing chain figure from failed criteria")
    p = read(directory / "protocol.json")
    source = load_source(directory / "secretion", p)
    times = source["times_min"]
    matplotlib.rcParams.update({"svg.hashsalt": "bc007-chain", "font.size": 10})
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), layout="constrained")
    fig.suptitle(
        "BC-007 · Prescribed glucose → secretion → paired kinetics\n"
        "Synthetic chain; glucose is imposed, with no feedback",
        fontsize=15,
    )
    axes[0, 0].plot(times, source["glucose_mmol_l"], color="#0072B2")
    axes[0, 0].set(title="Input: declining post-bolus glucose", ylabel="Glucose [mmol/L]")
    labels = {
        "zero_increment": "Zero increment",
        "half_increment": "Half evoked",
        "full_increment": "Full evoked",
        "full_synthetic_total": "Full evoked + synthetic basal",
        "basal_only": "Synthetic basal only",
        "matched_constant_increment": "Equal-amount constant",
    }
    colors = ["#777777", "#009E73", "#0072B2", "#D55E00", "#999999", "#CC79A7"]
    styles = [":", "--", "-", "-", ":", "--"]
    for case, color, style in zip(p["cases"], colors, styles, strict=True):
        from experiments.m4.kinetic_inlet.forcing import Forcing

        item = read(directory / "insulin" / f"{case['id']}.json")
        force = Forcing(**item["request"]["forcing"])
        factor = p["boundary"]["body_weight_kg"] * p["boundary"]["insulin_molar_mass_g_mol"] / 1e6
        axes[0, 1].plot(
            times,
            [force.evaluate(t) * factor for t in times],
            color=color,
            linestyle=style,
            label=labels[case["id"]],
        )
        for branch, ax in (("insulin", axes[1, 0]), ("cpeptide", axes[1, 1])):
            data = read(directory / branch / f"{case['id']}.json")
            ax.plot(
                times,
                [row[0] / data["volume_l_kg"] for row in data["states"]["reference"]],
                color=color,
                linestyle=style,
            )
    axes[0, 1].set(
        title="Transferred secretion scenarios", ylabel="Insulin-equivalent mass rate [µg/min]"
    )
    axes[0, 1].legend(fontsize=8, loc="upper right")
    axes[1, 0].set(title="Output: plasma insulin", ylabel="Insulin [pmol/L]")
    axes[1, 1].set(title="Output: plasma C-peptide", ylabel="C-peptide [pmol/L]")
    for ax in axes.flat:
        ax.set_xlabel("Time [min]")
        ax.grid(alpha=0.2)
    fig.savefig(output, metadata={"Date": None} if output.suffix == ".svg" else None)
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
