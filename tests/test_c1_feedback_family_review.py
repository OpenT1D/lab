"""C1 cross-round review refuses a hidden second configuration change."""

import copy
import unittest

from experiments.c1.feedback_family_review import _matched_inputs
from experiments.c1.feedback_study import plan as first_plan
from experiments.c1.feedback_target_plan import plan as second_plan


class FeedbackFamilyReviewTest(unittest.TestCase):
    def test_only_declared_target_change_is_accepted(self):
        first, second = first_plan(), second_plan()
        _matched_inputs(first, second)
        altered = copy.deepcopy(second)
        altered["cases"][1]["config"]["settings"]["kp_u_h_per_mg_dl"] *= 2
        with self.assertRaises(ValueError):
            _matched_inputs(first, altered)
        altered = copy.deepcopy(second)
        altered["cases"][0]["config"]["seed"] = 999
        with self.assertRaises(ValueError):
            _matched_inputs(first, altered)


if __name__ == "__main__":
    unittest.main()
