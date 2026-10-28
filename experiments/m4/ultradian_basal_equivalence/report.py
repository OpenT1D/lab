"""Reconstruct glucose-shape diagnostics from two verified synthetic archives."""

import argparse
import hashlib
import json
from pathlib import Path

from experiments.m4.basal_equivalence.common import context
from experiments.m4.basal_equivalence.report import reconstruct as reconstruct_search
from experiments.m4.causal_secretion.common import sha256
from experiments.m4.causal_secretion.report import reconstruct as reconstruct_causal
from experiments.m4.feedback.report import outcomes
from experiments.m4.paired_kinetics.common import dump, read

HERE = Path(__file__).resolve().parent
PLAN_SHA256 = "2b202a0c0a5513b40a899d164e734ce180056e22e9d0e3c6c35d7e6b399838c9"


def plan(value):
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    if hashlib.sha256(encoded).hexdigest() != PLAN_SHA256:
        raise ValueError("Ultradian basal worked-example plan is frozen")
    return value


def bind(search, causal, specification):
    """Reject another source pair, protocol or reference before reconstruction."""
    checks = {
        search / "protocol.json": specification["search_protocol_file_sha256"],
        causal / "protocol.json": specification["causal_protocol_file_sha256"],
        search / "reference/protocol.json": specification["bc008_protocol_file_sha256"],
        causal / "reference/protocol.json": specification["bc008_protocol_file_sha256"],
    }
    for slot, source in specification["sources"].items():
        checks[search / f"{slot}.py"] = source["source_sha256"]
        checks[search / f"{slot}.json"] = source["declaration_sha256"]
        if read(search / f"{slot}.json")["model_id"] != source["model_id"]:
            raise ValueError("Worked-example source ID changed")
    variant = specification["sources"]["synthetic_variant"]
    checks[causal / "model.py"] = variant["source_sha256"]
    checks[causal / "model.json"] = variant["declaration_sha256"]
    if any(sha256(path) != expected for path, expected in checks.items()):
        raise ValueError("Worked-example source or protocol identity changed")
    if sha256(search / "reference/manifest.json") != sha256(causal / "reference/manifest.json"):
        raise ValueError("Worked-example archives require the same fresh BC-008 reference")


def reconstruct(search, causal):
    search, causal = Path(search), Path(causal)
    specification = plan(read(HERE / "plan.json"))
    bind(search, causal, specification)
    comparison = reconstruct_search(search)
    diagnostic = reconstruct_causal(causal)
    if not comparison["passed"] or not diagnostic["passed"]:
        raise ValueError("Parent numerical verification failed")
    _, native, _, _, _, _ = context(search / "reference", search / "protocol.json")
    vg = native["parameters"]["Vg"]
    models = {}
    for slot, result in comparison["models"].items():
        history = []
        for item in result["history"]:
            record = read(search / "primary" / slot / item["file"])
            history.append(
                {
                    "factor": item["factor"],
                    "phase": item["phase"],
                    **outcomes(record["times"], record["states"], vg),
                }
            )
        confirmed = []
        for index, item in enumerate(result.get("reference_grid_confirmation", [])):
            record = read(search / "primary" / slot / f"confirm-{index:02d}-reference.json")
            confirmed.append(
                {"factor": item["factor"], **outcomes(record["times"], record["states"], vg)}
            )
        matched_diagnostics = None
        if result["solution"] is not None:
            matched_diagnostics = {}
            for scenario, name in (("meal", "root-reference"), ("fasting", "fasting-reference")):
                record = read(search / "primary" / slot / f"{name}.json")
                matched_diagnostics[scenario] = outcomes(record["times"], record["states"], vg)
        models[slot] = {
            "model_id": result["model_id"],
            "status": result["status"],
            "solution": result["solution"],
            "tight_search_outcomes": history,
            "reference_confirmation_outcomes": confirmed,
            "matched_diagnostics": matched_diagnostics,
        }
    anchor_item = next(
        item
        for item in comparison["models"]["synthetic_variant"]["history"]
        if item["factor"] == 0.75
    )
    anchor = read(search / "primary/synthetic_variant" / anchor_item["file"])
    causal_anchor = read(causal / "primary/gastric_load_30g/candidate-tight.json")
    if (
        anchor["states"] != causal_anchor["states"]
        or anchor["source_rates"] != causal_anchor["source_rates"]
    ):
        raise ValueError("Shared 75% candidate anchor differs between workflows")
    return {
        "schema": "m4-ultradian-basal-report/1",
        "plan_id": specification["id"],
        "plan_file_sha256": sha256(HERE / "plan.json"),
        "report_source_sha256": sha256(HERE / "report.py"),
        "search_report_sha256": sha256(search / "report.json"),
        "causal_report_sha256": sha256(causal / "report.json"),
        "reference_manifest_sha256": comparison["reference_manifest_sha256"],
        "target_auc_mg_min_dl": comparison["target_auc_mg_min_dl"],
        "models": models,
        "ultradian_starting_factor_diagnostics": {
            "sc_factor": 0.75,
            "fasting": diagnostic["scenarios"]["fasting"]["candidate"]["outcomes"],
            "meal": diagnostic["scenarios"]["gastric_load_30g"]["candidate"]["outcomes"],
        },
        "verification": {
            "search_metrics": comparison["metrics"],
            "causal_metrics": diagnostic["metrics"],
            "shared_anchor_exact": True,
        },
        "passed": True,
        "all_solved": comparison["all_solved"],
        "scope": specification["scope"],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--search", type=Path, required=True)
    parser.add_argument("--causal", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    if any(
        folder.resolve() == args.output.resolve()
        or folder.resolve() in args.output.resolve().parents
        for folder in (args.search, args.causal)
    ):
        raise ValueError("Keep diagnostic output outside the verified parent archives")
    result = reconstruct(args.search, args.causal)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    dump(args.output, result)
    print(
        f"Ultradian basal diagnostics: passed={result['passed']}, all_solved={result['all_solved']}"
    )


if __name__ == "__main__":
    main()
