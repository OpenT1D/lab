"""Packet binding and unanswered observations; actual native rehearsal is separate."""

import copy
import importlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tests.test_installed_gui import PACKAGE

packet = importlib.import_module(PACKAGE + ".study_packet")


class ReferenceSDK:
    def __init__(self, source):
        self.source = source
        self.source.mkdir()
        (source / "HEAD.json").write_text("unchanged reference")
        self.candidate = {
            "source": {"dirty": False, "revision": "a" * 40},
            "descriptor_sha256": "b" * 64,
        }
        self.plans, self.attempts = {}, []
        for role in packet.ROLES:
            task = "mmtt-sensitivity" if role == "mmtt" else "m4-study-installed"
            case = "gastric_load_15g" if role == "load15" else "fasting"
            self.plans[role] = {
                "plan": role,
                "task": task,
                "parent": "fasting" if role == "load15" else None,
                "boundary": {"planned_slots": ["dalla_man/" + case, "ultradian/" + case]},
                "original_sha256": {"input": packet.sha256(task.encode())},
            }
            self.attempts.append(
                {
                    "id": role,
                    "plan": role,
                    "outcome": {
                        "completeness": "incomplete" if role == "failed" else "complete",
                        "payload": "forensic" if role == "failed" else "native",
                    },
                }
            )
        self.readers = []

    def installation(self):
        return copy.deepcopy(self.candidate)

    def example(self, task, output, *, case):
        output.mkdir()
        target = output / "input"
        target.write_bytes(task.encode())
        return {"inputs": {"input": str(target)}}

    def Project(self, location):
        sdk = self

        class Project:
            def info(self):
                return {"head": {"tip": "original"}, "attempts": copy.deepcopy(sdk.attempts)}

            def plan(self, identity):
                return copy.deepcopy(sdk.plans[identity])

            def relocate(self, output):
                shutil.copytree(location, output)

            def reconstruct(self, identity, output, *, allow_failed):
                sdk.readers.append((Path(location), identity, allow_failed))
                output.mkdir()
                names = ["report.md", "report.json"]
                if identity != "mmtt":
                    names.append("figure.svg")
                for name in names:
                    (output / name).write_bytes((identity + name).encode())
                return {
                    "report_sha256": {
                        name: packet.sha256((output / name).read_bytes()) for name in names
                    }
                }

        return Project()


class SharedGUIPacketTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="sdk-packet-unit-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.sdk = ReferenceSDK(self.root / "reference")
        self.ids = {role: role for role in packet.ROLES}
        self.output = self.root / "packet"

    def create(self):
        return packet.create(self.sdk.source, self.ids, self.output, sdk=self.sdk)

    def test_actual_bindings_disposable_reader_and_unanswered_materials(self):
        before = packet.inventory(self.sdk.source)
        result = self.create()
        self.assertEqual(result["status"], "prepared")
        self.assertEqual(packet.inventory(self.sdk.source), before)
        self.assertEqual(len(self.sdk.readers), 3)
        self.assertTrue(all(location != self.sdk.source for location, _, _ in self.sdk.readers))
        manifest = json.loads((self.output / "packet.json").read_bytes())
        self.assertEqual(manifest["references"]["failed"]["kind"], "forensic-only")
        self.assertEqual(manifest["references"]["failed"]["report_sha256"], {})
        observations = json.loads(
            (self.output / "facilitator/observations.template.json").read_bytes()
        )
        for task in observations["tasks"]:
            self.assertIsNone(task["status"])
            self.assertIsNone(task["adjudication"])
            self.assertEqual(task["assistance"], [])
        participant = (self.output / "participant/Tasks.html").read_text()
        self.assertNotIn("MMTT key", participant)
        self.assertNotIn("seed 117", participant)
        self.assertEqual(packet.verify(self.output, sdk=self.sdk)["status"], "verified-preparation")
        with self.assertRaisesRegex(ValueError, "new destination"):
            self.create()

    def test_wrong_parent_wrong_inputs_failed_selection_and_dirty_candidate_refuse(self):
        mutations = [
            lambda: self.sdk.plans["load15"].update(parent=None),
            lambda: self.sdk.plans["mmtt"].update(original_sha256={"input": "wrong"}),
            lambda: self.sdk.attempts[-1]["outcome"].update(completeness="complete"),
            lambda: self.sdk.candidate["source"].update(dirty=True),
        ]
        for mutate in mutations:
            self.sdk = ReferenceSDK(self.root / ("reference-" + str(mutations.index(mutate))))
            mutate()
            with self.assertRaises(ValueError):
                self.create()
            self.assertFalse((self.output / "packet.json").exists())

    def test_resealed_answers_and_missing_references_still_refuse(self):
        self.create()
        manifest = self.output / "packet.json"
        original = json.loads(manifest.read_bytes())
        observations = self.output / "facilitator/observations.template.json"
        value = json.loads(observations.read_bytes())
        value["tasks"][0]["status"] = "complete"
        observations.write_bytes(packet.encoded(value))
        revised = copy.deepcopy(original)
        revised["files"]["facilitator/observations.template.json"] = {
            "bytes": observations.stat().st_size,
            "sha256": packet.sha256(observations.read_bytes()),
        }
        manifest.write_bytes(packet.encoded(revised))
        with self.assertRaisesRegex(ValueError, "blank observations"):
            packet.verify(self.output, sdk=self.sdk)
        revised = copy.deepcopy(original)
        revised["references"] = {}
        manifest.write_bytes(packet.encoded(revised))
        with self.assertRaisesRegex(ValueError, "structure"):
            packet.verify(self.output, sdk=self.sdk)

    def test_tamper_extra_file_link_and_candidate_mismatch_refuse(self):
        self.create()
        target = self.output / "participant/Tasks.html"
        original = target.read_bytes()
        target.write_bytes(b"edited tasks")
        with self.assertRaisesRegex(ValueError, "changed"):
            packet.verify(self.output, sdk=self.sdk)
        target.write_bytes(original)
        extra = self.output / "extra"
        extra.write_bytes(b"extra")
        with self.assertRaises(ValueError):
            packet.verify(self.output, sdk=self.sdk)
        extra.unlink()
        extra.symlink_to(target)
        with self.assertRaisesRegex(ValueError, "Linked"):
            packet.verify(self.output, sdk=self.sdk)
        extra.unlink()
        self.sdk.candidate["descriptor_sha256"] = "c" * 64
        with self.assertRaisesRegex(ValueError, "different candidate"):
            packet.verify(self.output, sdk=self.sdk)


if __name__ == "__main__":
    unittest.main()
