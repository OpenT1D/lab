"""Render conditional objective profiles and their fixed-nuisance comparators."""

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from .common import read
from .report import reconstruct


def plot(directory, output, *, allow_pending=False):
    report = reconstruct(directory, allow_pending=allow_pending)
    if not report["passed"]:
        raise ValueError("Cannot present an incomplete profile campaign as accepted")
    p = read(Path(directory) / "protocol.json")
    matplotlib.rcParams.update({"svg.hashsalt": "bc013-fixed", "font.size": 9})
    fig, axes = plt.subplots(4, 3, figsize=(12, 12), sharex=True, sharey=True)
    colors = {"free_volume": "#007A87", "fixed_volume": "#C45500", "GI": "#696878"}
    names = ["Evoked responsivity", "Insulin removal m4", "C-peptide removal k3", "Cp volume"]
    for case in report["cases"]:
        column = p["observation"]["data_cases"].index(case["data"])
        for profile in case["profiles"]:
            ax = axes[profile["parameter"], column]
            points = profile["points"]
            color = colors[case["design"]]
            ax.plot([v["value"] for v in points], [v["delta_q"] for v in points], color=color)
            for point in (points[0], points[-1]):
                if point["delta_q"] <= p["profiles"]["cutoff"]:
                    ax.scatter(
                        point["value"],
                        point["delta_q"],
                        marker="<" if point["value"] == 0.5 else ">",
                        color=color,
                        s=45,
                        clip_on=False,
                        zorder=5,
                    )
            if case["design"] == "free_volume":
                ax.plot(
                    [v["value"] for v in points],
                    [v["slice_delta_q"] for v in points],
                    color="#222222",
                    linestyle="--",
                    linewidth=0.9,
                    alpha=0.7,
                )
    for row, name in enumerate(names):
        for col in range(3):
            ax = axes[row, col]
            ax.axhline(p["profiles"]["cutoff"], color="#999999", linestyle=":", linewidth=1.2)
            ax.axvline(1, color="#cccccc", linestyle=":", linewidth=0.8)
            ax.set(xlim=(0.5, 1.5), ylim=(-0.15, 12), xticks=[0.5, 0.75, 1, 1.25, 1.5])
            ax.grid(axis="y", alpha=0.12)
            if col == 0:
                ax.set_ylabel(name + "\nΔ weighted objective Q")
            if row == 3:
                ax.set_xlabel("Fixed profile multiplier")
    for ax, title in zip(axes[0], ["Noiseless", "Noise seed 117", "Noise seed 221"]):
        ax.set_title(title)
    handles = [
        Line2D([0], [0], color=color, label=label)
        for color, label in zip(
            colors.values(), ["GIC, volume estimated", "GIC, volume fixed", "GI control"]
        )
    ]
    handles.append(
        Line2D([0], [0], color="#222222", linestyle="--", label="Free-V fixed-nuisance slice")
    )
    fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, 0.955), ncol=2)
    fig.suptitle("BC-013: conditional nuisance profiles in the synthetic model", fontsize=14)
    fig.text(
        0.5,
        0.018,
        "30-minute sampling · dotted horizontal: nominal ΔQ = 3.841 contour · "
        "triangles: bound-limited\n"
        "Vertical line: generating value 1 · tails above ΔQ = 12 omitted from display\n"
        "Engineering bounds and noise; no demonstrated confidence coverage or human validation",
        ha="center",
        fontsize=9,
    )
    fig.tight_layout(rect=(0, 0.085, 1, 0.90))
    output = Path(output)
    fig.savefig(output, metadata={"Date": None})
    plt.close(fig)
    if output.suffix.lower() == ".svg":
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
