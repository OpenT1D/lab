"""Numerical and comparison assessment from archived artifacts; standard library."""

import math

from experiments.m4.causal_secretion import report as causal_report
from experiments.m4.feedback import report as feedback_report
from experiments.m4.feedback.contract import baseline
from experiments.m4.feedback_observation.report import assess_case
from experiments.m4.kinetic_inlet.forcing import Forcing
from experiments.m4.paired_kinetics.report import matrix, maxdiff

from .common import (
    MODES,
    REFERENCE_MODES,
    SCENARIOS,
    SOLVERS,
    read,
    require,
    sha256,
    validate_native_record,
    verify_reference,
    verify_reference_snapshot,
)


def context(directory, plan):
    if (directory / "reference-manifest.json").exists():
        verify_reference_snapshot(directory)
    bc, native, probe, _ = verify_reference(directory / "historical")
    binding = read(directory / "reference-binding.json")
    require(
        binding
        == {
            "schema": "m4-initial-load-reference-binding/1",
            "manifest_sha256": sha256(directory / "historical/manifest.json"),
            "config_sha256": plan["config_sha256"],
        },
        "Historical reference identity changed",
    )
    require(
        plan.get("historical_manifest_sha256") in (None, binding["manifest_sha256"]),
        "Supplied historical reference identity changed",
    )
    task = read(directory / "sources/experiments/m4/causal_secretion/protocol.json")
    obs = read(directory / "sources/experiments/m4/feedback_observation/protocol.json")
    return bc, task, obs, native, probe["initial"]


def base(params, initial, mode, bc):
    return baseline(
        params,
        initial,
        0 if mode == "native_zero" else 0.25,
        bc["source"]["parameters"]["gamma_per_min"],
    )


def numeric_paths(scenarios, reference=False):
    modes = REFERENCE_MODES if reference else MODES[:2]
    result = {"worker.json", "native.json"}
    if not reference:
        result.add("preflight.json")
    for scenario in scenarios:
        result.update(f"{scenario}/{mode}-{solver}.json" for mode in modes for solver in SOLVERS)
        result.update(f"{scenario}/replay-{step}.json" for step in (0.25, 0.125, 0.0625))
        if reference:
            result.update(f"{scenario}/{name}.json" for name in ("native-padded", "native-class"))
    return result


def observation_paths(scenarios):
    return {"worker.json"} | {
        f"cases/{scenario}--{mode}.json" for scenario in scenarios for mode in MODES
    }


def repeated(folder, expected):
    changed = []
    for name in sorted(expected - {"worker.json"}):
        require(
            (folder / "primary" / name).is_file() and (folder / "repeat" / name).is_file(),
            f"Missing repeat evidence: {name}",
        )
        if sha256(folder / "primary" / name) != sha256(folder / "repeat" / name):
            changed.append(name)
    primary, repeat = (read(folder / label / "worker.json") for label in ("primary", "repeat"))
    require(
        primary.get("label") == "primary" and repeat.get("label") == "repeat", "Wrong repeat labels"
    )
    if {key: value for key, value in primary.items() if key != "label"} != {
        key: value for key, value in repeat.items() if key != "label"
    }:
        changed.append("worker.json metadata")
    return changed


def validate_worker(worker, kind, name, label, runtime, attempts, identity=None):
    require(
        worker.get("schema")
        == ("m4-initial-load-observer/1" if kind == "observer" else "m4-initial-load-worker/1")
        and worker.get("kind") == kind
        and worker.get("source") == name
        and worker.get("label") == label
        and worker.get("status") == "completed"
        and worker.get("attempts") == attempts,
        "Incomplete or mismatched numerical worker",
    )
    actual = worker.get("runtime", {})
    require(
        set(actual) == {"python", "numpy", "scipy"}
        and isinstance(actual["python"], str)
        and actual["python"].startswith(runtime["python"] + ".")
        and all(actual[key] == runtime[key] for key in ("numpy", "scipy")),
        "Wrong archived locked runtime",
    )
    if identity is not None:
        require(worker.get("native_identity") == identity, "Native worker ancestry changed")


def difference(left, right, column, volume=1):
    return max(abs(a[column] - b[column]) / volume for a, b in zip(left, right, strict=True))


def expected_source(bc, b, mode):
    p = bc["source"]["parameters"]
    return {
        "alpha": p["alpha_per_min"],
        "beta": p["beta_pmol_kg_min_per_mg_dl"],
        "K": p["K_pmol_kg_per_mg_dl"],
        "gamma": p["gamma_per_min"],
        "basal": b["Sb_pmol_kg_min"],
        "threshold": b["h_mg_dl"],
        "gain": 1 if mode == "bc008_reference" else 0,
    }


def inspect_reference(item, bc, params, b, scene, mode, solver):
    require(
        item.get("schema") == "bc008-trajectory/1"
        and item.get("solver") == solver
        and item.get("baseline") == b
        and item.get("load_mg") == SCENARIOS[scene]
        and item.get("source_active") is True
        and item.get("source_parameters") == expected_source(bc, b, mode),
        "Reference scenario, initial convention or source identity changed",
    )
    initial = b["state"] + [b["Z_pmol_kg_min"], b["P_pmol_kg"]] + [0.0] * 5
    initial[0] = SCENARIOS[scene]
    result = feedback_report.inspect_trajectory(item, bc, params, initial)
    return result


def replay_checks(folder, scene, parent, bc, params, metrics):
    initial = parent["initial"].copy()
    initial[13:15] = [0.0, 0.0]
    diagnostics = []
    for step in (0.25, 0.125, 0.0625):
        item = read(folder / scene / f"replay-{step}.json")
        require(
            item.get("schema") == "bc008-trajectory/1"
            and item.get("source_active") is False
            and item.get("solver") == bc["solvers"][-1]
            and item.get("sample_step_min") == step
            and item.get("load_mg") == SCENARIOS[scene]
            and item.get("baseline") == parent["baseline"],
            "Mismatched replay scenario or solver",
        )
        assessed = feedback_report.inspect_trajectory(item, bc, params, initial)
        force = Forcing(**item["forcing"])
        require(
            list(force.edges) == [i * step for i in range(round(240 / step) + 1)]
            and all(a == b for a, b in zip(force.right[:-1], force.left[1:])),
            "Incomplete replay forcing grid",
        )
        require(
            max(
                abs(force.evaluate(time) - rate[1])
                for time, rate in zip(parent["times"], parent["source_rates"], strict=True)
            )
            <= 1e-12,
            "Replay differs from parent arrival",
        )
        diagnostics.append(
            {
                "step_min": step,
                "amount_pmol_kg": force.integral(),
                "glucose_error_mg_dl": difference(
                    item["states"], parent["states"], 3, params["Vg"]
                ),
                "insulin_error_pmol_l": difference(
                    item["states"], parent["states"], 5, params["Vi"]
                ),
                **assessed,
            }
        )
        for key, source in (
            ("insulin_mass_error_pmol_kg", "insulin_mass_error"),
            ("glucose_mass_error_mg_kg", "glucose_mass_error"),
            ("negative_amount_tolerance", "negative"),
        ):
            metrics[key] = max(metrics[key], assessed[source])
    for key, source in (
        ("fine_replay_glucose_error_mg_dl", "glucose_error_mg_dl"),
        ("fine_replay_insulin_error_pmol_l", "insulin_error_pmol_l"),
    ):
        metrics[key] = max(metrics[key], diagnostics[-1][source])
    return diagnostics


def assess_numeric(directory, plan, name=None):
    bc, task, _, native, initial = context(directory, plan)
    params = native["parameters"]
    folder = directory / ("reference" if name is None else f"children/{name}")
    config = plan["configuration"]
    frozen = plan["protocol"]["numerical"]
    solvers = frozen["solvers"]
    modes = REFERENCE_MODES if name is None else MODES[:2]
    expected_attempts = [
        {"scenario": scene, "mode": mode, "solver": solver, "status": "completed"}
        for scene in config["scenarios"]
        for mode in modes
        for solver in SOLVERS
    ]
    for label in ("primary", "repeat"):
        current_native = read(folder / label / "native.json")
        validate_native_record(current_native, native)
        validate_worker(
            read(folder / label / "worker.json"),
            "reference" if name is None else "source",
            name,
            label,
            bc["runtime"],
            expected_attempts,
            current_native["identity"],
        )
    metrics = dict.fromkeys(frozen["criteria"], 0.0)
    preflight = read(directory / "historical/preflight.json")
    metrics["zero_extension_derivative_error"] = preflight["metrics"]["zero_extension_error"]
    metrics["basal_derivative_change_max_native_units_per_min"] = preflight["metrics"][
        "baseline_derivative_change"
    ]
    repeat_changed = repeated(folder, numeric_paths(config["scenarios"], name is None))
    metrics["repeat_error"] = float(bool(repeat_changed))
    if name is not None:
        declared = plan["sources"][name]["declaration"]
        first = read(folder / "primary/preflight.json")
        b = base(params, initial, "candidate", bc)
        points = [
            [0.0, b["h_mg_dl"], 0.0, b["Sb_pmol_kg_min"]],
            [120.0, b["h_mg_dl"], 0.0, b["Sb_pmol_kg_min"]],
            [240.0, b["h_mg_dl"], 0.0, b["Sb_pmol_kg_min"]],
            [4.0, b["h_mg_dl"] + 30.0, 2.0, b["Sb_pmol_kg_min"]],
            [3.0, b["h_mg_dl"] - 20.0, -1.0, b["Sb_pmol_kg_min"] + 0.2],
        ]
        outputs = matrix(first.get("outputs"), 5, 2)
        equilibrium = max(max(abs(dz), abs(rate - b["Sb_pmol_kg_min"])) for dz, rate in outputs[:3])
        require(
            first.get("schema") == "m4-causal-preflight/1"
            and first.get("points") == points
            and first.get("passed") is True
            and first.get("equilibrium_error") == equilibrium
            and equilibrium <= task["source_equilibrium_tolerance"],
            "Source equilibrium/preflight evidence changed",
        )
    scenarios, records = {}, {}
    for scene in config["scenarios"]:
        records[scene], assessed = {}, {}
        for mode in modes:
            b = base(params, initial, mode, bc)
            records[scene][mode], assessed[mode] = {}, {}
            for solver in solvers:
                item = read(folder / "primary" / scene / f"{mode}-{solver['name']}.json")
                records[scene][mode][solver["name"]] = item
                if name is None:
                    result = inspect_reference(item, bc, params, b, scene, mode, solver)
                    mapping = {
                        "insulin_mass_error_pmol_kg": result["insulin_mass_error"],
                        "glucose_mass_error_mg_kg": result["glucose_mass_error"],
                        "negative_amount_tolerance": result["negative"],
                    }
                else:
                    result = causal_report.inspect(
                        item,
                        bc,
                        task,
                        params,
                        b,
                        bc["source"]["parameters"]["gamma_per_min"],
                        {"id": scene, "stomach_solid_mg": SCENARIOS[scene]},
                        mode,
                        solver,
                        declared["source_sha256"],
                    )
                    mapping = result["metrics"]
                assessed[mode][solver["name"]] = result
                for key, value in mapping.items():
                    metrics[key] = max(metrics[key], value)
            exact = records[scene][mode]["reference"]
            for solver in ("coarse", "tight"):
                item = records[scene][mode][solver]
                for key, col, volume in (
                    ("glucose_solver_error_mg_dl", 3, params["Vg"]),
                    ("insulin_solver_error_pmol_l", 5, params["Vi"]),
                ):
                    metrics[key] = max(
                        metrics[key], difference(item["states"], exact["states"], col, volume)
                    )
                metrics["source_solver_error_pmol_kg_min"] = max(
                    metrics["source_solver_error_pmol_kg_min"],
                    maxdiff(item["source_rates"], exact["source_rates"]),
                )
            if scene == "fasting":
                for key, col, volume in (
                    ("fasting_glucose_drift_mg_dl", 3, params["Vg"]),
                    ("fasting_insulin_drift_pmol_l", 5, params["Vi"]),
                ):
                    metrics[key] = max(
                        metrics[key],
                        max(
                            abs(row[col] - exact["states"][0][col]) / volume
                            for row in exact["states"]
                        ),
                    )
        if name is None:
            zero = records[scene]["native_zero"]["reference"]
            padded = read(folder / "primary" / scene / "native-padded.json")
            require(
                padded.get("schema") == "bc008-trajectory/1"
                and padded.get("solver") == solvers[-1]
                and padded.get("baseline") == zero["baseline"]
                and padded.get("load_mg") == SCENARIOS[scene]
                and padded.get("source_active") is False,
                "Zero-extension scenario changed",
            )
            feedback_report.inspect_trajectory(padded, bc, params, zero["initial"])
            metrics["same_solver_zero_extension_state_error"] = max(
                metrics["same_solver_zero_extension_state_error"],
                maxdiff(zero["states"], padded["states"]),
            )
            native_case = read(folder / "primary" / scene / "native-class.json")
            require(
                native_case.get("times") == list(range(241)), "Incomplete native class diagnostic"
            )
            native_states = matrix(native_case.get("states"), 241, 13)
            for key, col, volume in (
                ("native_class_glucose_error_mg_dl", 3, params["Vg"]),
                ("native_class_insulin_error_pmol_l", 5, params["Vi"]),
            ):
                metrics[key] = max(
                    metrics[key], difference(native_states, zero["states"][::4], col, volume)
                )
            constant = records[scene]["host_constant_basal"]["reference"]
            for key, col, volume in (
                ("basal_control_glucose_error_mg_dl", 3, params["Vg"]),
                ("basal_control_insulin_error_pmol_l", 5, params["Vi"]),
            ):
                metrics[key] = max(
                    metrics[key], difference(zero["states"], constant["states"], col, volume)
                )
            if scene != "gastric_load_15g":
                for mode, old_mode in (
                    ("native_zero", "native_zero"),
                    ("host_constant_basal", "constant_basal"),
                    ("bc008_reference", "feedback_full"),
                ):
                    for solver in solvers:
                        old = read(
                            directory / "historical" / scene / f"{old_mode}-{solver['name']}.json"
                        )
                        if old["solver"] == solver:
                            require(
                                records[scene][mode][solver["name"]] == old,
                                "Historical numeric anchor parity changed",
                            )
        else:
            shared = read(
                directory / "reference/primary" / scene / "host_constant_basal-reference.json"
            )
            control = records[scene]["host_constant_basal"]["reference"]
            for key in (
                "times",
                "states",
                "source_rates",
                "glucose_flux_integrals",
                "glucose_quadrature_error_bounds",
                "initial",
                "baseline",
                "load_mg",
                "solver",
            ):
                require(
                    control[key] == shared[key],
                    f"Host control differs from common reference: {key}",
                )
        active = records[scene]["bc008_reference" if name is None else "candidate"]["reference"]
        replays = replay_checks(folder / "primary", scene, active, bc, params, metrics)
        scenarios[scene] = {
            "initial_gastric_solid_mg": SCENARIOS[scene],
            "assessments": assessed,
            "replays": replays,
        }
    return {
        "passed": all(metrics[key] <= limit for key, limit in frozen["criteria"].items()),
        "checks": metrics,
        "limits": frozen["criteria"],
        "repeat_changed": repeat_changed,
        "scenarios": scenarios,
    }, records


def assess_observer(directory, plan, name, records):
    _, _, p, native, _ = context(directory, plan)
    scenarios = plan["configuration"]["scenarios"]
    folder = directory / "children" / name / "observations"
    attempts = [
        {"scenario": scene, "mode": mode, "status": "completed"}
        for scene in scenarios
        for mode in MODES
    ]
    for label in ("primary", "repeat"):
        validate_worker(
            read(folder / label / "worker.json"), "observer", name, label, p["runtime"], attempts
        )
    changed = repeated(folder, observation_paths(scenarios))
    checks = dict.fromkeys(
        (key for key in p["criteria"] if key != "sampling_ratio_floor_pmol_l"), 0.0
    )
    checks["repeat_artifact_differences"] = float(bool(changed))
    summaries, curves = {}, {}
    for scene in scenarios:
        summaries[scene], curves[scene] = {}, {}
        for mode in MODES:
            parent = (
                records[scene][mode]
                if mode != "bc008_reference"
                else {
                    solver: read(directory / "reference/primary" / scene / f"{mode}-{solver}.json")
                    for solver in ("tight", "reference")
                }
            )
            item = read(folder / "primary/cases" / f"{scene}--{mode}.json")
            require(
                item.get("schema") == "m4-initial-load-observation/1"
                and item.get("id") == f"{scene}--{mode}",
                "Observer identity changed",
            )
            assessed_item = item.copy()
            if mode == "host_constant_basal":
                assessed_item["id"] = f"{scene}--constant_basal--host"
            assessed = assess_case(p, assessed_item, parent["reference"], parent["tight"])
            for key, value in assessed["checks"].items():
                checks[key] = max(checks[key], value)
            summaries[scene][mode] = assessed
            concentration = [
                row[0] / p["cpeptide"]["parameters"]["volume_l_kg"]
                for row in item["states"]["reference"]
            ]
            curves[scene][mode] = {
                "times": parent["reference"]["times"],
                "glucose": [
                    row[3] / native["parameters"]["Vg"] for row in parent["reference"]["states"]
                ],
                "insulin": [
                    row[5] / native["parameters"]["Vi"] for row in parent["reference"]["states"]
                ],
                "cpeptide": concentration,
            }
    return {
        "passed": all(value <= p["criteria"][key] for key, value in checks.items()),
        "checks": checks,
        "limits": p["criteria"],
        "repeat_changed": changed,
        "scenarios": summaries,
    }, curves


def contrast(left, right):
    require(left["times"] == right["times"] == [i * 0.25 for i in range(961)], "Pair grid mismatch")
    result = {}
    for signal in ("glucose", "insulin", "cpeptide"):
        a, b = left[signal], right[signal]
        require(
            len(a) == len(b) == 961
            and all(type(value) in (int, float) and math.isfinite(value) for value in a + b),
            "Incomplete pair signal",
        )
        differences = [x - y for x, y in zip(a, b, strict=True)]
        auc = math.fsum((x + y) * 0.25 / 2 for x, y in zip(differences, differences[1:]))
        result[signal] = {
            "signed_auc_difference": auc,
            "signed_time_mean_difference": auc / 240,
            "maximum_absolute_pointwise_difference": max(abs(value) for value in differences),
        }
    return result
