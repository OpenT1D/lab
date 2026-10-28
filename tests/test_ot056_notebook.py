"""Cell-execution controls only; no researcher session or scientific claim."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.catalogue.storage import digest, load_sealed, read
from experiments.ot056_pilot.notebook import execute_document, execute_notebook


class NotebookRunnerTests(unittest.TestCase):
    def test_supplied_notebook_paths_cannot_be_executed(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "output"
            with self.assertRaisesRegex(ValueError, "fixed repository comparator"):
                execute_notebook({}, output, task="../../archived-notebook.ipynb")
            self.assertFalse(output.exists())

    def test_state_outputs_and_failure_stop_are_retained(self):
        def cell(source):
            return {"cell_type": "code", "source": source, "execution_count": None, "outputs": []}

        document = {
            "nbformat": 4,
            "cells": [
                cell(
                    "value = PARAMETERS['value'] + 1\nprint(value)\n"
                    "import sys\nprint('retained warning', file=sys.stderr)"
                ),
                cell("assert value == 3\nraise RuntimeError('selected fault')"),
                cell("raise AssertionError('must not execute after failed cell')"),
            ],
        }
        executed, result = execute_document(document, {"value": 2})
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["cells"], 2)
        self.assertEqual(executed["cells"][0]["outputs"][0]["text"], "3\n")
        self.assertEqual(executed["cells"][0]["outputs"][1]["text"], "retained warning\n")
        self.assertEqual(executed["cells"][1]["outputs"][0]["ename"], "RuntimeError")
        self.assertIsNone(executed["cells"][2]["execution_count"])
        self.assertIsNone(document["cells"][0]["execution_count"])

    def test_execution_archive_binds_source_and_preserves_selected_error(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "trusted-test.ipynb"
            document = {
                "nbformat": 4,
                "nbformat_minor": 5,
                "metadata": {},
                "cells": [
                    {
                        "cell_type": "code",
                        "id": "test-cell",
                        "metadata": {},
                        "source": "assert PARAMETERS['value'] == 2\nprint('checked')",
                        "execution_count": None,
                        "outputs": [],
                    }
                ],
            }
            source.write_text(json.dumps(document))
            with patch("experiments.ot056_pilot.notebook.NOTEBOOK", source):
                record = execute_notebook({"value": 2}, root / "success")
                self.assertEqual(record["source_sha256"], digest(source.read_bytes()))
                self.assertEqual(record["human_sessions"], 0)
                self.assertTrue(load_sealed(root / "success").is_dir())
                with self.assertRaises(ValueError):
                    execute_notebook({"value": 2}, root / "success")
                with self.assertRaisesRegex(ValueError, "retained cell output"):
                    execute_notebook({"value": 3}, root / "failure")
            failed = read(root / "failure/execution.json")
            self.assertEqual(failed["status"], "failed")
            self.assertEqual(failed["error"]["ename"], "AssertionError")
            self.assertTrue(load_sealed(root / "failure").is_dir())


if __name__ == "__main__":
    unittest.main()
