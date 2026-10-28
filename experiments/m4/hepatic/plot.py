"""Original scientific figure from checked BC-009 artifacts."""

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
        raise ValueError("Incomplete comparison cannot support a passing figure")
    params = read(directory / "native.json")["parameters"]
    matplotlib.rcParams.update({"svg.hashsalt": "bc009-hepatic", "font.size": 10})
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), layout="constrained")
    fig.suptitle(
        "BC-009 · Two hepatic assumptions, matched initial conditions\n"
        "Full secretory response · Synthetic 30 g gastric load · No biological validation"
    )
    for variant, label, color in (
        ("fixed", "BC-008 fixed", "#555555"),
        ("extraction", "Variable extraction", "#009E73"),
        ("portal", "Portal EGP term", "#0072B2"),
        ("both", "Both relations", "#D55E00"),
    ):
        data = read(
            directory / "cases" / f"gastric_load_30g--feedback_full--{variant}--reference.json"
        )
        t, y, h = data["times"], data["states"], data["hepatic"]
        axes[0, 0].plot(t, [x[3] / params["Vg"] for x in y], color=color, label=label)
        axes[0, 1].plot(t, [x[5] / params["Vi"] for x in y], color=color)
        axes[1, 0].plot(t, [x["HE"] for x in h], color=color)
        axes[1, 1].plot(t, [x["EGP"] for x in h], color=color)
    axes[0, 0].set(title="Plasma glucose", ylabel="Glucose [mg/dL]")
    axes[0, 0].legend(fontsize=8)
    axes[0, 1].set(title="Plasma insulin", ylabel="Insulin [pmol/L]")
    axes[1, 0].set(title="Hepatic extraction fraction", ylabel="HE [dimensionless]")
    axes[1, 1].set(title="Endogenous glucose production", ylabel="EGP [mg/(kg min)]")
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
