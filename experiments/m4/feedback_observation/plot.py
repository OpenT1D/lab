"""Original figure from checked synthetic observations; no kinetic rerun."""

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .common import read, source
from .report import reconstruct


def render(directory, output, *, allow_pending=False):
    directory, output = Path(directory), Path(output)
    if output.exists():
        raise FileExistsError(output)
    if not reconstruct(directory, allow_pending=allow_pending)["passed"]:
        raise ValueError("Cannot plot an incomplete observation matrix as accepted evidence")
    matplotlib.rcParams.update({"svg.hashsalt": "bc010-observation", "font.size": 10})
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), layout="constrained")
    fig.suptitle(
        "BC-010 · C-peptide observes pancreatic feedback secretion\n"
        "Synthetic 30 g gastric load · Nominal fixed kinetics · No human validation"
    )
    for variant, label, color in (
        ("fixed", "BC-008 fixed", "#555555"),
        ("extraction", "Variable extraction", "#009E73"),
        ("portal", "Portal EGP", "#0072B2"),
        ("both", "Both relations", "#D55E00"),
    ):
        name = f"gastric_load_30g--feedback_full--{variant}"
        data = read(directory / "cases" / (name + ".json"))
        parent = source(directory, name)
        b, y = data["boundary"], data["states"]["reference"]
        t, v = b["times"], b["parameters"]["volume_l_kg"]
        axes[0, 0].plot(t, [r[0] for r in parent["source_rates"]], color=color, label=label)
        axes[0, 1].plot(t, [r[0] / v for r in y], color=color)
        wrong = data["diagnostics"]["liver_fault"]["states"]
        axes[1, 0].plot(t, [(a[0] - r[0]) / v for a, r in zip(wrong, y)], color=color)
        axes[1, 1].plot(
            t,
            [
                abs(a[0] - r[0]) / v
                for a, r in zip(data["diagnostics"]["sampling_0.5"]["states"], y)
            ],
            color=color,
        )
    axes[0, 0].set(title="Pancreatic appearance Spo", ylabel="Rate [pmol/(kg min)]")
    axes[0, 0].legend(fontsize=8)
    axes[0, 1].set(title="Forward C-peptide concentration", ylabel="C-peptide [pmol/L]")
    axes[1, 0].set(
        title="Wrong liver inlet minus pancreatic inlet", ylabel="Concentration difference [pmol/L]"
    )
    axes[1, 1].set(
        title="0.5 versus 0.25 min source samples", ylabel="Absolute difference [pmol/L]"
    )
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
