"""Standard-library trajectory assessment; no ODE or execution of saved code."""

import argparse
import hashlib
import math
import struct
from pathlib import Path

from experiments.m4.kinetic_inlet.forcing import Forcing, interval_average

from .common import (
    NAMES,
    REUSED,
    SOURCES,
    VERSION,
    cases,
    dump,
    finite,
    grid,
    read,
    validate,
    verify_files,
)


def matrix(values, nrows, ncols):
    if (
        not isinstance(values, list)
        or len(values) != nrows
        or any(not isinstance(r, list) or len(r) != ncols for r in values)
    ):
        raise ValueError("Incomplete state matrix")
    if any(
        isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
        for r in values
        for v in r
    ):
        raise ValueError("Nonfinite state matrix")
    return values


def maxdiff(a, b):
    if len(a) != len(b) or any(len(x) != len(y) for x, y in zip(a, b, strict=True)):
        raise ValueError("Different state matrix shapes")
    return max(abs(x - y) for r, s in zip(a, b, strict=True) for x, y in zip(r, s, strict=True))


def state_checks(values, times, forcing, initial):
    expected = math.fsum(initial[:2])
    return {
        "mass_error_pmol_kg": max(abs(math.fsum(r[:-1]) - r[-1] - expected) for r in values),
        "input_error_pmol_kg": max(
            abs(r[-1] - forcing.integral(0, t)) for r, t in zip(values, times, strict=True)
        ),
        "negative_tolerance_pmol_kg": max(0, -min(v for r in values for v in r)),
    }


def assess_case(data, case, p, branch, volume):
    times = grid(case, p)
    initial = case[branch]["initial"]
    force = Forcing(**case[branch]["forcing"])
    ncols = 5 if branch == "insulin" else 4
    if (
        data.get("schema") != "bc005-case/1"
        or data.get("id") != case["id"]
        or data.get("branch") != branch
        or data.get("times_min") != times
        or data.get("initial") != initial
        or data.get("input") != force.to_dict()
        or data.get("volume_l_kg") != volume
    ):
        raise ValueError("Case grid, input, initialization, volume or identity mismatch")
    finite(volume, positive=True)
    states = data["states"]
    if set(states) != {"coarse", "tight", "reference"}:
        raise ValueError("Incomplete solver comparison")
    for values in states.values():
        matrix(values, len(times), ncols)
        if values[0] != initial:
            raise ValueError("Initial inventory was not preserved")
    exact = matrix(data["oracle"], len(times), ncols)
    if exact[0] != initial:
        raise ValueError("Oracle initial inventory mismatch")
    ref, tight = states["reference"], states["tight"]
    measured = {
        "oracle_state_error_pmol_kg": maxdiff(ref, exact),
        "concentration_error_pmol_l": max(
            abs(a[0] - b[0]) / volume for a, b in zip(ref, tight, strict=True)
        ),
        "repeat_error": finite(data["repeat_error"]),
    }
    for values in (ref, tight, exact):
        for key, value in state_checks(values, times, force, initial).items():
            measured[key] = max(measured.get(key, 0), value)
    packed = b"".join(struct.pack("<d", v) for row in ref for v in row)
    if data["repeat_sha256"] != hashlib.sha256(packed).hexdigest():
        raise ValueError("Repeated state bytes differ from recorded reference")
    if case["id"] == "zero_increment" and any(
        v != 0 for rows in [*states.values(), exact] for row in rows for v in row
    ):
        raise ValueError("Zero input/inventory produced nonzero states")
    if case["id"] == "basal_only":
        measured["equilibrium_error_pmol_kg"] = max(
            abs(r[k] - initial[k]) for r in ref for k in (0, 1)
        )
    if branch == "insulin" and not any(initial):
        legacy = matrix(data["legacy"], len(times), ncols)
        measured["legacy_zero_initial_error"] = maxdiff(legacy, ref)
    elif data["legacy"] is not None:
        raise ValueError("Unexpected zero-initial legacy comparison")
    if branch == "cpeptide" and force.left == force.right:
        analytical = data["analytical_pmol_l"]
        if not isinstance(analytical, list) or len(analytical) != len(times):
            raise ValueError("Missing analytical C-peptide comparison")
        error = max(abs(finite(v) - r[0] / volume) for v, r in zip(analytical, ref, strict=True))
        measured["concentration_error_pmol_l"] = max(measured["concentration_error_pmol_l"], error)
    elif data["analytical_pmol_l"] is not None:
        raise ValueError("Unexpected analytical concentration reference")
    return {
        "metrics": measured,
        "passed": all(v <= p["criteria"][k] for k, v in measured.items()),
        "peak_sampled_concentration_pmol_l": max(r[0] / volume for r in ref),
        "initial_concentration_pmol_l": ref[0][0] / volume,
        "final_concentration_pmol_l": ref[-1][0] / volume,
        "final_delivered_pmol_kg": ref[-1][-1],
        "coarse_reference_concentration_error_pmol_l": max(
            abs(a[0] - b[0]) / volume for a, b in zip(ref, states["coarse"], strict=True)
        ),
    }


def assess_branch(directory, p, input_cases, branch, boundary):
    folder = Path(directory) / branch
    metadata = read(folder / "worker.json")
    if (
        metadata.get("schema") != "bc005-worker/1"
        or metadata.get("status") != "completed"
        or metadata.get("branch") != branch
        or metadata.get("implementation") != VERSION
    ):
        raise ValueError("Incomplete/wrong paired worker")
    if any(metadata["runtime"][k] != p["runtime"][branch][k] for k in ("numpy", "scipy")):
        raise ValueError("Worker runtime mismatch")
    order = (
        ["Ip", "Il", "hepatic_loss", "peripheral_loss", "input"]
        if branch == "insulin"
        else ["central", "peripheral", "eliminated", "input"]
    )
    if metadata["state_order"] != order:
        raise ValueError("Wrong state order")
    volume = boundary[branch]["volume_l_kg"]
    if metadata["volume_l_kg"] != volume:
        raise ValueError("Worker volume mismatch")
    if branch == "insulin":
        identity = metadata["native_identity"]
        if (
            identity["upstream_revision"] != boundary["insulin"]["revision"]
            or identity["body_weight_kg"] != boundary["body_weight_kg"]
            or identity["profile"] != "adult#001"
        ):
            raise ValueError("Native identity differs from paired specification")
        native_protocol = read(
            Path(directory) / "source-experiments__m4__kinetic_inlet__protocol.json"
        )
        for key in ("patient_file_sha256", "parameter_file_sha256"):
            if identity[key] != native_protocol["upstream"][key]:
                raise ValueError("Wrong native source/table hash")
        for key in ("m1", "m2", "m30", "m4"):
            if not math.isclose(
                identity["kinetic_parameters"][key], boundary["insulin"][key], rel_tol=1e-14
            ):
                raise ValueError("Native kinetic parameter mismatch")
        if identity["kinetic_parameters"]["Vi"] != volume:
            raise ValueError("Native volume mismatch")
    data, summaries = {}, {}
    for case in input_cases:
        item = read(folder / f"{case['id']}.json")
        data[case["id"]] = item
        summaries[case["id"]] = assess_case(item, case, p, branch, volume)
    total, basal, extra = [
        data[n]["states"]["reference"]
        for n in ("pulse_synthetic_total", "basal_only", "pulse_increment")
    ]
    superposition = max(
        abs(a - b - c)
        for rt, rb, re in zip(total, basal, extra, strict=True)
        for a, b, c in zip(rt, rb, re, strict=True)
    )
    ramp = data[p["communication_case"]]
    communication = read(folder / "communication.json")
    if (
        communication["case"] != p["communication_case"]
        or [r["dt_min"] for r in communication["runs"]] != p["communication_intervals_min"]
    ):
        raise ValueError("Incomplete communication comparison")
    errors, accounting = [], 0.0
    reference_force = Forcing(**ramp["input"])
    for run in communication["runs"]:
        force = interval_average(reference_force, run["dt_min"])
        if run["input"] != force.to_dict():
            raise ValueError("Communication does not preserve the declared averaging rule")
        rows = matrix(run["states"], len(ramp["times_min"]), len(order))
        if rows[0] != ramp["initial"]:
            raise ValueError("Communicated input initialization mismatch")
        values = state_checks(rows, ramp["times_min"], force, ramp["initial"])
        accounting = max(
            accounting,
            abs(force.integral() - reference_force.integral()),
            values["input_error_pmol_kg"],
        )
        if any(v > p["criteria"][k] for k, v in values.items()):
            raise ValueError("Communicated trajectory violates mass/input/positivity")
        errors.append(
            max(
                abs(a[0] - b[0]) / volume
                for a, b in zip(rows, ramp["states"]["reference"], strict=True)
            )
        )
    metrics = {
        "superposition_error_pmol_kg": superposition,
        "fine_communication_error_pmol_l": errors[-1],
        "fine_coarse_error_ratio": errors[-1] / errors[0]
        if errors[0]
        else (0 if errors[-1] == 0 else math.inf),
        "input_error_pmol_kg": accounting,
    }
    return {
        "metadata": metadata,
        "cases": summaries,
        "metrics": metrics,
        "communication_errors_pmol_l": errors,
        "passed": all(s["passed"] for s in summaries.values())
        and all(v <= p["criteria"][k] for k, v in metrics.items()),
    }


def required_files():
    return {
        "protocol.json",
        "boundary/protocol.json",
        "boundary/manifest.json",
        "boundary/preflight.json",
        *(f"source-{n}" for n in SOURCES),
        *("source-" + n.replace("/", "__") for n in REUSED),
        *(f"{b}-{n}" for b in ("insulin", "cpeptide") for n in ("uv.lock", "pyproject.toml")),
        *(
            f"{b}/{n}.json"
            for b in ("insulin", "cpeptide")
            for n in (*NAMES, "worker", "communication")
        ),
    }


def reconstruct(directory, *, allow_pending=False):
    directory = Path(directory)
    manifest = read(directory / "manifest.json")
    statuses = {"completed", "calculated"} if allow_pending else {"completed"}
    if (
        manifest.get("schema") != "bc005-run/1"
        or manifest.get("status") not in statuses
        or manifest.get("implementation") != VERSION
    ):
        raise ValueError("Paired run is not complete")
    required = required_files() | (set() if allow_pending else {"report.json", "figure.svg"})
    verify_files(directory, manifest, required)
    p = read(directory / "protocol.json")
    validate(p)
    inputs = cases(directory / "boundary", p)
    boundary = read(directory / "boundary/protocol.json")
    branches = {b: assess_branch(directory, p, inputs, b, boundary) for b in p["branches"]}
    return {
        "schema": "bc005-report/1",
        "protocol": p["id"],
        "implementation": VERSION,
        "passed": all(b["passed"] for b in branches.values()),
        "branches": branches,
        "paired_input": "both branches match the same archived BC-004 rates; no shared clearance",
        "evidence": (
            "synthetic numerical paired kinetics; no glucose trajectory or human validation"
        ),
        "limitations": p["excluded"],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = reconstruct(args.directory)
    if args.output.exists():
        raise FileExistsError(args.output)
    dump(args.output, result)
    if not result["passed"]:
        raise SystemExit("Paired numerical criteria failed")


if __name__ == "__main__":
    main()
