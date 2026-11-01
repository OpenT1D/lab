"""Explicit v2 qualification cannot relabel a legacy pass or ignore packet bytes."""

import copy
import json
import unittest

from experiments.shared_services import reader_compatibility
from scripts import qualify_reader_candidate as qualification


class QualificationPolicyTests(unittest.TestCase):
    def current(self, packet=None):
        raw = reader_compatibility.CURRENT_REGISTRY.read_bytes()
        packet = json.loads(raw) if packet is None else packet
        raw = qualification.canonical(packet)
        checksum = qualification.hashlib.sha256(raw).hexdigest()
        result = {
            "reader_transition": {
                "policy": qualification.CURRENT_POLICY,
                "registry_sha256": checksum,
            },
            "reader": copy.deepcopy(packet["successor"])
            | {
                "compatibility": {
                    "schema": qualification.CURRENT_POLICY,
                    "registry_sha256": checksum,
                }
            },
        }
        return raw, result

    def test_historical_default_and_explicit_current_modes_remain_distinct(self):
        old = {"reader_transition": {"policy": qualification.LEGACY_POLICY}}
        qualification.transition_identity(old)
        raw, result = self.current()
        qualification.transition_identity(result, qualification.CURRENT_POLICY, raw)
        with self.assertRaises(AssertionError):
            qualification.transition_identity(result)
        with self.assertRaises(AssertionError):
            qualification.transition_identity(old, qualification.CURRENT_POLICY, raw)
        with self.assertRaises(AssertionError):
            qualification.transition_identity(result, qualification.CURRENT_POLICY)

    def test_current_mode_binds_whole_packet_metadata_and_typed_reader(self):
        raw, result = self.current()
        changed = copy.deepcopy(result)
        changed["reader"]["archived_code_execution"] = 0
        with self.assertRaises(AssertionError):
            qualification.transition_identity(changed, qualification.CURRENT_POLICY, raw)
        changed = copy.deepcopy(result)
        changed["reader"]["reader_static_dependencies_sha256"][
            "experiments/shared_services/reader_compatibility.py"
        ] = "0" * 64
        with self.assertRaises(AssertionError):
            qualification.transition_identity(changed, qualification.CURRENT_POLICY, raw)
        changed = copy.deepcopy(result)
        changed["reader"]["compatibility"]["schema"] = "unknown"
        with self.assertRaises(AssertionError):
            qualification.transition_identity(changed, qualification.CURRENT_POLICY, raw)
        changed = copy.deepcopy(result)
        changed["reader_transition"]["registry_sha256"] = "0" * 64
        with self.assertRaises(AssertionError):
            qualification.transition_identity(changed, qualification.CURRENT_POLICY, raw)
        for field in ("historical_registry_sha256", "m3_predecessor_revision"):
            packet = json.loads(raw)
            packet[field] = "unknown"
            altered_raw, altered_result = self.current(packet)
            with self.assertRaises(AssertionError):
                qualification.transition_identity(
                    altered_result, qualification.CURRENT_POLICY, altered_raw
                )
        packet = json.loads(raw)
        packet["m3_predecessor"]["archived_code_execution"] = 0
        altered_raw, altered_result = self.current(packet)
        with self.assertRaises(AssertionError):
            qualification.transition_identity(
                altered_result, qualification.CURRENT_POLICY, altered_raw
            )


if __name__ == "__main__":
    unittest.main()
