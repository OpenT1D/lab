"""Frozen setup plans reject independently changed process-helper source bytes."""

import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.catalogue import storage
from experiments.setup import core

ROOT = Path(__file__).resolve().parents[1]
# Independent expectations: copying only core.SOURCES would hide an omitted helper.
PROCESS_HELPERS = (
    "experiments/platform_process.py",
    "experiments/gui/windows_process.py",
    "experiments/gui/windows_worker.py",
)


class SetupSourceIdentityTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.checkout = self.base / "checkout"
        names = {*core.SOURCES, *PROCESS_HELPERS, "uv.lock", "pyproject.toml", ".python-version"}
        for name in names:
            destination = self.checkout / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, destination)
        self.uv = {"path": "/declared/uv", "sha256": "a" * 64, "version": "uv fixture"}
        for mocked in (
            patch.object(core, "ROOT", self.checkout),
            patch.object(storage, "ROOT", self.checkout),
            patch.object(core, "uv_identity", return_value=self.uv),
        ):
            mocked.start()
            self.addCleanup(mocked.stop)

    def test_plan_records_each_process_helper_from_its_actual_bytes(self):
        data = core.plan("mmtt-sensitivity", self.base / "plan")
        self.assertLessEqual(set(PROCESS_HELPERS), set(data["source_sha256"]))
        for name in PROCESS_HELPERS:
            self.assertEqual(
                data["source_sha256"][name],
                hashlib.sha256((self.checkout / name).read_bytes()).hexdigest(),
            )
        self.assertEqual(core.load(self.base / "plan")[1], data)

    def test_unchanged_plan_checks_missing_environment_without_installing(self):
        plan = self.base / "plan"
        data = core.plan("mmtt-sensitivity", plan)
        with patch.object(core, "install_project") as installer:
            result = core.execute(plan, self.base / "checked")
        installer.assert_not_called()
        self.assertFalse(result["ready"])
        self.assertFalse(result["numerical_validation"])
        self.assertFalse(result["source_or_model_executed"])
        self.assertEqual(len(result["projects"]), 1)
        self.assertEqual(result["projects"][0]["project"], ".")
        self.assertEqual(result["projects"][0]["reason"], "missing_or_aliased_environment")
        self.assertEqual(result["projects"][0]["installation"]["status"], "not_requested")
        self.assertEqual(result["plan_sha256"], core.digest(core.encoded(data)))
        core.load_sealed(self.base / "checked")
        self.assertFalse((self.checkout / ".venv").exists())

    def assert_mutation_refused(self, helper):
        plan = self.base / (Path(helper).stem + "-plan")
        core.plan("mmtt-sensitivity", plan)
        path = self.checkout / helper
        original = path.read_bytes()
        try:
            path.write_bytes(original + b"\n# independently changed implementation\n")
            for install in (False, True):
                output = self.base / (Path(helper).stem + ("-install" if install else "-check"))
                with self.subTest(helper=helper, install=install):
                    with (
                        patch.object(
                            core,
                            "install_project",
                            return_value={"status": "completed", "exit_code": 0},
                        ) as installer,
                        patch.object(core, "check_project", wraps=core.check_project) as readiness,
                        self.assertRaisesRegex(ValueError, "Setup implementation changed"),
                    ):
                        core.execute(plan, output, install=install)
                    installer.assert_not_called()
                    readiness.assert_not_called()
                    self.assertFalse(output.exists())
                    self.assertFalse((self.checkout / ".venv").exists())
        finally:
            path.write_bytes(original)
        self.assertEqual(core.load(plan)[1]["schema"], core.PLAN)

    def test_every_process_helper_mutation_is_refused_before_checks_installs_or_output(self):
        for helper in PROCESS_HELPERS:
            self.assert_mutation_refused(helper)

    def test_listed_setup_source_mutation_remains_a_rejecting_control(self):
        self.assert_mutation_refused("experiments/setup/core.py")

    def test_failed_explicit_install_retains_its_receipt_without_claiming_readiness(self):
        plan = self.base / "plan"
        data = core.plan("mmtt-sensitivity", plan)
        failure = {"status": "failed", "exit_code": 7}
        with patch.object(core, "install_project", return_value=failure) as installer:
            result = core.execute(plan, self.base / "failed", install=True)
        installer.assert_called_once()
        self.assertEqual(installer.call_args.args[0], ["/declared/uv", "sync", "--locked"])
        self.assertFalse(result["ready"])
        self.assertEqual(result["projects"][0]["installation"], failure)
        self.assertFalse(result["source_or_model_executed"])
        receipt = core.load_sealed(self.base / "failed")
        self.assertEqual(json.loads((receipt / "setup.json").read_bytes()), result)
        self.assertEqual(json.loads((receipt / "plan.json").read_bytes()), data)
        self.assertFalse((self.checkout / ".venv").exists())


if __name__ == "__main__":
    unittest.main()
