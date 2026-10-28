"""Rebuild the BC-015-P4 figure from archived synthetic observations."""

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .report import read_json, reconstruct


def render(archive, destination, *, verify=True):
    archive = Path(archive)
    destination = Path(destination)
    if destination.suffix not in (".svg", ".png"):
        raise ValueError("Figure output must be SVG or PNG")
    report = reconstruct(archive) if verify else read_json(archive / "report.json")
    data = read_json(archive / "observations.json")
    times = data["times_min_after_injection"]
    values = data["reference_pmol_l"]
    n_early = report["sample_counts"]["early"]
    plt.rcParams["svg.hashsalt"] = "bc015-p4-synthetic-window"
    figure, axes = plt.subplots(1, 2, figsize=(10, 3.6), layout="constrained")
    for axis, limit in zip(axes, (25, 181), strict=True):
        axis.plot([0, *times], [0, *values], color="#326f9e", linewidth=1.7)
        axis.scatter(times[:n_early], values[:n_early], color="#cf642d", s=28, label="early Cp")
        if limit > 25:
            axis.scatter(
                times[n_early:],
                values[n_early:],
                color="#34865c",
                marker="s",
                s=24,
                label="hypothetical late Cp",
            )
        axis.axvline(10, color="#777777", linestyle="--", linewidth=1)
        axis.set(
            xlim=(0, limit),
            xlabel="Minutes after nominal injection",
            ylabel="Incremental Cp (pmol/L)",
        )
        axis.grid(alpha=0.2)
        axis.legend(frameon=False, fontsize=8)
    figure.suptitle("Synthetic known-shape pulse: sampling windows, not CIT-07 observations")
    figure.savefig(
        destination,
        format=destination.suffix[1:],
        metadata={"Date": None} if destination.suffix == ".svg" else None,
    )
    plt.close(figure)
    if destination.suffix == ".svg":
        # Matplotlib writes spaces after multiline path commands. Keep the
        # plotted geometry while making the checked-in SVG diff-clean.
        destination.write_text(
            "\n".join(line.rstrip() for line in destination.read_text().splitlines()) + "\n"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Choose a new figure output")
    render(args.archive, args.output)
