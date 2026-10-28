"""BC-011 conditional joint model; unchanged BC-008 RHS plus passive C-peptide.

Native states 0:20 retain BC-008 ownership. Added states 20:24 are central
and peripheral C-peptide amounts, elimination, and pancreatic appearance,
all in pmol/kg. This wrapper does not implement an inverse estimator.
"""

import json
import platform
from dataclasses import replace
from pathlib import Path

import numpy as np
import scipy
from scipy.integrate import solve_ivp

from experiments.m4.feedback.contract import baseline, validate
from experiments.m4.feedback.coupled import PHYSICAL, rhs_factory
from experiments.m4.feedback.secretion import parameters, settings
from experiments.m4.kinetic_inlet.native import load as load_native


class Model:
    """Verified native model with exact nominal basal glucose/insulin conditioning."""

    def __init__(self, protocol):
        self.protocol = protocol
        self.parent_protocol = json.loads(
            (Path(__file__).parents[1] / "feedback" / "protocol.json").read_text()
        )
        validate(self.parent_protocol)
        runtime = {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        }
        expected = protocol["runtime"]
        if not runtime["python"].startswith(expected["python"] + ".") or any(
            runtime[key] != expected[key] for key in ("numpy", "scipy")
        ):
            raise ValueError("BC-011 requires its frozen native numerical environment")
        native, self.identity = load_native(self.parent_protocol["upstream"]["profile"])
        self.identity = {**self.identity, "runtime": runtime}
        self.params = native.to_dict()
        self.nominal = baseline(
            self.params,
            native.iloc[2:15].astype(float).tolist(),
            protocol["model"]["basal_replacement_fraction"],
            self.parent_protocol["source"]["parameters"]["gamma_per_min"],
        )
        self.sd = np.asarray(protocol["observation"]["synthetic_sd"], dtype=float)

    def _theta(self, theta):
        if any(
            isinstance(x, (bool, np.bool_, str, bytes))
            for x in np.asarray(theta, dtype=object).flat
        ):
            raise ValueError("Three finite numeric parameters required")
        value = np.asarray(theta, dtype=float)
        if (
            value.shape != (3,)
            or not np.isfinite(value).all()
            or np.any(value < self.protocol["model"]["lower"])
            or np.any(value > self.protocol["model"]["upper"])
        ):
            raise ValueError("Parameters must lie within the three frozen positive bounds")
        return value

    def prepare(self, theta, source_scale=1.0):
        """Return parameters, conditioned baseline, source and fasting initial state.

        The returned RHS has zero gastric load. A loaded trajectory creates its
        own RHS only after the fasting equilibrium check, preventing meal input
        from contaminating the conditioning test.
        """
        theta = self._theta(theta)
        if isinstance(source_scale, (bool, np.bool_)) or source_scale not in (0.5, 1.0, 2.0):
            raise ValueError("Only the frozen exact-symmetry diagnostic scales are allowed")
        params = {**self.params, "m4": self.params["m4"] * theta[1]}
        state = np.asarray(self.nominal["state"], dtype=float).copy()
        rsc = params["ka1"] * state[10] + params["ka2"] * state[11]
        state[9] = ((params["m2"] + params["m4"]) * state[5] - rsc) / params["m1"]
        sb = (params["m1"] + params["m30"]) * state[9] - params["m2"] * state[5]
        basal = {
            **self.nominal,
            "state": state.tolist(),
            "Sb_pmol_kg_min": float(sb),
            "Z_pmol_kg_min": float(sb),
            "P_pmol_kg": float(sb / self.parent_protocol["source"]["parameters"]["gamma_per_min"]),
        }
        source = parameters(self.parent_protocol, basal, float(theta[0]))
        source = replace(
            source,
            gain=source.gain * source_scale,
            beta=source.beta / source_scale,
            K=source.K / source_scale,
        )
        cp = self.protocol["model"]["cpeptide"]
        q1 = sb / (cp["k3"] * theta[2])
        initial = np.r_[
            state, sb, basal["P_pmol_kg"], np.zeros(5), q1, cp["k1"] / cp["k2"] * q1, 0, 0
        ]
        if not np.isfinite(initial).all() or np.any(initial[list(PHYSICAL) + [20, 21]] < 0):
            raise ValueError("Conditioning produced a nonphysical initial inventory")
        rhs = self._rhs(params, basal, source, 0, theta[2])
        physical_derivatives = rhs(0, initial)[list(range(15)) + [20, 21]]
        if (
            np.max(np.abs(physical_derivatives))
            > self.protocol["criteria"]["baseline_derivative_error"]
        ):
            raise ValueError("Conditioned fasting state is not an equilibrium")
        return params, basal, source, initial, rhs

    def _rhs(self, params, basal, source, load, k3_scale):
        parent_rhs = rhs_factory(params, basal, source, load)
        cp = self.protocol["model"]["cpeptide"]
        k1, k2, k3 = cp["k1"], cp["k2"], cp["k3"] * k3_scale

        def rhs(time, state):
            parent = parent_rhs(time, state)
            central, peripheral = state[20:22]
            exchange, removed = k1 * central - k2 * peripheral, k3 * central
            pancreatic = parent[16]
            return np.r_[parent, pancreatic - exchange - removed, exchange, removed, pancreatic]

        return rhs

    def simulate(self, theta, times=None, solver="fit", load=None, source_scale=1.0):
        theta = self._theta(theta)
        params, basal, source, initial, _ = self.prepare(theta, source_scale)
        horizon = self.protocol["model"]["horizon_min"]
        if times is None:
            step = self.protocol["model"]["output_step_min"]
            times = np.arange(0, horizon + step / 2, step)
        times = np.asarray(times, dtype=float)
        if (
            times.ndim != 1
            or len(times) < 2
            or not np.isfinite(times).all()
            or times[0] != 0
            or times[-1] != horizon
            or np.any(np.diff(times) <= 0)
        ):
            raise ValueError("Output grid must increase from zero to the complete horizon")
        load = self.protocol["model"]["load_mg"] if load is None else load
        if isinstance(load, (bool, np.bool_, str, bytes)) or not np.isscalar(load):
            raise ValueError("Gastric load must be finite and nonnegative")
        if not np.isfinite(load) or load < 0:
            raise ValueError("Gastric load must be finite and nonnegative")
        if solver not in self.protocol["solvers"]:
            raise ValueError("Unknown solver specification")
        opts = settings(self.protocol["solvers"][solver])
        initial = initial.copy()
        initial[0] = load
        rhs = self._rhs(params, basal, source, load, theta[2])
        low, high = self.protocol["model"]["domain"]["glucose_mg_dl"]
        tolerance = self.protocol["model"]["domain"]["negative_amount_tolerance"]

        def lower(time, state):
            return state[3] / params["Vg"] - low

        def upper(time, state):
            return high - state[3] / params["Vg"]

        def negative(time, state):
            return np.min(state[list(PHYSICAL) + [20, 21]]) + tolerance

        events = (lower, upper, negative)
        for event in events:
            event.terminal = True
            event.direction = -1
        if any(event(0, initial) <= 0 for event in events):
            raise ValueError("Initial state outside the declared model domain")
        result = solve_ivp(
            rhs,
            (0, horizon),
            initial,
            t_eval=times,
            events=events,
            first_step=min(horizon, opts["max_step"]),
            **opts,
        )
        if (
            result.status != 0
            or result.y.shape != (24, len(times))
            or not np.array_equal(result.t, times)
            or not np.isfinite(result.y).all()
        ):
            raise RuntimeError(
                "Joint solve failed, exited its domain, or was incomplete/nonfinite: "
                + result.message
            )
        states = result.y.T
        observations = states[:, [3, 5, 20]] / np.array(
            [params["Vg"], params["Vi"], self.protocol["model"]["cpeptide"]["volume_l_kg"]]
        )
        if not np.isfinite(observations).all() or np.any(
            states[:, list(PHYSICAL) + [20, 21]] < -tolerance
        ):
            raise RuntimeError("Joint solve returned nonfinite or negative observations/amounts")
        if np.any(observations[:, 0] < low) or np.any(observations[:, 0] > high):
            raise RuntimeError("Sampled glucose left the declared model domain")
        return {
            "theta": theta,
            "times": times,
            "observations": observations,
            "states": states,
            "initial": initial,
            "baseline": basal,
            "status": "completed",
            "failure": None,
            "solver": solver,
            "nfev": result.nfev,
        }
