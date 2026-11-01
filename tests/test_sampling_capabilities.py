"""Installed descriptor versions admit only their explicitly selected tasks."""

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "sampling_integrity", ROOT / "packaging/sdk/opent1d_lab/_integrity.py"
)
INTEGRITY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INTEGRITY)


class SamplingCapabilities(unittest.TestCase):
    def test_supported_versions_and_refused_task_promotion(self):
        with tempfile.TemporaryDirectory(prefix="sampling-capabilities-") as temporary:
            root = Path(temporary).resolve()
            raw = b"inert capability fixture\n"
            (root / "data.txt").write_bytes(raw)
            current = ["mmtt-sensitivity", "m4-study-secure", "m4-study-installed", "mmtt-sampling"]
            for version, tasks in (
                (1, current[:2]),
                (2, current[:3]),
                (3, current),
                (4, ["mmtt-sensitivity", "mmtt-sampling"]),
                (5, current),
                (6, current + ["m3-compare"]),
            ):
                descriptor = {
                    "schema": f"opent1d.installed-sdk/{version}",
                    "tasks": tasks,
                    "native_execution": "unavailable-public-policy"
                    if version in {1, 4}
                    else "explicit-reviewed-attachment/1",
                    "source": {"revision": "a" * 40, "dirty": False},
                    "build_label": "controlled",
                    "files": {
                        "data.txt": {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
                    },
                }
                manifest = root / "_manifest.json"
                manifest.write_text(json.dumps(descriptor))
                with self.subTest(version=version):
                    self.assertEqual(INTEGRITY.verify(root), descriptor)
                    changed = {**descriptor, "tasks": tasks + ["unselected-task"]}
                    if version < 3:
                        changed["tasks"] = tasks + ["mmtt-sampling"]
                    manifest.write_text(json.dumps(changed))
                    with self.assertRaisesRegex(ValueError, "Unsupported installed artifact"):
                        INTEGRITY.verify(root)
                    if version in {4, 5, 6}:
                        for roster in (
                            tasks[::-1],
                            tasks + [tasks[0]],
                            tasks[:-1],
                            ["mmtt-sensitivity", "mmtt-sampling", "m4-study-installed"],
                        ):
                            manifest.write_text(json.dumps({**descriptor, "tasks": roster}))
                            with self.assertRaisesRegex(
                                ValueError, "Unsupported installed artifact"
                            ):
                                INTEGRITY.verify(root)
                        for policy in (
                            "unrestricted",
                            "explicit-reviewed-attachment/2",
                            "explicit-reviewed-attachment/1"
                            if version == 4
                            else "unavailable-public-policy",
                        ):
                            manifest.write_text(
                                json.dumps({**descriptor, "native_execution": policy})
                            )
                            with self.assertRaisesRegex(
                                ValueError, "Unsupported installed artifact"
                            ):
                                INTEGRITY.verify(root)


if __name__ == "__main__":
    unittest.main()
