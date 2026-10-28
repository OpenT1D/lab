"""C1 training cannot silently change M1's installed numeric runtime."""

import unittest

from experiments.c1.g2p2c_runtime_parity import C1, M0, _lock_versions, _require_parity


class G2P2CRuntimeParityTests(unittest.TestCase):
    def test_core_locks_and_installed_locations_must_match(self):
        m0_lock = _lock_versions(M0 / "uv.lock")
        c1_lock = _lock_versions(C1 / "uv.lock")
        m0_installed = {
            "python": "3.12.13",
            "simglucose_file": str(
                M0 / ".venv/lib/python3.12/site-packages/simglucose/__init__.py"
            ),
            "versions": dict(m0_lock),
        }
        c1_installed = {
            "python": "3.12.13",
            "simglucose_file": str(
                C1 / ".venv/lib/python3.12/site-packages/simglucose/__init__.py"
            ),
            "versions": dict(c1_lock),
        }
        _require_parity(m0_lock, c1_lock, m0_installed, c1_installed)
        with self.assertRaisesRegex(ValueError, "runtime or locks differ"):
            _require_parity(m0_lock, dict(c1_lock, scipy="0.0"), m0_installed, c1_installed)
        with self.assertRaisesRegex(ValueError, "runtime or locks differ"):
            _require_parity(
                m0_lock,
                c1_lock,
                m0_installed,
                dict(c1_installed, simglucose_file="/tmp/other/simglucose/__init__.py"),
            )


if __name__ == "__main__":
    unittest.main()
