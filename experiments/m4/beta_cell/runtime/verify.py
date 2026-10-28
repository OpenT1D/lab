"""Numerical evidence for BC-001; no patient fit or biological validation.

The constant-forcing oracle solves the triangular linear system analytically,
with its coefficients written independently from model.algebraic().
"""

import argparse
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
from model import (
    GlucoseInput,
    Parameters,
    algebraic,
    initial_state,
    mg_dl_to_mmol_l,
    simulate,
)


def reference_rates(glucose, p):
    """Independent rational expressions for Figure 2c/d, nominal parameters."""
    glucose = np.asarray(glucose, dtype=float)
    excess_cubed = np.maximum(glucose - p.g_b, 0.0) ** 3
    activation_denominator = (p.k_phi - p.g_b) ** 3 + excess_cubed
    delivery_numerator = p.f * p.p_plus * excess_cubed
    total_denominator = p.r * (p.p_minus + p.f) * activation_denominator + delivery_numerator
    delay = (p.p_minus + p.f) * activation_denominator / total_denominator
    mobilization = p.m0 + p.c * glucose**p.n / (p.k_m**p.n + glucose**p.n)
    y_infinity = delivery_numerator * mobilization / total_denominator
    return 1.0 / delay, y_infinity


def constant_solution(times, *, m, rho, y_infinity, x0, y0=0.0):
    """Independent exact constant-forcing solution, including m == rho.

    X is a convolution of Y with exp(-m t). Using the slower exponential
    and expm1 avoids cancellation and overflow in the two-exponential term.
    """
    times = np.asarray(times, dtype=float)
    e_m = np.exp(-m * times)
    e_rho = np.exp(-rho * times)
    delta = abs(m - rho)
    if delta == 0.0:
        convolution = times * e_m
    else:
        convolution = np.exp(-min(m, rho) * times) * (-np.expm1(-delta * times)) / delta
    y = y_infinity + (y0 - y_infinity) * e_rho
    x = x0 * e_m + y_infinity * (-np.expm1(-m * times)) / m
    x += (y0 - y_infinity) * convolution
    return np.column_stack((x, y))


def _settings(protocol, name):
    return {
        k: v
        for k, v in next(s for s in protocol["solvers"] if s["name"] == name).items()
        if k != "name"
    }


def time_grid(protocol):
    horizon, step = protocol["horizon_min"], protocol["sample_step_min"]
    if not np.isfinite(horizon) or not np.isfinite(step) or horizon <= 0 or step <= 0:
        raise ValueError("horizon and sample step must be finite and positive")
    count = round(horizon / step)
    if count < 1 or not np.isclose(count * step, horizon, rtol=0, atol=1e-12):
        raise ValueError("sample step must divide the horizon exactly")
    return np.linspace(0.0, horizon, count + 1)


def verify(protocol):
    p = Parameters(**protocol["parameters"])
    glucose_input = GlucoseInput(**protocol["input"])
    times = time_grid(protocol)
    criteria = protocol["criteria"]
    reference = _settings(protocol, "reference")
    checks = {}

    def record(name, passed, **details):
        checks[name] = {"passed": bool(passed), **details}

    solutions = {
        s["name"]: simulate(times, p, glucose_input, **_settings(protocol, s["name"]))
        for s in protocol["solvers"]
    }
    baseline = solutions["reference"]
    solver_error = float(np.max(np.abs(p.m * (solutions["tight"][:, 0] - baseline[:, 0]))))
    coarse_error = float(np.max(np.abs(p.m * (solutions["coarse"][:, 0] - baseline[:, 0]))))
    record(
        "solver_sensitivity",
        solver_error <= criteria["max_solver_secretion_error_ug_per_min"],
        tight_reference_max_sr_error_ug_per_min=solver_error,
        coarse_reference_max_sr_error_ug_per_min=coarse_error,
        tolerance_ug_per_min=criteria["max_solver_secretion_error_ug_per_min"],
        methods_and_settings=protocol["solvers"],
    )

    repeat = simulate(times, p, glucose_input, **reference)
    repeat_error = float(np.max(np.abs(repeat - baseline)))
    record(
        "deterministic_repeat",
        repeat_error <= criteria["repeat_absolute_error"],
        maximum_absolute_state_error=repeat_error,
    )

    capacities = {}
    maximum_scaling_error = 0.0
    minimum_state = float(np.min(baseline))
    for capacity in protocol["capacity_values"]:
        state = simulate(times, p, glucose_input, capacity=capacity, **reference)
        error = float(np.max(np.abs(state - capacity * baseline)))
        maximum_scaling_error = max(maximum_scaling_error, error)
        minimum_state = min(minimum_state, float(np.min(state)))
        capacities[str(capacity)] = {
            "maximum_absolute_state_scaling_error": error,
            "maximum_secretion_ug_per_min": float(np.max(p.m * state[:, 0])),
        }
    zero_state = simulate(times, p, glucose_input, capacity=0.0, **reference)
    basal_input = GlucoseInput(g_max=p.g_b, g_b=p.g_b, tau_min=glucose_input.tau_min)
    basal_state = simulate(times, p, basal_input, **reference)
    record(
        "capacity_linearity",
        maximum_scaling_error <= criteria["capacity_linearity_error"],
        maximum_absolute_state_error=maximum_scaling_error,
        scenarios=capacities,
    )
    record(
        "zero_capacity",
        np.array_equal(zero_state, np.zeros_like(zero_state)),
        maximum_absolute_state=float(np.max(np.abs(zero_state))),
    )
    record(
        "basal_threshold",
        np.array_equal(basal_state, np.zeros_like(basal_state)),
        maximum_absolute_state=float(np.max(np.abs(basal_state))),
        meaning="evoked secretion only; zero is not a claim of no basal insulin in vivo",
    )
    record(
        "positivity",
        minimum_state >= -criteria["negative_state_tolerance"],
        minimum_state=minimum_state,
        negative_state_tolerance=criteria["negative_state_tolerance"],
    )

    # Supra-threshold constant forcing deliberately has input basal != model threshold.
    constant_input = GlucoseInput(g_max=10.0, g_b=10.0, tau_min=30.0)
    rho, y_infinity = reference_rates(10.0, p)
    constant_cases = {}
    for name, m_value in (
        ("distinct_rates", p.m),
        ("equal_rates", float(rho)),
        ("nearly_equal_rates", float(rho) * (1.0 + 1e-12)),
    ):
        test_p = replace(p, m=m_value)
        numerical = simulate(times, test_p, constant_input, x0_override=1.7, **reference)
        exact = constant_solution(
            times, m=m_value, rho=float(rho), y_infinity=float(y_infinity), x0=1.7
        )
        constant_cases[name] = float(np.max(np.abs(numerical - exact)))
    record(
        "constant_forcing_closed_form",
        max(constant_cases.values()) <= criteria["constant_input_closed_form_error"],
        maximum_absolute_state_errors=constant_cases,
        tolerance=criteria["constant_input_closed_form_error"],
        constant_glucose_mmol_l=10.0,
        x0_ug=1.7,
    )

    converted_input = replace(
        glucose_input,
        g_max=float(mg_dl_to_mmol_l(glucose_input.g_max * 18)),
        g_b=float(mg_dl_to_mmol_l(glucose_input.g_b * 18)),
    )
    converted_states = simulate(times, p, converted_input, **reference)
    conversion_error = float(np.max(np.abs(converted_states - baseline)))
    conversion_anchor_error = abs(float(mg_dl_to_mmol_l(90.0)) - 5.0)
    record(
        "glucose_conversion",
        conversion_anchor_error == 0 and conversion_error <= 1e-12,
        mg_dl_per_mmol_l=18.0,
        anchor_90_mg_dl_in_mmol_l=float(mg_dl_to_mmol_l(90.0)),
        maximum_absolute_state_error=conversion_error,
    )

    grid_spec = protocol["reference_glucose_grid"]
    grid = np.linspace(
        grid_spec["start"],
        grid_spec["stop"],
        round((grid_spec["stop"] - grid_spec["start"]) / grid_spec["step"]) + 1,
    )
    rho_grid, provision_grid = algebraic(grid, p)
    independent_rho, independent_provision = reference_rates(grid, p)
    grid_error = float(
        max(
            np.max(np.abs(rho_grid - independent_rho)),
            np.max(np.abs(provision_grid - independent_provision)),
        )
    )
    delay = 1.0 / rho_grid
    low, high = criteria["published_delay_min_bounds"]
    limit_delay = 1.0 / (p.r + p.f * p.p_plus / (p.p_minus + p.f))
    limit_provision = (1.0 - p.r * limit_delay) * (p.m0 + p.c)
    huge_rho, huge_provision = algebraic(1e100, p)
    asymptote_error = max(
        abs(1.0 / float(huge_rho) - limit_delay), abs(float(huge_provision) - limit_provision)
    )
    record(
        "published_algebraic_relationships",
        grid_error <= criteria["reference_grid_absolute_error"]
        and low <= np.min(delay) <= np.max(delay) <= high
        and asymptote_error <= criteria["reference_grid_absolute_error"],
        maximum_independent_expression_error=grid_error,
        minimum_grid_delay_min=float(np.min(delay)),
        maximum_grid_delay_min=float(np.max(delay)),
        infinite_glucose_delay_min=limit_delay,
        infinite_glucose_provision_ug_per_min=limit_provision,
        asymptote_absolute_error=float(asymptote_error),
        provision_at_10_mmol_l_ug_per_min=float(algebraic(10.0, p)[1]),
        evidence=(
            "reconstructed Figure 2c/d equations; not digitized observations or cohort dynamics"
        ),
    )

    # Independently expand printed 4.13 using the declared D0 convention.
    excess = glucose_input.g_max - p.g_b
    activation0 = excess**3 / ((p.k_phi - p.g_b) ** 3 + excess**3)
    basal_power = glucose_input.g_b**p.n
    d0 = (p.m0 + p.c * basal_power / (p.k_m**p.n + basal_power)) / p.r
    expected_x0 = p.p_plus * activation0 * d0 / (p.p_minus + p.f)
    initial = initial_state(p, glucose_input)
    initial_error = float(np.max(np.abs(initial - [expected_x0, 0.0])))
    alternative_x0 = protocol["initialization_alternative"]["x0_ug"]
    alternate = simulate(times, p, glucose_input, x0_override=alternative_x0, **reference)
    exact_initial_pool_release = (alternative_x0 - initial[0]) * np.exp(-p.m * times)
    initial_pool_release_error = float(
        np.max(np.abs(alternate[:, 0] - baseline[:, 0] - exact_initial_pool_release))
    )
    baseline_auc = float(np.trapezoid(p.m * baseline[:, 0], times))
    record(
        "initialization",
        initial_error <= 1e-12
        and np.array_equal(baseline[0], initial)
        and initial_pool_release_error <= criteria["constant_input_closed_form_error"],
        d0_ug=float(d0),
        printed_equation_x0_ug=float(initial[0]),
        y0_ug_per_min=float(initial[1]),
        independent_expression_absolute_error=initial_error,
        author_code_x0_ug=alternative_x0,
        printed_equation_auc_ug=baseline_auc,
        author_initialization_auc_ug=float(np.trapezoid(p.m * alternate[:, 0], times)),
        initial_pool_release_closed_form_max_x_error_ug=initial_pool_release_error,
        exact_continuous_extra_secretion_ug=float(
            (alternative_x0 - initial[0]) * (-np.expm1(-p.m * times[-1]))
        ),
        maximum_sr_difference_ug_per_min=float(
            np.max(np.abs(p.m * (alternate[:, 0] - baseline[:, 0])))
        ),
        interpretation="unresolved source discrepancy; alternative is sensitivity, not correction",
    )

    # Capacity=1,c,m0 versus capacity=.5,2*c,2*m0 also scales derived X0.
    confounded = simulate(
        times, replace(p, c=2 * p.c, m0=2 * p.m0), glucose_input, capacity=0.5, **reference
    )
    confounding_error = float(np.max(np.abs(confounded - baseline)))
    record(
        "capacity_amplitude_confounding",
        confounding_error <= criteria["capacity_linearity_error"],
        maximum_absolute_state_difference=confounding_error,
        case_a={"capacity": 1.0, "c": p.c, "m0": p.m0, "x0_ug": float(initial[0])},
        case_b={
            "capacity": 0.5,
            "c": 2 * p.c,
            "m0": 2 * p.m0,
            "nominal_x0_ug": float(2 * initial[0]),
        },
        conclusion="exact common-amplitude confounding; no human identifiability estimate",
    )

    invalid = [
        lambda: replace(p, r=0),
        lambda: replace(p, k_phi=p.g_b),
        lambda: replace(p, c=float("nan")),
        lambda: replace(glucose_input, g_max=1.0),
        lambda: replace(glucose_input, tau_min=float("inf")),
        lambda: simulate([0, 1, 1], p, glucose_input),
        lambda: simulate([0, float("nan")], p, glucose_input),
        lambda: simulate(times, p, glucose_input, capacity=-1),
        lambda: simulate(times, p, glucose_input, rtol=0),
        lambda: simulate(times, p, glucose_input, x0_override=float("inf")),
    ]
    rejected = 0
    for case in invalid:
        try:
            case()
        except ValueError:
            rejected += 1
    record(
        "invalid_input_rejection",
        rejected == len(invalid),
        rejected=rejected,
        attempted=len(invalid),
    )

    sensitivity = {}
    step = protocol["sensitivity"]["relative_step"]
    for name in protocol["sensitivity"]["parameters"]:
        aucs = {}
        for sign, label in ((-1, "minus"), (1, "plus")):
            changed = replace(p, **{name: getattr(p, name) * (1 + sign * step)})
            state = simulate(times, changed, glucose_input, **reference)
            aucs[label] = float(np.trapezoid(changed.m * state[:, 0], times))
        sensitivity[name] = {
            "minus_auc_ug": aucs["minus"],
            "plus_auc_ug": aucs["plus"],
            "normalized_central_sensitivity": (aucs["plus"] - aucs["minus"])
            / (2 * step * baseline_auc),
        }
    record(
        "local_sensitivity_finite",
        all(np.isfinite(v) for entry in sensitivity.values() for v in entry.values()),
        relative_parameter_step=step,
    )
    return {
        "passed": all(check["passed"] for check in checks.values()),
        "checks": checks,
        "sensitivity": sensitivity,
        "baseline_auc_ug": baseline_auc,
        "evidence_scope": "synthetic numerical and published algebraic equation verification",
        "human_validation": "not performed",
        "published_dynamic_figure_reproduction": "not performed",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--protocol", type=Path, default=Path(__file__).resolve().parents[1] / "protocol.json"
    )
    args = parser.parse_args()
    result = verify(json.loads(args.protocol.read_text()))
    print(json.dumps(result, indent=2, allow_nan=False))
    raise SystemExit(0 if result["passed"] else 1)
