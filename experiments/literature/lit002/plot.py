"""Plot verified LIT-002 artifacts without executing a physiological model.

Use the separately locked LIT-001 plotting runtime. Study verification and report
reconstruction use the standard-library report module before any figures are made.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

if __package__:
    from . import report
else:
    import report

ARMS = ("cambridge_native", "cambridge_mean_matched", "faggionato_sc")
LABELS = {
    "cambridge_native": "Original Cambridge",
    "cambridge_mean_matched": "Cambridge · mean time matched",
    "faggionato_sc": "Cambridge · experimental SC replacement",
}
COLORS = {
    "cambridge_native": "#234E70",
    "cambridge_mean_matched": "#C17C22",
    "faggionato_sc": "#007F78",
}
STYLES = {"cambridge_native": "-", "cambridge_mean_matched": "--", "faggionato_sc": "-."}
SCENARIOS = ("basal", "pulse", "meal_pulse")
TITLES = {
    "basal": "Constant basal",
    "pulse": "Basal + finite insulin pulse",
    "meal_pulse": "Basal + pulse + meal",
}


def load_impulse(study: Path) -> dict[str, list[dict]]:
    """Read the sealed illustration as recorded, without recalculating a curve."""
    rows = {arm: [] for arm in ARMS}
    with (study / "impulse.csv").open(newline="") as stream:
        for source in csv.DictReader(stream):
            arm = source.pop("arm")
            if arm not in rows:
                raise ValueError(f"Unexpected impulse arm: {arm}")
            converted = {key: float(value) for key, value in source.items()}
            if not all(math.isfinite(value) for value in converted.values()):
                raise ValueError("Nonfinite impulse plot input")
            rows[arm].append(converted)
    for arm, values in rows.items():
        if not values or any(
            right["time_min"] <= left["time_min"] for left, right in zip(values, values[1:])
        ):
            raise ValueError(f"Missing or non-increasing impulse plot input: {arm}")
    return rows


def legend(figure) -> None:
    handles = [
        Line2D([], [], color=COLORS[arm], linestyle=STYLES[arm], linewidth=2.3, label=LABELS[arm])
        for arm in ARMS
    ]
    figure.legend(
        handles=handles,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.92),
        ncol=3,
        frameon=False,
        fontsize=10,
        handlelength=3,
        columnspacing=2,
    )


def decorate(axis, horizon: float) -> None:
    axis.set_xlim(0, horizon)
    axis.set_xlabel("Elapsed time (min)")
    axis.spines[["top", "right"]].set_visible(False)
    axis.grid(axis="y", color="#DEE3E8", linewidth=0.7)
    axis.set_axisbelow(True)
    axis.tick_params(colors="#46525D", labelsize=9)


def save(figure, output: Path, stem: str) -> None:
    for extension in ("svg", "png"):
        figure.savefig(
            output / f"{stem}.{extension}",
            dpi=180,
            facecolor="white",
            metadata={"Creator" if extension == "svg" else "Software": "OpenT1D LIT-002"},
        )
    plt.close(figure)


def absorption_figure(study: Path, output: Path) -> None:
    rows = load_impulse(study)
    figure, axes = plt.subplots(1, 3, figsize=(14, 5))
    figure.subplots_adjust(left=0.075, right=0.98, bottom=0.25, top=0.73, wspace=0.33)
    figure.suptitle("Subcutaneous absorption · synthetic impulse", x=0.5, y=0.99, fontsize=17)
    legend(figure)
    panels = (
        ("appearance_mU_per_kg_min", 1, "Appearance in blood", "Insulin appearance (mU/kg/min)"),
        ("cumulative_fraction", 100, "Cumulative appearance", "Delivered amount (%)"),
        ("unabsorbed_fraction", 100, "Insulin still subcutaneous", "Delivered amount (%)"),
    )
    horizon = max(values[-1]["time_min"] for values in rows.values())
    for axis, (field, scale, title, ylabel) in zip(axes, panels):
        for arm, values in rows.items():
            axis.plot(
                [row["time_min"] for row in values],
                [row[field] * scale for row in values],
                color=COLORS[arm],
                linestyle=STYLES[arm],
                linewidth=2.1,
            )
        decorate(axis, horizon)
        axis.set_ylim(bottom=0)
        if scale == 100:
            axis.set_ylim(0, 102)
        axis.set_title(title, fontsize=12, pad=12)
        axis.set_ylabel(ylabel, fontsize=10)
    figure.text(
        0.075,
        0.095,
        "Ideal impulse: 200 mU/kg at t = 0; zero prior insulin. Remaining subcutaneous insulin "
        "includes the experimental input-delay reservoir.\n"
        "These are model calculations from recorded artifacts. The finite-pulse native experiment "
        "uses a separate schedule and basal prehistory.",
        fontsize=9,
        color="#46525D",
        linespacing=1.65,
    )
    save(figure, output, "absorption")


def coupled_figure(study: Path, output: Path, manifest: dict) -> None:
    selected = {}
    for case in manifest["cases"]:
        if case["resolution"] != "standard":
            continue
        key = (case["scenario"], case["arm"])
        if key in selected:
            raise ValueError(f"Duplicate standard case: {key}")
        selected[key] = case
    traces = {}
    unavailable = []
    for scenario in SCENARIOS:
        for arm in ARMS:
            case = selected.get((scenario, arm))
            if not case or case["status"] != "completed":
                unavailable.append(f"{scenario}/{arm}")
                continue
            path = (study / case["path"] / "trace.jsonl").resolve()
            if not path.is_relative_to(study.resolve()):
                raise ValueError("Case trace must stay inside the verified study")
            traces[(scenario, arm)] = [json.loads(line) for line in path.read_text().splitlines()]
    figure, axes = plt.subplots(2, 3, figsize=(14, 8), sharex=True, sharey="row")
    figure.subplots_adjust(left=0.075, right=0.98, bottom=0.205, top=0.78, wspace=0.15, hspace=0.22)
    figure.suptitle("Native Cambridge · synthetic absorption sensitivity", y=0.99, fontsize=17)
    legend(figure)
    fields = (
        ("insulin_mU_L", "Plasma insulin (mU/L)"),
        ("glucose_mg_dl", "Plasma glucose (mg/dL)"),
    )
    for column, scenario in enumerate(SCENARIOS):
        for row_index, (field, ylabel) in enumerate(fields):
            axis = axes[row_index, column]
            horizons = []
            missing = []
            for arm in ARMS:
                values = traces.get((scenario, arm))
                if not values:
                    missing.append(LABELS[arm])
                    continue
                horizons.append(values[-1]["time_min"])
                axis.plot(
                    [value["time_min"] for value in values],
                    [value[field] for value in values],
                    color=COLORS[arm],
                    linestyle=STYLES[arm],
                    linewidth=2.1,
                )
            decorate(axis, max(horizons, default=720))
            if row_index == 0:
                axis.set_xlabel("")
                axis.set_title(TITLES[scenario], fontsize=12, pad=12)
            if column == 0:
                axis.set_ylabel(ylabel, fontsize=11)
            if scenario != "basal":
                axis.axvspan(120, 125, color="#59656F", alpha=0.13, linewidth=0)
                if scenario == "meal_pulse":
                    axis.axvspan(
                        120, 135, ymin=0, ymax=0.035, color="#59656F", alpha=0.3, linewidth=0
                    )
            if missing:
                axis.text(
                    0.98,
                    0.97,
                    "Unavailable:\n" + "\n".join(missing),
                    transform=axis.transAxes,
                    ha="right",
                    va="top",
                    fontsize=8,
                    color="#8E3940",
                )
    for row_index, (field, _) in enumerate(fields):
        values = [point[field] for trace in traces.values() for point in trace]
        if values:
            low, high = min(values), max(values)
            margin = max((high - low) * 0.09, 1 if row_index == 0 else 5)
            axes[row_index, 0].set_ylim(max(0, low - margin), high + margin)
    caption = (
        "Identical basal delivery and native plasma/action/glucose equilibrium across arms; "
        "each absorption system has its own steady depots.\n"
        "Pulse: 2 U delivered over minutes 120–125 (shaded). Meal: 40 g over minutes 120–135 "
        "(bottom bar). Standard 0.25 min maximum integration interval.\n"
        "The experimental arm replaces absorption only; native clearance and glucose equations "
        "remain. These synthetic differences do not establish clinical accuracy."
    )
    if unavailable:
        caption += (
            f"\n{len(unavailable)} standard case(s) unavailable; "
            "missing curves are not interpolated."
        )
    figure.text(0.075, 0.045, caption, fontsize=9, color="#46525D", linespacing=1.65)
    save(figure, output, "coupled")


def render(study: Path, output: Path) -> None:
    """Verify the seal first; create only new plots from recorded artifacts."""
    report.reconstruct(study)
    manifest = json.loads((study / "manifest.json").read_text())
    if "impulse.csv" not in manifest["artifacts"]:
        raise ValueError("The impulse illustration must be part of the verified artifact seal")
    if output.exists():
        raise FileExistsError("Choose a new output directory to preserve prior figures")
    output.mkdir(parents=True)
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "svg.fonttype": "none",
            "axes.labelcolor": "#25313B",
            "text.color": "#25313B",
        }
    )
    absorption_figure(study, output)
    coupled_figure(study, output, manifest)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    render(arguments.study.resolve(), arguments.output.resolve())
