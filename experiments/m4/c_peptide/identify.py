"""Bounded synthetic recovery and sensitivity; no human-data inverse interface."""

from dataclasses import replace

import numpy as np
from scipy.linalg import expm
from scipy.optimize import least_squares

from .model import Parameters
from .reference import bolus

KEYS = ("k1", "k2", "k3", "volume_l_kg")


def sensitivity(times, parameters, dose, step, *, free_dose=False):
    """d(concentration)/d(log parameter), including optional log input amplitude."""
    columns = []
    for key in KEYS:
        upper = replace(parameters, **{key: getattr(parameters, key) * np.exp(step)})
        lower = replace(parameters, **{key: getattr(parameters, key) * np.exp(-step)})
        columns.append((bolus(times, upper, dose) - bolus(times, lower, dose)) / (2 * step))
    if free_dose:
        columns.append(
            (
                bolus(times, parameters, dose * np.exp(step))
                - bolus(times, parameters, dose * np.exp(-step))
            )
            / (2 * step)
        )
    return np.column_stack(columns)


def summarize(matrix, relative_threshold):
    singular = np.linalg.svd(matrix, compute_uv=False)
    rank = int(np.sum(singular > singular[0] * relative_threshold))
    return {
        "singular_values_pmol_l": singular.tolist(),
        "rank": rank,
        "rows": matrix.shape[0],
        "columns": matrix.shape[1],
        "condition_number": float(singular[0] / singular[-1]) if rank == matrix.shape[1] else None,
    }


def analyze(protocol):
    spec = protocol["identifiability"]
    params = Parameters(**protocol["profiles"][spec["profile"]])
    times = np.array(spec["times_min"], dtype=float)
    dose = spec["dose_pmol_kg"]
    observations = bolus(times, params, dose)
    nominal = np.array([getattr(params, key) for key in KEYS])
    log_nominal = np.log(nominal)
    fits = []

    def residual(log_parameters):
        p = Parameters(**dict(zip(KEYS, np.exp(log_parameters), strict=True)))
        matrix = np.array([[-p.k1 - p.k3, p.k2], [p.k1, -p.k2]])
        predicted = np.array([(expm(matrix * t) @ [dose, 0])[0] / p.volume_l_kg for t in times])
        return (predicted - observations) / np.max(observations)

    for factors in spec["recovery_start_factors"]:
        result = least_squares(
            residual,
            log_nominal + np.log(factors),
            bounds=(
                log_nominal + np.log(spec["bound_factors"][0]),
                log_nominal + np.log(spec["bound_factors"][1]),
            ),
            xtol=1e-13,
            ftol=1e-13,
            gtol=1e-13,
            max_nfev=1000,
        )
        if not result.success or not np.isfinite(result.x).all():
            raise RuntimeError("Synthetic recovery did not complete")
        fits.append(
            {
                "start_factors": factors,
                "estimated_parameters": np.exp(result.x).tolist(),
                "max_relative_parameter_error": float(
                    np.max(np.abs(np.exp(result.x) / nominal - 1))
                ),
                "max_concentration_residual_pmol_l": float(
                    np.max(np.abs(residual(result.x))) * np.max(observations)
                ),
                "predictions_pmol_l": (
                    residual(result.x) * np.max(observations) + observations
                ).tolist(),
                "evaluations": int(result.nfev),
            }
        )
    steps = spec["finite_difference_steps"]
    matrices = [sensitivity(times, params, dose, step) for step in steps]
    matrix = matrices[-1]
    refinement = float(np.max(np.abs(matrices[0] - matrix)) / np.max(np.abs(matrix)))
    rank_threshold = spec["rank_relative_threshold"]
    designs = {"full_known_input": summarize(matrix, rank_threshold)}
    for name, grid in (
        ("early_known_input", spec["early_times_min"]),
        ("sparse_known_input", spec["sparse_times_min"]),
    ):
        designs[name] = summarize(sensitivity(grid, params, dose, steps[-1]), rank_threshold)
    joint = sensitivity(times, params, dose, steps[-1], free_dose=True)
    designs["full_unknown_amplitude"] = summarize(joint, rank_threshold)
    confounding = []
    for factor in spec["confounding_factors"]:
        curve = bolus(
            times, replace(params, volume_l_kg=params.volume_l_kg * factor), dose * factor
        )
        confounding.append(
            {
                "factor": factor,
                "max_concentration_difference_pmol_l": float(np.max(np.abs(curve - observations))),
            }
        )
    return {
        "schema": "bc003-synthetic-identifiability/1",
        "data_kind": "noiseless synthetic known-input bolus",
        "parameter_order": list(KEYS),
        "nominal_parameters": nominal.tolist(),
        "dose_pmol_kg": dose,
        "times_min": times.tolist(),
        "observations_pmol_l": observations.tolist(),
        "sensitivity_matrix_pmol_l": matrix.tolist(),
        "joint_sensitivity_matrix_pmol_l": joint.tolist(),
        "sensitivity_refinement_relative_error": refinement,
        "rank_relative_threshold": rank_threshold,
        "designs": designs,
        "fits": fits,
        "amplitude_volume_confounding": confounding,
        "equilibrium_information": "concentration=q/(k3*Vp): no separate exchange-rate information",
        "human_identifiability": (
            "not assessed; noise, assay limits and input uncertainty not estimated"
        ),
    }
