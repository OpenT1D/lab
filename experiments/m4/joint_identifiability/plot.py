"""Rebuild the synthetic observations and recovery figure from saved artifacts."""

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .common import read
from .report import reconstruct


def plot(directory, output, *, allow_pending=False):
    directory, output = Path(directory), Path(output)
    report = reconstruct(directory, allow_pending=allow_pending)
    if not report["passed"]:
        raise ValueError("Cannot plot accepted recovery from a failing campaign")
    data = read(directory / "observations.json")
    matplotlib.rcParams.update({"svg.hashsalt": "bc011-fixed", "font.size": 10})
    fig, axes = plt.subplots(2, 3, figsize=(12, 7))
    colors = {10: "#007A87", 30: "#C45500"}
    titles = ["Plasma glucose (mg/dL)", "Plasma insulin (pmol/L)", "C-peptide (pmol/L)"]
    for j in range(3):
        ax = axes[0, j]
        ax.plot(
            data["times"],
            [r[j] for r in data["reference"]],
            color="#283444",
            label="Generating model",
        )
        for step, color in colors.items():
            times = list(range(0, 241, step))
            ax.scatter(
                times,
                [data["datasets"]["noise_117"][t][j] for t in times],
                s=13 if step == 10 else 36,
                facecolors="none",
                edgecolors=color,
                label=f"{step}-min sample, seed 117",
            )
        ax.set(title=titles[j], xlabel="Elapsed minutes")
        ax.grid(alpha=0.15)
        if j == 0:
            ax.legend(fontsize=8)
    names = [
        "Evoked responsivity gain",
        "Peripheral insulin removal scale",
        "C-peptide removal scale",
    ]
    for j, ax in enumerate(axes[1]):
        ax.axhline(1, color="#283444", linestyle="--", linewidth=1, label="Generating value")
        for case in report["cases"]:
            if case["regime"] != "unknown_clearance" or case["data"] == "noiseless":
                continue
            value = case["best"]["estimates"][j]
            if value is None:
                continue
            center = {"G": 0, "GI": 1, "GIC": 2}[case["modality"]]
            offset = (-0.12 if case["step"] == 10 else 0.12) + (
                -0.025 if case["data"] == "noise_117" else 0.025
            )
            ax.scatter(
                center + offset,
                value,
                color=colors[case["step"]],
                marker="o" if case["data"] == "noise_117" else "^",
                s=42,
            )
        ax.set(
            xticks=[0, 1, 2],
            xticklabels=["G", "G + I", "G + I + Cp"],
            ylim=(0.45, 1.55),
            xlim=(-0.45, 2.45),
            title=names[j],
            ylabel="Recovered multiplier",
        )
        ax.grid(axis="y", alpha=0.15)
        if j == 2:
            ax.text(0.5, 0.62, "Unobservable\nwithout Cp", ha="center", fontsize=9)
    fig.suptitle("BC-011: conditional synthetic recovery with unknown clearance", fontsize=15)
    fig.text(
        0.5,
        0.015,
        "Teal: 10 min · orange: 30 min · circles/triangles: two noise draws · bounds 0.5–1.5\n"
        "Exact basal G/I and other physiology assumed known; "
        "no human data or uncertainty intervals.",
        ha="center",
        fontsize=10,
    )
    fig.tight_layout(rect=(0, 0.08, 1, 0.95))
    fig.savefig(output, metadata={"Date": None})
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--allow-pending", action="store_true")
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Choose a new figure path")
    plot(args.directory, args.output, allow_pending=args.allow_pending)
