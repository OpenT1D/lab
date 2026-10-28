"""Packet retention, refusal and explicit setup boundaries; no physiology fixtures."""

import copy
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.usability import __main__ as entry
from experiments.usability.packet import (
    SCHEMA,
    clean_revision,
    digest,
    dump,
    encoded,
    inventory,
    receive,
    verify,
    write_first_steps,
    write_guides,
)
from experiments.usability.tasks import goals, participant_goals, session_goals

ROOT = Path(__file__).resolve().parents[1]


class PacketTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name).resolve()
        self.packet = self.directory / "packet"
        self.packet.mkdir()
        (self.packet / "source.bundle").write_bytes(b"unit-only byte inventory, not a Git bundle")
        references = {}
        for kind in ("complete", "interrupted"):
            folder = self.packet / "references" / kind
            (folder / "empty").mkdir(parents=True)
            for artifact in ("report.json", "report.md", "figure.svg"):
                (folder / artifact).write_text("Unit-only integrity payload")
            references[kind] = {
                "path": "references/" + kind,
                "status": "completed" if kind == "complete" else "interrupted",
                "passed": kind == "complete",
                "report_sha256": {
                    name: digest((folder / name).read_bytes())
                    for name in ("report.json", "report.md", "figure.svg")
                },
                "original_inventory_sha256": digest(encoded(inventory(folder))),
            }
        self.record = {
            "schema": SCHEMA,
            "id": "packet-" + "a" * 32,
            "commit": "a" * 40,
            "language": "nl",
            "target": "windows-wsl",
            "participant_results": "not_recorded",
            "prepared_platform": "unit test",
            "rights_scope": "unit-only inventory; not a native archive",
            "bundle_sha256": digest((self.packet / "source.bundle").read_bytes()),
            "references": references,
            "goals": goals("nl"),
        }
        self.seal()

    def seal(self):
        (self.packet / "manifest.json").unlink(missing_ok=True)
        self.record["inventory"] = inventory(self.packet)
        dump(self.packet / "manifest.json", self.record)

    def test_receive_preserves_bytes_and_empty_directories_without_overwriting(self):
        before = inventory(self.packet)
        output = self.directory / "received"
        self.assertEqual(receive(self.packet, output), self.record)
        self.assertEqual(inventory(output), before)
        self.assertEqual(inventory(self.packet), before)
        with self.assertRaisesRegex(ValueError, "fresh"):
            receive(self.packet, output)
        with self.assertRaisesRegex(ValueError, "overlaps"):
            receive(self.packet, self.packet / "child")

    def test_changed_missing_extra_and_empty_directory_payloads_refused(self):
        path = self.packet / "references/complete/report.json"
        original = path.read_bytes()
        path.write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "differ"):
            verify(self.packet)
        path.write_bytes(original)
        path.unlink()
        with self.assertRaisesRegex(ValueError, "differ"):
            verify(self.packet)
        path.write_bytes(original)
        extra = self.packet / "extra"
        extra.mkdir()
        with self.assertRaisesRegex(ValueError, "differ"):
            verify(self.packet)

    def test_symlink_hardlink_and_special_files_refused_before_read(self):
        linked = self.packet / "linked"
        linked.symlink_to(self.packet / "source.bundle")
        with self.assertRaisesRegex(ValueError, "Linked"):
            verify(self.packet)
        linked.unlink()
        os.link(self.packet / "source.bundle", linked)
        with self.assertRaisesRegex(ValueError, "Linked"):
            verify(self.packet)
        linked.unlink()
        os.mkfifo(linked)
        with self.assertRaisesRegex(ValueError, "special"):
            verify(self.packet)

    def test_role_goal_or_observation_claim_cannot_be_resealed(self):
        original = copy.deepcopy(self.record)
        changes = (
            ("participant_results", "completed"),
            ("target", "native-windows"),
            ("goals", []),
            ("references", {"complete": original["references"]["complete"]}),
        )
        for key, value in changes:
            with self.subTest(key=key):
                self.record = copy.deepcopy(original)
                self.record[key] = value
                self.seal()
                with self.assertRaises(ValueError):
                    verify(self.packet)
        self.record = original
        self.record["references"]["interrupted"]["passed"] = True
        self.seal()
        with self.assertRaisesRegex(ValueError, "role/status"):
            verify(self.packet)

    def test_bounds_and_duplicate_manifest_keys_refused(self):
        with patch("experiments.usability.packet.MAX_BYTES", 4):
            with self.assertRaisesRegex(ValueError, "limits"):
                inventory(self.packet)
        with patch("experiments.usability.packet.MAX_FILES", 1):
            with self.assertRaises(ValueError):
                inventory(self.packet)
        raw = (self.packet / "manifest.json").read_text()
        (self.packet / "manifest.json").write_text(raw[:-2] + ', "schema": "duplicate"}\n')
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            verify(self.packet)

    def test_first_steps_readable_without_server_and_no_fake_results(self):
        write_first_steps(self.directory, self.record)
        text = (self.directory / "FirstSteps.html").read_text()
        self.assertIn('lang="nl"', text)
        self.assertIn('href="assets/style.css"', text)
        self.assertIn("WSL", text)
        self.assertIn("nog geen", text)
        self.assertNotIn("/test/", text)
        self.assertNotIn("completed_without", text)

    def test_mmtt_packet_has_two_assignments_and_separate_setup_feedback(self):
        self.record["goals"] = session_goals("nl", "mmtt")
        self.seal()
        self.assertEqual(verify(self.packet), self.record)
        self.assertEqual(len(participant_goals(self.record["goals"])), 2)
        self.assertEqual(
            [item["id"] for item in self.record["goals"]],
            ["installation", "startup", "mmtt_assumptions", "mmtt_sampling"],
        )
        write_first_steps(self.packet, self.record)
        for name in ("FirstSteps", "Participant", "Observations"):
            text = (self.packet / (name + ".html")).read_text()
            self.assertNotIn("keert de richting om", text)
            self.assertNotIn("/test/", text)
        card = (self.packet / "FirstSteps.html").read_text()
        self.assertIn("geen gewone Windows-installatie", card)
        self.assertIn("internet", card)
        self.assertIn("M4-Observations.html", card)
        self.assertIn('"id": "mmtt_sampling"', (self.packet / "Observations.html").read_text())
        m4 = (self.packet / "M4-Observations.html").read_text()
        self.assertIn('"id": "interpret_partial"', m4)
        self.assertNotIn('"id": "mmtt_sampling"', m4)

    def test_mmtt_goals_cannot_be_silently_mixed_or_reworded(self):
        for changes in (
            session_goals("nl", "mmtt") + goals("nl"),
            [{"id": "mmtt_assumptions", "goal": "Invented answer"}],
        ):
            self.record["goals"] = changes
            self.seal()
            with self.assertRaisesRegex(ValueError, "goals changed"):
                verify(self.packet)

    def test_offline_guides_link_the_frozen_revision_to_its_public_or_private_repository(self):
        root = self.directory / "source"
        (root / "docs").mkdir(parents=True)
        for name in (
            "local-gui",
            "gui-test-session",
            "gui-researcher-exercise",
            "observation-analysis",
            "mmtt-sampling",
        ):
            (root / "docs" / (name + ".md")).write_text(
                "# Guide\n\n[Policy](publication-security.md)\n[Local guide](mmtt-sampling.md)\n"
            )
        for public in (False, True):
            output = self.directory / ("public-guides" if public else "private-guides")
            output.mkdir()
            if public:
                (root / "publication-snapshot.json").write_text("{}")
            with patch("experiments.usability.packet.clean_revision", return_value="b" * 40):
                write_guides(output, root)
            page = (output / "guides/local-gui.html").read_text()
            repository = "OpenT1D/lab" if public else "OpenT1D/OpenT1D"
            self.assertIn(
                "https://github.com/"
                + repository
                + "/blob/"
                + "b" * 40
                + "/docs/publication-security.md",
                page,
            )
            self.assertIn('href="mmtt-sampling.html"', page)

    def test_clean_revision_refuses_uncommitted_and_untracked_source(self):
        root = self.directory / "source"
        root.mkdir()
        subprocess.run(["git", "init", "--quiet", str(root)], check=True)
        path = root / "source.txt"
        path.write_text("committed")
        subprocess.run(["git", "add", "source.txt"], cwd=root, check=True)
        subprocess.run(
            [
                "git",
                "-c",
                "user.name=Unit fixture",
                "-c",
                "user.email=fixture@example.invalid",
                "commit",
                "--quiet",
                "-m",
                "unit fixture",
            ],
            cwd=root,
            check=True,
        )
        self.assertEqual(len(clean_revision(root)), 40)
        path.write_text("changed")
        with self.assertRaisesRegex(ValueError, "Commit"):
            clean_revision(root)
        path.write_text("committed")
        (root / "untracked.txt").write_text("not frozen")
        with self.assertRaisesRegex(ValueError, "Commit"):
            clean_revision(root)

    def test_native_windows_rejected_before_gui_import(self):
        with (
            patch.object(entry, "verify", return_value=self.record),
            patch.object(entry, "clean_revision", return_value=self.record["commit"]),
            patch.object(entry.sys, "platform", "win32"),
        ):
            with self.assertRaisesRegex(ValueError, "WSL"):
                entry.selected(self.packet)

    def test_setup_failure_has_nonzero_exit_and_preserved_receipt(self):
        with (
            patch("sys.argv", ["usability", "check", "--packet", str(self.packet)]),
            patch.object(
                entry, "setup", return_value={"setup": {"ready": False}, "receipt": "retained"}
            ),
        ):
            with self.assertRaises(SystemExit) as caught:
                entry.main()
            self.assertEqual(caught.exception.code, 2)

    @unittest.skipUnless(shutil.which("node"), "Node is required for worksheet contract checks")
    def test_actual_worksheet_import_and_retest_guards(self):
        result = subprocess.run(
            [shutil.which("node"), "tests/usability_frontend.cjs"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertGreaterEqual(json.loads(result.stdout)["checks"], 10)


if __name__ == "__main__":
    unittest.main()
