"""Applicable root-lock closure, recorded platform selection and real tooling attestation."""

import copy
import json
import subprocess
import sys
import unittest

from experiments.maintained_campaigns import common
from experiments.maintained_campaigns.runtime import ROOT_RUNTIME_SCHEMA, root_selection


class MaintainedCampaignRuntimeTests(unittest.TestCase):
    def test_actual_root_lock_requires_colorama_only_on_windows(self):
        darwin, selection = root_selection("darwin")
        linux, _ = root_selection("linux")
        windows, win_selection = root_selection("win32")
        self.assertEqual(darwin, linux)
        self.assertEqual(set(windows) - set(darwin), {"colorama"})
        self.assertEqual(
            {name: item for name, item in windows.items() if name != "colorama"}, darwin
        )
        self.assertEqual(selection["marker_environment"], {"sys_platform": "darwin"})
        self.assertEqual(
            selection["markers"],
            [
                {
                    "package": "sphinx",
                    "dependency": "colorama",
                    "marker": "sys_platform == 'win32'",
                    "included": False,
                }
            ],
        )
        self.assertTrue(win_selection["markers"][0]["included"])

    def test_reachable_dependency_closure_keeps_unconditional_shared_dependency(self):
        lock = {
            "manifest": {"dependency-groups": {"dev": [{"name": "app"}]}},
            "package": [
                {
                    "name": "app",
                    "version": "1",
                    "source": {"registry": "fixture"},
                    "dependencies": [
                        {"name": "conditional", "marker": "sys_platform == 'win32'"},
                        {"name": "other"},
                    ],
                },
                {
                    "name": "other",
                    "version": "1",
                    "source": {"registry": "fixture"},
                    "dependencies": [{"name": "conditional"}],
                },
                {"name": "conditional", "version": "1", "source": {"registry": "fixture"}},
                {"name": "unreachable", "version": "1", "source": {"registry": "fixture"}},
            ],
        }
        records, _ = root_selection("darwin", lock)
        self.assertEqual(set(records), {"app", "other", "conditional"})
        unsupported = copy.deepcopy(lock)
        unsupported["package"][0]["dependencies"][0]["marker"] = "python_version >= '3.12'"
        with self.assertRaisesRegex(ValueError, "Unsupported root lock environment marker"):
            root_selection("darwin", unsupported)
        unsupported["package"][0]["dependencies"][0] = {"name": "conditional", "extra": ["all"]}
        with self.assertRaisesRegex(ValueError, "Unsupported root dependency selector"):
            root_selection("darwin", unsupported)

    def test_actual_installed_root_probe_uses_applicable_locked_roster(self):
        probe = subprocess.run(
            [
                sys.executable,
                "-B",
                "-E",
                "-s",
                "-c",
                "import json; from experiments.maintained_campaigns.runtime import attest_root; "
                "print(json.dumps(attest_root(),sort_keys=True))",
            ],
            cwd=common.ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        self.assertEqual(probe.returncode, 0, probe.stderr)
        record = json.loads(probe.stdout)
        wanted, selection = root_selection(sys.platform)
        self.assertEqual(record["schema"], ROOT_RUNTIME_SCHEMA)
        self.assertEqual(record["selection"], selection)
        self.assertEqual(
            record["distributions"], {name: item["version"] for name, item in wanted.items()}
        )
        self.assertEqual(record["executable"], sys.executable)

    def test_archived_selection_uses_recorded_platform_and_rejects_forged_roster(self):
        from tests.test_maintained_campaigns import runtimes

        record = runtimes()
        selected, selection = root_selection("win32")
        record["."].update(
            distributions={name: item["version"] for name, item in selected.items()},
            selection=selection,
        )
        # Reconstruction is independent of this reader's live platform.
        common.validate_runtime_identity(record)
        record["."]["selection"]["packages"].remove("colorama")
        with self.assertRaisesRegex(ValueError, "Archived root platform selection differs"):
            common.validate_runtime_identity(record)
