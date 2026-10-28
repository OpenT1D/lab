"""Profile every nuisance coordinate, refine crossings and retain all starts."""

from experiments.m4.volume_sensitivity.common import specifications as parent_cases
from experiments.m4.volume_sensitivity.inference import fit_case as parent_fit

from .common import best, profile_starts, selection
from .optimizer import Problem, solve


def run_case(model, p, spec, observations, checkpoint=None):
    design = p["designs"][spec["design"]]
    selected = selection(p, spec)
    result = {
        **spec,
        "selection": selected,
        "observed": [observations["datasets"][spec["data"]][i // 3][i % 3] for i in selected],
        "sd": [p["observation"]["synthetic_sd"][i % 3] for i in selected],
        "baseline": {"fit": [], "reference": [], "parent_unprojected": None},
        "profiles": [],
    }

    def save():
        if checkpoint:
            checkpoint(result)

    def fit_all(problem, starts, interest, records):
        for start in starts:
            records.append(solve(problem, start, interest))
            save()
        return best(records)

    problems = {
        solver: Problem(model, observations, design, p, solver=solver, data=spec["data"])
        for solver in ("fit", "reference")
    }
    for solver in problems:
        fit_all(
            problems[solver],
            p["inference"]["unrestricted_starts"],
            None,
            result["baseline"][solver],
        )
    baseline = best(result["baseline"]["fit"])
    if spec["design"] == "free_volume":
        parent_spec = next(
            s
            for s in parent_cases(model.protocol)
            if s["regime"] == "estimated_rates"
            and s["arm"] == "estimated"
            and s["step"] == p["observation"]["step_min"]
            and s["data"] == spec["data"]
        )

        def parent_checkpoint(records):
            result["baseline"]["parent_unprojected"] = {**parent_spec, "fits": records}
            save()

        result["baseline"]["parent_unprojected"] = parent_fit(
            model, parent_spec, observations, checkpoint=parent_checkpoint
        )
        save()

    for parameter in design["profiled"]:
        estimate = baseline["evaluated_parameters"][parameter]
        coarse = sorted(set(p["profiles"]["coarse_grid"] + [estimate]))
        values = sorted(set(coarse + p["profiles"]["refinement_grid"]))
        profile = {
            "parameter": parameter,
            "coarse_values": coarse,
            "initial_values": values,
            "points": [],
            "crossings": [],
            "reference_checks": [],
        }
        result["profiles"].append(profile)
        points = {}
        starts = profile_starts(p, spec, baseline, parameter)

        def point(value, stage):
            if value not in points:
                record = {"value": value, "stage": stage, "fits": []}
                points[value] = record
                profile["points"].append(record)
                fit_all(problems["fit"], starts, (parameter, value), record["fits"])
                # Deliberately keep *all* nuisance values at the unrestricted best.
                theta = list(baseline["evaluated_parameters"])
                theta[parameter] = value
                record["slice"] = problems["fit"].evaluate(theta)
                save()
            return points[value]

        def inside(value):
            return (
                best(points[value]["fits"])["objective"] - baseline["objective"]
                <= p["profiles"]["cutoff"]
            )

        for value in values:
            stage = (
                "coarse"
                if value in p["profiles"]["coarse_grid"]
                else "grid_refinement"
                if value in p["profiles"]["refinement_grid"]
                else "estimate"
            )
            point(value, stage)
        for left, right in zip(values, values[1:]):
            if inside(left) == inside(right):
                continue
            crossing = {"initial_bracket": [left, right], "history": [], "bracket": [left, right]}
            profile["crossings"].append(crossing)
            for _ in range(12):
                if right - left <= p["criteria"]["crossing_max_width"]:
                    break
                middle = (left + right) / 2
                crossing["history"].append({"bracket": [left, right], "midpoint": middle})
                point(middle, "crossing_refinement")
                if inside(middle) == inside(left):
                    left = middle
                else:
                    right = middle
                crossing["bracket"] = [left, right]
                save()
            if right - left > p["criteria"]["crossing_max_width"]:
                raise RuntimeError("Crossing refinement incomplete; retain the partial profile")
        check_values = sorted(
            {
                p["model"]["lower"][parameter],
                p["model"]["upper"][parameter],
                *(v for crossing in profile["crossings"] for v in crossing["bracket"]),
            }
        )
        for value in check_values:
            check = {"value": value, "fits": []}
            profile["reference_checks"].append(check)
            fit_all(problems["reference"], starts, (parameter, value), check["fits"])
            theta = best(points[value]["fits"])["evaluated_parameters"]
            check["at_fit_best"] = problems["reference"].evaluate(theta)
            save()
        profile["points"].sort(key=lambda item: item["value"])
        save()
    return result
