"""Task-owned selectors and saved endpoints; no estimator or supplied model runs."""

from experiments.m4.initial_load.analysis import contrast
from experiments.m4.initial_load.common import SCENARIOS
from experiments.mmtt_sampling.comparison import finite_or_missing
from experiments.mmtt_sampling.report import conditional_direction, point_value

from .store import read, require

TASKS = {"mmtt-sensitivity", "mmtt-sampling", "m4-study-installed"}
SIGNALS = {"glucose": "mg/dL", "insulin": "pmol/L", "cpeptide": "pmol/L"}


def plan_data(project, identity):
    project.require_lease()
    require(isinstance(identity, str) and identity in project.plans, "Unknown comparison plan")
    descriptor, folder = project.plans[identity]
    task = descriptor["task"]
    require(task in TASKS, "Unsupported comparison task")
    if task == "m4-study-installed":
        config = read(folder / "input/config.json")
        options = [
            {
                "selector": {"source": source["id"], "scenario": scenario},
                "label": f"{source['id']} / {scenario}",
            }
            for source in config["sources"]
            for scenario in config["scenarios"]
        ]
        support = {
            "task": task,
            "window_min": [0, 240],
            "step_min": 0.25,
            "signals": SIGNALS,
            "population": "adult#001",
        }
        scientific = {"configuration": config}
    else:
        frozen = read(folder / "input/plan.json")
        package = read(folder / "original/package.json")
        settings = frozen["settings"]
        variants = [item["id"] for item in settings["variants"]]
        options = [{"selector": {"variant": variant}, "label": variant} for variant in variants]
        if task == "mmtt-sampling":
            design = frozen["design"]
            schedules = {"full": design["full_times_minutes"], **design["subsets"]}
            options = [
                {
                    "selector": {"schedule": schedule, "variant": variant},
                    "label": f"{schedule} / {variant}",
                }
                for schedule in schedules
                for variant in variants
            ]
        support = {
            "task": task,
            "window_min": [0, 120],
            "unit": "pmol",
            "quantity": "whole-body secretion including basal",
            "paired_contrast": "followup minus baseline",
            "visit_order": settings["visit_order"],
            "package_sha256": descriptor["original_sha256"]["package.json"],
            "observations_sha256": descriptor["original_sha256"]["observations.csv"],
            "participants": [
                {"id": person["id"], "allocation": person["allocation"]}
                for person in package["participants"]
            ],
        }
        scientific = {"settings": settings}
        if task == "mmtt-sampling":
            support["development_manifest_sha256"] = frozen["development_manifest_sha256"]
            scientific["design"] = frozen["design"]
    return {
        "plan": identity,
        "task": task,
        "options": options,
        "support": support,
        "scientific": scientific,
        "binding": descriptor["boundary"]["binding"],
        "reader": descriptor["reader"],
    }


def selected(project, member):
    info = plan_data(project, member["plan"])
    require(
        any(member["selector"] == item["selector"] for item in info["options"]),
        "Selector is not present in this frozen plan",
    )
    return info


def scientific_view(info, selector):
    view = {**info["scientific"], "selector": selector}
    if info["task"] == "m4-study-installed":
        source = selector["source"]
        view["selected_source"] = {"id": source, **info["binding"]["source_sha256"][source]}
        view["selected_load"] = {
            "scenario": selector["scenario"],
            "initial_gastric_solid_mg": SCENARIOS[selector["scenario"]],
        }
    else:
        view["selected_assumptions"] = next(
            v for v in info["scientific"]["settings"]["variants"] if v["id"] == selector["variant"]
        )
        if info["task"] == "mmtt-sampling":
            design = info["scientific"]["design"]
            view["selected_times_minutes"] = {
                "full": design["full_times_minutes"],
                **design["subsets"],
            }[selector["schedule"]]
    return view


def mmtt_rows(info, member, directory, reason):
    native = None
    if directory is not None:
        filename = directory / "report.json"
        if info["task"] == "mmtt-sampling":
            filename = directory / "studies" / member["selector"]["schedule"] / "report.json"
        if filename.exists():
            native = read(filename)
    rows = []
    variant = member["selector"]["variant"]
    for person in info["support"]["participants"]:
        data = None if native is None else native.get("people", {}).get(person["id"])
        if native and native.get("import_errors"):
            data = None
        value = None if data is None else data["variants"][variant]
        for visit in [*info["support"]["visit_order"], None]:
            point = finite_or_missing(point_value(data, variant, visit))
            complete = value is not None and value["status"] == "complete"
            interval = (
                None
                if not complete
                else (
                    value["conditional_interval_pmol"]
                    if visit is None
                    else value["visit_intervals_pmol"][visit]
                )
            )
            if interval is not None:
                require(len(interval) == 2, "Native interval support differs")
                interval = [finite_or_missing(x) for x in interval]
                require(
                    None not in interval and interval[0] <= interval[1], "Native interval invalid"
                )
            rows.append(
                {
                    "case": person["id"],
                    "allocation": person["allocation"],
                    "endpoint": "paired_change" if visit is None else "visit_total:" + visit,
                    "unit": "pmol",
                    "value": point,
                    "interval": interval,
                    "direction": conditional_direction(data, variant) if visit is None else None,
                    "status": "complete"
                    if complete
                    else "incomplete"
                    if point is not None
                    else "unavailable",
                    "reason": None
                    if complete
                    else reason or "Native point/required uncertainty incomplete",
                    "native_variant_status": None if value is None else value["status"],
                }
            )
    return rows


def m4_curve(member, directory):
    if directory is None:
        return None
    native = read(directory / "report.json")
    source = native["sources"][member["selector"]["source"]]
    scenario = member["selector"]["scenario"]
    if not (
        source["accepted"]
        and native["reference"]["accepted"]
        and native["common_controls"]["passed"]
        and source["scenarios"][scenario]["accepted"]
    ):
        return None
    curve = source["curves"][scenario]["candidate"]
    contrast(curve, curve)  # The native contrast validates the complete finite grid.
    return curve


def m4_rows(curve, baseline, reason):
    metrics = None if curve is None or baseline is None else contrast(curve, baseline)
    return [
        {
            "case": "adult#001",
            "allocation": "synthetic",
            "endpoint": signal,
            "unit": unit,
            "value": None,
            "interval": None,
            "direction": None,
            "status": "complete" if metrics is not None else "unavailable",
            "reason": None
            if metrics is not None
            else reason or "Entire native source/reference/control acceptance required",
            "metrics": None if metrics is None else metrics[signal],
            "metric_units": {
                "signed_auc_difference": unit + " × min",
                "signed_time_mean_difference": unit,
                "maximum_absolute_pointwise_difference": unit,
            },
        }
        for signal, unit in SIGNALS.items()
    ]
