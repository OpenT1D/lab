"""Presentation regressions; numerical validity stays with authoritative readers."""

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.catalogue.formats import metadata

ROOT = Path(__file__).resolve().parents[1]


class UsabilityFixTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node is required for frontend checks")
    def test_real_frontend_functions_preserve_timing_errors_and_operation_ownership(self):
        result = subprocess.run(
            [shutil.which("node"), "tests/gui_usability_fixes.mjs"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {"passed": True, "checks": 8})

    def test_native_interruption_is_separate_from_catalogue_acceptance(self):
        # Stub existing scientific adaptation, exercise real additive metadata
        # extraction; native integration is checked on retained archives locally.
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            raw = b'{"status":"interrupted","passed":false}\n'
            (folder / "report.json").write_bytes(raw)
            with (
                patch(
                    "experiments.catalogue.formats._m4",
                    return_value=("protocol", [], {}, {}, "failed"),
                ),
                patch("experiments.catalogue.formats.repeat_conditions", return_value=({}, {})),
            ):
                result = metadata(folder, "m4-study-secure", {})
            self.assertEqual(result["recorded_status"], "failed")
            self.assertEqual(result["native_report_status"], "interrupted")
            self.assertEqual((folder / "report.json").read_bytes(), raw)


if __name__ == "__main__":
    unittest.main()
