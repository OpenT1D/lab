"""BC-012 observation-volume wrapper around the unchanged BC-011 model.

The fourth multiplier scales only central C-peptide concentration. It never
changes an amount, initial inventory, source, rate constant or mass ledger.
"""

import copy
import json
from collections import OrderedDict
from pathlib import Path

import numpy as np

from experiments.m4.joint_identifiability.common import validate as validate_parent
from experiments.m4.joint_identifiability.model import Model as ParentModel

from .common import validate


class Model:
    """Exact BC-011 forward solves with an independently varied Cp observation volume."""

    CACHE_SIZE = 96

    def __init__(self, protocol):
        validate(protocol)
        self.protocol = protocol
        self.parent = json.loads(
            (Path(__file__).parents[1] / "joint_identifiability" / "protocol.json").read_text()
        )
        validate_parent(self.parent)
        if protocol["parent_protocol"] != self.parent["id"] or (
            protocol["model"]["volume_l_kg"] != self.parent["model"]["cpeptide"]["volume_l_kg"]
        ):
            raise ValueError("BC-012 requires its unchanged BC-011 parent and volume units")
        self.base = ParentModel(self.parent)
        self.identity, self.params, self.sd = self.base.identity, self.base.params, self.base.sd
        self._cache = OrderedDict()

    def _theta(self, theta):
        if any(
            isinstance(x, (bool, np.bool_, str, bytes, complex, np.complexfloating))
            for x in np.asarray(theta, dtype=object).flat
        ):
            raise ValueError("Four finite real numeric parameters required")
        value = np.asarray(theta, dtype=float)
        if (
            value.shape != (4,)
            or not np.isfinite(value).all()
            or np.any(value < self.protocol["model"]["lower"])
            or np.any(value > self.protocol["model"]["upper"])
        ):
            raise ValueError("Parameters must lie within the four frozen positive bounds")
        return value

    def simulate(self, theta, times=None, solver="fit", load=None, source_scale=1.0):
        """Return detached parent arrays and Cp divided by the volume multiplier.

        Exact parent solves for the normal experiment grid can be reused across
        volume perturbations. Custom grids, loads and source diagnostics bypass
        this bounded cache and retain the unchanged parent's input validation.
        """
        theta = self._theta(theta)
        cacheable = (
            times is None
            and load is None
            and isinstance(solver, str)
            and solver in self.parent["solvers"]
            and isinstance(source_scale, (int, float, np.integer, np.floating))
            and not isinstance(source_scale, (bool, np.bool_))
            and source_scale == 1
        )
        key = (tuple(theta[:3]), solver) if cacheable else None
        if cacheable and key in self._cache:
            self._cache.move_to_end(key)
            original = self._cache[key]
        else:
            original = self.base.simulate(
                theta[:3], times=times, solver=solver, load=load, source_scale=source_scale
            )
            if cacheable:
                self._cache[key] = copy.deepcopy(original)
                if len(self._cache) > self.CACHE_SIZE:
                    self._cache.popitem(last=False)
        result = copy.deepcopy(original)
        result["theta"] = theta.copy()
        # Divide concentration once, after integration. Division by 1 is exact.
        result["observations"][:, 2] /= theta[3]
        return result
