"""Consequential boundary counterexamples using an explicitly synthetic format fixture."""

import json
import tempfile
import unittest
from pathlib import Path

from m2_fixture import fixture

from experiments.m0.simglucose.recording import write_json
from experiments.m1.artifacts import digest, strict_json
from experiments.m2.analysis import read_run


class FaultBoundaryTests(unittest.TestCase):
    def test_complete_fixture_then_missing_final_point(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "case"
            m = fixture(out)
            self.assertEqual(read_run(out)["manifest"]["status"], "completed")
            rows = (out / "trace.jsonl").read_bytes().splitlines(keepends=True)
            (out / "trace.jsonl").write_bytes(b"".join(rows[:-1]))
            m["completed_rows"] = 2880
            m["files_sha256"]["trace.jsonl"] = digest(out / "trace.jsonl")
            write_json(out / "manifest.json", m)
            with self.assertRaisesRegex(ValueError, "False completion"):
                read_run(out)

    def test_changed_input_bytes_with_identical_json_value(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "case"
            fixture(out)
            self.assertEqual(read_run(out)["manifest"]["status"], "completed")
            original = strict_json((out / "config.json").read_bytes())
            with (out / "config.json").open("ab") as stream:
                stream.write(b" ")
            self.assertEqual(strict_json((out / "config.json").read_bytes()), original)
            with self.assertRaisesRegex(ValueError, "Artifact changed: config.json"):
                read_run(out)

    def test_package_provenance_matches_locked_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "case"
            m = fixture(out)
            self.assertEqual(read_run(out)["manifest"]["status"], "completed")
            original = strict_json((out / "runtime.json").read_bytes())
            # A nonempty object must not stand in for the actual locked environment.
            for packages in ({"fixture": True}, {}, None):
                runtime = original | {"packages": packages}
                write_json(out / "runtime.json", runtime)
                m["files_sha256"]["runtime.json"] = digest(out / "runtime.json")
                write_json(out / "manifest.json", m)
                with self.assertRaisesRegex(ValueError, "package provenance"):
                    read_run(out)
            changed = json.loads(json.dumps(original["packages"]))
            name = next(k for k, v in changed.items() if v.get("dev") is True)
            changed[name]["dev"] = 1  # Python equality alone would equate this with True.
            write_json(out / "runtime.json", original | {"packages": changed})
            m["files_sha256"]["runtime.json"] = digest(out / "runtime.json")
            write_json(out / "manifest.json", m)
            with self.assertRaisesRegex(ValueError, "package provenance"):
                read_run(out)
