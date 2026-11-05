"""Package data to invented-byte staging, without a native environment."""

import json
import os
import platform
import socket
import tarfile
import tempfile
import unittest
from pathlib import Path

from experiments.lt1_diagnostic import frozen_setup as stage
from experiments.lt1_diagnostic.archive_preflight import inspect_archive
from experiments.lt1_diagnostic.payload_selection import filemap_digest
from experiments.lt1_diagnostic.setup_payload import package_blobs
from tests import test_lt1_archive_preflight as archive_fixtures


class LT1SetupPayloadTests(unittest.TestCase):
    def fixture(self):
        raw, row = archive_fixtures.LT1ArchivePreflightTests().archive(
            [
                ("package/LICENSE", b"invented notice", tarfile.REGTYPE),
                ("package/main.js", b"never executed", tarfile.REGTYPE),
                ("package/browser.js", b"omitted", tarfile.REGTYPE),
            ]
        )
        row["lock_path"] = "node_modules/invented"
        report = inspect_archive(raw, row)
        prefix = "toolchain/node_modules/invented/"
        mapped = {prefix + p.removeprefix("package/"): v for p, v in report["files"].items()}
        notices = {prefix + "LICENSE": mapped[prefix + "LICENSE"]}
        selected = {p: v for p, v in mapped.items() if p != prefix + "browser.js"}
        inv = json.dumps({"lock_sha256": "0" * 64, "packages": [row]}).encode()
        profile = {
            "schema": "opent1d.lt1-headless-selection-proposal/1",
            "profile": "invented-setup/1",
            "historical_lock_sha256": "0" * 64,
            "notice_inventory_sha256": stage.digest(inv),
            "packages": [
                {k: row[k] for k in ("name", "version", "lock_path", "archive_sha256", "root")}
                | {
                    "files": len(mapped),
                    "payload_bytes": sum(v["bytes"] for v in mapped.values()),
                    "filemap_sha256": filemap_digest(mapped),
                }
            ],
            "source_files": len(mapped),
            "source_payload_bytes": sum(v["bytes"] for v in mapped.values()),
            "source_filemap_sha256": filemap_digest(mapped),
            "excluded": {"path": prefix + "browser.js", **mapped[prefix + "browser.js"]},
            "selected_files": len(selected),
            "selected_payload_bytes": sum(v["bytes"] for v in selected.values()),
            "selected_filemap_sha256": filemap_digest(selected),
            "recognized_notice_files": 1,
            "retained_notice_filemap_sha256": filemap_digest(notices),
            "complete_remaining_embedded_license_closure": False,
            "functional_loader_qualification": "unrun",
            "setup_authorized": False,
            "execution_authorized": False,
        }
        return {row["archive_sha256"]: raw}, inv, json.dumps(profile).encode()

    def test_selected_members_and_notice_survive_memory_preparation(self):
        archives, inv, profile = self.fixture()
        payload, selection = package_blobs(archives, inv, profile, stage.digest(profile))
        self.assertEqual(len(payload), 3)
        self.assertNotIn("toolchain/node_modules/invented/browser.js", payload)
        self.assertEqual(payload["toolchain/node_modules/invented/LICENSE"], b"invented notice")
        self.assertEqual(
            {p: {"bytes": len(v), "sha256": stage.digest(v)} for p, v in payload.items()},
            selection["files"],
        )

    def test_bad_archive_or_roster_never_becomes_package_payload(self):
        archives, inv, profile = self.fixture()
        key = next(iter(archives))
        for changed in ({}, {key: archives[key] + b"altered"}, {**archives, "1" * 64: b"extra"}):
            with self.subTest(changed=list(changed)), self.assertRaises(ValueError):
                package_blobs(changed, inv, profile, stage.digest(profile))

    @unittest.skipUnless(os.name == "posix", "POSIX descriptor backend only")
    def test_invented_archive_selection_materializes_and_reconstructs_exactly(self):
        archives, inv, profile = self.fixture()
        payload, _ = package_blobs(archives, inv, profile, stage.digest(profile))
        with tempfile.TemporaryDirectory() as temp:
            parent = Path(temp).resolve()
            parent.chmod(0o700)
            blobs = {stage.digest(p.encode()): v for p, v in payload.items()}
            blobs["review"] = b"invented not approved"
            inputs = {k: {"bytes": len(v), "sha256": stage.digest(v)} for k, v in blobs.items()}
            request = {
                "schema": "opent1d.lt1-materialization-request/1",
                "kind": "invented",
                "parent": str(parent),
                "name": "package-fixture",
                "inputs": inputs,
                "files": {
                    p: {
                        "input": stage.digest(p.encode()),
                        **inputs[stage.digest(p.encode())],
                        "mode": 0o400,
                    }
                    for p in payload
                },
                "review_receipts": {k: "review" for k in ("rights", "security", "harness")},
                "stager_identity": stage.source_identity(),
                "host": socket.gethostname(),
                "platform": __import__("sys").platform,
                "machine": platform.machine(),
            }
            raw = json.dumps(request).encode()
            registry = {
                "schema": "opent1d.lt1-setup-request-admissions/1",
                "requests": [stage.digest(raw)],
            }
            result = stage._materialize_reviewed(raw, registry, lambda k, n: blobs[k])
            root = parent / request["name"]
            manifest = (root / "materialized.json").read_bytes()
            self.assertEqual(
                result, stage.inspect_materialized(root, stage.digest(raw), stage.digest(manifest))
            )
            self.assertEqual(
                (root / "payload/toolchain/node_modules/invented/main.js").read_bytes(),
                b"never executed",
            )
            self.assertFalse((root / "payload/toolchain/node_modules/invented/browser.js").exists())
