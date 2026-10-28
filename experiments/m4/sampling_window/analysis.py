"""BC-015-P4 synthetic sampling experiment; no participant observations."""

import numpy as np
from scipy.optimize import least_squares

from experiments.m4.c_peptide.model import Parameters, simulate
from experiments.m4.c_peptide.reference import constant_schedule
from experiments.m4.kinetic_inlet.forcing import Forcing


def grids(protocol):
    observation = protocol["observation"]
    shift = observation["injection_clock_shift_min"]
    early = np.asarray(observation["protocol_early_clock_min"], dtype=float) + shift
    late = np.asarray(observation["hypothetical_late_clock_min"], dtype=float) + shift
    if (
        np.any(np.diff(early) <= 0)
        or np.any(np.diff(late) <= 0)
        or early[0] <= 0
        or late[0] <= early[-1]
        or late[-1] >= protocol["model"]["horizon_min_after_injection"]
    ):
        raise ValueError("Sampling clocks must be ordered within the source horizon")
    full = np.r_[early, late]
    return {"early": early, "early_plus_hypothetical_late": full}


def parameters(protocol, k3_scale):
    model = protocol["model"]
    return Parameters(
        model["k1_per_min"],
        model["k2_per_min"],
        model["k3_per_min"] * k3_scale,
        model["volume_l_kg"],
    )


def forcing(protocol, gain):
    model = protocol["model"]
    return Forcing(
        (0, model["pulse_interval_min_after_injection"][1], model["horizon_min_after_injection"]),
        (model["incremental_pulse_pmol_kg_min"] * gain, 0),
        (model["incremental_pulse_pmol_kg_min"] * gain, 0),
    )


def predict(protocol, times, theta):
    values = np.asarray(theta, dtype=float)
    lower, upper = np.asarray(protocol["model"]["lower"]), np.asarray(protocol["model"]["upper"])
    if (
        values.shape != (2,)
        or not np.isfinite(values).all()
        or np.any(values < lower)
        or np.any(values > upper)
    ):
        raise ValueError("Two finite bounded multipliers required")
    return constant_schedule(
        np.asarray(times),
        parameters(protocol, values[1]),
        forcing(protocol, values[0]),
        np.zeros(4),
    )


def ode_truth(protocol, times, theta):
    model = protocol["model"]
    grid = np.r_[0, times, model["horizon_min_after_injection"]]
    p = parameters(protocol, theta[1])
    states = simulate(
        grid,
        p,
        forcing(protocol, theta[0]),
        np.zeros(4),
        {"method": "DOP853", "rtol": 1e-11, "atol": 1e-13, "max_step": 0.125},
    )
    return states[1:-1, 0] / p.volume_l_kg, states


def log_jacobian(protocol, times, theta, step):
    theta = np.asarray(theta, dtype=float)
    center = np.log(theta)
    cols = []
    for j in range(2):
        delta = np.zeros(2)
        delta[j] = step
        cols.append(
            (
                predict(protocol, times, np.exp(center + delta))
                - predict(protocol, times, np.exp(center - delta))
            )
            / (2 * step * protocol["observation"]["noise_sd_pmol_l"])
        )
    return np.column_stack(cols)


def fit(protocol, times, observed, start):
    lower, upper = np.log(protocol["model"]["lower"]), np.log(protocol["model"]["upper"])
    sd = protocol["observation"]["noise_sd_pmol_l"]

    def residual(log_theta):
        return (predict(protocol, times, np.exp(log_theta)) - observed) / sd

    try:
        result = least_squares(
            residual,
            np.log(start),
            bounds=(lower, upper),
            method="trf",
            max_nfev=200,
            xtol=1e-11,
            ftol=1e-11,
            gtol=1e-11,
        )
        theta = np.exp(result.x)
        prediction = predict(protocol, times, theta)
        if not result.success or not np.isfinite(theta).all() or not np.isfinite(prediction).all():
            raise RuntimeError("Incomplete or nonfinite optimization")
        return {
            "status": "completed",
            "start": list(start),
            "parameters": theta.tolist(),
            "predicted_pmol_l": prediction.tolist(),
            "objective": float(np.sum(((prediction - observed) / sd) ** 2)),
            "evaluations": int(result.nfev),
            "bound_hits": [
                bool(
                    abs(theta[j] - np.exp(lower[j])) < 1e-5
                    or abs(theta[j] - np.exp(upper[j])) < 1e-5
                )
                for j in range(2)
            ],
        }
    except (ValueError, RuntimeError, FloatingPointError) as exc:
        return {"status": "failed", "start": list(start), "error": str(exc)}


def run_analysis(protocol):
    schedules = grids(protocol)
    full = schedules["early_plus_hypothetical_late"]
    truth = np.asarray(protocol["model"]["truth"], dtype=float)
    checks = {}
    for name, candidate in (
        ("truth", truth),
        (
            "low_gain_high_k3",
            np.array([protocol["model"]["lower"][0], protocol["model"]["upper"][1]]),
        ),
        (
            "high_gain_low_k3",
            np.array([protocol["model"]["upper"][0], protocol["model"]["lower"][1]]),
        ),
    ):
        ode, states = ode_truth(protocol, full, candidate)
        analytical = predict(protocol, full, candidate)
        checks[name] = {
            "max_ode_analytical_error_pmol_l": float(np.max(np.abs(ode - analytical))),
            "final_mass_balance_pmol_kg": float(
                abs(states[-1, 0] + states[-1, 1] + states[-1, 2] - states[-1, 3])
            ),
        }
    source, _ = ode_truth(protocol, full, truth)
    if (
        max(c["max_ode_analytical_error_pmol_l"] for c in checks.values())
        > protocol["verification"]["ode_analytical_max_error_pmol_l"]
    ):
        raise RuntimeError("ODE and analytical concentration disagree")
    if max(c["final_mass_balance_pmol_kg"] for c in checks.values()) > 1e-7:
        raise RuntimeError("C-peptide mass balance failed")
    matrices = {}
    for design, times in schedules.items():
        coarse, fine = (
            log_jacobian(protocol, times, truth, step)
            for step in protocol["analysis"]["log_difference_steps"]
        )
        refinement = float(np.linalg.norm(coarse - fine) / np.linalg.norm(fine))
        if refinement > protocol["verification"]["jacobian_refinement_relative_max"]:
            raise RuntimeError("Sampling sensitivity is step-size dependent")
        singular = np.linalg.svd(fine, compute_uv=False)
        matrices[design] = {
            "jacobian_scaled": fine.tolist(),
            "singular_values": singular.tolist(),
            "relative_refinement": refinement,
            "rank": int(
                np.count_nonzero(
                    singular > singular[0] * protocol["analysis"]["svd_relative_cutoff"]
                )
            ),
            "condition_number": float(singular[0] / singular[-1]),
        }
    observations = {
        "times_min_after_injection": full.tolist(),
        "reference_pmol_l": source.tolist(),
        "draws": {},
    }
    cases = {}
    for seed in [
        None,
        *range(
            protocol["observation"]["noise_seed_first"],
            protocol["observation"]["noise_seed_first"]
            + protocol["observation"]["noise_seed_count"],
        ),
    ]:
        key = "noiseless" if seed is None else str(seed)
        noise = (
            np.zeros_like(source)
            if seed is None
            else np.random.default_rng(seed).normal(size=len(full))
            * protocol["observation"]["noise_sd_pmol_l"]
        )
        observed = source + noise
        observations["draws"][key] = {
            "noise_pmol_l": noise.tolist(),
            "observed_pmol_l": observed.tolist(),
        }
        for design, times in schedules.items():
            n = len(times)
            values = observed[:n]
            starts = [
                fit(protocol, times, values, start) for start in protocol["analysis"]["starts"]
            ]
            cases[f"{key}-{design}"] = {"seed": seed, "design": design, "starts": starts}
            if seed is None:
                if any(
                    start["status"] != "completed"
                    or max(abs(np.array(start["parameters"]) / truth - 1))
                    > protocol["verification"]["noiseless_relative_parameter_error_max"]
                    for start in starts
                ):
                    raise RuntimeError(f"Noiseless recovery failed in {design}")
    return {
        "checks": checks,
        "sensitivities": matrices,
        "observations": observations,
        "cases": cases,
    }
