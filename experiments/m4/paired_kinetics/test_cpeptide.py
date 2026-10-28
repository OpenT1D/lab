"""Run in the locked C-peptide runtime: independent affine/nonzero-state reference."""

import unittest

import numpy as np

from experiments.m4.c_peptide.model import Parameters, simulate
from experiments.m4.c_peptide.reference import constant_schedule
from experiments.m4.kinetic_inlet.forcing import Forcing
from experiments.m4.paired_kinetics.oracle import cpeptide

SETTINGS = {"method": "DOP853", "rtol": 1e-11, "atol": 1e-13, "max_step": 0.125}


class CpeptideTests(unittest.TestCase):
    def test_matrix_reference_matches_published_constant_kernel(self):
        p = Parameters(0.037, 0.031, 0.052, 0.0655)
        force = Forcing([0, 0.7, 10], [1, 3], [1, 3])
        t = np.linspace(0, 10, 21)
        initial = [4, 2, 0, 0]
        expected = cpeptide(t, p, force, initial)
        np.testing.assert_allclose(
            expected[:, 0] / p.volume_l_kg, constant_schedule(t, p, force, initial), atol=1e-9
        )
        np.testing.assert_allclose(simulate(t, p, force, initial, SETTINGS), expected, atol=1e-9)

    def test_affine_input_matches_single_compartment_closed_form(self):
        p = Parameters(0, 0.05, 0.05, 0.1)
        t = np.linspace(0, 20, 41)
        force = Forcing([0, 20], [0], [40])
        expected = 4 * np.exp(-0.05 * t) + 2 * (t / 0.05 + np.expm1(-0.05 * t) / 0.05**2)
        result = cpeptide(t, p, force, [4, 0, 0, 0])
        np.testing.assert_allclose(result[:, 0], expected, rtol=0, atol=1e-9)
        np.testing.assert_allclose(result[:, :3].sum(axis=1) - result[:, 3], 4, atol=1e-10)

    def test_equal_decay_rates_with_initial_peripheral_inventory(self):
        p = Parameters(0, 0.05, 0.05, 0.1)
        t = np.arange(11, dtype=float)
        force = Forcing([0, 10], [0], [0])
        result = cpeptide(t, p, force, [0, 2, 0, 0])
        np.testing.assert_allclose(result[:, 0], 2 * 0.05 * t * np.exp(-0.05 * t), atol=1e-12)


if __name__ == "__main__":
    unittest.main()
