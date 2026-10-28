"""Catalogue reports retain canonical UTF-8/LF bytes across host text defaults."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.catalogue import core
from experiments.catalogue.storage import digest, dump, seal


class CatalogueMarkdownTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        archive = self.root / "synthetic-source"
        archive.mkdir()
        source = b"raise AssertionError('Catalogue indexing must never execute this source')\n"
        (archive / "controller.py").write_bytes(source)
        dump(
            archive / "workflow.json",
            {
                "schema": "opent1d.p1-external-workflow/1",
                "profile": "adult#001",
                "seed": 101,
                "controller": {"name": "synthetic-caf\u00e9", "source_sha256": digest(source)},
                "implementation_sha256": {"synthetic": "0" * 64},
            },
        )
        dump(
            archive / "study.json",
            {
                "schema": "opent1d.p1-external-workflow/1",
                "cases": list("ABCD"),
                "status": "completed",
            },
        )
        self.request = self.root / "request.json"
        dump(
            self.request,
            {
                "schema": core.REQUEST,
                "entries": [
                    {
                        "id": "synthetic",
                        "task": "p1-controller",
                        "archive": str(archive),
                        "tags": [],
                    }
                ],
            },
        )

    def test_save_and_load_use_utf8_lf_under_windows_text_defaults(self):
        original = Path.open

        def windows_text(path, mode="r", buffering=-1, encoding=None, errors=None, newline=None):
            if path.name == "report.md" and mode == "w":
                encoding = "cp1252" if encoding in (None, "locale") else encoding
                newline = "\r\n" if newline is None else newline
            return original(path, mode, buffering, encoding, errors, newline)

        output = self.root / "catalogue"
        with patch.object(Path, "open", windows_text):
            data = core.index(self.request, output)
        raw = (output / "report.md").read_bytes()
        self.assertEqual(raw, core.markdown(data).encode("utf-8"))
        self.assertNotIn(b"\r\n", raw)
        self.assertIn("synthetic-caf\u00e9", raw.decode("utf-8"))
        self.assertEqual(core.load(output)[1], data)

    def test_resealed_crlf_substitution_remains_a_reader_error(self):
        output = self.root / "catalogue"
        core.index(self.request, output)
        report = output / "report.md"
        report.write_bytes(report.read_bytes().replace(b"\n", b"\r\n"))
        (output / "manifest.json").unlink()
        seal(output)
        with self.assertRaisesRegex(ValueError, "Catalogue report differs"):
            core.load(output)


if __name__ == "__main__":
    unittest.main()
