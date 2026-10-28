"""Selected information-boundary checks in the isolated simglucose environment."""

import unittest

from experiments.m1.control import Information


class FaultInformationTests(unittest.TestCase):
    def test_announcement_interval(self):
        information = Information("A")
        delivered = {}
        for t in range(0, 424, 3):
            information.observe(t, 120.0)
            delivered[t] = information.announce(t)
        self.assertEqual(delivered[417], 0)
        self.assertEqual(delivered[420], 45)
        self.assertEqual(delivered[423], 0)
