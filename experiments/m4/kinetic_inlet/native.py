"""A bounded insulin inlet around the unmodified, verified simglucose derivative.

Nonzero execution integrates only native Ip/Il kinetics and mass ledgers.
The fixed 13-state carrier is not a simulated glucose/metabolic trajectory.
"""

import hashlib
import importlib.metadata
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from scipy.integrate import solve_ivp
from simglucose.patient import t1dpatient
from simglucose.patient.t1dpatient import Action, T1DPatient

try:
    from .forcing import Forcing
except ImportError:
    from forcing import Forcing

PROTOCOL_PATH = Path(__file__).with_name("protocol.json")
ROUTE_INDEX = {"liver": 9, "peripheral": 5}


def load(profile="adult#001"):
    """Load the declared virtual profile only after exact installed-source checks."""
    expected = json.loads(PROTOCOL_PATH.read_text())["upstream"]
    if profile != expected["profile"]:
        raise ValueError("only the prespecified native virtual profile is supported")
    distribution = importlib.metadata.distribution("simglucose")
    direct_url = json.loads(distribution.read_text("direct_url.json") or "{}")
    revision = direct_url.get("vcs_info", {}).get("commit_id")
    if revision != expected["revision"]:
        raise ValueError("installed simglucose revision does not match the protocol")
    patient_path = Path(t1dpatient.__file__).resolve()
    parameter_path = Path(t1dpatient.PATIENT_PARA_FILE).resolve()
    patient_hash = hashlib.sha256(patient_path.read_bytes()).hexdigest()
    parameter_hash = hashlib.sha256(parameter_path.read_bytes()).hexdigest()
    if patient_hash != expected["patient_file_sha256"]:
        raise ValueError("installed native patient source hash does not match the protocol")
    if parameter_hash != expected["parameter_file_sha256"]:
        raise ValueError("installed native parameter-table hash does not match the protocol")
    params = T1DPatient.withName(profile)._params.copy(deep=True)
    required = ("BW", "Vi", "m1", "m2", "m30", "m4")
    if params.Name != profile or any(
        not np.isfinite(params[k]) or params[k] <= 0 for k in required
    ):
        raise ValueError("native profile is missing or has invalid kinetic parameters")
    return params, {
        "upstream_revision": revision,
        "package_version": distribution.version,
        "profile": profile,
        "patient_file_sha256": patient_hash,
        "parameter_file_sha256": parameter_hash,
        "patient_file": str(patient_path),
        "parameter_file": str(parameter_path),
        "body_weight_kg": float(params.BW),
        "kinetic_parameters": {key: float(params[key]) for key in required},
    }


def derivative(t, state, action, params, last_Qsto=0, last_foodtaken=0, *, q=0, route="liver"):
    """Call original derivative; add only q under the selected native state guard."""
    if route not in ROUTE_INDEX:
        raise ValueError("route must be liver or peripheral")
    if isinstance(q, (bool, np.bool_)) or not np.isscalar(q) or not np.isfinite(q) or q < 0:
        raise ValueError("q must be finite and nonnegative, in pmol/(kg min)")
    state = np.asarray(state, dtype=float)
    if state.shape != (13,) or not np.all(np.isfinite(state)):
        raise ValueError("native carrier must contain 13 finite states")
    result = T1DPatient.model(t, state, action, params, last_Qsto, last_foodtaken)
    if q != 0:
        index = ROUTE_INDEX[route]
        result[index] += q * (state[index] >= 0)
    if not np.all(np.isfinite(result)):
        raise RuntimeError("native derivative returned nonfinite values")
    return result


def simulate(times, params, forcing, route, settings):
    """Integrate Ip,Il,hepatic loss,peripheral loss,input; split every input edge."""
    if not isinstance(forcing, Forcing) or route not in ROUTE_INDEX:
        raise ValueError("valid Forcing and liver/peripheral route are required")
    times = np.asarray(times, dtype=float)
    if (
        times.ndim != 1
        or len(times) < 2
        or not np.all(np.isfinite(times))
        or times[0] != 0
        or times[-1] != forcing.horizon
        or np.any(np.diff(times) <= 0)
    ):
        raise ValueError("finite increasing output grid must span exactly the forcing horizon")
    solver = {key: value for key, value in settings.items() if key != "name"}
    if set(solver) != {"method", "rtol", "atol", "max_step"}:
        raise ValueError("solver settings must specify method, rtol, atol, and max_step")
    if solver["method"] not in ("RK45", "DOP853"):
        raise ValueError("unsupported integration method")
    for key in ("rtol", "atol", "max_step"):
        value = solver[key]
        if (
            isinstance(value, bool)
            or not np.isscalar(value)
            or not np.isfinite(value)
            or value <= 0
        ):
            raise ValueError(f"{key} must be finite and positive")
    if solver["rtol"] >= 1:
        raise ValueError("rtol must be less than one")
    carrier = np.asarray(params.iloc[2:15].values, dtype=float).copy()
    # The derivative owns every equation. A value-preserving attribute carrier
    # avoids repeated pandas label lookup at every solver evaluation.
    model_params = SimpleNamespace(**params.to_dict())
    carrier[10:12] = 0.0  # No pharmaceutical SC absorption in incremental kinetics.
    action = Action(CHO=0.0, insulin=0.0)
    state = np.zeros(5, dtype=float)
    output = np.empty((len(times), 5), dtype=float)
    output[0] = state
    filled = np.zeros(len(times), dtype=bool)
    filled[0] = True
    for segment in range(forcing.segments):
        start, stop = forcing.edges[segment : segment + 2]
        indices = np.flatnonzero((times > start) & (times <= stop))
        requested = times[indices]
        integration_times = np.unique(np.append(requested, stop))

        def rhs(time, current):
            carrier[5], carrier[9] = current[:2]
            q = forcing.segment_value(segment, time)
            native = derivative(time, carrier, action, model_params, q=q, route=route)
            return [
                native[5],
                native[9],
                model_params.m30 * current[1],
                model_params.m4 * current[0],
                q,
            ]

        # SciPy 1.13's automatic initial-step estimator may evaluate outside
        # t_span before enforcing max_step. Keep every probe in this segment;
        # accepted steps still adapt to the prespecified error tolerances.
        result = solve_ivp(
            rhs,
            (start, stop),
            state,
            t_eval=integration_times,
            first_step=min(stop - start, solver["max_step"]),
            **solver,
        )
        if (
            not result.success
            or result.y.shape != (5, len(integration_times))
            or not np.array_equal(result.t, integration_times)
            or not np.all(np.isfinite(result.y))
        ):
            raise RuntimeError(
                f"native subsystem solve failed or incomplete at segment {segment}: "
                f"{result.message}"
            )
        output[indices] = result.y[:, : len(indices)].T
        filled[indices] = True
        state = result.y[:, -1].copy()
    if not np.all(filled) or not np.all(np.isfinite(output)):
        raise RuntimeError("native subsystem output is incomplete or nonfinite")
    return output


class _ZeroExtensionPatient(T1DPatient):
    @staticmethod
    def model(t, x, action, params, last_Qsto, last_foodtaken):
        return derivative(t, x, action, params, last_Qsto, last_foodtaken, q=0, route="liver")


def _native_trajectory(patient, action, horizon):
    history = [np.asarray(patient.state, dtype=float).copy()]
    for expected_time in range(1, horizon + 1):
        patient.step(action)
        if (
            not patient._odesolver.successful()
            or patient.t != expected_time
            or np.asarray(patient.state).shape != (13,)
            or not np.all(np.isfinite(patient.state))
        ):
            raise RuntimeError("native full-state zero-extension solve failed or is incomplete")
        history.append(np.asarray(patient.state, dtype=float).copy())
    return np.asarray(history)


def zero_extension(params, protocol):
    """Exact original/wrapper all-state regression, fresh instances and reset."""
    spec = protocol["native_zero_extension"]
    horizon = spec["horizon_min"]
    if (
        isinstance(horizon, bool)
        or not isinstance(horizon, int)
        or horizon <= 0
        or spec["sample_step_min"] != 1
    ):
        raise ValueError(
            "native whole-patient regression requires positive integer minutes at 1 min"
        )
    action = Action(CHO=0.0, insulin=float(params.u2ss * params.BW / 6000))
    base = np.asarray(params.iloc[2:15].values, dtype=float)
    derivative_error = 0.0
    probes = [base.copy()]
    for index in (3, 4, 5, 9, 10, 11, 12):
        for value in (-1.0, 0.0):
            probe = base.copy()
            probe[index] = value
            probes.append(probe)
    for probe in probes:
        native = T1DPatient.model(0, probe, action, params, 0, 0)
        for route in ROUTE_INDEX:
            wrapped = derivative(0, probe, action, params, q=0, route=route)
            derivative_error = max(derivative_error, float(np.max(np.abs(wrapped - native))))
    original = T1DPatient(params, seed=1)
    wrapped = _ZeroExtensionPatient(params, seed=1)
    original_trace = _native_trajectory(original, action, horizon)
    wrapped_trace = _native_trajectory(wrapped, action, horizon)
    fresh_trace = _native_trajectory(_ZeroExtensionPatient(params, seed=1), action, horizon)
    original.reset()
    wrapped.reset()
    reset_original = _native_trajectory(original, action, horizon)
    reset_wrapped = _native_trajectory(wrapped, action, horizon)
    trajectory_error = float(np.max(np.abs(wrapped_trace - original_trace)))
    fresh_error = float(np.max(np.abs(fresh_trace - wrapped_trace)))
    reset_error = float(
        max(
            np.max(np.abs(reset_original - original_trace)),
            np.max(np.abs(reset_wrapped - wrapped_trace)),
        )
    )
    errors = (derivative_error, trajectory_error, fresh_error, reset_error)
    return {
        "passed": all(error == 0.0 for error in errors),
        "derivative_max_error": derivative_error,
        "trajectory_max_error": trajectory_error,
        "fresh_max_error": fresh_error,
        "reset_max_error": reset_error,
        "samples": horizon + 1,
        "states_per_sample": 13,
        "basal_action_u_min": float(action.insulin),
        "guarded_probes": len(probes) * 2,
        "solver_successful": True,
    }
