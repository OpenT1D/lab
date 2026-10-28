"""C1 failure-audit summaries preserve signed outcomes and clamped requests."""

import unittest

from experiments.c1.diagnose import pid_bounds, signs


class C1DiagnoseTest(unittest.TestCase):
    def test_signs_do_not_relabel_positive_low_exposure_as_benefit(self):
        self.assertEqual(signs([0.2, -0.1, 0, 0]), {"positive": 1, "zero": 2, "negative": 1})

    def test_pid_bounds_count_requests_before_upward_slew(self):
        commands = [
            {"time_min": 1437, "requested_u_h": 4, "final_basal_u_h": 1},
            {"time_min": 1440, "requested_u_h": 0, "final_basal_u_h": 0},
            {"time_min": 1443, "requested_u_h": 4, "final_basal_u_h": 0.2},
            {"time_min": 1446, "requested_u_h": 1, "final_basal_u_h": 1},
        ]
        self.assertEqual(
            pid_bounds(commands),
            {
                "intervals": 3,
                "request_at_zero": 1,
                "request_at_max": 1,
                "upward_slew_limited": 1,
                "max_final_u_h": 1,
            },
        )


if __name__ == "__main__":
    unittest.main()
