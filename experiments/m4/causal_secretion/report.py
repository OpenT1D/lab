"""Reconstruct causal comparisons from saved states, without researcher code."""

import argparse
import math
from pathlib import Path

from experiments.m4.feedback.report import outcomes
from experiments.m4.paired_kinetics.common import dump, read, verify_files
from experiments.m4.paired_kinetics.report import matrix, maxdiff

from .common import (
    CASES,
    REUSED,
    SCENARIOS,
    SOLVERS,
    SOURCES,
    VERSION,
    baseline_context,
    declaration,
    protocol,
    reference,
    sha256,
)


def required():
    return {
        "protocol.json",
        "model.json",
        "model.py",
        "primary.log",
        "repeat.log",
        "reference/manifest.json",
        *(f"source-{name}" for name in SOURCES),
        *("source-" + name.replace("/", "__") for name in REUSED),
        "uv.lock",
        "pyproject.toml",
        *(f"{label}/worker.json" for label in ("primary", "repeat")),
        *(f"{label}/preflight.json" for label in ("primary", "repeat")),
        *(
            f"{label}/{scenario}/{mode}-{solver}.json"
            for label in ("primary", "repeat")
            for scenario in SCENARIOS
            for mode in CASES
            for solver in SOLVERS
        ),
    }


def inspect(data, bc, task, params, basal, gamma, scenario, mode, solver, source_hash):
    if (
        data.get("schema") != "m4-causal-trajectory/1"
        or data.get("status") != "completed"
        or data.get("failure") is not None
        or data.get("mode") != mode
        or data.get("solver") != solver
        or data.get("baseline") != basal
        or data.get("load_mg") != scenario["stomach_solid_mg"]
        or data.get("gamma_per_min") != gamma
        or data.get("model_source_sha256") != source_hash
    ):
        raise ValueError("Incomplete or mismatched causal trajectory")
    times = [
        i * bc["sample_step_min"]
        for i in range(round(bc["horizon_min"] / bc["sample_step_min"]) + 1)
    ]
    if data["times"] != times:
        raise ValueError("Causal output grid differs from BC-008")
    states = matrix(data["states"], len(times), 20)
    rates = matrix(data["source_rates"], len(times), 2)
    flux = matrix(data["glucose_flux_integrals"], len(times), 5)
    initial = basal["state"] + [basal["Z_pmol_kg_min"], basal["P_pmol_kg"]] + [0.0] * 5
    initial[0] = scenario["stomach_solid_mg"]
    if data["initial"] != initial or states[0] != initial or any(flux[0]):
        raise ValueError("Initial inventories or flux ledgers changed")
    errors = data["glucose_quadrature_error_bounds"]
    if (
        not isinstance(errors, list)
        or len(errors) != len(times)
        or any(
            isinstance(v, bool)
            or not isinstance(v, (int, float))
            or not math.isfinite(v)
            or v < 0
            or v > 1e-6
            for v in errors
        )
        or data["quadrature"]
        != {
            "method": "quad_vec",
            "epsabs": 1e-9,
            "epsrel": 1e-9,
            "norm": "max",
            "flux_order": ["EGP", "Ra", "Uii", "Uid", "renal"],
        }
    ):
        raise ValueError("Incomplete glucose quadrature evidence")
    if any(
        pancreatic < 0
        or pancreatic > task["max_rate_pmol_kg_min"]
        or abs(liver - gamma * row[14]) > 1e-10
        for row, (pancreatic, liver) in zip(states, rates, strict=True)
    ):
        raise ValueError("Pancreatic/liver rate boundary changed")
    if mode == "host_constant_basal" and any(
        abs(row[13] - basal["Sb_pmol_kg_min"]) > 1e-10
        or abs(rate[0] - basal["Sb_pmol_kg_min"]) > 1e-10
        for row, rate in zip(states, rates, strict=True)
    ):
        raise ValueError("Host constant-basal control is not constant")
    inventory_indices = (5, 9, 10, 11, 14)
    initial_inventory = math.fsum(initial[index] for index in inventory_indices)
    insulin_mass = max(
        abs(
            math.fsum(row[index] for index in inventory_indices)
            - initial_inventory
            - row[15]
            - row[16]
            + row[18]
            + row[19]
        )
        for row in states
    )
    portal = max(abs(row[14] - initial[14] - row[16] + row[17]) for row in states)
    glucose_mass = max(
        abs(row[3] + row[4] - initial[3] - initial[4] - f[0] - f[1] + f[2] + f[3] + f[4])
        for row, f in zip(states, flux, strict=True)
    )
    physical = [i for i in range(15) if i != 6]
    negative = max(0, -min(row[index] for row in states for index in physical))
    sc_error = max(
        abs(row[15] - t * basal["u_sc_pmol_kg_min"]) for t, row in zip(times, states, strict=True)
    )
    lower, upper = bc["glucose_envelope_mg_dl"]
    if any(not lower <= row[3] / params["Vg"] <= upper for row in states):
        raise ValueError("Glucose left the declared BC-008 envelope")
    metrics = {
        "insulin_mass_error_pmol_kg": max(insulin_mass, portal, sc_error),
        "glucose_mass_error_mg_kg": glucose_mass,
        "negative_amount_tolerance": negative,
    }
    return {
        "metrics": metrics,
        "outcomes": outcomes(times, states, params["Vg"]),
        "pancreatic_amount_pmol_kg": states[-1][16],
        "liver_arrival_pmol_kg": states[-1][17],
        "peak_plasma_insulin_pmol_l": max(row[5] / params["Vi"] for row in states),
        "final_plasma_insulin_pmol_l": states[-1][5] / params["Vi"],
    }


def reconstruct(directory, *, allow_pending=False, allow_failed=False):
    directory = Path(directory)
    manifest = read(directory / "manifest.json")
    statuses = {"completed"}
    if allow_pending:
        statuses.add("calculated")
    if allow_failed:
        statuses.add("failed")
    if manifest.get("schema") != "m4-causal-run/1" or manifest.get("status") not in statuses:
        raise ValueError("Causal archive is not complete")
    need = {"protocol.json", "model.json", "model.py", "reference/manifest.json"}
    if manifest["status"] != "failed":
        need |= required() | (set() if allow_pending else {"report.json"})
    verify_files(directory, manifest, need)
    if manifest["status"] == "failed":
        return {
            "schema": "m4-causal-report/1",
            "passed": False,
            "error": manifest.get("error"),
            "attempts": {
                label: read(directory / label / "worker.json").get("attempts", [])
                for label in ("primary", "repeat")
                if (directory / label / "worker.json").exists()
            },
            "missing_evidence": sorted(required() - manifest["files"].keys()),
            "scenarios": {},
            "limitations": ["Incomplete execution; no scenario contrast accepted"],
        }
    declared = declaration(read(directory / "model.json"))
    if (
        sha256(directory / "model.py") != declared["source_sha256"]
        or manifest["model_source_sha256"] != declared["source_sha256"]
    ):
        raise ValueError("Archived model source hash differs from declaration")
    bc, archived_native, probe, reference_report = reference(directory / "reference")
    task = protocol(read(directory / "protocol.json"), bc)
    basal, gamma = baseline_context(bc, archived_native, probe)
    params = archived_native["parameters"]
    for label in ("primary", "repeat"):
        worker = read(directory / label / "worker.json")
        expected_attempts = [
            {"scenario": scenario, "mode": mode, "solver": solver, "status": "completed"}
            for scenario in SCENARIOS
            for mode in CASES
            for solver in SOLVERS
        ]
        if (
            worker.get("schema") != "m4-causal-worker/1"
            or worker.get("status") != "completed"
            or worker.get("label") != label
            or worker.get("native_identity") != archived_native["identity"]
            or any(worker["runtime"][key] != bc["runtime"][key] for key in ("numpy", "scipy"))
            or worker.get("attempts") != expected_attempts
        ):
            raise ValueError("Incomplete or mismatched causal worker")
    first = read(directory / "primary" / "preflight.json")
    second = read(directory / "repeat" / "preflight.json")
    outputs = matrix(first.get("outputs"), 5, 2)
    equilibrium_error = max(
        max(abs(dz), abs(rate - basal["Sb_pmol_kg_min"])) for dz, rate in outputs[:3]
    )
    expected_points = [
        [0.0, basal["h_mg_dl"], 0.0, basal["Sb_pmol_kg_min"]],
        [120.0, basal["h_mg_dl"], 0.0, basal["Sb_pmol_kg_min"]],
        [240.0, basal["h_mg_dl"], 0.0, basal["Sb_pmol_kg_min"]],
        [4.0, basal["h_mg_dl"] + 30.0, 2.0, basal["Sb_pmol_kg_min"]],
        [3.0, basal["h_mg_dl"] - 20.0, -1.0, basal["Sb_pmol_kg_min"] + 0.2],
    ]
    if (
        first != second
        or first.get("schema") != "m4-causal-preflight/1"
        or first.get("points") != expected_points
        or first.get("passed") is not True
        or first.get("equilibrium_error") != equilibrium_error
        or equilibrium_error > task["source_equilibrium_tolerance"]
    ):
        raise ValueError("Missing or changed model preflight")
    repeat_changed = []
    for scenario in SCENARIOS:
        for mode in CASES:
            for solver in SOLVERS:
                name = f"{scenario}/{mode}-{solver}.json"
                if sha256(directory / "primary" / name) != sha256(directory / "repeat" / name):
                    repeat_changed.append(name)
    metrics = {key: 0.0 for key in task["criteria"]}
    metrics["repeat_error"] = float(bool(repeat_changed))
    scenarios = {}
    for scenario in bc["scenarios"]:
        records, assessments = {}, {}
        for mode in CASES:
            records[mode], assessments[mode] = {}, {}
            for solver in bc["solvers"]:
                if solver["name"] not in SOLVERS:
                    continue
                name = solver["name"]
                item = read(directory / "primary" / scenario["id"] / f"{mode}-{name}.json")
                records[mode][name] = item
                assessed = inspect(
                    item,
                    bc,
                    task,
                    params,
                    basal,
                    gamma,
                    scenario,
                    mode,
                    solver,
                    declared["source_sha256"],
                )
                assessments[mode][name] = assessed
                for key, value in assessed["metrics"].items():
                    metrics[key] = max(metrics[key], value)
            tight, exact = records[mode]["tight"], records[mode]["reference"]
            metrics["glucose_solver_error_mg_dl"] = max(
                metrics["glucose_solver_error_mg_dl"],
                max(
                    abs(a[3] - b[3]) / params["Vg"]
                    for a, b in zip(tight["states"], exact["states"], strict=True)
                ),
            )
            metrics["insulin_solver_error_pmol_l"] = max(
                metrics["insulin_solver_error_pmol_l"],
                max(
                    abs(a[5] - b[5]) / params["Vi"]
                    for a, b in zip(tight["states"], exact["states"], strict=True)
                ),
            )
            metrics["source_solver_error_pmol_kg_min"] = max(
                metrics["source_solver_error_pmol_kg_min"],
                maxdiff(tight["source_rates"], exact["source_rates"]),
            )
        if scenario["id"] == "fasting":
            baseline_states = records["candidate"]["reference"]["states"]
            metrics["fasting_glucose_drift_mg_dl"] = max(
                abs(row[3] - baseline_states[0][3]) / params["Vg"] for row in baseline_states
            )
            metrics["fasting_insulin_drift_pmol_l"] = max(
                abs(row[5] - baseline_states[0][5]) / params["Vi"] for row in baseline_states
            )
        bc_constant = read(
            directory / "reference" / scenario["id"] / "constant_basal-reference.json"
        )
        bc_full = read(directory / "reference" / scenario["id"] / "feedback_full-reference.json")
        host = records["host_constant_basal"]["reference"]
        candidate = records["candidate"]["reference"]
        if host["initial"] != bc_constant["initial"] or candidate["initial"] != bc_full["initial"]:
            raise ValueError("Candidate/control initial state differs from BC-008")
        metrics["basal_control_glucose_error_mg_dl"] = max(
            metrics["basal_control_glucose_error_mg_dl"],
            max(
                abs(a[3] - b[3]) / params["Vg"]
                for a, b in zip(host["states"], bc_constant["states"], strict=True)
            ),
        )
        metrics["basal_control_insulin_error_pmol_l"] = max(
            metrics["basal_control_insulin_error_pmol_l"],
            max(
                abs(a[5] - b[5]) / params["Vi"]
                for a, b in zip(host["states"], bc_constant["states"], strict=True)
            ),
        )
        candidate_outcome = assessments["candidate"]["reference"]["outcomes"]
        reference_outcome = outcomes(candidate["times"], bc_full["states"], params["Vg"])
        basal_outcome = assessments["host_constant_basal"]["reference"]["outcomes"]
        scenarios[scenario["id"]] = {
            "candidate": assessments["candidate"]["reference"],
            "host_constant_basal": assessments["host_constant_basal"]["reference"],
            "bc008_reference": reference_outcome,
            "glucose_contrast_vs_bc008": {
                key: candidate_outcome[key] - reference_outcome[key] for key in candidate_outcome
            },
            "glucose_contrast_vs_basal_control": {
                key: candidate_outcome[key] - basal_outcome[key] for key in candidate_outcome
            },
        }
    report = {
        "schema": "m4-causal-report/1",
        "implementation": VERSION,
        "model_id": declared["model_id"],
        "model_source_sha256": declared["source_sha256"],
        "reference_manifest_sha256": sha256(directory / "reference" / "manifest.json"),
        "reference_protocol": reference_report["protocol"],
        "metrics": metrics,
        "repeat_changed": repeat_changed,
        "scenarios": scenarios,
        "passed": all(metrics[key] <= limit for key, limit in task["criteria"].items()),
        "claim": task["claim"],
        "limitations": task["excluded"],
    }
    if not allow_pending and read(directory / "report.json") != report:
        raise ValueError("Saved causal report differs from artifact reconstruction")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    result = reconstruct(args.directory)
    dump(args.output, result)
    if not result["passed"]:
        raise SystemExit("Causal numerical checks failed")


if __name__ == "__main__":
    main()
