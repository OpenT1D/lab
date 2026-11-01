"""Actual integrated source/data wheel, without installing native physiology."""

import functools
import hashlib
import json
import os
import subprocess
import sys
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from experiments.shared_services import store
from tests import test_installed_connected as connected
from tests import test_installed_sampling as installed
from tests import test_workbench_installed as editable

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(
    os.name == "posix" and sys.version_info[:2] == (3, 12), "POSIX CPython 3.12 candidate"
)
class IntegratedCandidate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        builder = functools.partial(installed.build_sdk.build, integrated_candidate=True)
        with patch.object(installed.build_sdk, "build", builder):
            installed.InstalledSampling.setUpClass.__func__(cls)
        cls.receipts = {5: json.loads((cls.base / "build/receipt.json").read_bytes())}
        for version, flags in ((3, {}), (4, {"mmtt_only": True})):
            cls.receipts[version] = installed.build_sdk.build(
                cls.base / f"build-{version}",
                allow_dirty=True,
                build_label="sampling-test",
                **flags,
            )

    setUp = installed.InstalledSampling.setUp
    call = installed.InstalledSampling.call
    python = connected.InstalledConnectedStudies.python
    server = editable.EditableWorkbench.server

    def test_all_existing_wheel_scopes_bind_both_reader_packets_and_helper(self):
        for receipt in self.receipts.values():
            with zipfile.ZipFile(receipt["wheel"]) as wheel:
                metadata = json.loads(wheel.read("opent1d_lab/_manifest.json"))
                prefix = "_payload/app/experiments/shared_services/"
                for name in ("reader_compatibility.json", "reader_compatibility_m3.json"):
                    raw = wheel.read("opent1d_lab/" + prefix + name)
                    self.assertEqual(
                        hashlib.sha256(raw).hexdigest(), metadata["files"][prefix + name]["sha256"]
                    )
                packet = json.loads(
                    wheel.read("opent1d_lab/" + prefix + "reader_compatibility_m3.json")
                )
                helper = wheel.read("opent1d_lab/" + prefix + "reader_compatibility.py")
                self.assertEqual(
                    hashlib.sha256(helper).hexdigest(),
                    packet["successor"]["reader_static_dependencies_sha256"][
                        "experiments/shared_services/reader_compatibility.py"
                    ],
                )

    def test_candidate_preserves_entire_developer_and_mmtt_scientific_payload(self):
        payloads = {}
        for version, receipt in self.receipts.items():
            with zipfile.ZipFile(receipt["wheel"]) as wheel:
                metadata = json.loads(wheel.read("opent1d_lab/_manifest.json"))
                self.assertEqual(metadata["schema"], f"opent1d.installed-sdk/{version}")
                payloads[version] = {
                    name: hashlib.sha256(wheel.read(name)).hexdigest()
                    for name in wheel.namelist()
                    if name.startswith("opent1d_lab/_payload/app/")
                }
            self.assertFalse(receipt["native_runtimes_shipped"])
            self.assertEqual(receipt["runtime_dependencies"], [])
            self.assertEqual(receipt["source"], self.receipts[5]["source"])
        self.assertIn(
            "opent1d_lab/_payload/app/experiments/shared_services/reader_compatibility.json",
            payloads[5],
        )
        self.assertTrue(any("/experiments/m4/installed_study/" in name for name in payloads[5]))
        self.assertEqual(payloads[5], payloads[3])
        self.assertEqual(payloads[5], payloads[4])

    def test_native_attachment_required_and_legacy_execution_still_refused(self):
        metadata = self.call("installation")
        self.assertEqual(metadata["schema"], "opent1d.installed-sdk/5")
        self.assertEqual(
            metadata["tasks"],
            ["mmtt-sensitivity", "m4-study-secure", "m4-study-installed", "mmtt-sampling"],
        )
        self.assertEqual(metadata["native_execution"], "explicit-reviewed-attachment/1")
        self.assertEqual(
            self.python(
                "import importlib.util,json;print(json.dumps({name:importlib.util.find_spec(name)"
                " is None for name in ['numpy','scipy','simglucose']}))"
            ),
            {"numpy": True, "scipy": True, "simglucose": True},
        )
        project = self.root / "project"
        self.call("create", "--project", project, "--name", "Invented native admission")
        plans = {}
        for task, policy in (
            ("m4-study-secure", "unavailable-public-policy"),
            ("m4-study-installed", "explicit-reviewed-attachment/1"),
        ):
            inputs = self.call(
                "example", "--task", task, "--case", "fasting", "--output", self.root / task
            )["inputs"]
            flags = ["--task", task, "--config", inputs["config.json"]]
            self.call("validate", *flags)
            plans[task] = self.call("freeze", "--project", project, *flags)["plan"]
            before = store.inventory(project, store.Budget())
            checked = self.call("check", "--project", project, "--plan", plans[task])
            self.assertFalse(checked["runtimes_ready"])
            self.assertFalse(checked["setup_performed"])
            self.assertEqual(checked["native_policy"], policy)
            self.assertEqual(store.inventory(project, store.Budget()), before)
            outcome = self.call("run", "--project", project, "--plan", plans[task], expected=1)
            self.assertEqual(outcome["result"]["payload"], "forensic")
            self.assertEqual(outcome["result"]["completeness"], "incomplete")
            self.assertEqual(len(outcome["result"]["slot_statuses"]), 2)
            self.assertEqual(set(outcome["result"]["slot_statuses"].values()), {"unavailable"})
            self.assertEqual(outcome["receipt"]["remaining_owned_processes"], [])
        package = self.environment / "lib/python3.12/site-packages/opent1d_lab"
        output = self.root / "legacy-native-output"
        result = subprocess.run(
            [
                str(self.environment / "bin/python"),
                "-I",
                "-B",
                "-S",
                str(package / "_bootstrap.py"),
                "--native",
                "m4-study-secure",
                "run",
                "--output",
                str(output),
            ],
            cwd=self.root,
            env=self.env,
            capture_output=True,
            text=True,
            timeout=20,
        )
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("not an admitted installed capability", json.loads(result.stdout)["error"])
        self.assertFalse(output.exists())

    def test_missing_attachment_keeps_four_slots_and_72_rows_across_installed_surfaces(self):
        connected.InstalledConnectedStudies.test_gui_cli_python_failed_forward_keeps_all_rows_and_old_prefix(
            self
        )
        moved = self.root / "moved"
        with store.opened(moved) as saved:
            self.assertEqual(len(saved.plans), 1)
            plan = next(iter(saved.plans.values()))[0]
            self.assertEqual(len(plan["boundary"]["planned_slots"]), 4)
            self.assertEqual(len(saved.finishes), 1)
            finished = next(iter(saved.finishes.values()))[0]
            self.assertEqual(len(finished["result"]["slot_statuses"]), 4)
            self.assertEqual(set(finished["result"]["slot_statuses"].values()), {"unavailable"})
            self.assertEqual(finished["receipt"]["owned_processes"], [])
            self.assertEqual(finished["receipt"]["remaining_owned_processes"], [])

    def test_mutually_exclusive_candidate_builds_leave_no_output(self):
        output = self.root / "ambiguous-api-build"
        with self.assertRaisesRegex(ValueError, "Choose either"):
            installed.build_sdk.build(
                output, allow_dirty=True, mmtt_only=True, integrated_candidate=True
            )
        self.assertFalse(output.exists())
        output = self.root / "ambiguous-cli-build"
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/build_sdk.py"),
                "--output",
                str(output),
                "--mmtt-only",
                "--integrated-candidate",
            ],
            cwd=self.root,
            env=self.env,
            capture_output=True,
            text=True,
            timeout=20,
        )
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("not allowed with argument", result.stderr)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
