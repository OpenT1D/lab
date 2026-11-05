"""Invented-byte stager qualification; no native environment is materialized."""

import copy
import json
import os
import platform
import socket
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.lt1_diagnostic import frozen_setup as stage


@unittest.skipUnless(os.name == "posix", "POSIX descriptor backend only")
class LT1FrozenSetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.parent = Path(self.temp.name).resolve()
        self.parent.chmod(0o700)
        self.blobs = {
            "one": b"invented-one",
            "two": b"invented-two",
            "review": b"invented-no-approval",
        }
        self.request = {
            "schema": "opent1d.lt1-materialization-request/1",
            "kind": "invented",
            "parent": str(self.parent),
            "name": "attempt-1",
            "inputs": {
                k: {"bytes": len(v), "sha256": stage.digest(v)} for k, v in self.blobs.items()
            },
            "files": {},
            "review_receipts": {k: "review" for k in ("rights", "security", "harness")},
            "stager_identity": stage.source_identity(),
            "host": socket.gethostname(),
            "platform": __import__("sys").platform,
            "machine": platform.machine(),
        }
        for path, blob in (("a.txt", "one"), ("nested/b.txt", "two")):
            self.request["files"][path] = {
                "input": blob,
                **self.request["inputs"][blob],
                "mode": 0o400,
            }

    def run_request(self, request=None, read=None):
        raw = json.dumps(self.request if request is None else request).encode()
        registry = {
            "schema": "opent1d.lt1-setup-request-admissions/1",
            "requests": [stage.digest(raw)],
        }
        return stage._materialize_reviewed(raw, registry, read or (lambda k, n: self.blobs[k]))

    def inspect(self):
        raw = (self.parent / "attempt-1/materialized.json").read_bytes()
        request = json.dumps(self.request).encode()
        return stage.inspect_materialized(
            self.parent / "attempt-1", stage.digest(request), stage.digest(raw)
        )

    def test_complete_invented_payload_exact_permissions_and_no_authority(self):
        result = self.run_request()
        self.assertEqual(result, self.inspect())
        root = self.parent / "attempt-1"
        self.assertEqual((root / "payload/a.txt").read_bytes(), self.blobs["one"])
        self.assertEqual(stat.S_IMODE((root / "payload").stat().st_mode), 0o500)
        self.assertEqual(stat.S_IMODE((root / "payload/a.txt").stat().st_mode), 0o400)
        self.assertFalse(result["setup_admitted"])
        self.assertFalse(result["native_execution_authorized"])
        with self.assertRaises(FileExistsError):
            self.run_request()
        self.assertEqual(result, self.inspect())

    def test_empty_production_authority_refuses_before_supplied_paths(self):
        class NoPath:
            def __fspath__(self):
                raise AssertionError("inspected caller path")

        with self.assertRaisesRegex(ValueError, "no reviewed setup request"):
            stage.materialize(b"not even JSON", NoPath())

    def test_invalid_bytes_and_source_refuse_before_output(self):
        with self.assertRaisesRegex(ValueError, "input bytes"):
            self.run_request(read=lambda k, n: b"wrong")
        bad = copy.deepcopy(self.request)
        bad["stager_identity"] = {}
        with self.assertRaisesRegex(ValueError, "stager identity"):
            self.run_request(bad)
        self.assertEqual(list(self.parent.iterdir()), [])

    def test_traversal_aliases_parent_collisions_and_modes_refuse_before_output(self):
        for names in (
            ("../outside",),
            ("/absolute",),
            ("a\\b",),
            ("a./x",),
            ("A/file", "a/other"),
            ("a", "a/file"),
            ("unicode-\u00e9",),
            ("/".join(["deep"] * 17),),
            ("a" * 513,),
        ):
            bad = copy.deepcopy(self.request)
            value = next(iter(bad["files"].values()))
            bad["files"] = {n: value for n in names}
            with self.subTest(names=names), self.assertRaises(ValueError):
                self.run_request(bad)
        bad = copy.deepcopy(self.request)
        value = next(iter(bad["files"].values()))
        bad["files"] = {"dir-" + str(i) + "/x": value for i in range(129)}
        with self.assertRaisesRegex(ValueError, "directory count"):
            self.run_request(bad)
        bad = copy.deepcopy(self.request)
        bad["files"]["a.txt"]["mode"] = 0o777
        with self.assertRaisesRegex(ValueError, "payload mode"):
            self.run_request(bad)
        self.assertEqual(list(self.parent.iterdir()), [])

    def test_existing_output_and_nonprivate_parent_are_not_adopted(self):
        output = self.parent / "attempt-1"
        output.mkdir()
        sentinel = output / "sentinel"
        sentinel.write_bytes(b"keep")
        with self.assertRaises(FileExistsError):
            self.run_request()
        self.assertEqual(sentinel.read_bytes(), b"keep")
        self.request["name"] = "different"
        self.parent.chmod(0o755)
        with self.assertRaisesRegex(ValueError, "private owned"):
            self.run_request()
        self.assertFalse((self.parent / "different").exists())

    def test_file_write_failure_retains_prefix_and_failure_record(self):
        original = stage._write_at

        def fail(folder, name, raw, mode):
            if name == "b.txt":
                raise OSError("invented disk failure")
            return original(folder, name, raw, mode)

        with (
            patch.object(stage, "_write_at", fail),
            self.assertRaisesRegex(OSError, "invented disk failure"),
        ):
            self.run_request()
        root = self.parent / "attempt-1"
        self.assertEqual((root / "payload/a.txt").read_bytes(), self.blobs["one"])
        self.assertTrue((root / "failure.json").is_file())
        self.assertFalse((root / "materialized.json").exists())
        with self.assertRaisesRegex(ValueError, "incomplete"):
            stage.inspect_materialized(root, "0" * 64, "0" * 64)

    def test_symlink_substitution_cannot_write_outside_owned_descriptors(self):
        outside = self.parent / "outside"
        outside.mkdir()
        (outside / "sentinel").write_bytes(b"keep")
        original = stage._write_at

        def substitute(folder, name, raw, mode):
            if name == "a.txt":
                payload = self.parent / "attempt-1/payload"
                payload.rename(payload.with_name("retained"))
                payload.symlink_to(outside, target_is_directory=True)
            return original(folder, name, raw, mode)

        with (
            patch.object(stage, "_write_at", substitute),
            self.assertRaisesRegex(ValueError, "directory changed"),
        ):
            self.run_request()
        self.assertEqual(set(p.name for p in outside.iterdir()), {"sentinel"})
        self.assertEqual((outside / "sentinel").read_bytes(), b"keep")
        self.assertTrue((self.parent / "attempt-1/retained/a.txt").is_file())

    def test_failed_atomic_completion_and_changed_payload_refuse(self):
        with (
            patch.object(stage.os, "link", side_effect=OSError("invented publish failure")),
            self.assertRaises(OSError),
        ):
            self.run_request()
        root = self.parent / "attempt-1"
        self.assertFalse((root / "materialized.json").exists())
        self.assertTrue((root / ".inventory.pending").exists())
        self.request["name"] = "attempt-2"
        self.run_request()
        root = self.parent / "attempt-2"
        raw = (root / "materialized.json").read_bytes()
        path = root / "payload/a.txt"
        path.chmod(0o600)
        path.write_bytes(b"corruption")
        with self.assertRaises(ValueError):
            stage.inspect_materialized(
                root, stage.digest(json.dumps(self.request).encode()), stage.digest(raw)
            )

    def test_reader_rejects_directory_rebinding_after_open(self):
        self.run_request()
        self.assertEqual(self.inspect()["status"], "materialized")
        outside = self.parent / "outside"
        outside.mkdir()
        (outside / "sentinel").write_bytes(b"keep")
        original = stage._verify_payload

        def swap(dirs, files, check=lambda: None):
            payload = self.parent / "attempt-1/payload"
            payload.chmod(0o700)
            payload.rename(self.parent / "retained-good")
            payload.symlink_to(outside, target_is_directory=True)
            return original(dirs, files, check)

        with (
            patch.object(stage, "_verify_payload", swap),
            self.assertRaisesRegex(ValueError, "directory changed"),
        ):
            self.inspect()
        self.assertEqual(list(p.name for p in outside.iterdir()), ["sentinel"])

    def test_writer_rejects_substituted_pending_inventory(self):
        original = stage.os.link
        for index, same_bytes in enumerate((False, True), 1):
            self.request["name"] = "attempt-" + str(index)
            root = self.parent / self.request["name"]

            def swap(source, target, **kwargs):
                pending = root / ".inventory.pending"
                raw = pending.read_bytes() if same_bytes else b"not the inventory"
                pending.unlink()
                pending.write_bytes(raw)
                pending.chmod(0o600)
                return original(source, target, **kwargs)

            with (
                self.subTest(same_bytes=same_bytes),
                patch.object(stage.os, "link", swap),
                self.assertRaisesRegex(
                    ValueError, "published inventory changed|published inventory mode"
                ),
            ):
                self.run_request()
            self.assertTrue((root / "failure.json").exists())

    def test_reader_enforces_independent_bounds_and_receipt_schema(self):
        self.run_request()
        with (
            patch.object(stage, "TOTAL_LIMIT", 1),
            self.assertRaisesRegex(ValueError, "total bound"),
        ):
            self.inspect()
        root = self.parent / "attempt-1"
        path = root / "materialized.json"
        base = json.loads(path.read_bytes())
        for mutate in (
            lambda r: r.update(review_receipt_sha256="not a role map"),
            lambda r: r["review_receipt_sha256"].update(rights="invalid"),
            lambda r: r.update(request_sha256="not a digest"),
        ):
            record = copy.deepcopy(base)
            mutate(record)
            raw = json.dumps(record).encode()
            path.chmod(0o600)
            path.write_bytes(raw)
            path.chmod(0o400)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                stage.inspect_materialized(root, record["request_sha256"], stage.digest(raw))

    def test_parent_namespace_replacement_does_not_complete(self):
        original = stage._write_at
        parent = self.parent

        def substitute(folder, name, raw, mode):
            result = original(folder, name, raw, mode)
            if name == "a.txt":
                parent.rename(parent.with_name(parent.name + "-retained"))
                parent.mkdir(mode=0o700)
            return result

        self.addCleanup(
            lambda: __import__("shutil").rmtree(
                parent.with_name(parent.name + "-retained"), ignore_errors=True
            )
        )
        with (
            patch.object(stage, "_write_at", substitute),
            self.assertRaisesRegex(ValueError, "namespace changed"),
        ):
            self.run_request()
        self.assertEqual(list(parent.iterdir()), [])

    def test_extra_payload_and_hardlink_mutation_withdraw_materialization(self):
        self.run_request()
        root = self.parent / "attempt-1"
        raw = (root / "materialized.json").read_bytes()
        expected = stage.digest(json.dumps(self.request).encode())
        (root / "payload").chmod(0o700)
        (root / "payload/extra").write_bytes(b"extra")
        (root / "payload").chmod(0o500)
        with self.assertRaisesRegex(ValueError, "unexpected payload"):
            stage.inspect_materialized(root, expected, stage.digest(raw))
        (root / "payload").chmod(0o700)
        (root / "payload/extra").unlink()
        (root / "payload").chmod(0o500)
        os.link(root / "payload/a.txt", self.parent / "alias")
        with self.assertRaisesRegex(ValueError, "regular bounded"):
            stage.inspect_materialized(root, expected, stage.digest(raw))
