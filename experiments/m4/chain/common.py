"""Frozen BC-007 boundary and source reader, independent of scientific packages."""

import hashlib
import json
from pathlib import Path

from experiments.m4.beta_cell.runtime.report import (
    TRACE_COLUMNS,
    read_table,
)
from experiments.m4.beta_cell.runtime.report import (
    reconstruct as source_report,
)
from experiments.m4.kinetic_inlet.forcing import Forcing, from_source_samples
from experiments.m4.paired_kinetics.common import (
    dump as dump,
)
from experiments.m4.paired_kinetics.common import (
    file_hashes as file_hashes,
)
from experiments.m4.paired_kinetics.common import (
    finite,
)
from experiments.m4.paired_kinetics.common import (
    read as read,
)
from experiments.m4.paired_kinetics.common import (
    verify_files as verify_files,
)
from experiments.m4.paired_observation.contract import prepare_case
from experiments.m4.paired_observation.run import digest as digest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
VERSION = "bc007-glucose-secretion-kinetics/1"
PROTOCOL_SHA256 = "f7a54462b3423e7c50cf6fcf611d82e355aab59daca3aa9c2747a3d60be69076"
SOURCES = ("common.py", "source.py", "worker.py", "report.py", "run.py", "plot.py")
REUSED = (
    "experiments/m4/beta_cell/runtime/model.py",
    "experiments/m4/beta_cell/runtime/report.py",
    "experiments/m4/kinetic_inlet/forcing.py",
    "experiments/m4/kinetic_inlet/native.py",
    "experiments/m4/kinetic_inlet/oracle.py",
    "experiments/m4/kinetic_inlet/protocol.json",
    "experiments/m4/c_peptide/model.py",
    "experiments/m4/paired_observation/contract.py",
    "experiments/m4/paired_observation/run.py",
    "experiments/m4/paired_kinetics/insulin.py",
    "experiments/m4/paired_kinetics/oracle.py",
    "experiments/m4/paired_kinetics/common.py",
    "experiments/m4/paired_kinetics/report.py",
)


def validate(p):
    encoded = json.dumps(p, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    if hashlib.sha256(encoded).hexdigest() != PROTOCOL_SHA256:
        raise ValueError("BC-007/1 is frozen; unsupported protocol or changed criteria")


def grid(p, step=None):
    step = p["sample_step_min"] if step is None else step
    return [i * step for i in range(round(p["horizon_min"] / step) + 1)]


def load_source(directory, p):
    """Check the whole unchanged source archive before trusting a secretion sample."""
    validate(p)
    directory = Path(directory)
    if (
        directory.is_symlink()
        or digest(directory / "protocol.json") != p["source"]["protocol_sha256"]
    ):
        raise ValueError("Wrong BC-001 protocol or source path")
    report = source_report(directory)
    manifest = read(directory / "manifest.json")
    if (
        not report["passed"]
        or report["protocol"] != p["source"]["protocol"]
        or manifest.get("model_version") != p["source"]["model"]
    ):
        raise ValueError("Failed or unsupported secretion source")
    rows = read_table(directory / "trace.csv", TRACE_COLUMNS)
    times = [r["time_min"] for r in rows]
    if times != grid(p):
        raise ValueError("Source grid does not match chain; no extrapolation allowed")
    return {
        "times_min": times,
        "glucose_mmol_l": [r["glucose_mmol_per_L"] for r in rows],
        "secretion_ug_min": [r["secretion_ug_per_min"] for r in rows],
        "source_manifest_sha256": digest(directory / "manifest.json"),
    }


def convert(times, mass_rates, *, body_weight_kg, molar_mass_g_mol, gain=1.0):
    """The only mass/body-size normalization in the chain."""
    factor = (
        finite(gain)
        * 1e6
        / (finite(molar_mass_g_mol, positive=True) * finite(body_weight_kg, positive=True))
    )
    return from_source_samples(times, [finite(v) * factor for v in mass_rates])


def boundary(directory, p):
    path = Path(directory) / "boundary.json"
    if digest(path) != p["boundary"]["protocol_sha256"]:
        raise ValueError("Changed BC-004 parameter/basal reference")
    return read(path)


def prepare(p, b, case, samples):
    """Make distinct process-owned states and one shared, normalized input."""
    validate(p)
    if case not in p["cases"]:
        raise ValueError("Unknown chain case")
    spec = p["boundary"]
    if b["body_weight_kg"] != spec["body_weight_kg"]:
        raise ValueError("Mismatched source and kinetic body mass")
    signal = convert(
        samples["times_min"],
        samples["secretion_ug_min"],
        body_weight_kg=spec["body_weight_kg"],
        molar_mass_g_mol=spec["insulin_molar_mass_g_mol"],
        gain=case["evoked_gain"],
    )
    if signal.horizon != p["horizon_min"]:
        raise ValueError("Wrong secretion horizon")
    if case["shape"] == "equal_amount_constant":
        rate = signal.integral() / signal.horizon
        signal = Forcing([0, signal.horizon], [rate], [rate])
    basal_q = spec["basal_pmol_min"] / spec["body_weight_kg"] if case["basal"] else 0.0
    total = Forcing(
        signal.edges, [v + basal_q for v in signal.left], [v + basal_q for v in signal.right]
    )
    initial = {"insulin": [0] * 5, "cpeptide": [0] * 4}
    if case["basal"]:
        baseline_case = next(c for c in b["cases"] if c["id"] == "pulse_synthetic_total")
        if baseline_case["basal_pmol_min"] != spec["basal_pmol_min"]:
            raise ValueError("Different declared basal convention")
        baseline = prepare_case(b, baseline_case)
        initial = {key: baseline[key]["initial"] for key in initial}
    return {
        "id": case["id"],
        "evoked_gain": case["evoked_gain"],
        "basal_q_pmol_kg_min": basal_q,
        "evoked": signal.to_dict(),
        "forcing": total.to_dict(),
        "initial": initial,
    }
