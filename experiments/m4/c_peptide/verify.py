"""Verification beyond self-consistency: source formula, limits and synthetic recovery."""

from dataclasses import replace

import numpy as np

from experiments.m4.kinetic_inlet.forcing import Forcing

from .model import concentration_to_pmol_l, initial_state, insulin_mass_to_molar_input, simulate


def verify(protocol, runs, identification, parameters):
    criteria = protocol["criteria"]
    checks = {}

    def record(name, value, criterion=None):
        limit = 0 if criterion is None else criteria[criterion]
        checks[name] = {"value": float(value), "limit": limit, "passed": bool(0 <= value <= limit)}

    def maximum(values):
        return float(np.max(np.abs(values)))

    agreement, refinement, balance, accounting, negative, zero, repeat = [0.0] * 7
    for run in runs.values():
        times, forcing, initial = run["times"], run["forcing"], run["initial"]
        states, exact = run["states"], run["analytical"]
        volume = run["params"].volume_l_kg
        delivered = np.array([forcing.integral(0, t) for t in times])
        for method in ("tight", "reference"):
            state = states[method]
            agreement = max(agreement, maximum(state[:, 0] / volume - exact))
            balance = max(
                balance, maximum(np.sum(state[:, :3], axis=1) - state[:, 3] - sum(initial[:2]))
            )
            accounting = max(accounting, maximum(state[:, 3] - delivered))
            negative = max(negative, float(max(0, -np.min(state))))
        refinement = max(
            refinement, maximum((states["tight"][:, 0] - states["reference"][:, 0]) / volume)
        )
        if run["name"] == "zero":
            zero = max(zero, maximum(states["reference"]))
        if run["name"] == "basal_pulse":
            repeated = simulate(times, run["params"], forcing, initial, protocol["solvers"][-1])
            repeat = max(repeat, maximum(repeated - states["reference"]))
    record("analytical_agreement", agreement, "max_concentration_error_pmol_l")
    record("solver_sensitivity", refinement, "max_concentration_error_pmol_l")
    record("mass_balance", balance, "max_mass_balance_error_pmol_kg")
    record("input_accounting", accounting, "max_input_amount_error_pmol_kg")
    record("positivity", negative, "negative_state_tolerance_pmol_kg")
    record("zero_input", zero)
    record("repeatability", repeat, "repeat_state_error")
    equilibrium_error, one_error = 0.0, 0.0
    for params in parameters.values():
        grid = np.arange(241, dtype=float)
        q = 1.5
        forcing = Forcing([0, 240], [q], [q])
        initial = initial_state({"kind": "equilibrium", "basal_q_pmol_kg_min": q}, params)
        state = simulate(grid, params, forcing, initial, protocol["solvers"][-1])
        equilibrium_error = max(equilibrium_error, maximum(state[:, :2] - initial[:2]))
        one = replace(params, k1=0)
        zero_force = Forcing([0, 240], [0], [0])
        state = simulate(grid, one, zero_force, [100, 0, 0, 0], protocol["solvers"][-1])
        analytical = 100 / one.volume_l_kg * np.exp(-one.k3 * grid)
        one_error = max(one_error, maximum(state[:, 0] / one.volume_l_kg - analytical))
    record("equilibrium", equilibrium_error, "max_equilibrium_state_error_pmol_kg")
    record("one_compartment_limit", one_error, "max_one_compartment_error_pmol_l")
    unit_error = max(
        abs(concentration_to_pmol_l(1, "pmol/mL") / 1000 - 1),
        abs(concentration_to_pmol_l(3.021, "ng/mL") / 1000 - 1),
        abs(insulin_mass_to_molar_input(5.808, 80) / 12.5 - 1),
    )
    record("unit_conversion", unit_error, "max_unit_conversion_relative_error")
    record(
        "synthetic_recovery",
        max(f["max_relative_parameter_error"] for f in identification["fits"]),
        "max_synthetic_recovery_relative_error",
    )
    record(
        "synthetic_fit",
        max(f["max_concentration_residual_pmol_l"] for f in identification["fits"]),
        "max_synthetic_fit_error_pmol_l",
    )
    record(
        "sensitivity_refinement",
        identification["sensitivity_refinement_relative_error"],
        "max_sensitivity_refinement_relative_error",
    )
    record(
        "scale_confounding",
        max(
            f["max_concentration_difference_pmol_l"]
            for f in identification["amplitude_volume_confounding"]
        ),
        "max_scale_confounding_error_pmol_l",
    )
    designs = identification["designs"]
    rank_error = (
        abs(designs["full_known_input"]["rank"] - 4)
        + abs(designs["full_unknown_amplitude"]["rank"] - 4)
        + max(designs["sparse_known_input"]["rank"] - 3, 0)
    )
    record("identifiability_ranks", rank_error)
    return {
        "schema": "bc003-verification/1",
        "protocol": protocol["id"],
        "passed": all(c["passed"] for c in checks.values()),
        "checks": checks,
        "maxima": "sampled at declared output times; no continuous-time or biological bound",
        "evidence": "numerical checks and noiseless synthetic known-input identifiability only",
    }
