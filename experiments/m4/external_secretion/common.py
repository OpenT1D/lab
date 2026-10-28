"""Artifact and input contract for one researcher supplied secretion trace."""

import hashlib
import math
from pathlib import Path

from experiments.m4.chain.common import boundary, load_source, prepare, read, validate
from experiments.m4.kinetic_inlet.forcing import Forcing, from_source_samples

VERSION = "m4-external-secretion/1"
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCES = ("common.py", "model_host.py", "worker.py", "report.py", "run.py")
REUSED = (
    "experiments/m4/chain/common.py",
    "experiments/m4/chain/report.py",
    "experiments/m4/kinetic_inlet/forcing.py",
    "experiments/m4/kinetic_inlet/native.py",
    "experiments/m4/kinetic_inlet/oracle.py",
    "experiments/m4/c_peptide/model.py",
    "experiments/m4/paired_kinetics/insulin.py",
    "experiments/m4/paired_kinetics/oracle.py",
    "experiments/m4/paired_kinetics/report.py",
    "experiments/m4/paired_observation/contract.py",
)
CASES = ("full_increment", "full_synthetic_total")
MAX_RATE = 1000.0  # Engineering limit, not a physiological plausibility claim.


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def declaration(data):
    expected = {
        "schema",
        "model_id",
        "source_sha256",
        "rights_basis",
        "dependencies",
        "output_unit",
    }
    if not isinstance(data, dict) or set(data) != expected or data["schema"] != "m4-model/1":
        raise ValueError("Model declaration has missing or unsupported fields")
    for key in ("model_id", "rights_basis", "dependencies"):
        if not isinstance(data[key], str) or not data[key].strip() or len(data[key]) > 500:
            raise ValueError(f"Model {key} must be nonempty text")
    if data["output_unit"] != "pmol/(kg min)":
        raise ValueError("Model output must declare pmol/(kg min)")
    if not isinstance(data["source_sha256"], str) or len(data["source_sha256"]) != 64:
        raise ValueError("Model source SHA-256 is required")
    int(data["source_sha256"], 16)
    return data


def samples(data, times, glucose):
    if not isinstance(data, dict) or set(data) != {
        "schema",
        "times_min",
        "glucose_mmol_l",
        "secretion_pmol_kg_min",
        "unit",
    }:
        raise ValueError("Incomplete or unsupported model sample output")
    if data["schema"] != "m4-model-samples/1" or data["unit"] != "pmol/(kg min)":
        raise ValueError("Wrong model sample schema or units")
    if data["times_min"] != times or data["glucose_mmol_l"] != glucose:
        raise ValueError("Model samples differ from the prescribed glucose grid")
    values = data["secretion_pmol_kg_min"]
    if not isinstance(values, list) or len(values) != len(times):
        raise ValueError("Model must return one secretion rate per prescribed sample")
    if any(
        isinstance(v, bool)
        or not isinstance(v, (int, float))
        or not math.isfinite(v)
        or not 0 <= v <= MAX_RATE
        for v in values
    ):
        raise ValueError(
            "Secretion rates must be finite and within the nonnegative engineering bound"
        )
    return from_source_samples(times, values)


def reference(directory):
    from experiments.m4.chain.report import reconstruct

    directory = Path(directory)
    if directory.is_symlink():
        raise ValueError("Reference archive must not be a symlink")
    report = reconstruct(directory)
    if not report["passed"]:
        raise ValueError("BC-007 reference did not pass")
    protocol = read(directory / "protocol.json")
    validate(protocol)
    source = load_source(directory / "secretion", protocol)
    base = boundary(directory, protocol)
    return protocol, source, base, report


def candidate_request(directory, case_id, *, context=None):
    protocol, source, base = (
        reference(Path(directory) / "reference")[:3] if context is None else context
    )
    if case_id not in CASES:
        raise ValueError("Unsupported comparison case")
    sampled = read(Path(directory) / "model-samples.json")
    evoked = samples(sampled, source["times_min"], source["glucose_mmol_l"])
    case = next(item for item in protocol["cases"] if item["id"] == case_id)
    original = prepare(protocol, base, case, source)
    basal = original["basal_q_pmol_kg_min"]
    forcing = Forcing(
        evoked.edges, [v + basal for v in evoked.left], [v + basal for v in evoked.right]
    )
    return {
        "id": case_id,
        "evoked": evoked.to_dict(),
        "forcing": forcing.to_dict(),
        "initial": original["initial"],
        "basal_q_pmol_kg_min": basal,
    }
