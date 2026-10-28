"""Portable model boundaries using declared synthetic coefficients, never fitting.

The export unit fixture mocks original learned_read validation. Native integration
must separately exercise an actual fit; these tests do not manufacture fit proof.
"""

import copy
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.m3.azt1d.common import PROTOCOL, ROOT
from experiments.m3.azt1d.common import SCHEMA as SOURCE_SCHEMA
from experiments.m3.azt1d.ledger import _identity_sha
from experiments.m3.common import digest, read, save
from experiments.m3.external.model import FILES, export_model, load_model


def declared_fixture(root, kind="synthetic"):
    """Make test coefficients and the minimal verified-reader return contract."""
    folder, fit = root / "plan", root / "fit"
    folder.mkdir()
    fit.mkdir()
    people = [
        {"id": "invented-a", "source_sha256": "a" * 64},
        {"id": "invented-b", "source_sha256": "b" * 64},
    ]
    identity = {"schema": SOURCE_SCHEMA, "kind": kind, "people": people}
    plan = {"kind": kind, "registry_sha256": "c" * 64, "identity": identity}
    save(folder / "plan.json", plan)
    lock = tomllib.loads((ROOT / "experiments/m3/runtime/uv.lock").read_text())
    model = {
        "method": "sklearn-ridge",
        "settings": {"alpha": 1.0, "fit_intercept": True, "solver": "svd"},
        "mean": [0.0] * 6,
        "scale": [1.0] * 6,
        "coef": [0.0] * 6,
        "intercept": 123.0,
        "feature_rank": 0,
        "singular_values": [0.0] * 6,
        "training_counts": {"invented-a": 300},
        "packages": {p["name"]: p["version"] for p in lock["package"] if "registry" in p["source"]},
    }
    save(fit / "model.json", model)
    frozen = {
        "schema": SOURCE_SCHEMA,
        "stage": "learned",
        "plan_sha256": digest((folder / "plan.json").read_bytes()),
        "model_sha256": digest((fit / "model.json").read_bytes()),
        "validation_sha256": "d" * 64,
        "result_sha256": "e" * 64,
        "inputs_sha256": "f" * 64,
        "ledger_anchor": {
            "identity_sha256": _identity_sha(identity),
            "kind": kind,
            "event": "created",
            "sequence": 0,
        },
        "provenance": {
            "protocol": PROTOCOL,
            "revision": "a" * 40,
            "dirty": False,
            "sources": {"historical-unavailable-source.py": "b" * 64},
            "python": "synthetic historical runtime",
            "platform": "synthetic test",
        },
    }
    save(fit / "freeze.json", frozen)
    # A trace must not be copied just because it exists beside the saved model.
    (fit / "trace.jsonl").write_text("synthetic observation not for export\n")
    return folder / "plan.json", fit, (plan, frozen, digest((fit / "freeze.json").read_bytes()))


def refresh_inventory(folder):
    inventory, _ = read(folder / "bundle.json")
    inventory["files"] = {name: digest((folder / name).read_bytes()) for name in sorted(FILES)}
    save(folder / "bundle.json", inventory)


class ExternalModelBundle(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def exported(self, kind="synthetic"):
        plan, fit, verified = declared_fixture(self.root, kind)
        output = self.root / "bundle"
        with (
            patch("experiments.m3.external.model.learned_read", return_value=verified) as verify,
            patch("experiments.m3.estimator.fit", side_effect=AssertionError("No fitting")),
        ):
            metadata = export_model(plan, fit, output)
        verify.assert_called_once_with(plan, fit)
        return plan, fit, output, metadata

    def test_export_preserves_exact_model_and_freeze_but_no_observations(self):
        _, fit, bundle, metadata = self.exported()
        self.assertEqual({p.name for p in bundle.iterdir()}, FILES | {"bundle.json"})
        for name in ("model.json", "freeze.json"):
            self.assertEqual((bundle / name).read_bytes(), (fit / name).read_bytes())
        self.assertEqual(metadata["source_people"], ["invented-a", "invented-b"])
        self.assertEqual(metadata["training_people"], ["invented-a"])
        self.assertFalse(metadata["verification"]["fit_recomputed"])
        self.assertNotIn("synthetic observation", (bundle / "origin.json").read_text())
        self.assertEqual(stat.S_IMODE(bundle.stat().st_mode), 0o700)
        self.assertTrue(all(stat.S_IMODE(p.stat().st_mode) == 0o600 for p in bundle.iterdir()))

    def test_portable_load_needs_no_original_inputs_or_historical_source_tree(self):
        plan, fit, bundle, metadata = self.exported()
        shutil.rmtree(plan.parent)
        shutil.rmtree(fit)
        with (
            patch("experiments.m3.external.model.learned_read", side_effect=AssertionError),
            patch("experiments.m3.azt1d.common.provenance", side_effect=AssertionError),
            patch("experiments.m3.estimator.fit", side_effect=AssertionError),
        ):
            model, loaded, identity = load_model(bundle)
        self.assertEqual(loaded, metadata)
        self.assertEqual(model["intercept"], 123.0)
        self.assertEqual(identity, digest((bundle / "bundle.json").read_bytes()))
        code = (
            "import sys; from experiments.m3.external.model import load_model; "
            "load_model(sys.argv[1]); "
            "assert 'sklearn' not in sys.modules and 'numpy' not in sys.modules"
        )
        result = subprocess.run(
            [sys.executable, "-S", "-c", code, str(bundle)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_failed_original_verification_writes_nothing(self):
        plan, fit, _ = declared_fixture(self.root)
        with patch(
            "experiments.m3.external.model.learned_read", side_effect=ValueError("Invalid fit")
        ):
            with self.assertRaisesRegex(ValueError, "Invalid fit"):
                export_model(plan, fit, self.root / "bundle")
        self.assertFalse((self.root / "bundle").exists())

    def test_byte_tamper_and_rehashed_model_still_fail_original_freeze_binding(self):
        _, _, bundle, _ = self.exported()
        model, _ = read(bundle / "model.json")
        model["intercept"] += 1
        save(bundle / "model.json", model)
        with self.assertRaisesRegex(ValueError, "artifact changed"):
            load_model(bundle)
        refresh_inventory(bundle)
        with self.assertRaisesRegex(ValueError, "original learned freeze"):
            load_model(bundle)

    def test_model_shape_settings_packages_and_alias_binding_checked_after_rehash(self):
        _, _, original, _ = self.exported()
        mutations = (
            ("coef", [1.0]),
            ("settings", {"alpha": 2.0, "fit_intercept": True, "solver": "svd"}),
            ("packages", {}),
            ("training_counts", {"unplanned": 300}),
        )
        for index, (key, value) in enumerate(mutations):
            with self.subTest(field=key):
                bundle = self.root / f"changed-{index}"
                shutil.copytree(original, bundle)
                model, _ = read(bundle / "model.json")
                model[key] = value
                save(bundle / "model.json", model)
                frozen, _ = read(bundle / "freeze.json")
                frozen["model_sha256"] = digest((bundle / "model.json").read_bytes())
                save(bundle / "freeze.json", frozen)
                refresh_inventory(bundle)
                with self.assertRaises(ValueError):
                    load_model(bundle)

    def test_symlinks_extra_files_and_empty_directories_fail_closed(self):
        _, _, original, _ = self.exported()
        for index, extra in enumerate(("file", "directory", "symlink")):
            with self.subTest(extra=extra):
                bundle = self.root / f"extra-{index}"
                shutil.copytree(original, bundle)
                if extra == "file":
                    (bundle / "unplanned.tmp").write_text("not allowed")
                elif extra == "directory":
                    (bundle / "empty").mkdir()
                else:
                    (bundle / "model.json").unlink()
                    (bundle / "model.json").symlink_to(original / "model.json")
                with self.assertRaises(ValueError):
                    load_model(bundle)
        link = self.root / "link"
        link.symlink_to(original, target_is_directory=True)
        with self.assertRaises(ValueError):
            load_model(link)

    def test_kind_is_bound_to_source_anchor_and_human_files_stay_private(self):
        _, _, bundle, metadata = self.exported(kind="human")
        self.assertEqual(metadata["kind"], "human")
        load_model(bundle)
        os.chmod(bundle / "model.json", 0o644)
        with self.assertRaisesRegex(ValueError, "Private model file"):
            load_model(bundle)
        os.chmod(bundle / "model.json", 0o600)
        origin = copy.deepcopy(metadata)
        origin["kind"] = origin["source_study_identity"]["kind"] = "synthetic"
        save(bundle / "origin.json", origin)
        refresh_inventory(bundle)
        with self.assertRaisesRegex(ValueError, "source access anchor"):
            load_model(bundle)

    def test_human_repository_output_is_rejected_before_original_inputs(self):
        plan, fit, _ = declared_fixture(self.root, "human")
        with patch("experiments.m3.external.model.learned_read") as access:
            with self.assertRaisesRegex(ValueError, "outside repository"):
                export_model(plan, fit, ROOT / "results/forbidden-external-model")
        access.assert_not_called()

    def test_modified_origin_changes_pinned_bundle_identity(self):
        _, _, bundle, _ = self.exported()
        _, _, before = load_model(bundle)
        origin, _ = read(bundle / "origin.json")
        origin["source_registry_sha256"] = "f" * 64
        save(bundle / "origin.json", origin)
        refresh_inventory(bundle)
        _, _, after = load_model(bundle)
        self.assertNotEqual(before, after)
        # Internal checksums cannot authenticate an actor replacing every hash.
        inventory = json.loads((bundle / "bundle.json").read_text())
        self.assertEqual(
            inventory["files"]["origin.json"], digest((bundle / "origin.json").read_bytes())
        )
