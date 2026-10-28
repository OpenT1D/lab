"""Execute/reconstruct BC-008-P1 algebra and native derivative checks, not feedback."""

import argparse
import math
import platform
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from experiments.m4.paired_kinetics.common import dump, file_hashes, read, verify_files

from .contract import baseline, number, secretion_terms, validate

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
VERSION = "bc008-preflight/1"
SOURCES = ("contract.py", "preflight.py")
REUSED = (
    "experiments/m4/kinetic_inlet/native.py",
    "experiments/m4/kinetic_inlet/forcing.py",
    "experiments/m4/kinetic_inlet/protocol.json",
    "experiments/m4/paired_kinetics/common.py",
    "experiments/m4/paired_observation/run.py",
    "experiments/m4/paired_observation/contract.py",
)


def probe(directory):
    import numpy as np
    import scipy

    from experiments.m4.kinetic_inlet.native import Action, T1DPatient, derivative, load

    p = read(directory / "protocol.json")
    validate(p)
    runtime = {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
    }
    if any(runtime[k] != p["runtime"][k] for k in ("numpy", "scipy")):
        raise ValueError("Wrong native runtime")
    params, identity = load()
    keys = ("u2ss", "m1", "m30", "m2", "m4", "ka1", "ka2", "kd", "BW", "Vi", "Vg")
    parameters = {k: float(params[k]) for k in keys}
    initial = [float(v) for v in params.iloc[2:15]]
    action = Action(CHO=0, insulin=float(params.u2ss * params.BW / 6000))
    native = T1DPatient.model(0, np.array(initial), action, params, 0, 0).tolist()
    cases = []
    for case in p["cases"]:
        b = baseline(
            parameters, initial, case["fraction"], p["source"]["parameters"]["gamma_per_min"]
        )
        action_case = Action(CHO=0, insulin=b["action_insulin_u_min"])
        dx = derivative(0, b["state"], action_case, params, q=b["Sb_pmol_kg_min"]).tolist()
        cases.append({"id": case["id"], "initial": b, "native_derivative": dx})
    probes = []
    for liver_state in (initial[9], 0.0, -1.0):
        state = initial.copy()
        state[9] = liver_state
        native_dx = T1DPatient.model(0, np.array(state), action, params, 0, 0).tolist()
        probes.append(
            {
                "state": state,
                "q": 1.5,
                "native": native_dx,
                "zero": derivative(0, state, action, params, q=0).tolist(),
                "added": derivative(0, state, action, params, q=1.5).tolist(),
            }
        )
    dump(
        directory / "probe.json",
        {
            "schema": VERSION,
            "runtime": runtime,
            "native_identity": identity,
            "parameters": parameters,
            "initial": initial,
            "native_derivative": native,
            "cases": cases,
            "locality_probes": probes,
        },
    )


def vector(value):
    if not isinstance(value, list) or len(value) != 13:
        raise ValueError("Incomplete native vector")
    return [number(v, signed=True) for v in value]


def assess(p, data):
    validate(p)
    if data["schema"] != VERSION:
        raise ValueError("Wrong preflight version")
    for key in ("numpy", "scipy"):
        if data["runtime"][key] != p["runtime"][key]:
            raise ValueError("Wrong runtime")
    if not data["runtime"]["python"].startswith(p["runtime"]["python"] + "."):
        raise ValueError("Wrong Python runtime")
    for key, native_key in (
        ("revision", "upstream_revision"),
        ("profile", "profile"),
        ("patient_file_sha256", "patient_file_sha256"),
        ("parameter_file_sha256", "parameter_file_sha256"),
    ):
        if data["native_identity"][native_key] != p["upstream"][key]:
            raise ValueError("Wrong native identity")
    params = data["parameters"]
    for value in params.values():
        number(value, positive=True)
    initial, original = vector(data["initial"]), vector(data["native_derivative"])
    if [c["id"] for c in data["cases"]] != [c["id"] for c in p["cases"]]:
        raise ValueError("Incomplete preflight cases")
    metrics = dict.fromkeys(p["preflight_criteria"], 0.0)
    summaries = []
    for spec, result in zip(p["cases"], data["cases"], strict=True):
        b = baseline(params, initial, spec["fraction"], p["source"]["parameters"]["gamma_per_min"])
        if result["initial"] != b:
            raise ValueError("Changed basal boundary")
        dx = vector(result["native_derivative"])
        error = max(abs(a - z) for a, z in zip(dx, original, strict=True))
        metrics["baseline_derivative_change"] = max(metrics["baseline_derivative_change"], error)
        state = b["state"]
        for key, index, volume in (
            ("baseline_glucose_concentration_change", 3, "Vg"),
            ("baseline_plasma_insulin_change", 5, "Vi"),
        ):
            metrics[key] = max(metrics[key], abs(state[index] - initial[index]) / params[volume])
        accounted = (
            b["u_sc_pmol_kg_min"]
            + b["Sb_pmol_kg_min"]
            - params["m4"] * state[5]
            - params["m30"] * state[9]
        )
        residual = abs(math.fsum(dx[i] for i in (5, 9, 10, 11)) - accounted)
        metrics["insulin_inventory_derivative_balance"] = max(
            metrics["insulin_inventory_derivative_balance"], residual
        )
        summaries.append({"id": spec["id"], **b, "derivative_change": error})
    if [r["state"][9] for r in data["locality_probes"]] != [initial[9], 0, -1]:
        raise ValueError("Incomplete guard probes")
    for item in data["locality_probes"]:
        state, native, zero, added = [vector(item[k]) for k in ("state", "native", "zero", "added")]
        if item["q"] != 1.5:
            raise ValueError("Changed inlet probe")
        for index in range(13):
            metrics["zero_extension_error"] = max(
                metrics["zero_extension_error"], abs(zero[index] - native[index])
            )
            expected = item["q"] if index == 9 and state[9] >= 0 else 0
            error = abs(added[index] - native[index] - expected)
            metrics["native_derivative_locality_error"] = max(
                metrics["native_derivative_locality_error"], error
            )
    # Independently express the literal signed Y equation, including its lower branch.
    checks = []
    sp = p["source"]["parameters"]
    for glucose in (40.0, 100.0, 110.0, 140.0):
        for rate in (-2.0, 0.0, 2.0):
            sb, h, y, portal = 1.1, 100.0, -0.4, 3.0
            terms = secretion_terms(glucose, rate, y + sb, portal, sb, h, 1.0, sp)
            demand = sp["beta_pmol_kg_min_per_mg_dl"] * (glucose - h)
            literal_y = -sp["alpha_per_min"] * y + sp["alpha_per_min"] * (
                demand if demand > -sb else -sb
            )
            literal_spo = y + sb + (sp["K_pmol_kg_per_mg_dl"] * rate if rate > 0 else 0)
            error = max(abs(terms["Z_dot"] - literal_y), abs(terms["pancreatic"] - literal_spo))
            metrics["rhs_equivalence_error"] = max(metrics["rhs_equivalence_error"], error)
            checks.append({"G": glucose, "Gdot": rate, **terms})
    return {
        "schema": VERSION,
        "claim": "pointwise_algebra_and_native_derivatives_only",
        "feedback_executed": False,
        "protocol": p["id"],
        "metrics": metrics,
        "passed": all(v <= p["preflight_criteria"][k] for k, v in metrics.items()),
        "baselines": summaries,
        "source_equation_probes": checks,
        "native_initial_derivative_max": max(abs(v) for v in original),
        "limitations": p["excluded"],
    }


def reconstruct(directory, *, pending=False):
    manifest = read(directory / "manifest.json")
    if manifest.get("schema") != VERSION or manifest.get("status") not in (
        {"calculated", "completed"} if pending else {"completed"}
    ):
        raise ValueError("Preflight is not complete")
    required = {
        "protocol.json",
        "probe.json",
        "sources.json",
        "uv.lock",
        "pyproject.toml",
        *(f"source-{v}" for v in SOURCES),
        *("source-" + v.replace("/", "__") for v in REUSED),
    }
    verify_files(directory, manifest, required | (set() if pending else {"report.json"}))
    return assess(read(directory / "protocol.json"), read(directory / "probe.json"))


def command(args, output):
    with (output / "native.log").open("x") as log:
        subprocess.run(args, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)


def execute(output):
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    m = {
        "schema": VERSION,
        "status": "started",
        "started_utc": datetime.now(UTC).isoformat(),
        "files": {},
    }
    dump(output / "manifest.json", m)
    try:
        m["git_head"] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
        for name in ("protocol.json", "sources.json"):
            shutil.copyfile(HERE / name, output / name)
        p = read(output / "protocol.json")
        validate(p)
        for name in SOURCES:
            shutil.copyfile(HERE / name, output / f"source-{name}")
        for name in REUSED:
            shutil.copyfile(ROOT / name, output / ("source-" + name.replace("/", "__")))
        for name in ("uv.lock", "pyproject.toml"):
            shutil.copyfile(ROOT / p["runtime"]["project"] / name, output / name)
        args = [
            "uv",
            "run",
            "--locked",
            "--project",
            str(ROOT / p["runtime"]["project"]),
            "python",
            "-m",
            "experiments.m4.feedback.preflight",
            "--native",
            str(output),
        ]
        m["command"] = args
        dump(output / "manifest.json", m)
        command(args, output)
        m.update(status="calculated", files=file_hashes(output))
        dump(output / "manifest.json", m)
        report = reconstruct(output, pending=True)
        dump(output / "report.json", report)
        if not report["passed"]:
            raise RuntimeError("Preflight criteria failed; preserve and inspect this attempt")
        m.update(
            status="completed",
            finished_utc=datetime.now(UTC).isoformat(),
            files=file_hashes(output),
        )
        dump(output / "manifest.json", m)
        return report
    except BaseException as exc:
        m.update(
            status="failed",
            error={"type": type(exc).__name__, "message": str(exc)},
            files=file_hashes(output),
        )
        dump(output / "manifest.json", m)
        raise


def main():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--native", type=Path)
    mode.add_argument("--reconstruct", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.native:
        if args.output:
            parser.error("Native worker does not accept --output")
        probe(args.native)
        return
    if args.output is None:
        parser.error("--output is required")
    if args.reconstruct:
        if args.output.exists():
            raise FileExistsError(args.output)
        report = reconstruct(args.reconstruct)
        dump(args.output, report)
    else:
        report = execute(args.output)
    if not report["passed"]:
        raise SystemExit("Preflight criteria failed")
    print("BC-008 preflight passed; feedback trajectories have not been executed")


if __name__ == "__main__":
    main()
