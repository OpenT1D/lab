"""Reconstruct volume-assumption comparisons from the sealed synthetic archive."""

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .common import VOLUME
from .report import reconstruct


def plot(directory, output, *, allow_pending=False):
    report = reconstruct(directory, allow_pending=allow_pending)
    if not report["passed"]:
        raise ValueError("Cannot present an incomplete campaign as accepted")
    matplotlib.rcParams.update({"svg.hashsalt": "bc012-fixed", "font.size": 10})
    fig, axes = plt.subplots(2, 2, figsize=(11, 8))
    arms = ["correct", "low", "high", "estimated", "control"]
    colors = {10: "#007A87", 30: "#C45500"}
    labels = ["V correct", "V low", "V high", "V estimated", "GI control"]
    titles = [
        "Evoked responsivity",
        "Peripheral insulin removal rate",
        "C-peptide removal rate",
        "C-peptide volume: assumed or estimated",
    ]
    for j, ax in enumerate(axes.flat):
        ax.axhline(1, color="#273440", linestyle="--", linewidth=1)
        for case in report["cases"]:
            if case["regime"] != "estimated_rates" or case["data"] == "noiseless":
                continue
            best = case["best"]
            if best is None or best["estimates"][j] is None:
                continue
            center = arms.index(case["arm"])
            offset = (-0.13 if case["step"] == 10 else 0.13) + (
                -0.025 if case["data"] == "noise_117" else 0.025
            )
            ax.scatter(
                center + offset,
                best["estimates"][j],
                color=colors[case["step"]],
                marker="o" if case["data"] == "noise_117" else "^",
                s=42,
            )
        if j == 3:
            for arm, value in VOLUME.items():
                ax.scatter(arms.index(arm), value, marker="s", color="#606873", s=48)
        if j in (2, 3):
            ax.text(4, 0.61, "No estimate\nwithout Cp", ha="center", fontsize=8)
        ax.set(
            xticks=range(5),
            xticklabels=labels,
            xlim=(-0.5, 4.5),
            ylim=(0.45, 1.55),
            title=titles[j],
            ylabel="Multiplier (generating value = 1)",
        )
        ax.tick_params(axis="x", labelrotation=12)
        ax.grid(axis="y", alpha=0.15)
    fig.suptitle("BC-012: volume assumptions can change fitted secretion and removal", fontsize=14)
    fig.text(
        0.5,
        0.018,
        "Estimated removal rates · teal: 10 min · orange: 30 min · "
        "circles/triangles: two noise draws\n"
        "Squares: fixed volume assumptions · bounds 0.5–1.5 · synthetic observations only",
        ha="center",
        fontsize=10,
    )
    fig.tight_layout(rect=(0, 0.085, 1, 0.95))
    output = Path(output)
    fig.savefig(output, metadata={"Date": None})
    plt.close(fig)
    if output.suffix.lower() == ".svg":
        # Matplotlib path whitespace is irrelevant; keep versioned SVG diffs clean.
        output.write_text(
            "\n".join(line.rstrip() for line in output.read_text().splitlines()) + "\n"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--allow-pending", action="store_true")
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Choose a new figure output")
    plot(args.directory, args.output, allow_pending=args.allow_pending)
