"""Fixed synthetic M5 intake, causal projection and strict artifact boundaries."""

import hashlib
import json
import math
import platform
import re
from pathlib import Path

from experiments.m5.synthetic_prognosis.run import features, fixture

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
VERSION = "m5-researcher-workflow/1"
INPUT_SCHEMA = "m5-landmark-input/1"
BUNDLE_FILES = {"model.py", "state.json", "model.json"}
SOURCES = {
    "source-contract.py": HERE / "contract.py",
    "source-worker.py": HERE / "worker.py",
    "source-report.py": HERE / "report.py",
    "source-run.py": HERE / "run.py",
    "source-synthetic.py": ROOT / "experiments/m5/synthetic_prognosis/run.py",
}
ARCHIVE_FILES = (
    BUNDLE_FILES
    | set(SOURCES)
    | {
        "protocol.json",
        "fixture.json",
        "baseline.json",
        "predictions.json",
        "provenance.json",
        "tooling-uv.lock",
        "report.json",
        "report.md",
    }
)
PROTOCOL = {
    "schema": VERSION,
    "fixture": "ot027-invented-prognosis-fixture/1",
    "input_schema": INPUT_SCHEMA,
    "output_unit": "U/day",
    "prediction_engineering_range": [0, 1000],
    "repeat_rule": "two fresh processes; exact prediction and runtime equality",
    "random_seed": 0,
    "baseline": "development-only standardized ridge; slope penalty 1",
    "metric": "paired mean absolute error; full eligible baseline reported separately",
    "human_execution_authorized": False,
    "treatment_effect_or_cure_estimated": False,
}


def encode(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def decode(data):
    def reject(value):
        raise ValueError("Nonfinite JSON number")

    value = json.loads(data, object_pairs_hook=_pairs, parse_constant=reject)

    def check(item):
        if isinstance(item, float) and not math.isfinite(item):
            raise ValueError("Nonfinite JSON number")
        if isinstance(item, dict):
            for child in item.values():
                check(child)
        elif isinstance(item, list):
            for child in item:
                check(child)

    check(value)
    return value


def snapshot(directory, names):
    directory = Path(directory)
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("Expected a regular directory")
    if {item.name for item in directory.iterdir()} != set(names):
        raise ValueError("Unexpected or missing files")
    return {name: read_bytes(directory / name) for name in sorted(names)}


def read_bytes(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 500_000:
        raise ValueError("Expected a regular file of at most 500 kB")
    with path.open("rb") as stream:
        data = stream.read(500_001)
    if len(data) > 500_000:
        raise ValueError("File exceeds 500 kB")
    return data


def number(value, *, minimum=0, maximum=1000):
    if (
        type(value) not in (int, float)
        or not math.isfinite(value)
        or not minimum <= value <= maximum
    ):
        raise ValueError("Expected a finite number within the engineering range")
    return value


def keys(value, expected):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise ValueError("Missing or unsupported fields")


def rows():
    development, evaluation, roster = [], [], []
    for person in fixture()["people"]:
        row, issues = features(person)
        alias = person["alias"]
        split = "evaluation" if int(alias[-3:]) % 4 == 0 else "development"
        roster.append(
            {
                "alias": alias,
                "split": split,
                "eligible": row is not None,
                "issues": issues,
                "intervening_infusion_days": [
                    day for day in person["infusion_days"][1:] if person["mmtt"]["day"] < day < 365
                ],
                "y1_present": any(item["visit"] == "Y1" for item in person["outcomes"]),
                "visit15_present": any(item["visit"] == "V15" for item in person["outcomes"]),
            }
        )
        if row is not None:
            (evaluation if split == "evaluation" else development).append((alias, row))
    return development, evaluation, roster


def request(row):
    return {
        "schema": INPUT_SCHEMA,
        "prior_insulin_u_day": row["baseline"][0],
        "prior_glycemic_status_mg_dl": row["baseline"][1],
        "landmark_day_after_first_infusion": row["baseline"][2],
        "observed_function_index": row["function_index"],
    }


def runtime():
    return {
        "implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "python_major_minor": ".".join(platform.python_version_tuple()[:2]),
    }


def declaration(data, source, state):
    keys(
        data,
        {
            "schema",
            "model_id",
            "rights_basis",
            "input_schema",
            "output_unit",
            "source_sha256",
            "state_sha256",
            "runtime",
            "training",
        },
    )
    if (
        data["schema"] != "m5-prognostic-model/1"
        or data["input_schema"] != INPUT_SCHEMA
        or data["output_unit"] != "U/day"
    ):
        raise ValueError("Unsupported prognostic model contract")
    for field in ("model_id", "rights_basis"):
        if not isinstance(data[field], str) or not data[field].strip() or len(data[field]) > 500:
            raise ValueError("Model identity and rights basis must be nonempty bounded text")
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", data["model_id"]) is None:
        raise ValueError("Model ID must be a simple identifier of at most 128 characters")
    if data["source_sha256"] != sha(source) or data["state_sha256"] != sha(state):
        raise ValueError("Model source or state hash mismatch")
    keys(data["runtime"], {"python_major_minor", "dependencies"})
    if (
        data["runtime"]["python_major_minor"] != runtime()["python_major_minor"]
        or data["runtime"]["dependencies"] != []
    ):
        raise ValueError("This intake supports the current Python major/minor and stdlib only")
    keys(data["training"], {"phase", "fixture_sha256", "participant_aliases"})
    if data["training"] != {
        "phase": "development_only",
        "fixture_sha256": sha(encode(fixture())),
        "participant_aliases": [alias for alias, _ in rows()[0]],
    }:
        raise ValueError("Training declaration must identify the fixed eligible development people")
    if not isinstance(decode(state), dict):
        raise ValueError("Frozen model state must be a JSON object")
    return data


def worker_result(value, model_declaration, *, expected_runtime=None):
    keys(value, {"schema", "prediction_u_day", "runtime"})
    if value["schema"] != "m5-prognostic-worker/1":
        raise ValueError("Wrong worker result schema")
    number(value["prediction_u_day"])
    keys(value["runtime"], {"implementation", "python_version", "python_major_minor"})
    if (
        value["runtime"]["python_major_minor"] != model_declaration["runtime"]["python_major_minor"]
        or value["runtime"]["implementation"] != "CPython"
        or not isinstance(value["runtime"]["python_version"], str)
        or re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", value["runtime"]["python_version"]) is None
        or not value["runtime"]["python_version"].startswith(
            value["runtime"]["python_major_minor"] + "."
        )
    ):
        raise ValueError("Wrong model runtime")
    if expected_runtime is not None and value["runtime"] != expected_runtime:
        raise ValueError("Worker runtime differs from archived host runtime")
    return value
