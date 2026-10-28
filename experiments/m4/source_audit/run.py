"""BC-006 isolated source audit, durable artifacts and standard-library reconstruction."""

import argparse
import hashlib
import json
import math
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from .audit import burst, calculate

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RUNTIME = ROOT / "experiments/m4/beta_cell/runtime"
VERSION = "bc006-source-audit/1"
SOURCES = ("audit.py", "numerical.py", "run.py")
REUSED = ("model.py", "uv.lock", "pyproject.toml")


def read(path):
    return json.loads(Path(path).read_text())


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def grid(horizon, step):
    return [i * step for i in range(round(horizon / step) + 1)]


def matrix(rows, count, width):
    if not isinstance(rows, list) or len(rows) != count:
        raise ValueError("Incomplete trajectory")
    for row in rows:
        if (
            not isinstance(row, list)
            or len(row) != width
            or any(
                isinstance(x, bool) or not isinstance(x, (float, int)) or not math.isfinite(x)
                for x in row
            )
        ):
            raise ValueError("Malformed/nonfinite trajectory")
    return rows


def difference(a, b):
    return max(abs(x - y) for ra, rb in zip(a, b, strict=True) for x, y in zip(ra, rb, strict=True))


def assess(p, n):
    if p.get("id") != "BC-006/1" or n.get("schema") != "bc006-numerical/1":
        raise ValueError("Wrong source audit identity")
    if any(n["runtime"][k] != v for k, v in {"numpy": "2.2.6", "scipy": "1.15.3"}.items()):
        raise ValueError("Wrong source audit runtime")
    calc = calculate(p)
    b, r, rates = p["burst"], p["reduced_comparison"], p["parameters"]
    times = grid(b["horizon_min"], b["step_min"])
    rt = grid(r["horizon_min"], r["step_min"])
    if n["burst_times_min"] != times or n["reduced_times_min"] != rt:
        raise ValueError("Incomplete or changed grid")
    expected = [burst(t, b["h0_ug"], rates["f"], rates["p_minus"], rates["m"]) for t in times]
    exact = matrix(n["burst_analytic"], len(times), 4)
    if exact != expected:
        raise ValueError("Changed analytical reference")
    if len(n["burst_states"]) != 2:
        raise ValueError("Missing numerical solver")
    states = [matrix(v, len(times), 4) for v in n["burst_states"]]
    for values in states:
        if values[0] != [b["h0_ug"], 0, 0, 0]:
            raise ValueError("Changed isolated-pool initial condition")
    initials = {
        "printed": calc["pools"]["caption_basal_equilibrium"]["printed_qss_ug"],
        "author_explicit": calc["author_explicit_x0_ug"],
        "pre_bolus_hypothesis": calc["pools"]["caption_basal_equilibrium"][
            "pre_bolus_recruited_ug"
        ],
    }
    if n["reduced_initials_ug"] != initials or set(n["reduced_states"]) != set(initials):
        raise ValueError("Changed initialization comparison")
    for name, start in initials.items():
        values = n["reduced_states"][name]
        if len(values) != 2:
            raise ValueError("Missing reduced solver")
        for rows in values:
            matrix(rows, len(rt), 2)
            if rows[0] != [start, 0]:
                raise ValueError("Changed reduced initial condition")
    ref = n["reduced_states"]["printed"][-1]
    delta_error = 0.0
    contrasts = {}
    for name in ("author_explicit", "pre_bolus_hypothesis"):
        delta0 = initials[name] - initials["printed"]
        rows = n["reduced_states"][name][-1]
        delta_error = max(
            delta_error,
            max(
                abs(a[0] - z[0] - delta0 * math.exp(-rates["m"] * t))
                for a, z, t in zip(rows, ref, rt, strict=True)
            ),
            max(abs(a[1] - z[1]) for a, z in zip(rows, ref, strict=True)),
        )
        contrasts[name] = {
            "initial_secretion_difference_ug_min": rates["m"] * delta0,
            "analytical_cumulative_secretion_difference_ug": -delta0
            * math.expm1(-rates["m"] * r["horizon_min"]),
        }
    repeated = matrix(n["repeated_reference"], len(rt), 2)
    metrics = {
        "burst_state_error_ug": max(difference(v, exact) for v in states),
        "burst_mass_error_ug": max(
            abs(math.fsum(row) - b["h0_ug"]) for values in states for row in values
        ),
        "reduced_initial_difference_error_ug": delta_error,
        "solver_state_error_ug": max(
            difference(*states), *(difference(*v) for v in n["reduced_states"].values())
        ),
        "chain_rule_relative_error": max(v["relative_error"] for v in calc["chain_rule"]),
        "repeat_absolute_error": difference(
            repeated, n["reduced_states"]["pre_bolus_hypothesis"][-1]
        ),
    }
    return {
        "schema": "bc006-report/1",
        "implementation": VERSION,
        "calculations": calc,
        "contrasts": contrasts,
        "numerical_metrics": metrics,
        "passed": all(v <= p["criteria"][k] for k, v in metrics.items()),
        "external_review": "not_performed",
        "excluded": p["excluded"],
    }


def hashes(directory):
    return {
        p.name: digest(p)
        for p in sorted(directory.iterdir())
        if p.is_file() and p.name != "manifest.json"
    }


def reconstruct(directory):
    directory = Path(directory)
    m = read(directory / "manifest.json")
    required = {
        "protocol.json",
        "sources.json",
        "numerical.json",
        "report.json",
        *(f"source-{s}" for s in SOURCES),
        *(f"bc001-{s}" for s in REUSED),
    }
    if (
        m.get("status") != "completed"
        or m.get("implementation") != VERSION
        or not required.issubset(m.get("files", {}))
    ):
        raise ValueError("Incomplete audit archive")
    for name, value in m["files"].items():
        path = directory / name
        if (
            Path(name).name != name
            or name in (".", "..")
            or path.is_symlink()
            or not path.is_file()
            or digest(path) != value
        ):
            raise ValueError("Changed, missing or unsafe audit artifact")
    return assess(read(directory / "protocol.json"), read(directory / "numerical.json"))


def execute(output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    m = {
        "implementation": VERSION,
        "status": "started",
        "started_utc": datetime.now(UTC).isoformat(),
        "files": {},
    }
    dump(output / "manifest.json", m)
    try:
        m["git_head"] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
        m["git_dirty"] = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT))
        for name in ("protocol.json", "sources.json"):
            shutil.copyfile(HERE / name, output / name)
        for name in SOURCES:
            shutil.copyfile(HERE / name, output / f"source-{name}")
        for name in REUSED:
            shutil.copyfile(RUNTIME / name, output / f"bc001-{name}")
        cmd = [
            "uv",
            "run",
            "--locked",
            "--project",
            str(RUNTIME),
            "python",
            "-m",
            "experiments.m4.source_audit.numerical",
            str(output),
        ]
        m["command"] = cmd
        dump(output / "manifest.json", m)
        with (output / "numerical.log").open("x") as log:
            subprocess.run(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
        report = assess(read(output / "protocol.json"), read(output / "numerical.json"))
        dump(output / "report.json", report)
        if not report["passed"]:
            raise RuntimeError("Source audit numerical criteria failed")
        m["status"] = "completed"
    except BaseException as exc:
        m.update(status="failed", error={"type": type(exc).__name__, "message": str(exc)})
        raise
    finally:
        m.update(finished_utc=datetime.now(UTC).isoformat(), files=hashes(output))
        dump(output / "manifest.json", m)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reconstruct", type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    if args.reconstruct:
        report = reconstruct(args.reconstruct)
        dump(args.output, report)
    else:
        report = execute(args.output)
    if not report["passed"]:
        raise SystemExit("Source audit numerical criteria failed")
    print("BC-006 completed; hypotheses only, external review remains open")


if __name__ == "__main__":
    main()
