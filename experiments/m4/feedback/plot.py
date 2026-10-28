"""Scientific figure regenerated from checked BC-008 data."""

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
        raise ValueError("Unverified archive cannot support a passing figure")
    params = read(directory / "native.json")["parameters"]
    p = read(directory / "protocol.json")
    matplotlib.rcParams.update({"svg.hashsalt": "bc008-feedback", "font.size": 10})
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), layout="constrained")
    fig.suptitle(
        "BC-008 · Glucose-responsive secretion in one synthetic metabolic route\n"
        "30 g initial gastric load; no meal bolus · Not human or therapy validation"
    )
    colors = ["#555555", "#999999", "#009E73", "#0072B2", "#D55E00", "#CC79A7"]
    for name, color in zip([c["id"] for c in p["cases"]] + ["equal-arrival"], colors):
        data = read(directory / "gastric_load_30g" / f"{name}-reference.json")
        t, y = data["times"], data["states"]
        for ax, col, scale in ((axes[0, 0], 3, params["Vg"]), (axes[0, 1], 5, params["Vi"])):
            ax.plot(t, [row[col] / scale for row in y], color=color, label=name.replace("_", " "))
        axes[1, 0].plot(t, [row[1] for row in data["source_rates"]], color=color)
    parent = read(directory / "gastric_load_30g" / "feedback_full-reference.json")
    for step in p["refinement"]["replay_sample_steps_min"]:
        data = read(directory / "gastric_load_30g" / f"replay-{step}.json")
        axes[1, 1].plot(
            data["times"],
            [(a[3] - b[3]) / params["Vg"] for a, b in zip(data["states"], parent["states"])],
            label=f"{step} min",
        )
    axes[0, 0].set(title="Plasma glucose", ylabel="Glucose [mg/dL]")
    axes[0, 0].legend(fontsize=8)
    axes[0, 1].set(title="Plasma insulin", ylabel="Insulin [pmol/L]")
    axes[1, 0].set(title="Liver arrival S (after portal transit)", ylabel="Rate [pmol/(kg min)]")
    axes[1, 1].set(
        title="Prescribed replay minus full feedback", ylabel="Glucose difference [mg/dL]"
    )
    axes[1, 1].legend(fontsize=8)
    for ax in axes.flat:
        ax.set_xlabel("Time [min]")
        ax.grid(alpha=0.2)
    fig.savefig(output, metadata={"Date": None} if output.suffix == ".svg" else None)
    plt.close(fig)
    if output.suffix == ".svg":
        output.write_text(
            "\n".join(line.rstrip() for line in output.read_text().splitlines()) + "\n"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--allow-pending", action="store_true")
    args = parser.parse_args()
    render(args.directory, args.output, allow_pending=args.allow_pending)
