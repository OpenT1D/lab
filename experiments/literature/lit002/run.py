"""Execute the frozen synthetic absorption matrix in separate native processes."""

import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from .kinetics import CAMBRIDGE, SCParameters, impulse, matched_cambridge

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def save(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def timestamp() -> str:
    return datetime.now(UTC).isoformat()


def configs(protocol: dict) -> list[tuple[dict, dict]]:
    """Materialize every planned case before any native process starts."""
    result = []
    for scenario in protocol["scenarios"]:
        for arm in protocol["arms"]:
            for resolution, step in [
                ("standard", protocol["max_step_min"]),
                ("refined", protocol["refinement_max_step_min"]),
            ]:
                identity = f"{scenario['id']}__{arm}__{resolution}"
                case = {
                    "id": identity,
                    "scenario": scenario["id"],
                    "arm": arm,
                    "resolution": resolution,
                    "max_step_min": step,
                    "path": f"cases/{identity}",
                    "status": "planned",
                    "error": None,
                }
                config = {
                    key: protocol[key]
                    for key in [
                        "horizon_min",
                        "sample_step_min",
                        "relative_tolerance",
                        "equilibrium_glucose_mg_dl",
                        "absorption",
                    ]
                }
                config.update(
                    arm=arm,
                    max_step_min=step,
                    insulin_segments=scenario["insulin_segments"],
                    meals=scenario["meals"],
                )
                result.append((case, config))
    return result


def write_impulse(output: Path, protocol: dict) -> None:
    """The separate zero-history impulse is not the native finite infusion."""
    settings = protocol["impulse_comparison"]
    dose, step, horizon = (settings[k] for k in ["dose_mU_per_kg", "step_min", "horizon_min"])
    absorption = protocol["absorption"]
    source = SCParameters(
        absorption["ka1_per_min"],
        absorption["kd_per_min"],
        absorption["ka2_per_min"],
        absorption["tau_min"],
    )
    parameters_by_arm = {
        "cambridge_native": CAMBRIDGE,
        "cambridge_mean_matched": matched_cambridge(source),
        "faggionato_sc": source,
    }
    metrics = {}
    with (output / "impulse.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=[
                "time_min",
                "arm",
                "appearance_mU_per_kg_min",
                "cumulative_fraction",
                "unabsorbed_fraction",
                "sc1_mU_per_kg",
                "sc2_mU_per_kg",
                "queue_mU_per_kg",
            ],
        )
        writer.writeheader()
        for arm in protocol["arms"]:
            parameters = parameters_by_arm[arm]
            for index in range(round(horizon / step) + 1):
                sample = impulse(index * step, dose, parameters)
                writer.writerow(
                    {
                        "time_min": sample.time_min,
                        "arm": arm,
                        "appearance_mU_per_kg_min": sample.appearance,
                        "cumulative_fraction": sample.cumulative_absorbed / dose,
                        "unabsorbed_fraction": (sample.sc1 + sample.sc2 + sample.delay_inventory)
                        / dose,
                        "sc1_mU_per_kg": sample.sc1,
                        "sc2_mU_per_kg": sample.sc2,
                        "queue_mU_per_kg": sample.delay_inventory,
                    }
                )
            quantiles = {}
            for fraction in (0.5, 0.9):
                lower, upper = 0.0, float(horizon)
                if impulse(upper, dose, parameters).cumulative_absorbed / dose < fraction:
                    quantiles[f"t{round(100 * fraction)}_min"] = None
                    continue
                for _ in range(80):
                    middle = (lower + upper) / 2
                    if impulse(middle, dose, parameters).cumulative_absorbed / dose < fraction:
                        lower = middle
                    else:
                        upper = middle
                quantiles[f"t{round(100 * fraction)}_min"] = (lower + upper) / 2
            metrics[arm] = {
                **quantiles,
                "fraction_absorbed_at_horizon": impulse(
                    horizon, dose, parameters
                ).cumulative_absorbed
                / dose,
            }
    save(
        output / "impulse_metrics.json",
        {
            "scope": (
                "Model cumulative appearance after an ideal synthetic impulse; "
                "not clinical duration of action."
            ),
            "settings": settings,
            "arms": metrics,
        },
    )


def run(output: Path, *, timeout_seconds: int = 180) -> dict:
    from .report import write_report
    from .verification import verify_case

    output = output.resolve()
    if output.exists():
        raise ValueError("Choose a new output directory; previous evidence is never overwritten")
    protocol = json.loads((HERE / "protocol.json").read_text())
    parameters = HERE.parent / "lit001/parameters.json"
    if digest(parameters) != protocol["source_parameter_record_sha256"]:
        raise ValueError("Source parameter record changed after protocol freeze")
    node = shutil.which("node")
    if (
        not node
        or subprocess.check_output([node, "--version"], text=True).strip()
        != protocol["node_version"]
    ):
        raise ValueError("Install the exact Node version specified in protocol.json")
    loader = ROOT / "experiments/m0/lt1/node_modules/ts-node/esm.mjs"
    if not loader.is_file():
        raise ValueError("Install the locked M0 LT1 toolchain first; see docs/lit002-tutorial.md")
    subprocess.run([node, str(ROOT / "experiments/m0/lt1/setup.mjs")], cwd=ROOT, check=True)
    output.mkdir(parents=True)
    shutil.copy2(HERE / "protocol.json", output / "protocol.json")
    planned = configs(protocol)
    manifest = {
        "schema": "lit002-study/1",
        "started_utc": timestamp(),
        "status": "running",
        "expected_case_count": len(planned),
        "cases": [case for case, _ in planned],
        "protocol_sha256": digest(output / "protocol.json"),
        "artifacts": {},
        "python": sys.version,
        "node": protocol["node_version"],
        "git_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "git_branch": subprocess.check_output(
            ["git", "branch", "--show-current"], cwd=ROOT, text=True
        ).strip(),
        "source_snapshot": (
            "Exact local experiment and toolchain files, including uncommitted changes, in source/."
        ),
    }
    sources = [p for p in HERE.rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    sources += [parameters, ROOT / "uv.lock", ROOT / "pyproject.toml"]
    sources += sorted((ROOT / "tests").glob("test_lit002_*.py"))
    sources += [
        ROOT / "docs/research/lit002-protocol.md",
        ROOT / "docs/decisions/0009-experimental-insulin-absorption.md",
    ]
    sources += [
        ROOT / "experiments/m0/lt1" / name
        for name in [
            "setup.mjs",
            "record.mjs",
            "package.json",
            "package-lock.json",
            "tsconfig.json",
        ]
    ]
    sources += [HERE.parent / "lit001/runtime" / name for name in ["uv.lock", "pyproject.toml"]]
    for source in sources:
        target = output / "source" / source.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    for case, config in planned:
        destination = output / case["path"]
        destination.mkdir(parents=True)
        save(destination / "config.json", config)
    save(output / "manifest.json", manifest)
    preparation_error = None
    try:
        write_impulse(output, protocol)
    except Exception as error:
        preparation_error = f"{type(error).__name__}: {error}"
        manifest["preparation_error"] = preparation_error
        save(output / "preparation_failure.json", {"error": preparation_error})
    env = {
        **os.environ,
        "TS_NODE_PROJECT": str(ROOT / "experiments/m0/lt1/tsconfig.json"),
        "OPENT1D_PARENT_PID": str(os.getpid()),
    }
    interrupted = False
    for case, _ in planned:
        directory = output / case["path"]
        try:
            if preparation_error:
                raise RuntimeError("Not executed after preparation failure: " + preparation_error)
            if interrupted:
                raise RuntimeError("Not executed after supervisor interruption; retained in matrix")
            case["status"] = "running"
            save(output / "manifest.json", manifest)
            with (directory / "native.log").open("w") as log:
                process = subprocess.run(
                    [
                        node,
                        "--loader",
                        str(loader),
                        str(HERE / "native/worker.mjs"),
                        str(directory),
                    ],
                    cwd=ROOT,
                    env=env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    timeout=timeout_seconds,
                )
            if process.returncode:
                raise RuntimeError(f"Native process exited {process.returncode}; see native.log")
            verification = verify_case(directory, protocol)
            save(directory / "verification.json", verification)
            case["status"] = "completed"
        except (KeyboardInterrupt, Exception) as error:
            if isinstance(error, KeyboardInterrupt):
                interrupted = True
            case["status"] = "failed"
            case["error"] = f"{type(error).__name__}: {error}"
            save(directory / "supervisor_failure.json", {"error": case["error"]})
        save(output / "manifest.json", manifest)
        print(f"{case['id']}: {case['status']}", flush=True)
    manifest["status"] = (
        "completed"
        if all(c["status"] == "completed" for c, _ in planned)
        else "completed_with_failures"
    )
    manifest["completed_utc"] = timestamp()
    manifest["artifacts"] = {
        str(p.relative_to(output)): digest(p)
        for p in sorted(output.rglob("*"))
        if p.is_file() and p != output / "manifest.json"
    }
    save(output / "manifest.json", manifest)
    report = write_report(output, output / "report")
    return report
