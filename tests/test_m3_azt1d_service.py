"""Synthetic phase, provenance, allocation and privacy checks for AZ preparation."""

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.m3.azt1d.common import digest, read, save
from experiments.m3.azt1d.fixtures import generate
from experiments.m3.azt1d.service import human_gate, load_conversion, normalize, prepare


class AZT1DServiceTests(unittest.TestCase):
    def make_fixture(self, root):
        source = root / "input"
        generate(source)
        return source

    def test_roundtrip_exclusions_and_all_three_synthetic_phases(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = self.make_fixture(root)
            for phase in ("development", "validation", "evaluation"):
                normalized = root / phase
                normalize(source / "source.csv", source / f"{phase}-intake.json", normalized)
                intake, rows, _ = load_conversion(normalized)
                self.assertEqual(intake["phase"], phase)
                self.assertTrue(rows)
                self.assertTrue(all(intake["start_us"] <= t < intake["end_us"] for t in rows))
                if phase != "development":
                    with self.assertRaisesRegex(ValueError, "Unexpected conversion phase"):
                        prepare(normalized, root / "forbidden")
            prepare(root / "development", root / "prepared")
            result, _ = read(root / "prepared/development.json")
            self.assertFalse(result["model_fit_or_evaluation"])
            self.assertFalse(result["eligible_development"])
            self.assertEqual(
                len(result["registered_origins_us"]),
                len(result["training_windows"]) + sum(result["window_exclusions"].values()),
            )
            self.assertGreater(len(result["training_windows"]), 0)
            self.assertIn("target_ambiguous", result["window_exclusions"])
            with self.assertRaises(FileExistsError):
                prepare(root / "development", root / "prepared")

    def test_prepare_rejects_later_phases_before_opening_glucose(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = self.make_fixture(root)
            for phase in ("validation", "evaluation"):
                output = root / phase
                normalize(source / "source.csv", source / f"{phase}-intake.json", output)

                def metadata_only(path):
                    self.assertNotEqual(Path(path).name, "observations.json")
                    return read(path)

                with patch("experiments.m3.azt1d.service.read", side_effect=metadata_only):
                    with self.assertRaisesRegex(ValueError, "Unexpected conversion phase"):
                        prepare(output, root / "forbidden")
                self.assertFalse((root / "forbidden").exists())

    def test_tampering_and_uncompleted_conversion_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = self.make_fixture(root)
            output = root / "converted"
            normalize(source / "source.csv", source / "development-intake.json", output)
            state, _ = read(output / "status.json")
            save(output / "status.json", dict(state, status="started"))
            with self.assertRaisesRegex(ValueError, "did not complete"):
                load_conversion(output)
            save(output / "status.json", state)
            with (output / "observations.json").open("a") as stream:
                stream.write(" ")
            with self.assertRaisesRegex(ValueError, "Observations changed"):
                load_conversion(output)

    def test_rehashed_but_noncontiguous_lineage_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = self.make_fixture(root)
            output = root / "converted"
            normalize(source / "source.csv", source / "development-intake.json", output)
            doc, _ = read(output / "observations.json")
            doc["rows"][-1]["source_rows"] = [99999]
            save(output / "observations.json", doc)
            receipt, _ = read(output / "conversion.json")
            receipt["observations_sha256"] = digest((output / "observations.json").read_bytes())
            save(output / "conversion.json", receipt)
            with self.assertRaisesRegex(ValueError, "row accounting"):
                load_conversion(output)

    def test_missing_revision_metadata_is_not_accepted_as_provenance(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = self.make_fixture(root)
            output = root / "converted"
            normalize(source / "source.csv", source / "development-intake.json", output)
            receipt, _ = read(output / "conversion.json")
            for key in ("revision", "dirty"):
                altered = copy.deepcopy(receipt)
                del altered["provenance"][key]
                save(output / "conversion.json", altered)
                with self.subTest(key=key), self.assertRaisesRegex(ValueError, "revision metadata"):
                    load_conversion(output)

    def test_frozen_intake_identity_checked_before_glucose(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = self.make_fixture(root)
            output = root / "converted"
            normalize(source / "source.csv", source / "development-intake.json", output)
            expected, _ = read(output / "intake.json")
            expected["person"] = "different-invented-person"

            def metadata_only(path):
                self.assertNotEqual(Path(path).name, "observations.json")
                return read(path)

            with patch("experiments.m3.azt1d.service.read", side_effect=metadata_only):
                with self.assertRaisesRegex(ValueError, "frozen request"):
                    load_conversion(output, expected_intake=expected)

    def human_metadata(self, root):
        # Completely invented metadata exercises gates; this is not actual consent or data.
        source = self.make_fixture(root)
        request, _ = read(source / "development-intake.json")
        request["kind"] = "human"
        members = [
            {
                "alias": "invented-person" if n == 0 else f"invented-{n}",
                "sha256": request["source_sha256"] if n == 0 else digest(str(n).encode()),
                "group": "study" if n < 20 else "reserved",
            }
            for n in range(25)
        ]
        policy = digest(b"invented allocation policy")
        allocation = {"files": members, "policy_sha256": policy}
        save(root / "allocation.json", allocation)
        split = {
            "schema": "opent1d.azt1d.partition-reference/1",
            "alias": request["person"],
            "phase": request["phase"],
            "source_sha256": request["source_sha256"],
            "policy_sha256": policy,
            "data_row_start_inclusive": request["row_start"],
            "data_row_stop_exclusive": request["row_stop"],
            "rows": request["row_stop"] - request["row_start"],
            "bounds_seconds": [request["start_us"] / 1_000_000, request["end_us"] / 1_000_000],
        }
        save(root / "partition.json", split)
        for key, filename in (
            ("allocation_reference", "allocation.json"),
            ("partition_reference", "partition.json"),
        ):
            request[key] = {
                "file": str(root / filename),
                "sha256": digest((root / filename).read_bytes()),
            }
        request["reviews"] = {
            key: True
            for key in (
                "authorized_processing",
                "derived_retention",
                "release_reviewed",
                "units_reviewed",
                "status_policy_reviewed",
                "availability_reviewed",
                "clock_reviewed",
            )
        }
        request["reviews"].update(
            {
                key: "invented test-only reference"
                for key in (
                    "authorization_reference",
                    "retention_reference",
                    "availability_reference",
                )
            }
        )
        return request, source

    def test_human_gate_requires_reviews_and_preserves_allocation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            request, source = self.human_metadata(root)
            paths = (source / "source.csv", root / "request.json", root / "output")
            human_gate(request, *paths)
            for mutate in ("review", "reserved", "bounds", "allocation_bytes"):
                value = copy.deepcopy(request)
                if mutate == "review":
                    value["reviews"]["status_policy_reviewed"] = False
                elif mutate == "reserved":
                    value["person"] = "invented-24"
                elif mutate == "bounds":
                    value["row_stop"] -= 1
                else:
                    value["allocation_reference"]["sha256"] = "0" * 64
                with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                    human_gate(value, *paths)

    def test_human_evaluation_gate_rejects_before_source_open(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            request, _ = self.human_metadata(root)
            request["phase"] = "evaluation"
            split, _ = read(root / "partition.json")
            split["phase"] = "evaluation"
            save(root / "partition.json", split)
            request["partition_reference"]["sha256"] = digest(
                (root / "partition.json").read_bytes()
            )
            save(root / "request.json", request)
            with self.assertRaisesRegex(ValueError, "evaluation conversion is not enabled"):
                normalize(root / "absent.csv", root / "request.json", root / "output")
            self.assertFalse((root / "output").exists())

    def test_failed_normalization_retains_safe_status_and_cli_hides_records(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = self.make_fixture(root)
            request, _ = read(source / "development-intake.json")
            secret = "DO-NOT-LOG-THIS-INVENTED-RECORD"
            (source / "source.csv").write_text(secret)
            request["source_sha256"] = digest(secret.encode())
            save(source / "development-intake.json", request)
            output = root / "failed"
            process = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "experiments.m3.azt1d",
                    "normalize",
                    "--input",
                    str(source / "source.csv"),
                    "--intake",
                    str(source / "development-intake.json"),
                    "--output",
                    str(output),
                ],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(process.returncode, 0)
            self.assertNotIn(secret, process.stdout + process.stderr)
            state = json.loads((output / "status.json").read_text())
            self.assertEqual(state["status"], "failed")
            self.assertNotIn(secret, json.dumps(state))
