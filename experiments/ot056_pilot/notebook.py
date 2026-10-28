"""Execute the checked-in comparator's Python cells with retained outputs.

This is a small standard-library cell runner, not a Jupyter UI/runtime claim.
The public entry executes only the fixed repository notebook, never an archived
notebook or a supplied arbitrary file. Scientific work stays in the shared core.
"""

import contextlib
import copy
import io
import json
from pathlib import Path

from experiments.catalogue.storage import digest, dump, fresh, seal

NOTEBOOK = Path(__file__).with_name("same-estimator.ipynb")
SAMPLING_NOTEBOOK = Path(__file__).with_name("same-estimator-sampling.ipynb")


def execute_document(document, parameters):
    document = copy.deepcopy(document)
    if document.get("nbformat") != 4:
        raise ValueError("Expected a version-4 notebook")
    namespace = {"__name__": "__main__", "PARAMETERS": parameters}
    executed = 0
    error = None
    for index, cell in enumerate(document["cells"]):
        if cell["cell_type"] != "code":
            continue
        executed += 1
        cell["execution_count"], cell["outputs"] = executed, []
        source = cell["source"]
        source = "".join(source) if isinstance(source, list) else source
        stream = io.StringIO()
        errors = io.StringIO()
        try:
            with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(errors):
                exec(compile(source, f"same-estimator.ipynb:cell-{index}", "exec"), namespace)
        except Exception as failure:
            error = {"ename": type(failure).__name__, "evalue": str(failure)}
        if stream.getvalue():
            cell["outputs"].append(
                {
                    "output_type": "stream",
                    "name": "stdout",
                    "text": stream.getvalue(),
                }
            )
        if errors.getvalue():
            cell["outputs"].append(
                {
                    "output_type": "stream",
                    "name": "stderr",
                    "text": errors.getvalue(),
                }
            )
        if error:
            cell["outputs"].append({"output_type": "error", **error, "traceback": []})
            break
    return document, {
        "status": "failed" if error else "executed",
        "cells": executed,
        "error": error,
    }


def execute_notebook(parameters, output, *, task="task1"):
    if task not in ("task1", "task2"):
        raise ValueError("Only the two fixed repository comparator notebooks are allowed")
    source = NOTEBOOK if task == "task1" else SAMPLING_NOTEBOOK
    raw = source.read_bytes()
    output = fresh(output)
    (output / "source.ipynb").write_bytes(raw)
    parameters = {**parameters, "OUTPUT_DIRECTORY": str(output)}
    executed, record = execute_document(json.loads(raw), parameters)
    record.update({"source_sha256": digest(raw), "human_sessions": 0, "task": task})
    dump(output / "executed.ipynb", executed)
    dump(output / "execution.json", record)
    seal(output)
    if record["status"] != "executed":
        raise ValueError("Notebook execution failed; retained cell output identifies the failure")
    return record
