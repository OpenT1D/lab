"""Independent kinetic checks in the existing C-peptide environment."""

import unittest

import numpy as np

from experiments.m4.c_peptide.model import Parameters, simulate
from experiments.m4.c_peptide.reference import constant_schedule
from experiments.m4.kinetic_inlet.forcing import Forcing
from experiments.m4.paired_kinetics.oracle import cpeptide

from .common import HERE, read


class ObservationNumerics(unittest.TestCase):
    def setUp(self):
        self.p = read(HERE / "protocol.json")
        self.params = Parameters(**self.p["cpeptide"]["parameters"])
        self.solver = self.p["solvers"][-1]

    def test_published_kernel_with_nonzero_inventory_and_step(self):
        times = np.arange(0, 60.25, 0.25)
        forcing = Forcing([0, 10, 30, 60], [1, 3, 1], [1, 3, 1])
        initial = [1 / self.params.k3, self.params.k1 / self.params.k2 / self.params.k3, 0, 0]
        actual = simulate(times, self.params, forcing, initial, self.solver)
        kernel = constant_schedule(times, self.params, forcing, initial)
        np.testing.assert_allclose(
            actual[:, 0] / self.params.volume_l_kg, kernel, atol=1e-7, rtol=0
        )
        np.testing.assert_allclose(
            actual, cpeptide(times, self.params, forcing, initial), atol=1e-8, rtol=0
        )

    def test_linear_input_mass_and_volume_scaling(self):
        times = np.arange(0, 60.25, 0.25)
        forcing = Forcing([0, 20, 60], [0, 4], [4, 0])
        actual = simulate(times, self.params, forcing, [0] * 4, self.solver)
        oracle = cpeptide(times, self.params, forcing, [0] * 4)
        np.testing.assert_allclose(actual, oracle, atol=1e-8, rtol=0)
        self.assertAlmostEqual(actual[-1, 3], 120, places=8)
        self.assertAlmostEqual(sum(actual[-1, :3]), 120, places=8)
        for scale in (0.5, 2):
            params = Parameters(
                self.params.k1, self.params.k2, self.params.k3, self.params.volume_l_kg * scale
            )
            scaled = Forcing(
                forcing.edges, [q * scale for q in forcing.left], [q * scale for q in forcing.right]
            )
            y = simulate(times, params, scaled, [0] * 4, self.solver)
            np.testing.assert_allclose(
                y[:, 0] / params.volume_l_kg,
                actual[:, 0] / self.params.volume_l_kg,
                atol=1e-7,
                rtol=0,
            )

    def test_no_exogenous_source_and_declared_basal(self):
        times = [0, 10, 240]
        for q in (0, 0.7741402585):
            initial = [
                q / self.params.k3,
                self.params.k1 / self.params.k2 * q / self.params.k3,
                0,
                0,
            ]
            y = simulate(times, self.params, Forcing([0, 240], [q], [q]), initial, self.solver)
            np.testing.assert_allclose(y[:, :2], np.tile(initial[:2], (3, 1)), atol=1e-10, rtol=0)
            self.assertAlmostEqual(y[-1, 3], q * 240, places=9)


if __name__ == "__main__":
    unittest.main()
