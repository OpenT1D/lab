"""Render checked BC-003 artifacts; never integrate a model while plotting."""

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .report import reconstruct, table


def render(directory, output, *, allow_pending=False):
    directory, output = Path(directory), Path(output)
    if output.exists():
        raise FileExistsError(output)
    report = reconstruct(directory, allow_pending=allow_pending)
    if not report["passed"]:
        raise ValueError("Cannot plot failed reference")
    with plt.rc_context({"svg.hashsalt": "bc003", "font.size": 10}):
        fig, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
        for profile, label, color in (
            ("normal_mean", "Normal nominal", "#186a8b"),
            ("t1d_mean", "T1D nominal", "#a34f21"),
        ):
            for col, case in enumerate(("bolus", "step")):
                rows = table(directory / f"{profile}--{case}.csv")
                axes[0, col].plot(
                    [r["time_min"] for r in rows],
                    [r["cpeptide_pmol_l"] for r in rows],
                    label=label,
                    color=color,
                )
                if case == "step" and profile == "t1d_mean":
                    axes[0, col].plot(
                        [r["time_min"] for r in rows],
                        [r["one_compartment_pmol_l"] for r in rows],
                        "--",
                        color="#777777",
                        label="T1D single compartment",
                    )
        axes[0, 0].set_title("Synthetic normalized bolus: 100 pmol/kg")
        axes[0, 1].set_title("Published stimulus: 3 → 30 pmol/(kg min) at 120 min")
        axes[0, 1].axvline(120, color="#777777", linewidth=0.7)
        rows = table(directory / "t1d_mean--basal_pulse.csv")
        times = [r["time_min"] for r in rows]
        ax = axes[1, 0]
        ax.plot(times, [r["cpeptide_pmol_l"] for r in rows], label="Total", color="#a34f21")
        ax.plot(
            times,
            [r["cpeptide_pmol_l"] - rows[0]["cpeptide_pmol_l"] for r in rows],
            label="Above initial baseline",
            color="#186a8b",
        )
        ax.set_title("Synthetic pulse: nominal T1D kinetics")
        right = ax.twinx()
        right.step(
            times,
            [r["input_pmol_kg_min"] for r in rows],
            where="post",
            color="#555555",
            linestyle=":",
            label="Appearance rate",
        )
        right.set_ylabel("Appearance [pmol/(kg min)]")
        right.set_ylim(0, 25)
        for ax in (axes[0, 0], axes[0, 1], axes[1, 0]):
            ax.set(xlabel="Time [min]", ylabel="C-peptide [pmol/L]")
            ax.grid(alpha=0.2)
            ax.legend(fontsize=8, loc="upper right")
        axes[1, 0].legend(fontsize=8, loc="upper right", bbox_to_anchor=(1, 0.87))
        right.legend(fontsize=8, loc="upper right")
        ax = axes[1, 1]
        for name, label in (
            ("full_known_input", "30 times, known dose"),
            ("early_known_input", "Early only, known dose"),
            ("sparse_known_input", "3 times, known dose"),
            ("full_unknown_amplitude", "30 times, unknown dose"),
        ):
            design = report["identifiability"]["designs"][name]
            values = design["singular_values_pmol_l"]
            ax.semilogy(
                range(1, len(values) + 1),
                [max(v / values[0], 1e-16) for v in values],
                "o-",
                label=f"{label} (rank {design['rank']})",
                markersize=3,
            )
        ax.axhline(1e-8, color="#777777", linestyle=":", label="Declared rank threshold")
        ax.set(
            title="Noiseless local sensitivity spectrum",
            xlabel="Singular value index",
            ylabel="Singular value / largest",
            xticks=[1, 2, 3, 4, 5],
        )
        ax.legend(fontsize=8, loc="lower left")
        ax.grid(alpha=0.2)
        fig.suptitle(
            "BC-003 · Polonsky et al. (1986) kinetics · Synthetic / nominal profiles\n"
            "No patient-curve reproduction or clinical validation",
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
    args = parser.parse_args()
    render(args.directory, args.output)


if __name__ == "__main__":
    main()
