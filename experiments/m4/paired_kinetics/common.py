"""BC-005 artifact/layout conventions; standard library only."""

import copy
import math
from pathlib import Path

from experiments.m4.kinetic_inlet.forcing import Forcing
from experiments.m4.paired_observation.run import digest, reconstruct
from experiments.m4.paired_observation.run import dump as dump
from experiments.m4.paired_observation.run import read as read

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
VERSION = "bc005-paired-kinetics/1"
NAMES = (
    "zero_increment",
    "pulse_increment",
    "pulse_synthetic_total",
    "mass_ramp_increment",
    "basal_only",
    "washout",
)
LIMITS = (
    "oracle_state_error_pmol_kg",
    "concentration_error_pmol_l",
    "mass_error_pmol_kg",
    "input_error_pmol_kg",
    "negative_tolerance_pmol_kg",
    "equilibrium_error_pmol_kg",
    "superposition_error_pmol_kg",
    "legacy_zero_initial_error",
    "repeat_error",
    "fine_communication_error_pmol_l",
    "fine_coarse_error_ratio",
)
SOURCES = (
    "common.py",
    "insulin.py",
    "oracle.py",
    "worker.py",
    "report.py",
    "run.py",
    "plot.py",
    "test_insulin.py",
    "test_cpeptide.py",
)
REUSED = (
    "experiments/m4/kinetic_inlet/native.py",
    "experiments/m4/kinetic_inlet/oracle.py",
    "experiments/m4/kinetic_inlet/forcing.py",
    "experiments/m4/kinetic_inlet/protocol.json",
    "experiments/m4/c_peptide/model.py",
    "experiments/m4/c_peptide/reference.py",
    "experiments/m4/paired_observation/run.py",
    "experiments/m4/paired_observation/contract.py",
)


def finite(value, *, positive=False):
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
        raise ValueError("Finite numeric value required")
    if value <= 0 if positive else value < 0:
        raise ValueError("Invalid numeric sign")
    return value


def validate(p):
    if (
        p.get("schema") != "bc005-protocol/1"
        or p.get("id") != "BC-005/1"
        or p.get("claim") != "synthetic_paired_kinetics_only"
        or p.get("branches") != ["insulin", "cpeptide"]
    ):
        raise ValueError("Unsupported paired protocol")
    finite(p["sample_step_min"], positive=True)
    if set(p["criteria"]) != set(LIMITS):
        raise ValueError("Missing paired criteria")
    for value in p["criteria"].values():
        finite(value)
    if [s["name"] for s in p["solvers"]] != ["coarse", "tight", "reference"]:
        raise ValueError("Incomplete solver comparison")
    for s in p["solvers"]:
        if set(s) != {"name", "method", "rtol", "atol", "max_step"} or s["method"] not in {
            "RK45",
            "DOP853",
        }:
            raise ValueError("Invalid solver specification")
        for key in ("rtol", "atol", "max_step"):
            finite(s[key], positive=True)
        if s["rtol"] >= 1:
            raise ValueError("Invalid relative tolerance")
    steps = p["communication_intervals_min"]
    if len(steps) < 2 or any(b >= a for a, b in zip(steps, steps[1:])):
        raise ValueError("Incomplete communication refinement")
    for step in steps:
        finite(step, positive=True)
    if p["communication_case"] != "mass_ramp_increment":
        raise ValueError("Unsupported communication case")
    if set(p["extra_cases"]) != {"basal_only", "washout"}:
        raise ValueError("Missing extra initial-state cases")
    if p["extra_cases"]["basal_only"]["source"] != "pulse_synthetic_total":
        raise ValueError("Unsupported basal source")
    if p["extra_cases"]["basal_only"]["horizon_min"] != 240:
        raise ValueError("Basal horizon must match the frozen pulse case")
    for branch, n in (("insulin", 5), ("cpeptide", 4)):
        values = p["extra_cases"]["washout"][branch + "_initial"]
        if len(values) != n or any(values[2:]):
            raise ValueError("Invalid washout state/ledgers")
        for value in values:
            finite(value)
    finite(p["extra_cases"]["washout"]["horizon_min"], positive=True)
    expected = {
        "insulin": {"project": "experiments/m0/simglucose", "numpy": "1.26.4", "scipy": "1.13.1"},
        "cpeptide": {
            "project": "experiments/m4/beta_cell/runtime",
            "numpy": "2.2.6",
            "scipy": "1.15.3",
        },
    }
    if p["runtime"] != expected:
        raise ValueError("Unsupported isolated runtime")


def cases(directory, p):
    validate(p)
    if digest(Path(directory) / "protocol.json") != p["boundary_protocol_sha256"]:
        raise ValueError("BC-004 protocol identity mismatch")
    result = reconstruct(directory)
    items = copy.deepcopy(result["bundles"])
    total = next(c for c in items if c["id"] == "pulse_synthetic_total")
    basal = copy.deepcopy(total)
    basal["id"] = "basal_only"
    q = total["basal_pmol_kg_min"]
    for branch in p["branches"]:
        basal[branch]["forcing"] = Forcing([0, 240], [q], [q]).to_dict()
    washout = copy.deepcopy(total)
    washout["id"] = "washout"
    washout["baseline_mode"] = "nonstationary_inventory"
    washout["basal_pmol_kg_min"] = 0
    for branch in p["branches"]:
        washout[branch]["forcing"] = Forcing(
            [0, p["extra_cases"]["washout"]["horizon_min"]], [0], [0]
        ).to_dict()
        washout[branch]["initial"] = p["extra_cases"]["washout"][branch + "_initial"]
    items.extend([basal, washout])
    if tuple(c["id"] for c in items) != NAMES:
        raise ValueError("Unexpected paired case matrix")
    # Only transfer fields relevant to kinetics; omit obsolete preflight capability flags.
    return [
        {
            "id": c["id"],
            "baseline_mode": c["baseline_mode"],
            "basal_pmol_kg_min": c["basal_pmol_kg_min"],
            **{b: {"forcing": c[b]["forcing"], "initial": c[b]["initial"]} for b in p["branches"]},
        }
        for c in items
    ]


def grid(case, p):
    edges = case["insulin"]["forcing"]["edges"]
    count = edges[-1] / p["sample_step_min"]
    if not math.isfinite(count) or count != round(count) or not 1 <= count <= 100000:
        raise ValueError("Incomplete reporting grid")
    return sorted({*[i * p["sample_step_min"] for i in range(round(count) + 1)], *edges})


def file_hashes(directory):
    return {
        p.relative_to(directory).as_posix(): digest(p)
        for p in sorted(Path(directory).rglob("*"))
        if p.is_file() and p != Path(directory) / "manifest.json"
    }


def verify_files(directory, manifest, required):
    files = manifest.get("files", {})
    if not required.issubset(files):
        raise ValueError("Missing required paired artifacts")
    for name, expected in files.items():
        path = Path(name)
        if path.is_absolute() or ".." in path.parts or not path.parts or path.as_posix() != name:
            raise ValueError("Unsafe paired artifact path")
        current = Path(directory)
        for part in path.parts:
            current /= part
            if current.is_symlink():
                raise ValueError("Symlink in paired archive")
        if not current.is_file() or digest(current) != expected:
            raise ValueError(f"Changed/missing paired artifact: {name}")
