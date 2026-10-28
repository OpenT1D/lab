"""Reassess archived numerical evidence using the standard library only."""

import argparse
import math
import sys
from pathlib import Path
from types import SimpleNamespace

from experiments.m4.kinetic_inlet.forcing import Forcing
from experiments.m4.paired_kinetics.report import matrix, maxdiff

from . import preflight, source_oracle
from .common import (
    VERSION,
    digest,
    dump,
    numerical_files,
    read,
    required_files,
    validate_source_cases,
    verify_files,
)
from .contract import baseline, number, validate


def difference(a, b, column, scale=1):
    return max(abs(x[column] - y[column]) / scale for x, y in zip(a, b, strict=True))


def outcomes(times, states, vg):
    glucose = [x[3] / vg for x in states]
    return {
        "auc_above_initial_mg_min_dl": math.fsum(
            (b - a) * (x + y - 2 * glucose[0]) / 2
            for a, b, x, y in zip(times, times[1:], glucose, glucose[1:])
        ),
        "peak_mg_dl": max(glucose),
        "nadir_mg_dl": min(glucose),
        "final_mg_dl": glucose[-1],
    }


def inspect_trajectory(data, p, params, expected_initial=None):
    step, horizon = p["sample_step_min"], p["horizon_min"]
    times = [i * step for i in range(round(horizon / step) + 1)]
    if data["status"] != "completed" or data["failure"] is not None or data["times"] != times:
        raise ValueError("Incomplete/failed trajectory cannot support scenario contrasts")
    y = matrix(data["states"], len(times), 20)
    rates = matrix(data["source_rates"], len(times), 2)
    flux = matrix(data["glucose_flux_integrals"], len(times), 5)
    if y[0] != data["initial"] or (expected_initial is not None and y[0] != expected_initial):
        raise ValueError("Wrong initial state")
    if any(y[0][15:]) or any(flux[0]):
        raise ValueError("Nonzero initial cumulative flux")
    errors = data["glucose_quadrature_error_bounds"]
    if len(errors) != len(times) or any(number(e) > 1e-6 for e in errors):
        raise ValueError("Unverified glucose quadrature")
    if data["quadrature"] != {
        "method": "quad_vec",
        "epsabs": 1e-9,
        "epsrel": 1e-9,
        "norm": "max",
        "flux_order": ["EGP", "Ra", "Uii", "Uid", "renal"],
    }:
        raise ValueError("Changed quadrature specification")
    active = data["source_active"]
    indices = [5, 9, 10, 11] + ([14] if active else [])
    inventory0 = math.fsum(y[0][i] for i in indices)
    mass = max(
        abs(
            math.fsum(row[i] for i in indices)
            - inventory0
            - row[15]
            - row[16 if active else 17]
            + row[18]
            + row[19]
        )
        for row in y
    )
    portal = max(abs(row[14] - y[0][14] - row[16] + row[17]) for row in y) if active else 0
    glucose = max(
        abs(row[3] + row[4] - y[0][3] - y[0][4] - f[0] - f[1] + f[2] + f[3] + f[4])
        for row, f in zip(y, flux, strict=True)
    )
    physical = [i for i in range(15) if i != 6]
    negative = max(0, -min(row[i] for row in y for i in physical))
    # Transfer inlet can never share pancreatic and liver flux as two inputs.
    if active:
        sp = data["source_parameters"]
        expected = []
        for row in y:
            gp = row[3]
            gd = (
                max(params["kp1"] - params["kp2"] * gp - params["kp3"] * row[8], 0)
                + params["f"] * params["kabs"] * row[2] / params["BW"]
                - params["Fsnc"]
                - params["ke1"] * max(gp - params["ke2"], 0)
                - params["k1"] * gp
                + params["k2"] * row[4]
            ) / params["Vg"]
            expected.append([row[13] + sp["gain"] * sp["K"] * max(gd, 0), sp["gamma"] * row[14]])
        if maxdiff(expected, rates) > 1e-10:
            raise ValueError("Source output differs from recorded state boundary")
    else:
        if any(row[13] or row[14] or row[16] for row in y):
            raise ValueError("Unused source inventory included in a derived control")
        if "forcing" in data:
            force = Forcing(**data["forcing"])
            if abs(force.integral() - data["transferred_amount_pmol_kg"]) > 1e-10:
                raise ValueError("Wrong transferred amount")
            if max(abs(q[1] - force.evaluate(t)) for t, q in zip(times, rates)) > 1e-10:
                raise ValueError("Control inlet does not match its forcing")
    sc = data["baseline"]["u_sc_pmol_kg_min"]
    if max(abs(row[15] - t * sc) for t, row in zip(times, y)) > 1e-7:
        raise ValueError("SC unit conversion or input ledger mismatch")
    lo, hi = p["glucose_envelope_mg_dl"]
    if any(not lo <= row[3] / params["Vg"] <= hi for row in y):
        raise ValueError("Glucose outside prespecified envelope")
    return {
        "insulin_mass_error": max(mass, portal),
        "glucose_mass_error": glucose,
        "negative": negative,
        "quadrature_bound": max(errors),
        "outcomes": outcomes(times, y, params["Vg"]),
        "pancreatic_amount_pmol_kg": y[-1][16],
        "liver_arrival_pmol_kg": y[-1][17],
    }


def reconstruct(directory, *, allow_pending=False, allow_failed=False):
    directory = Path(directory)
    p, manifest = read(directory / "protocol.json"), read(directory / "manifest.json")
    validate(p)
    statuses = {"completed"}
    if allow_pending:
        statuses.add("calculated")
    if allow_failed:
        statuses.add("failed")
    if manifest["schema"] != VERSION or manifest["status"] not in statuses:
        raise ValueError("Incomplete BC-008 archive")
    # A failure report never fabricates missing 240-minute contrasts. Hash-check
    # what exists, list missing evidence and preserve explicit terminal records.
    verify_files(directory, manifest, {"protocol.json", "source-cases.json"})
    failures = {}
    for name in sorted(manifest["files"]):
        if name.endswith(".json") and name.split("/")[0] in {s["id"] for s in p["scenarios"]}:
            item = read(directory / name)
            if item.get("status") == "failed" or "reason" in item:
                failures[name] = item.get("failure", item)
    missing = sorted(required_files(p) - manifest["files"].keys())
    if failures or (manifest["status"] == "failed" and missing):
        return {
            "schema": VERSION,
            "protocol": p["id"],
            "claim": p["claim"],
            "passed": False,
            "failures": failures,
            "missing_evidence": missing,
            "error": manifest.get("error"),
            "scenarios": {},
            "limitations": ["Incomplete execution; no scenario contrasts accepted"],
        }
    verify_files(directory, manifest, required_files(p))
    native = read(directory / "native.json")
    params = native["parameters"]
    prep = preflight.assess(p, read(directory / "probe.json"))
    if not prep["passed"] or prep != read(directory / "preflight.json"):
        raise ValueError("Preflight is not established")
    if native["identity"] != read(directory / "probe.json")["native_identity"]:
        raise ValueError("Native identity differs from preflight")
    if native["runtime"] != read(directory / "probe.json")["runtime"]:
        raise ValueError("Numerical runtime differs from preflight")
    for key, value in read(directory / "probe.json")["parameters"].items():
        if params[key] != value:
            raise ValueError("Native parameters differ from preflight")
    metrics = dict.fromkeys(p["criteria"], 0.0)
    metrics.pop(
        "effect_to_numerical_uncertainty_ratio_min"
    )  # Per contrast, not an overall maximum.
    metrics["zero_extension_derivative_error"] = prep["metrics"]["zero_extension_error"]
    metrics["basal_derivative_change_max_native_units_per_min"] = prep["metrics"][
        "baseline_derivative_change"
    ]
    # A fresh numerical worker produced every data file again; paths and source
    # snapshots are outside this comparison. Fail on any changed numeric byte.
    changed = [
        name
        for name in sorted(numerical_files(p))
        if digest(directory / name) != digest(directory / "repeat" / name)
    ]
    metrics["repeat_error"] = 1.0 if changed else 0.0  # Binary exact-artifact discrepancy.
    source = read(directory / "source-reference.json")
    fixtures = read(directory / "source-cases.json")
    validate_source_cases(fixtures)
    if [c["id"] for c in source["cases"]] != [c["id"] for c in fixtures["cases"]]:
        raise ValueError("Incomplete source reference")
    for fixture, case in zip(fixtures["cases"], source["cases"], strict=True):
        coefficients = p["source"]["parameters"]
        expected_source = {
            "alpha": coefficients["alpha_per_min"],
            "beta": coefficients["beta_pmol_kg_min_per_mg_dl"],
            "K": coefficients["K_pmol_kg_per_mg_dl"],
            "gamma": fixture.get("gamma", coefficients["gamma_per_min"]),
            "basal": fixture.get("basal", fixtures["default_basal"]),
            "threshold": fixtures["default_threshold"],
            "gain": fixture.get("gain", fixtures["default_gain"]),
        }
        times = [
            i * fixtures["sample_step_min"]
            for i in range(round(fixture["times"][-1] / fixtures["sample_step_min"]) + 1)
        ]
        if case["parameters"] != expected_source or case["times"] != times:
            raise ValueError("Changed source reference conditions")
        signal = SimpleNamespace(
            edges=fixture["times"],
            left=fixture["glucose"][:-1],
            right=fixture["glucose"][1:],
            segments=len(fixture["times"]) - 1,
        )
        n = len(case["times"])
        exact = matrix(case["analytic"], n, 4)
        rebuilt = source_oracle.simulate(
            times, signal, fixture["initial"], SimpleNamespace(**expected_source)
        )
        if maxdiff(rebuilt, exact) != 0:
            raise ValueError("Saved analytic reference is not reconstructible")
        for name in ("tight", "reference"):
            actual = matrix(case["solutions"][name], n, 4)
            for key, column in (
                ("secretion_rate_closed_form_error_pmol_kg_min", 0),
                ("secretion_closed_form_error_pmol_kg", 1),
            ):
                metrics[key] = max(metrics[key], difference(actual, exact, column))
    scenarios = {}
    for scenario in p["scenarios"]:
        folder = directory / scenario["id"]
        records, assessments = {}, {}
        for case in p["cases"]:
            b = baseline(
                params,
                read(directory / "probe.json")["initial"],
                case["fraction"],
                p["source"]["parameters"]["gamma_per_min"],
            )
            expected = b["state"] + [b["Z_pmol_kg_min"], b["P_pmol_kg"]] + [0.0] * 5
            expected[0] = scenario["stomach_solid_mg"]
            records[case["id"]], assessments[case["id"]] = {}, {}
            for solver in p["solvers"]:
                name = solver["name"]
                data = read(folder / f"{case['id']}-{name}.json")
                if data["solver"] != solver or data["baseline"] != b or not data["source_active"]:
                    raise ValueError("Changed solver or baseline contract")
                source_parameters = p["source"]["parameters"]
                expected_source = {
                    "alpha": source_parameters["alpha_per_min"],
                    "beta": source_parameters["beta_pmol_kg_min_per_mg_dl"],
                    "K": source_parameters["K_pmol_kg_per_mg_dl"],
                    "gamma": source_parameters["gamma_per_min"],
                    "basal": b["Sb_pmol_kg_min"],
                    "threshold": b["h_mg_dl"],
                    "gain": case["gain"],
                }
                if (
                    data["source_parameters"] != expected_source
                    or data["load_mg"] != scenario["stomach_solid_mg"]
                ):
                    raise ValueError("Changed source coefficients or gastric load")
                records[case["id"]][name] = data
                assessments[case["id"]][name] = inspect_trajectory(data, p, params, expected)
            tight, ref = [records[case["id"]][n] for n in ("tight", "reference")]
            for key, column, scale in (
                ("glucose_solver_error_mg_dl", 3, params["Vg"]),
                ("insulin_solver_error_pmol_l", 5, params["Vi"]),
            ):
                metrics[key] = max(
                    metrics[key], difference(tight["states"], ref["states"], column, scale)
                )
            metrics["source_solver_error_pmol_kg_min"] = max(
                metrics["source_solver_error_pmol_kg_min"],
                maxdiff(tight["source_rates"], ref["source_rates"]),
            )
            for n in ("tight", "reference"):
                assessed = assessments[case["id"]][n]
                for key, item in (
                    ("insulin_mass_error_pmol_kg", "insulin_mass_error"),
                    ("glucose_mass_error_mg_kg", "glucose_mass_error"),
                    ("negative_amount_tolerance", "negative"),
                ):
                    metrics[key] = max(metrics[key], assessed[item])
            if scenario["id"] == "fasting":
                for key, column, scale in (
                    ("fasting_glucose_drift_mg_dl", 3, params["Vg"]),
                    ("fasting_insulin_drift_pmol_l", 5, params["Vi"]),
                ):
                    metrics[key] = max(
                        metrics[key],
                        max(
                            abs(row[column] - ref["states"][0][column]) / scale
                            for row in ref["states"]
                        ),
                    )
        original = read(folder / "native-class.json")
        padded = read(folder / "native-padded.json")
        inspect_trajectory(padded, p, params)
        zero = records["native_zero"]["reference"]
        if original["times"] != list(range(p["horizon_min"] + 1)):
            raise ValueError("Incomplete original native class trajectory")
        actual = matrix(original["states"], len(original["times"]), 13)
        sampled = zero["states"][:: round(1 / p["sample_step_min"])]
        for key, col, scale in (
            ("native_class_glucose_error_mg_dl", 3, params["Vg"]),
            ("native_class_insulin_error_pmol_l", 5, params["Vi"]),
        ):
            metrics[key] = max(metrics[key], difference(actual, sampled, col, scale))
        metrics["same_solver_zero_extension_state_error"] = max(
            metrics["same_solver_zero_extension_state_error"],
            maxdiff(zero["states"], padded["states"]),
        )
        metrics["basal_control_glucose_error_mg_dl"] = max(
            metrics["basal_control_glucose_error_mg_dl"],
            difference(
                zero["states"], records["constant_basal"]["reference"]["states"], 3, params["Vg"]
            ),
        )
        parent = records["feedback_full"]["reference"]
        replays = []
        for step in p["refinement"]["replay_sample_steps_min"]:
            data = read(folder / f"replay-{step}.json")
            control_initial = parent["initial"].copy()
            control_initial[13:15] = [0.0, 0.0]
            result = inspect_trajectory(data, p, params, control_initial)
            if data["solver"] != p["solvers"][-1] or data["sample_step_min"] != step:
                raise ValueError("Changed replay grid/solver")
            force = Forcing(**data["forcing"])
            expected_edges = [i * step for i in range(round(p["horizon_min"] / step) + 1)]
            if list(force.edges) != expected_edges or any(
                a != b for a, b in zip(force.right[:-1], force.left[1:])
            ):
                raise ValueError("Replay is not the declared continuous sampling grid")
            if (
                max(
                    abs(force.evaluate(t) - rate[1])
                    for t, rate in zip(parent["times"], parent["source_rates"], strict=True)
                )
                > 1e-12
            ):
                raise ValueError("Replay does not agree with its parent source samples")
            replays.append(
                {
                    "step_min": step,
                    "amount_pmol_kg": data["transferred_amount_pmol_kg"],
                    "glucose_error_mg_dl": difference(
                        data["states"], parent["states"], 3, params["Vg"]
                    ),
                    "insulin_error_pmol_l": difference(
                        data["states"], parent["states"], 5, params["Vi"]
                    ),
                    **result,
                }
            )
        for key, item in (
            ("fine_replay_glucose_error_mg_dl", "glucose_error_mg_dl"),
            ("fine_replay_insulin_error_pmol_l", "insulin_error_pmol_l"),
        ):
            metrics[key] = max(metrics[key], replays[-1][item])
        equals, equal_states = {}, {}
        for solver in p["solvers"]:
            data = read(folder / f"equal-arrival-{solver['name']}.json")
            equals[solver["name"]] = inspect_trajectory(data, p, params, control_initial)
            equal_states[solver["name"]] = data["states"]
            if data["solver"] != solver:
                raise ValueError("Changed equal-arrival solver")
            force = Forcing(**data["forcing"])
            mean = replays[-1]["amount_pmol_kg"] / p["horizon_min"]
            if force.to_dict() != Forcing([0, p["horizon_min"]], [mean], [mean]).to_dict():
                raise ValueError("Equal-arrival control is not the prescribed constant")
            metrics["equal_arrival_relative_error"] = max(
                metrics["equal_arrival_relative_error"],
                abs(data["states"][-1][17] - replays[-1]["amount_pmol_kg"])
                / max(replays[-1]["amount_pmol_kg"], sys.float_info.min),
            )
        for key, col, scale in (
            ("glucose_solver_error_mg_dl", 3, params["Vg"]),
            ("insulin_solver_error_pmol_l", 5, params["Vi"]),
        ):
            metrics[key] = max(
                metrics[key],
                difference(equal_states["tight"], equal_states["reference"], col, scale),
            )
        for control in replays + list(equals.values()):
            for key, item in (
                ("insulin_mass_error_pmol_kg", "insulin_mass_error"),
                ("glucose_mass_error_mg_kg", "glucose_mass_error"),
                ("negative_amount_tolerance", "negative"),
            ):
                metrics[key] = max(metrics[key], control[item])
        contrasts = {}
        for case in ("feedback_quarter", "feedback_half", "feedback_full", "equal_arrival_timing"):
            contrasts[case] = {}
            for outcome in assessments["constant_basal"]["reference"]["outcomes"]:
                if case == "equal_arrival_timing":
                    values = {
                        name: assessments["feedback_full"][name]["outcomes"][outcome]
                        - equals[name]["outcomes"][outcome]
                        for name in equals
                    }
                else:
                    values = {
                        name: assessments[case][name]["outcomes"][outcome]
                        - assessments["constant_basal"][name]["outcomes"][outcome]
                        for name in ("coarse", "tight", "reference")
                    }
                reference = values["reference"]
                uncertainty = max(abs(v - reference) for v in values.values())
                if case in ("feedback_full", "equal_arrival_timing"):
                    uncertainty = max(
                        uncertainty,
                        *(
                            abs(
                                c["outcomes"][outcome]
                                - assessments["feedback_full"]["reference"]["outcomes"][outcome]
                            )
                            for c in replays
                        ),
                    )
                uncertainty = max(uncertainty, sys.float_info.epsilon * (1 + abs(reference)))
                ratio = abs(reference) / uncertainty
                contrasts[case][outcome] = {
                    "contrast": reference,
                    "numerical_uncertainty": uncertainty,
                    "ratio": ratio,
                    "classification": "zero"
                    if reference == 0
                    else (
                        "resolved"
                        if ratio >= p["criteria"]["effect_to_numerical_uncertainty_ratio_min"]
                        else "unresolved"
                    ),
                }
        scenarios[scenario["id"]] = {
            "primary": assessments,
            "replays": replays,
            "equal_arrival": equals,
            "contrasts": contrasts,
            "transferred_minus_parent_amount_pmol_kg": replays[-1]["amount_pmol_kg"]
            - parent["states"][-1][17],
        }
    checks = {
        k: {"value": v, "limit": p["criteria"][k], "passed": v <= p["criteria"][k]}
        for k, v in metrics.items()
    }
    return {
        "schema": VERSION,
        "protocol": p["id"],
        "claim": p["claim"],
        "passed": all(c["passed"] for c in checks.values()),
        "checks": checks,
        "repeat_changed_files": changed,
        "scenarios": scenarios,
        "limitations": p["excluded"],
        "effect_classification": (
            "Valid only when all controls pass; unresolved effects are retained"
        ),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--allow-failed", action="store_true")
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    dump(args.output, reconstruct(args.directory, allow_failed=args.allow_failed))
