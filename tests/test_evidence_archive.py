"""Evidence remains verifiable without unpacking or trusting an existing bundle."""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "experiments/m0/archive.py"
SPEC = importlib.util.spec_from_file_location("m0_archive", MODULE)
archive = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(archive)


class EvidenceArchiveTests(unittest.TestCase):
    def test_index_rejects_replaced_inventory(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, store = Path(tmp) / "source", Path(tmp) / "store"
            source.mkdir()
            (source / "trace").write_text("synthetic")
            dest = store / "bundle"
            manifest = archive.create(source, dest)
            index = Path(tmp) / "index.json"
            index.write_text(
                json.dumps(
                    {
                        "archives": [
                            {
                                "directory": "bundle",
                                "archive_sha256": manifest["archive_sha256"],
                                "inventory_sha256": archive.digest(dest / "archive.json"),
                                "file_count": 1,
                            }
                        ]
                    }
                )
            )
            self.assertEqual(archive.verify_index(store, index)["verified_archives"], 1)
            metadata = dest / "archive.json"
            metadata.write_text(metadata.read_text() + "\n")
            with self.assertRaisesRegex(ValueError, "tracked index"):
                archive.verify_index(store, index)

    def test_roundtrip_corruption_and_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, dest = Path(tmp) / "source", Path(tmp) / "archive"
            source.mkdir()
            (source / "trace.csv").write_text("time,glucose\n0,100\n")
            manifest = archive.create(source, dest)
            self.assertEqual(archive.verify(dest), manifest)
            with self.assertRaises(FileExistsError):
                archive.create(source, dest)
            with (dest / "evidence.tar.gz").open("ab") as stream:
                stream.write(b"corruption")
            with self.assertRaisesRegex(ValueError, "checksum"):
                archive.verify(dest)

    def test_symlinks_and_recursive_destination_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            source.mkdir()
            (source / "trace").write_text("synthetic")
            with self.assertRaises(ValueError):
                archive.create(source, source / "nested")
            (source / "link").symlink_to(source / "trace")
            with self.assertRaisesRegex(ValueError, "regular"):
                archive.create(source, Path(tmp) / "archive")
