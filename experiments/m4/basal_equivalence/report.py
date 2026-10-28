"""Reconstruct the frozen SC-equivalence search without executing either model."""

import argparse
from pathlib import Path

from experiments.m4.causal_secretion.report import inspect as inspect_causal
from experiments.m4.paired_kinetics.common import dump, read, verify_files
from experiments.m4.paired_kinetics.report import matrix

from .common import (
    REUSED,
    SLOTS,
    SOURCES,
    VERSION,
    context,
    declared_sources,
    next_step,
    no_solution_confirmation_factors,
    sc_context,
    sha256,
)


def base_required():
    return {
        "protocol.json",
        "reference/manifest.json",
        "pyproject.toml",
        "uv.lock",
        "primary.log",
        "repeat.log",
        *(f"source-{name}" for name in SOURCES),
        *("source-" + name.replace("/", "__") for name in REUSED),
        *(f"{slot}.{suffix}" for slot in SLOTS for suffix in ("json", "py")),
        *(f"{label}/worker.json" for label in ("primary", "repeat")),
        *(
            f"{label}/{slot}/{name}.json"
            for label in ("primary", "repeat")
            for slot in SLOTS
            for name in ("search", "preflight")
        ),
        *(
            f"{label}/control/anchor-{solver}.json"
            for label in ("primary", "repeat")
            for solver in ("tight", "reference")
        ),
    }


def expected_preflight(basal, task):
    points = [
        [0.0, basal["h_mg_dl"], 0.0, basal["Sb_pmol_kg_min"]],
        [120.0, basal["h_mg_dl"], 0.0, basal["Sb_pmol_kg_min"]],
        [240.0, basal["h_mg_dl"], 0.0, basal["Sb_pmol_kg_min"]],
        [4.0, basal["h_mg_dl"] + 30.0, 2.0, basal["Sb_pmol_kg_min"]],
        [3.0, basal["h_mg_dl"] - 20.0, -1.0, basal["Sb_pmol_kg_min"] + 0.2],
    ]
    return points, task["source_equilibrium_tolerance"]


def attempt(slot, factor, phase, mode, scenario, solver, file):
    return {
        "slot": slot,
        "factor": factor,
        "phase": phase,
        "mode": mode,
        "scenario": scenario,
        "solver": solver,
        "file": file,
        "status": "completed",
    }


def reconstruct(directory, *, allow_pending=False, allow_failed=False):
    directory = Path(directory)
    manifest = read(directory / "manifest.json")
    allowed = {"completed"} | ({"calculated"} if allow_pending else set())
    if allow_failed and manifest.get("status") == "failed":
        verify_files(directory, manifest, {"protocol.json", "reference/manifest.json"})
        return {
            "schema": "m4-basal-equivalence-report/1",
            "passed": False,
            "error": manifest.get("error"),
            "attempts": {
                label: read(directory / label / "worker.json").get("attempts", [])
                for label in ("primary", "repeat")
                if (directory / label / "worker.json").exists()
            },
            "models": {},
            "limitations": ["Incomplete execution; no SC equivalence accepted"],
        }
    if (
        manifest.get("schema") != "m4-basal-equivalence-run/1"
        or manifest.get("status") not in allowed
    ):
        raise ValueError("Basal-equivalence archive is not complete")
    required = base_required() | (set() if allow_pending else {"report.json"})
    verify_files(directory, manifest, required)
    bc, native, basal, gamma, task, target = context(
        directory / "reference", directory / "protocol.json"
    )
    if manifest["reference_manifest_sha256"] != sha256(directory / "reference" / "manifest.json"):
        raise ValueError("BC-008 reference identity changed")
    declared = declared_sources(directory)
    if manifest["source_hashes"] != {slot: declared[slot]["source_sha256"] for slot in SLOTS}:
        raise ValueError("Manifest model identities changed")
    params = native["parameters"]
    meal = next(item for item in bc["scenarios"] if item["id"] == "gastric_load_30g")
    fasting = next(item for item in bc["scenarios"] if item["id"] == "fasting")
    solvers = {item["name"]: item for item in bc["solvers"]}
    metrics = {name: 0.0 for name in task["criteria"]}
    models = {}
    case_files = []
    expected_attempts = []

    def assess(path, slot, factor, mode, scenario, solver):
        record = read(directory / "primary" / path)
        if record.get("sc_factor") != factor:
            raise ValueError("Saved SC multiplier changed")
        result = inspect_causal(
            record,
            bc,
            task,
            params,
            sc_context(basal, params, factor),
            gamma,
            scenario,
            mode,
            solver,
            declared[slot]["source_sha256"],
        )
        for name in (
            "insulin_mass_error_pmol_kg",
            "glucose_mass_error_mg_kg",
            "negative_amount_tolerance",
        ):
            metrics[name] = max(metrics[name], result["metrics"][name])
        return record, result

    def compare_solvers(tight, reference_record, tight_auc, reference_auc):
        metrics["glucose_solver_error_mg_dl"] = max(
            metrics["glucose_solver_error_mg_dl"],
            max(
                abs(a[3] - b[3]) / params["Vg"]
                for a, b in zip(tight["states"], reference_record["states"], strict=True)
            ),
        )
        metrics["insulin_solver_error_pmol_l"] = max(
            metrics["insulin_solver_error_pmol_l"],
            max(
                abs(a[5] - b[5]) / params["Vi"]
                for a, b in zip(tight["states"], reference_record["states"], strict=True)
            ),
        )
        metrics["auc_solver_error_mg_min_dl"] = max(
            metrics["auc_solver_error_mg_min_dl"], abs(reference_auc - tight_auc)
        )

    for slot in SLOTS:
        model_dir = Path(slot)
        search_path = model_dir / "search.json"
        preflight_path = model_dir / "preflight.json"
        search = read(directory / "primary" / search_path)
        if search != read(directory / "repeat" / search_path):
            raise ValueError("Search decisions differ across processes")
        first = read(directory / "primary" / preflight_path)
        second = read(directory / "repeat" / preflight_path)
        points, tolerance = expected_preflight(basal, task)
        outputs = matrix(first.get("outputs"), 5, 2)
        error = max(max(abs(dz), abs(rate - basal["Sb_pmol_kg_min"])) for dz, rate in outputs[:3])
        if (
            first != second
            or first.get("schema") != "m4-causal-preflight/1"
            or first.get("points") != points
            or first.get("equilibrium_error") != error
            or first.get("passed") is not True
            or error > tolerance
        ):
            raise ValueError("Source preflight changed or failed")
        case_files.extend((str(search_path), str(preflight_path)))
        history = search.get("history")
        if search.get("schema") != "m4-basal-search/1" or not isinstance(history, list):
            raise ValueError("Missing search history")
        rebuilt = []
        anchor_record = None
        for index, item in enumerate(history):
            phase, factor = next_step(rebuilt, target, task)
            name = f"{index:02d}-{phase}-tight.json"
            if phase not in ("grid", "bisect") or item != {
                "factor": factor,
                "phase": phase,
                "file": name,
                "auc": item.get("auc"),
            }:
                raise ValueError("Search order or multiplier changed")
            path = model_dir / name
            record, result = assess(path, slot, factor, "candidate", meal, solvers["tight"])
            auc = result["outcomes"]["auc_above_initial_mg_min_dl"]
            if item["auc"] != auc:
                raise ValueError("Saved AUC differs from reconstructed trajectory")
            rebuilt.append(item)
            case_files.append(str(path))
            expected_attempts.append(
                attempt(slot, factor, phase, "candidate", meal["id"], "tight", str(path))
            )
            if factor == 0.75:
                anchor_record = record
        decision, factor = next_step(rebuilt, target, task)
        if decision != search.get("status") or factor != search.get("root_factor"):
            raise ValueError("Saved search conclusion changed")
        item_report = {
            "model_id": declared[slot]["model_id"],
            "source_sha256": declared[slot]["source_sha256"],
            "status": decision,
            "history": rebuilt,
            "bracket_endpoint_auc_mg_min_dl": [rebuilt[0]["auc"], rebuilt[4]["auc"]],
            "solution": None,
        }
        if decision == "matched":
            root_path = model_dir / "root-reference.json"
            fast_path = model_dir / "fasting-reference.json"
            root, root_check = assess(
                root_path, slot, factor, "candidate", meal, solvers["reference"]
            )
            _, fast_check = assess(
                fast_path, slot, factor, "candidate", fasting, solvers["reference"]
            )
            case_files.extend((str(root_path), str(fast_path)))
            expected_attempts.extend(
                [
                    attempt(
                        slot,
                        factor,
                        "confirmation",
                        "candidate",
                        meal["id"],
                        "reference",
                        str(root_path),
                    ),
                    attempt(
                        slot,
                        factor,
                        "diagnostic",
                        "candidate",
                        fasting["id"],
                        "reference",
                        str(fast_path),
                    ),
                ]
            )
            tight_path = model_dir / next(
                item["file"] for item in rebuilt if item["factor"] == factor
            )
            tight = read(directory / "primary" / tight_path)
            compare_solvers(
                tight,
                root,
                next(item["auc"] for item in rebuilt if item["factor"] == factor),
                root_check["outcomes"]["auc_above_initial_mg_min_dl"],
            )
            residual = root_check["outcomes"]["auc_above_initial_mg_min_dl"] - target
            item_report["solution"] = {
                "sc_factor_of_native_basal": factor,
                "sc_rate_pmol_kg_min": factor * params["u2ss"],
                "change_from_075_native_basal_pmol_kg_min": (factor - 0.75) * params["u2ss"],
                "reference_solver_auc_mg_min_dl": root_check["outcomes"][
                    "auc_above_initial_mg_min_dl"
                ],
                "target_residual_mg_min_dl": residual,
                "fasting_final_glucose_mg_dl": fast_check["outcomes"]["final_mg_dl"],
            }
        else:
            confirmed = []
            for index, tested_factor in enumerate(
                no_solution_confirmation_factors(rebuilt, target, task)
            ):
                path = model_dir / f"confirm-{index:02d}-reference.json"
                reference_record, reference_check = assess(
                    path, slot, tested_factor, "candidate", meal, solvers["reference"]
                )
                case_files.append(str(path))
                expected_attempts.append(
                    attempt(
                        slot,
                        tested_factor,
                        "no_solution_confirmation",
                        "candidate",
                        meal["id"],
                        "reference",
                        str(path),
                    )
                )
                search_item = next(item for item in rebuilt if item["factor"] == tested_factor)
                tight = read(directory / "primary" / model_dir / search_item["file"])
                reference_auc = reference_check["outcomes"]["auc_above_initial_mg_min_dl"]
                compare_solvers(tight, reference_record, search_item["auc"], reference_auc)
                confirmed.append(
                    {"factor": tested_factor, "reference_auc_mg_min_dl": reference_auc}
                )
            if decision in ("unbracketed", "nonmonotonic"):
                reference_grid = [
                    {"factor": item["factor"], "auc": item["reference_auc_mg_min_dl"]}
                    for item in confirmed[: len(task["sc_rate_multipliers_of_native_u2ss"])]
                ]
                if next_step(reference_grid, target, task)[0] != decision:
                    raise ValueError("No-solution decision changes under the reference solver")
            if decision == "resolution_limit" and any(
                abs(item["reference_auc_mg_min_dl"] - target)
                <= task["auc_match_tolerance_mg_min_dl"]
                for item in confirmed
            ):
                raise ValueError("Reference solver found a match at the search limit")
            item_report["reference_grid_confirmation"] = confirmed
        if slot == SLOTS[0]:
            if anchor_record is None:
                raise ValueError("Reference adapter anchor omitted")
            bc_anchor = read(directory / "reference" / meal["id"] / "feedback_full-tight.json")
            metrics["anchor_adapter_glucose_error_mg_dl"] = max(
                abs(a[3] - b[3]) / params["Vg"]
                for a, b in zip(anchor_record["states"], bc_anchor["states"], strict=True)
            )
        models[slot] = item_report

    control = {}
    for solver_name in ("tight", "reference"):
        path = Path("control") / f"anchor-{solver_name}.json"
        record, result = assess(
            path, SLOTS[0], 0.75, "host_constant_basal", meal, solvers[solver_name]
        )
        case_files.append(str(path))
        expected_attempts.append(
            attempt(
                SLOTS[0],
                0.75,
                "anchor_control",
                "host_constant_basal",
                meal["id"],
                solver_name,
                str(path),
            )
        )
        bc_control = read(
            directory / "reference" / meal["id"] / f"constant_basal-{solver_name}.json"
        )
        metrics["anchor_basal_control_glucose_error_mg_dl"] = max(
            metrics["anchor_basal_control_glucose_error_mg_dl"],
            max(
                abs(a[3] - b[3]) / params["Vg"]
                for a, b in zip(record["states"], bc_control["states"], strict=True)
            ),
        )
        control[solver_name] = result["outcomes"]

    changed = [
        name
        for name in case_files
        if (directory / "primary" / name).read_bytes() != (directory / "repeat" / name).read_bytes()
    ]
    metrics["repeat_error"] = float(bool(changed))
    required |= {f"{label}/{name}" for label in ("primary", "repeat") for name in case_files}
    verify_files(directory, manifest, required)
    for label in ("primary", "repeat"):
        worker = read(directory / label / "worker.json")
        if (
            worker.get("schema") != "m4-basal-equivalence-worker/1"
            or worker.get("implementation") != VERSION
            or worker.get("label") != label
            or worker.get("status") != "completed"
            or worker.get("native_identity") != native["identity"]
            or any(worker["runtime"][name] != bc["runtime"][name] for name in ("numpy", "scipy"))
            or worker.get("attempts") != expected_attempts
        ):
            raise ValueError("Worker attempt roster or runtime changed")
    passed = all(metrics[name] <= limit for name, limit in task["criteria"].items()) and all(
        item["solution"] is None
        or abs(item["solution"]["target_residual_mg_min_dl"])
        <= task["auc_match_tolerance_mg_min_dl"]
        for item in models.values()
    )
    report = {
        "schema": "m4-basal-equivalence-report/1",
        "implementation": VERSION,
        "reference_manifest_sha256": manifest["reference_manifest_sha256"],
        "target_auc_mg_min_dl": target,
        "native_basal_sc_rate_pmol_kg_min": params["u2ss"],
        "starting_sc_factor": 0.75,
        "models": models,
        "control_anchor": control,
        "metrics": metrics,
        "repeat_changed": changed,
        "all_solved": all(item["solution"] is not None for item in models.values()),
        "passed": passed,
        "claim": task["claim"],
        "limitations": task["excluded"],
    }
    if not allow_pending and read(directory / "report.json") != report:
        raise ValueError("Saved report differs from source-free reconstruction")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    result = reconstruct(args.directory)
    dump(args.output, result)
    if not result["passed"]:
        raise SystemExit("Basal-equivalence numerical checks failed")


if __name__ == "__main__":
    main()
