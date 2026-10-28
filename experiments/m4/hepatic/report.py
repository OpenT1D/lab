"""Independent scalar assessment and artifact reconstruction without SciPy."""

import argparse
import math
import sys
from pathlib import Path
from types import SimpleNamespace

from experiments.m4.feedback import source_oracle
from experiments.m4.feedback.common import validate_source_cases
from experiments.m4.feedback.contract import baseline, number, secretion_terms
from experiments.m4.feedback.report import outcomes
from experiments.m4.paired_kinetics.report import matrix, maxdiff

from .common import (
    VERSION,
    case_specs,
    digest,
    dump,
    key,
    numerical_files,
    read,
    required_files,
    validate,
    verify_files,
)
from .model import anchors, literal_mismatch


def literal(state, params, basal, source, variant):
    """Original equations/intercepts, independent of model.terms' delta form."""
    a = anchors(params, basal, source)
    s = source["gamma"] * state[14]
    he = a["m6_effective"] - a["m5"] * s if variant["extraction"] else a["HEb"]
    m3 = params["m1"] * he / (1 - he)
    raw = (
        ((a["kp1_effective"] - a["kp4"] * state[14]) if variant["portal"] else params["kp1"])
        - params["kp2"] * state[3]
        - params["kp3"] * state[8]
    )
    return he, m3, max(raw, 0)


def assess_preflight(p, parent, params, initial, data):
    keys = (
        "disabled_rhs_error",
        "stationary_derivative_change",
        "literal_equation_error",
        "source_stage_error",
    )
    checks = dict.fromkeys(keys, 0.0)
    cases = {c["id"]: c for c in parent["cases"] if c["id"] in p["cases"]}
    if [b["case"] for b in data["baselines"]] != list(cases) or len(data["probes"]) != len(
        cases
    ) * 8:
        raise ValueError("Incomplete hepatic preflight")
    src = parent["source"]["parameters"]
    hepatic = p["source"] | {"gamma": src["gamma_per_min"]}
    for item in data["baselines"]:
        c = cases[item["case"]]
        b = baseline(params, initial, c["fraction"], src["gamma_per_min"])
        if item["baseline"] != b or item["literal_mismatch"] != literal_mismatch(
            params, b, hepatic
        ):
            raise ValueError("Wrong baseline mismatch diagnostic")
        for v in p["variants"]:
            dx = matrix([item["variants"][v["id"]]], 1, 20)[0]
            original = matrix([item["original_derivative"]], 1, 20)[0]
            checks["stationary_derivative_change"] = max(
                checks["stationary_derivative_change"], maxdiff([dx], [original])
            )
    for item in data["probes"]:
        x = matrix([item["state"]], 1, 20)[0]
        dx = matrix([item["adjusted"]], 1, 20)[0]
        old = matrix([item["original"]], 1, 20)[0]
        b, v = item["baseline"], item["variant"]
        if v not in p["variants"]:
            raise ValueError("Unknown variant")
        he, m3, egp = literal(x, params, b, hepatic, v)
        checks["literal_equation_error"] = max(
            checks["literal_equation_error"],
            abs(he - item["hepatic"]["HE"]),
            abs(m3 - item["hepatic"]["m3"]),
            abs(egp - item["hepatic"]["EGP"]),
        )
        if v["id"] == "fixed":
            checks["disabled_rhs_error"] = max(checks["disabled_rhs_error"], maxdiff([dx], [old]))
        raw = max(params["kp1"] - params["kp2"] * x[3] - params["kp3"] * x[8], 0)
        corrected_gp = old[3] + (egp - raw) * (x[3] >= 0)
        sp = item["source_parameters"]
        new = secretion_terms(
            x[3] / params["Vg"],
            corrected_gp / params["Vg"],
            x[13],
            x[14],
            sp["basal"],
            sp["threshold"],
            sp["gain"],
            src,
        )
        expected = old.copy()
        expected[3] = corrected_gp
        expected[9] -= (m3 - params["m30"]) * x[9] * (x[9] >= 0)
        expected[18] = m3 * x[9]
        expected[13], expected[14], expected[16], expected[17] = (
            new["Z_dot"],
            new["P_dot"],
            new["pancreatic"],
            new["liver"],
        )
        checks["source_stage_error"] = max(checks["source_stage_error"], maxdiff([dx], [expected]))
    return checks


def difference(a, b, column, volume=1):
    return max(abs(x[column] - y[column]) / volume for x, y in zip(a, b, strict=True))


def assess_case(data, p, parent, params, initial, scenario, case, variant, solver):
    horizon, step = parent["horizon_min"], parent["sample_step_min"]
    times = [i * step for i in range(round(horizon / step) + 1)]
    b = baseline(params, initial, case["fraction"], parent["source"]["parameters"]["gamma_per_min"])
    expect = b["state"] + [b["Z_pmol_kg_min"], b["P_pmol_kg"]] + [0.0] * 5
    expect[0] = scenario["stomach_solid_mg"]
    if data["status"] != "completed" or data["failure"] is not None or data["times"] != times:
        raise ValueError("Incomplete case cannot support a completed contrast")
    if (
        data["initial"] != expect
        or data["baseline"] != b
        or data["variant"] != variant
        or data["solver"] != solver
        or data["load_mg"] != scenario["stomach_solid_mg"]
    ):
        raise ValueError("Changed initialization, mechanism or numerical settings")
    src = parent["source"]["parameters"]
    expected_source = dict(
        alpha=src["alpha_per_min"],
        beta=src["beta_pmol_kg_min_per_mg_dl"],
        K=src["K_pmol_kg_per_mg_dl"],
        gamma=src["gamma_per_min"],
        basal=b["Sb_pmol_kg_min"],
        threshold=b["h_mg_dl"],
        gain=case["gain"],
    )
    if data["source_parameters"] != expected_source:
        raise ValueError("Changed source parameters")
    y = matrix(data["states"], len(times), 20)
    q = matrix(data["source_rates"], len(times), 2)
    f = matrix(data["glucose_flux_integrals"], len(times), 5)
    if y[0] != expect or any(f[0]) or data["quadrature"] != p["quadrature"]:
        raise ValueError("Wrong state/flux initialization or quadrature")
    errors = data["quadrature_error_bounds"]
    if len(errors) != len(times) or any(
        number(e) > p["quadrature"]["max_estimated_cumulative_error"] for e in errors
    ):
        raise ValueError("Unverified quadrature precision")
    if len(data["hepatic"]) != len(times):
        raise ValueError("Missing hepatic outputs")
    hepatic = p["source"] | {"gamma": src["gamma_per_min"]}
    hevalues = []
    relation_error = 0.0
    for t, x, r, h in zip(times, y, q, data["hepatic"], strict=True):
        he, m3, egp = literal(x, params, b, hepatic, variant)
        for name, value in h.items():
            number(value, signed=True)
        if not p["HE_computational_envelope"][0] < he < p["HE_computational_envelope"][1]:
            raise ValueError("Hepatic extraction outside computational scope")
        hevalues.append(he)
        relation_error = max(
            relation_error, abs(h["HE"] - he), abs(h["m3"] - m3), abs(h["EGP"] - egp)
        )
        gd = (
            egp
            + params["f"] * params["kabs"] * x[2] / params["BW"]
            - params["Fsnc"]
            - params["ke1"] * max(x[3] - params["ke2"], 0)
            - params["k1"] * x[3]
            + params["k2"] * x[4]
        ) / params["Vg"]
        spo = x[13] + case["gain"] * src["K_pmol_kg_per_mg_dl"] * max(gd, 0)
        relation_error = max(
            relation_error, abs(spo - r[0]), abs(src["gamma_per_min"] * x[14] - r[1])
        )
        if abs(x[15] - b["u_sc_pmol_kg_min"] * t) > 1e-7:
            raise ValueError("SC units/input ledger mismatch")
        if (
            not parent["glucose_envelope_mg_dl"][0]
            <= x[3] / params["Vg"]
            <= parent["glucose_envelope_mg_dl"][1]
        ):
            raise ValueError("Glucose outside scope")
    indices = (5, 9, 10, 11, 14)
    amount0 = math.fsum(expect[i] for i in indices)
    insulin = max(
        abs(math.fsum(x[i] for i in indices) - amount0 - x[15] - x[16] + x[18] + x[19]) for x in y
    )
    portal = max(abs(x[14] - expect[14] - x[16] + x[17]) for x in y)
    glucose = max(
        abs(x[3] + x[4] - expect[3] - expect[4] - v[0] - v[1] + v[2] + v[3] + v[4])
        for x, v in zip(y, f, strict=True)
    )
    physical = [i for i in range(15) if i != 6]
    negative = max(0.0, -min(x[i] for x in y for i in physical))
    out = outcomes(times, y, params["Vg"])
    insulin_conc = [x[5] / params["Vi"] for x in y]
    out.update(
        final_insulin_pmol_l=insulin_conc[-1],
        insulin_auc_above_initial_pmol_min_l=math.fsum(
            (tb - ta) * (ib + ia - 2 * insulin_conc[0]) / 2
            for ta, tb, ia, ib in zip(times, times[1:], insulin_conc, insulin_conc[1:])
        ),
        EGP_integral_mg_kg=f[-1][0],
        hepatic_loss_pmol_kg=y[-1][18],
    )
    return {
        "insulin_mass_error_pmol_kg": max(insulin, portal),
        "glucose_mass_error_mg_kg": glucose,
        "negative_amount_tolerance": negative,
        "literal_equation_error": relation_error,
        "outcomes": out,
        "HE_min": min(hevalues),
        "HE_max": max(hevalues),
        "arrival_pmol_kg": y[-1][17],
        "pancreatic_pmol_kg": y[-1][16],
        "quadrature_error_bound": max(errors),
    }


def contrast(values):
    ref = values["reference"]
    uncertainty = max(
        max(abs(v - ref) for v in values.values()), sys.float_info.epsilon * (1 + abs(ref))
    )
    return {
        "value": ref,
        "uncertainty": uncertainty,
        "ratio": abs(ref) / uncertainty,
        "classification": "zero"
        if ref == 0
        else ("resolved" if abs(ref) >= 10 * uncertainty else "unresolved"),
    }


def assess_source(directory, p):
    """Rebuild the unchanged analytic source reference using scalar closed forms."""
    if read(directory / "protocol.json") != p:
        raise ValueError("Changed source-check protocol")
    metrics = dict.fromkeys(
        ("secretion_rate_closed_form_error_pmol_kg_min", "secretion_closed_form_error_pmol_kg"), 0.0
    )
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
            for metric_name, column in (
                ("secretion_rate_closed_form_error_pmol_kg_min", 0),
                ("secretion_closed_form_error_pmol_kg", 1),
            ):
                metrics[metric_name] = max(metrics[metric_name], difference(actual, exact, column))
    result = {
        "rate_error_pmol_kg_min": metrics["secretion_rate_closed_form_error_pmol_kg_min"],
        "mass_error_pmol_kg": metrics["secretion_closed_form_error_pmol_kg"],
        "passed": all(value <= p["criteria"][name] for name, value in metrics.items()),
    }
    if result != read(directory / "source-assessment.json"):
        raise ValueError("Source assessment cannot be rebuilt")
    return result


def reconstruct(directory, *, allow_pending=False, allow_failed=False):
    directory = Path(directory)
    p, parent = read(directory / "protocol.json"), read(directory / "parent.json")
    validate(p, parent)
    manifest = read(directory / "manifest.json")
    allowed = (
        {"completed"}
        | ({"calculated"} if allow_pending else set())
        | ({"failed"} if allow_failed else set())
    )
    if manifest["schema"] != VERSION or manifest["status"] not in allowed:
        raise ValueError("Incomplete hepatic archive")
    verify_files(directory, manifest, {"protocol.json", "parent.json"})
    required = required_files(p, parent)
    missing = sorted(required - manifest["files"].keys())
    failures = {}
    for name in manifest["files"]:
        if name.startswith("cases/") and name.endswith(".json"):
            data = read(directory / name)
            if data.get("status") != "completed":
                failures[name] = data.get("failure", {"reason": "Incomplete case"})
    if failures or (missing and manifest["status"] == "failed"):
        return {
            "schema": VERSION,
            "passed": False,
            "claim": p["claim"],
            "expected_cases": 24,
            "failures": failures,
            "missing_evidence": missing,
            "contrasts": {},
            "error": manifest.get("error"),
        }
    verify_files(directory, manifest, required)
    native = read(directory / "native.json")
    for key_, upkey in (
        ("upstream_revision", "revision"),
        ("profile", "profile"),
        ("patient_file_sha256", "patient_file_sha256"),
        ("parameter_file_sha256", "parameter_file_sha256"),
    ):
        if native["identity"][key_] != parent["upstream"][upkey]:
            raise ValueError("Wrong native source identity")
    if any(native["runtime"][k] != parent["runtime"][k] for k in ("numpy", "scipy")) or not native[
        "runtime"
    ]["python"].startswith(parent["runtime"]["python"] + "."):
        raise ValueError("Wrong numerical runtime")
    source_check = assess_source(directory / "source-check", parent)
    params, initial = native["parameters"], native["initial"]
    metrics = dict.fromkeys(p["verification"], 0.0)
    metrics.update(assess_preflight(p, parent, params, initial, read(directory / "preflight.json")))
    changed = [
        name
        for name in sorted(numerical_files(p, parent))
        if digest(directory / name) != digest(directory / "repeat" / name)
    ]
    metrics["repeat_artifact_differences"] = len(changed)
    summaries, records = {}, {}
    for scenario, case, variant in case_specs(p, parent):
        label = key(scenario, case, variant)
        records[label], summaries[label] = {}, {}
        for solver in parent["solvers"]:
            name = solver["name"]
            data = read(directory / "cases" / f"{label}--{name}.json")
            records[label][name] = data
            summary = assess_case(data, p, parent, params, initial, scenario, case, variant, solver)
            summaries[label][name] = summary
            if name in ("tight", "reference"):
                for k in (
                    "insulin_mass_error_pmol_kg",
                    "glucose_mass_error_mg_kg",
                    "negative_amount_tolerance",
                    "literal_equation_error",
                ):
                    metrics[k] = max(metrics[k], summary[k])
        tight, ref = [records[label][n] for n in ("tight", "reference")]
        for metric, col, volume in (
            ("glucose_solver_error_mg_dl", 3, params["Vg"]),
            ("insulin_solver_error_pmol_l", 5, params["Vi"]),
        ):
            metrics[metric] = max(
                metrics[metric], difference(tight["states"], ref["states"], col, volume)
            )
        metrics["source_solver_error_pmol_kg_min"] = max(
            metrics["source_solver_error_pmol_kg_min"],
            maxdiff(tight["source_rates"], ref["source_rates"]),
        )
        if variant["id"] == "fixed":
            old = read(directory / "parent" / f"{scenario['id']}--{case['id']}.json")
            if old["status"] != "completed" or old["times"] != ref["times"]:
                raise ValueError("Missing completed BC-008 comparison")
            matrix(old["states"], len(ref["times"]), 20)
            metrics["disabled_reference_state_error"] = max(
                metrics["disabled_reference_state_error"], maxdiff(old["states"], ref["states"])
            )
        fixed = records[key(scenario, case, p["variants"][0])]["reference"]
        if case["id"] == "native_zero":
            metrics["zero_control_state_error"] = max(
                metrics["zero_control_state_error"], maxdiff(fixed["states"], ref["states"])
            )
        if case["id"] == "constant_basal":
            metrics["constant_control_glucose_error_mg_dl"] = max(
                metrics["constant_control_glucose_error_mg_dl"],
                difference(fixed["states"], ref["states"], 3, params["Vg"]),
            )
        if scenario["id"] == "fasting":
            for k, col, vol in (
                ("fasting_glucose_drift_mg_dl", 3, params["Vg"]),
                ("fasting_insulin_drift_pmol_l", 5, params["Vi"]),
            ):
                metrics[k] = max(
                    metrics[k], max(abs(x[col] - ref["initial"][col]) / vol for x in ref["states"])
                )
    contrasts = {}
    for scenario in p["scenarios"]:
        values = {}
        for variant in p["variants"]:
            name = variant["id"]
            full = summaries[f"{scenario}--feedback_full--{name}"]
            constant = summaries[f"{scenario}--constant_basal--{name}"]
            values[name] = {
                out: {
                    sol: full[sol]["outcomes"][out] - constant[sol]["outcomes"][out] for sol in full
                }
                for out in full["reference"]["outcomes"]
            }
        changes = {
            v: {
                out: contrast(
                    {s: values[v][out][s] - values["fixed"][out][s] for s in values[v][out]}
                )
                for out in values[v]
            }
            for v in values
            if v != "fixed"
        }
        interaction = {
            out: contrast(
                {
                    s: values["both"][out][s]
                    - values["extraction"][out][s]
                    - values["portal"][out][s]
                    + values["fixed"][out][s]
                    for s in values["fixed"][out]
                }
            )
            for out in values["fixed"]
        }
        contrasts[scenario] = {
            "within_variant": {
                v: {o: contrast(d) for o, d in vals.items()} for v, vals in values.items()
            },
            "change_vs_fixed": changes,
            "interaction": interaction,
        }
    checks = {
        k: {"value": v, "limit": p["verification"][k], "passed": v <= p["verification"][k]}
        for k, v in metrics.items()
    }
    return {
        "schema": VERSION,
        "protocol": p["id"],
        "claim": p["claim"],
        "passed": manifest["status"] != "failed"
        and source_check["passed"]
        and all(c["passed"] for c in checks.values()),
        "source_checks": source_check,
        "checks": checks,
        "expected_cases": 24,
        "completed_cases": len(summaries),
        "failures": {},
        "baselines": read(directory / "preflight.json")["baselines"],
        "summaries": summaries,
        "contrasts": contrasts,
        "repeat_changed_files": changed,
        "limitations": p["excluded"],
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
