"""Standard-library boundary and archive helpers for M4-CAUSAL/1."""

import hashlib
import importlib.util
import json
import math
import re
from pathlib import Path

from experiments.m4.feedback.contract import baseline
from experiments.m4.feedback.contract import validate as validate_bc008
from experiments.m4.feedback.report import reconstruct as reconstruct_bc008
from experiments.m4.paired_kinetics.common import read

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
VERSION = "m4-causal-secretion/1"
SOURCES = ("protocol.json", "common.py", "coupled.py", "worker.py", "report.py", "run.py")
REUSED = (
    "experiments/m4/feedback/contract.py",
    "experiments/m4/feedback/report.py",
    "experiments/m4/feedback/preflight.py",
    "experiments/m4/feedback/source_oracle.py",
    "experiments/m4/feedback/coupled.py",
    "experiments/m4/kinetic_inlet/native.py",
    "experiments/m4/paired_kinetics/common.py",
    "experiments/m4/paired_kinetics/report.py",
)
CASES = ("candidate", "host_constant_basal")
SCENARIOS = ("fasting", "gastric_load_30g")
SOLVERS = ("tight", "reference")
BC008_FILE_SHA256 = "b66087592810be35fa74372ad07172359897ceb40653abdf420b3c3fa1a4fd99"
PROTOCOL_SHA256 = "00a32ccb6403e7921d09f7d28ca612d4bfa2b0d7a2778f7195a93482cdfca6f1"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def protocol(p, bc):
    validate_bc008(bc)
    encoded = json.dumps(p, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    if hashlib.sha256(encoded).hexdigest() != PROTOCOL_SHA256:
        raise ValueError("M4-CAUSAL/1 protocol and criteria are frozen")
    if (
        p.get("schema") != "m4-causal-secretion-protocol/1"
        or p.get("id") != "M4-CAUSAL/1"
        or p.get("reference_id") != bc["id"]
        or p.get("reference_protocol_file_sha256") != BC008_FILE_SHA256
        or p.get("cases") != list(CASES)
        or p.get("scenarios") != list(SCENARIOS)
        or p.get("solvers") != list(SOLVERS)
        or [s["id"] for s in bc["scenarios"]] != list(SCENARIOS)
        or not {"tight", "reference"}.issubset({s["name"] for s in bc["solvers"]})
    ):
        raise ValueError("Unsupported causal task or changed BC-008 boundary")
    return p


def declaration(value):
    keys = {
        "schema",
        "model_id",
        "source_sha256",
        "ancestry",
        "rights_basis",
        "dependencies",
        "parameters",
        "output_unit",
    }
    if not isinstance(value, dict) or set(value) != keys or value["schema"] != "m4-causal-model/1":
        raise ValueError("Incomplete or unsupported causal model declaration")
    for name in ("model_id", "ancestry", "rights_basis", "dependencies"):
        if not isinstance(value[name], str) or not value[name].strip() or len(value[name]) > 500:
            raise ValueError(f"Model {name} must be nonempty, bounded text")
    if value["output_unit"] != "pmol/(kg min)":
        raise ValueError("Pancreatic output unit must be pmol/(kg min)")
    source_hash = value["source_sha256"]
    if not isinstance(source_hash, str) or re.fullmatch(r"[0-9a-f]{64}", source_hash) is None:
        raise ValueError("Model source SHA-256 must be lowercase hexadecimal")
    params = value["parameters"]
    if not isinstance(params, dict) or len(params) > 32:
        raise ValueError("Model parameters must be a small flat numeric mapping")
    for name, number in params.items():
        if not isinstance(name, str) or re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,63}", name) is None:
            raise ValueError("Model parameter names must be simple identifiers")
        if (
            isinstance(number, bool)
            or not isinstance(number, (int, float))
            or not math.isfinite(number)
            or abs(number) > 1e6
        ):
            raise ValueError("Model parameters must be finite bounded numbers")
    return value


def load_model(source):
    spec = importlib.util.spec_from_file_location("researcher_causal_secretion", source)
    if spec is None or spec.loader is None:
        raise ValueError("Cannot load researcher source")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not callable(getattr(module, "evaluate", None)):
        raise ValueError("Model must define a callable evaluate function")
    return module.evaluate


def evaluate(fn, t, glucose, glucose_rate, z, basal_rate, threshold, params, p):
    values = fn(t, glucose, glucose_rate, z, basal_rate, threshold, dict(params))
    if not isinstance(values, (list, tuple)) or len(values) != 2:
        raise ValueError("Model must return [dZ/dt, pancreatic rate]")
    dz, pancreatic = values
    for value in values:
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            raise ValueError("Nonfinite or nonnumeric model output")
    if abs(dz) > p["max_abs_state_derivative_pmol_kg_min2"]:
        raise ValueError("Model state derivative exceeds engineering bound")
    if not 0 <= pancreatic <= p["max_rate_pmol_kg_min"]:
        raise ValueError("Pancreatic rate outside nonnegative engineering bound")
    return float(dz), float(pancreatic)


def preflight(fn, basal_rate, threshold, params, p):
    """Check the declared equilibrium and common hidden-state mistakes."""
    points = [
        (0.0, threshold, 0.0, basal_rate),
        (120.0, threshold, 0.0, basal_rate),
        (240.0, threshold, 0.0, basal_rate),
        (4.0, threshold + 30.0, 2.0, basal_rate),
        (3.0, threshold - 20.0, -1.0, basal_rate + 0.2),
    ]
    first = [evaluate(fn, *item, basal_rate, threshold, params, p) for item in points]
    second = [evaluate(fn, *item, basal_rate, threshold, params, p) for item in reversed(points)]
    if first != list(reversed(second)):
        raise ValueError("Model is not repeatable under out-of-order evaluations")
    error = max(max(abs(dz), abs(spo - basal_rate)) for dz, spo in first[:3])
    if error > p["source_equilibrium_tolerance"]:
        raise ValueError("Model does not preserve the declared basal equilibrium")
    return {
        "schema": "m4-causal-preflight/1",
        "points": points,
        "outputs": first,
        "equilibrium_error": error,
        "passed": True,
    }


def reference(directory):
    directory = Path(directory)
    if directory.is_symlink():
        raise ValueError("BC-008 reference archive cannot be a symlink")
    report = reconstruct_bc008(directory)
    if not report["passed"]:
        raise ValueError("BC-008 reference failed its own verification")
    bc = read(directory / "protocol.json")
    validate_bc008(bc)
    if sha256(directory / "protocol.json") != BC008_FILE_SHA256:
        raise ValueError("BC-008 reference file bytes changed")
    return bc, read(directory / "native.json"), read(directory / "probe.json"), report


def baseline_context(bc, native, probe):
    fraction = next(c["fraction"] for c in bc["cases"] if c["id"] == "feedback_full")
    gamma = bc["source"]["parameters"]["gamma_per_min"]
    initial = probe["initial"]
    return baseline(native["parameters"], initial, fraction, gamma), gamma
