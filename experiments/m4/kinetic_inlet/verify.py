"""Independent numerical/ledger evidence for the frozen BC-002 kinetic inlet.

Only the separate zero-extension regression advances native glucose states.
Nonzero-input cases describe incremental insulin kinetics, not clinical glucose,
endogenous basal release, insulin independence or graft function.
"""

import numpy as np

if __package__:
    from . import native, oracle
    from .forcing import Forcing, interval_average
else:
    import native
    import oracle
    from forcing import Forcing, interval_average


REQUIRED_CHECKS = (
    "native_zero_extension",
    "primary_oracle_agreement",
    "primary_mass_balance",
    "primary_input_integrals",
    "positivity",
    "repeatability",
    "conversion_anchor",
    "source_oracle_agreement",
    "source_mass_balance",
    "communication_amount",
    "communication_refinement",
    "equal_area_baseline",
    "gain_linearity",
    "zero_gain",
    "route_contrast_resolution",
)


def sample_times(protocol):
    """Frozen regular reporting grid plus explicitly requested off-grid points."""
    horizon, step = protocol["horizon_min"], protocol["sample_step_min"]
    count = round(horizon / step)
    if count < 1 or not np.isclose(count * step, horizon, rtol=0, atol=1e-12):
        raise ValueError("BC-002 horizon must be an integer number of sample steps")
    return np.unique(
        np.r_[np.linspace(0, horizon, count + 1), protocol["additional_sample_times_min"]]
    )


def _maximum(values):
    return float(np.max(np.abs(values)))


def _metrics(states, exact, forcing, times, volume):
    delivered = np.array([oracle.integral(forcing, 0, t) for t in times])
    return {
        "max_insulin_state_error_pmol_kg": _maximum(states[:, :2] - exact[:, :2]),
        "max_plasma_error_pmol_l": _maximum(states[:, 0] - exact[:, 0]) / volume,
        "max_ledger_state_error_pmol_kg": _maximum(states[:, 2:] - exact[:, 2:]),
        "max_mass_balance_error_pmol_kg": _maximum(np.sum(states[:, :4], axis=1) - states[:, 4]),
        "max_input_integral_error_pmol_kg": _maximum(states[:, 4] - delivered),
        "oracle_mass_balance_error_pmol_kg": _maximum(np.sum(exact[:, :4], axis=1) - exact[:, 4]),
        "minimum_state_pmol_kg": float(np.min(states)),
        "final_input_pmol_kg": float(states[-1, 4]),
        "final_hepatic_loss_pmol_kg": float(states[-1, 2]),
        "final_peripheral_loss_pmol_kg": float(states[-1, 3]),
        "final_inventory_pmol_kg": float(np.sum(states[-1, :2])),
        "sampled_peak_plasma_pmol_l": float(np.max(states[:, 0]) / volume),
        "plasma_auc_pmol_min_l": float(np.trapz(states[:, 0] / volume, times)),
    }


def verify(protocol, params, source_forcing):
    """Return JSON-safe measured checks; all thresholds come from frozen BC-002."""
    criteria = protocol["criteria"]
    times = sample_times(protocol)
    volume = float(params["Vi"])
    body_weight = float(params["BW"])
    if not np.isfinite(volume) or volume <= 0 or not np.isfinite(body_weight) or body_weight <= 0:
        raise ValueError("Finite positive native Vi and BW are required")
    if source_forcing.horizon != protocol["horizon_min"]:
        raise ValueError("Source forcing must cover the exact BC-002 horizon")
    settings = {entry["name"]: entry for entry in protocol["solvers"]}
    if set(settings) != {"coarse", "tight", "reference"}:
        raise ValueError("BC-002 requires coarse, tight and reference methods")
    if protocol["routes"] != ["liver", "peripheral"]:
        raise ValueError("BC-002 requires the separately named liver and peripheral routes")
    checks = {}

    def record(name, passed, **details):
        checks[name] = {"passed": bool(passed), **details}

    regression = native.zero_extension(params, protocol)
    record(
        "native_zero_extension",
        regression["passed"],
        **{key: value for key, value in regression.items() if key != "passed"},
        derivative_tolerance=criteria["native_zero_derivative_error"],
        trajectory_tolerance=criteria["native_zero_trajectory_error"],
    )

    # The amounts below are independent hand calculations of the frozen fixtures:
    # rectangle 1*100, rectangle 2*(15.7-5.3), triangles 2*20/2 + 2*80/2.
    expected_totals = {"zero": 0.0, "constant": 100.0, "pulse": 20.8, "ramp": 100.0}
    if {case["name"] for case in protocol["primary_cases"]} != set(expected_totals):
        raise ValueError("The four frozen primary fixtures are required")
    primary_cases = {}
    primary_metrics = []
    input_integral_error = 0.0
    minimum_state = 0.0
    repeat_error = 0.0
    for case in protocol["primary_cases"]:
        forcing = Forcing(case["edges"], case["left"], case["right"])
        expected = expected_totals[case["name"]]
        input_integral_error = max(input_integral_error, abs(oracle.integral(forcing) - expected))
        for route in protocol["routes"]:
            exact = oracle.simulate(times, params, forcing, route)
            solutions = {
                name: native.simulate(times, params, forcing, route, setting)
                for name, setting in settings.items()
            }
            measurements = {
                name: _metrics(state, exact, forcing, times, volume)
                for name, state in solutions.items()
            }
            for name in ("tight", "reference"):
                primary_metrics.append(measurements[name])
                minimum_state = min(minimum_state, measurements[name]["minimum_state_pmol_kg"])
                input_integral_error = max(
                    input_integral_error, abs(measurements[name]["final_input_pmol_kg"] - expected)
                )
            if case["name"] == "pulse":
                repeated = native.simulate(times, params, forcing, route, settings["reference"])
                repeat_error = max(repeat_error, _maximum(repeated - solutions["reference"]))
            primary_cases[f"{case['name']}__{route}"] = {
                "route": route,
                "input": forcing.to_dict(),
                "expected_integral_pmol_kg": expected,
                "methods": measurements,
                "tight_reference_plasma_error_pmol_l": _maximum(
                    solutions["tight"][:, 0] - solutions["reference"][:, 0]
                )
                / volume,
            }

    def agreement(name, metrics):
        state_error = max(item["max_insulin_state_error_pmol_kg"] for item in metrics)
        plasma_error = max(item["max_plasma_error_pmol_l"] for item in metrics)
        record(
            name,
            state_error <= criteria["max_insulin_state_error_pmol_kg"]
            and plasma_error <= criteria["max_plasma_error_pmol_l"],
            max_insulin_state_error_pmol_kg=state_error,
            max_plasma_error_pmol_l=plasma_error,
            state_tolerance_pmol_kg=criteria["max_insulin_state_error_pmol_kg"],
            plasma_tolerance_pmol_l=criteria["max_plasma_error_pmol_l"],
            compared_methods=["tight", "reference"],
            oracle="independent augmented matrix exponential, explicit piecewise-linear input",
        )

    def balance(name, metrics):
        error = max(
            max(
                item[field]
                for field in (
                    "max_mass_balance_error_pmol_kg",
                    "max_input_integral_error_pmol_kg",
                    "oracle_mass_balance_error_pmol_kg",
                )
            )
            for item in metrics
        )
        record(
            name,
            error <= criteria["max_mass_balance_error_pmol_kg"],
            max_error_pmol_kg=error,
            tolerance_pmol_kg=criteria["max_mass_balance_error_pmol_kg"],
        )

    agreement("primary_oracle_agreement", primary_metrics)
    balance("primary_mass_balance", primary_metrics)
    record(
        "primary_input_integrals",
        input_integral_error <= criteria["max_mass_balance_error_pmol_kg"],
        max_error_pmol_kg=input_integral_error,
        tolerance_pmol_kg=criteria["max_mass_balance_error_pmol_kg"],
        expected_integrals_pmol_kg=expected_totals,
    )

    # This independently checks the numerical mass/mole anchor. Actual source-row
    # conversion is a separate importer check because only converted input arrives here.
    calculated_anchor = 5.808 * 1e6 / (protocol["trace_bridge"]["molar_mass_g_mol"] * body_weight)
    expected_anchor = 1000.0 / body_weight
    conversion_error = abs(calculated_anchor - expected_anchor) / expected_anchor
    record(
        "conversion_anchor",
        conversion_error <= criteria["conversion_relative_error"],
        relative_error=conversion_error,
        tolerance=criteria["conversion_relative_error"],
        source_microgram_per_min=5.808,
        expected_pmol_per_min=1000.0,
        converted_pmol_kg_min=calculated_anchor,
        body_weight_kg=body_weight,
        scope=(
            "scalar 5.808 microgram = 1000 pmol anchor; source-row conversion checked by importer"
        ),
    )

    source_replay = {}
    source_metrics = []
    dynamic = {}
    source_exact = {}
    for route in protocol["routes"]:
        exact = oracle.simulate(times, params, source_forcing, route)
        source_exact[route] = exact
        solutions = {
            name: native.simulate(times, params, source_forcing, route, setting)
            for name, setting in settings.items()
        }
        dynamic[route] = solutions["reference"]
        measurements = {
            name: _metrics(state, exact, source_forcing, times, volume)
            for name, state in solutions.items()
        }
        source_replay[route] = {"methods": measurements}
        for name in ("tight", "reference"):
            source_metrics.append(measurements[name])
            minimum_state = min(minimum_state, measurements[name]["minimum_state_pmol_kg"])
        repeated = native.simulate(times, params, source_forcing, route, settings["reference"])
        repeat_error = max(repeat_error, _maximum(repeated - dynamic[route]))
    agreement("source_oracle_agreement", source_metrics)
    balance("source_mass_balance", source_metrics)

    communication = {}
    communication_amount_error = 0.0
    refinement_checks = []
    for route in protocol["routes"]:
        by_interval = []
        for interval in protocol["communication_intervals_min"]:
            averaged = interval_average(source_forcing, interval)
            delivered = native.simulate(times, params, averaged, route, settings["reference"])
            minimum_state = min(minimum_state, float(np.min(delivered)))
            plasma_error = _maximum(delivered[:, 0] - source_exact[route][:, 0]) / volume
            amount_error = max(
                abs(oracle.integral(averaged, a, b) - oracle.integral(source_forcing, a, b))
                for a, b in zip(averaged.edges[:-1], averaged.edges[1:], strict=True)
            )
            final_error = abs(delivered[-1, 4] - oracle.integral(source_forcing))
            communication_amount_error = max(communication_amount_error, amount_error, final_error)
            by_interval.append(
                {
                    "interval_min": float(interval),
                    "max_plasma_error_pmol_l": plasma_error,
                    "max_interval_amount_error_pmol_kg": float(amount_error),
                    "final_input_error_pmol_kg": float(final_error),
                }
            )
        coarse, fine = (
            by_interval[0]["max_plasma_error_pmol_l"],
            by_interval[-1]["max_plasma_error_pmol_l"],
        )
        ratio = fine / coarse if coarse > 0 else (0.0 if fine == 0 else None)
        refined = (
            fine <= criteria["fine_communication_plasma_error_pmol_l"]
            and ratio is not None
            and ratio <= criteria["fine_to_coarse_communication_error_ratio"]
        )
        refinement_checks.append(refined)
        communication[route] = {
            "intervals": by_interval,
            "fine_to_coarse_error_ratio": ratio,
            "refinement_passed": bool(refined),
        }
    record(
        "communication_amount",
        communication_amount_error <= criteria["max_communication_amount_error_pmol_kg"],
        max_error_pmol_kg=float(communication_amount_error),
        tolerance_pmol_kg=criteria["max_communication_amount_error_pmol_kg"],
    )
    record(
        "communication_refinement",
        all(refinement_checks),
        routes={
            route: {
                "finest_error_pmol_l": result["intervals"][-1]["max_plasma_error_pmol_l"],
                "fine_to_coarse_error_ratio": result["fine_to_coarse_error_ratio"],
            }
            for route, result in communication.items()
        },
        finest_tolerance_pmol_l=criteria["fine_communication_plasma_error_pmol_l"],
        ratio_tolerance=criteria["fine_to_coarse_communication_error_ratio"],
    )

    total = oracle.integral(source_forcing)
    constant = Forcing(
        [0.0, source_forcing.horizon],
        [total / source_forcing.horizon],
        [total / source_forcing.horizon],
    )
    zero = Forcing([0.0, source_forcing.horizon], [0.0], [0.0])
    baseline_comparison = {}
    equal_area_error = abs(oracle.integral(constant) - total)
    gains = {}
    gain_error = 0.0
    zero_error = 0.0
    for route in protocol["routes"]:
        constant_state = native.simulate(times, params, constant, route, settings["reference"])
        zero_state = native.simulate(times, params, zero, route, settings["reference"])
        constant_exact = oracle.simulate(times, params, constant, route)
        baseline_comparison[route] = {
            "dynamic": source_replay[route]["methods"]["reference"],
            "equal_area_constant": _metrics(
                constant_state, constant_exact, constant, times, volume
            ),
            "zero_max_absolute_state_pmol_kg": _maximum(zero_state),
            "dynamic_constant_max_plasma_difference_pmol_l": _maximum(
                dynamic[route][:, 0] - constant_state[:, 0]
            )
            / volume,
        }
        equal_area_error = max(
            equal_area_error, abs(constant_state[-1, 4] - total), abs(dynamic[route][-1, 4] - total)
        )
        minimum_state = min(minimum_state, float(np.min(constant_state)), float(np.min(zero_state)))
        zero_error = max(zero_error, _maximum(zero_state))
        by_gain = []
        for gain in protocol["trace_bridge"]["gains"]:
            forcing = Forcing(
                source_forcing.edges,
                [gain * value for value in source_forcing.left],
                [gain * value for value in source_forcing.right],
            )
            state = native.simulate(times, params, forcing, route, settings["reference"])
            linear_error = _maximum(state - gain * dynamic[route])
            gain_error = max(gain_error, linear_error)
            minimum_state = min(minimum_state, float(np.min(state)))
            if gain == 0:
                zero_error = max(zero_error, _maximum(state))
            by_gain.append(
                {
                    "gain": float(gain),
                    "max_state_scaling_error_pmol_kg": linear_error,
                    "final_input_pmol_kg": float(state[-1, 4]),
                    "sampled_peak_plasma_pmol_l": float(np.max(state[:, 0]) / volume),
                }
            )
        gains[route] = by_gain
    record(
        "equal_area_baseline",
        equal_area_error <= criteria["max_mass_balance_error_pmol_kg"],
        max_amount_error_pmol_kg=float(equal_area_error),
        total_input_pmol_kg=total,
        tolerance_pmol_kg=criteria["max_mass_balance_error_pmol_kg"],
    )
    record(
        "gain_linearity",
        gain_error <= criteria["max_insulin_state_error_pmol_kg"],
        max_state_error_pmol_kg=gain_error,
        tolerance_pmol_kg=criteria["max_insulin_state_error_pmol_kg"],
        scope="fixed linear kinetic block; synthetic input gain, not a treatment model",
    )
    record("zero_gain", zero_error == 0.0, max_absolute_state_pmol_kg=zero_error, tolerance=0.0)
    record(
        "positivity",
        minimum_state >= -criteria["negative_state_tolerance_pmol_kg"],
        minimum_state_pmol_kg=minimum_state,
        negative_tolerance_pmol_kg=criteria["negative_state_tolerance_pmol_kg"],
    )
    record(
        "repeatability",
        repeat_error <= criteria["repeat_state_error"],
        max_absolute_state_error=repeat_error,
        tolerance=criteria["repeat_state_error"],
        repeated_cases="pulse and source replay, both routes",
    )

    contrast = _maximum(dynamic["peripheral"][:, 0] - dynamic["liver"][:, 0]) / volume
    solver_oracle_error = max(item["max_plasma_error_pmol_l"] for item in source_metrics)
    finest_communication_error = max(
        entry["intervals"][-1]["max_plasma_error_pmol_l"] for entry in communication.values()
    )
    numerical_error = max(solver_oracle_error, finest_communication_error)
    fraction = numerical_error / contrast if contrast > 0 else None
    resolved = (
        fraction is not None and fraction < criteria["numerical_error_fraction_of_route_contrast"]
    )
    record(
        "route_contrast_resolution",
        resolved,
        max_route_contrast_pmol_l=contrast,
        max_numerical_error_pmol_l=numerical_error,
        solver_oracle_error_pmol_l=solver_oracle_error,
        finest_communication_error_pmol_l=finest_communication_error,
        numerical_error_fraction=fraction,
        maximum_fraction=criteria["numerical_error_fraction_of_route_contrast"],
        interpretation="numerical resolution only; neither route is clinically validated",
    )
    if set(checks) != set(REQUIRED_CHECKS):
        raise RuntimeError("Incomplete BC-002 verification implementation")
    return {
        "schema": "m4-kinetic-inlet-verification/1",
        "protocol": protocol["id"],
        "passed": all(check["passed"] for check in checks.values()),
        "checks": checks,
        "primary_cases": primary_cases,
        "source_replay": source_replay,
        "communication": communication,
        "baseline_comparison": baseline_comparison,
        "gains": gains,
        "source_integral_pmol_kg": total,
        "evidence_scope": "synthetic incremental insulin kinetics and numerical transfer only",
        "error_sampling": (
            "maxima over the prespecified 0.25 min output grid plus 5.3 and 15.7 min; "
            "not continuous-time error bounds"
        ),
        "human_validation": "not performed",
        "glucose_control_evaluation": "not performed",
    }
