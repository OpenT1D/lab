"""Reconstruct comparisons from archived values without executing researcher code."""

import argparse
from pathlib import Path

from experiments.m4.kinetic_inlet.forcing import Forcing
from experiments.m4.paired_kinetics.common import verify_files
from experiments.m4.paired_kinetics.report import matrix, maxdiff, state_checks

from .common import (
    CASES,
    REUSED,
    SOURCES,
    VERSION,
    candidate_request,
    declaration,
    read,
    reference,
    samples,
    sha256,
)


def reconstruct(directory, *, allow_pending=False):
    directory = Path(directory)
    manifest = read(directory / "manifest.json")
    if (
        manifest.get("schema") != "m4-external-run/1"
        or manifest.get("implementation") != VERSION
        or manifest.get("status")
        not in ({"calculated", "completed"} if allow_pending else {"completed"})
    ):
        raise ValueError("External secretion run is not complete")
    required = {
        "model.py",
        "model.json",
        "model-input.json",
        "model-samples.json",
        "model.log",
        *(f"source-{name}" for name in SOURCES),
        *("source-" + name.replace("/", "__") for name in REUSED),
        *(
            f"{branch}-{name}"
            for branch in ("insulin", "cpeptide")
            for name in ("uv.lock", "pyproject.toml")
        ),
        *(
            f"{branch}/{name}.json"
            for branch in ("insulin", "cpeptide")
            for name in (*CASES, "worker")
        ),
        *(f"{branch}.log" for branch in ("insulin", "cpeptide")),
        "reference/manifest.json",
    }
    if not allow_pending:
        required.add("report.json")
    verify_files(directory, manifest, required)
    declared = declaration(read(directory / "model.json"))
    if (
        sha256(directory / "model.py") != declared["source_sha256"]
        or manifest["model_source_sha256"] != declared["source_sha256"]
    ):
        raise ValueError("Researcher source differs from declared hash")
    protocol, source, base, reference_report = reference(directory / "reference")
    sampled = read(directory / "model-samples.json")
    evoked = samples(sampled, source["times_min"], source["glucose_mmol_l"])
    if read(directory / "model-input.json") != {
        "times_min": source["times_min"],
        "glucose_mmol_l": source["glucose_mmol_l"],
    }:
        raise ValueError("Model input was not the prescribed source glucose")
    if evoked.integral() < 0:
        raise ValueError("Negative integrated secretion")
    branches = {}
    for branch in ("insulin", "cpeptide"):
        meta = read(directory / branch / "worker.json")
        volume = base[branch]["volume_l_kg"]
        if (
            meta.get("schema") != "m4-external-worker/1"
            or meta.get("status") != "completed"
            or meta.get("branch") != branch
            or meta.get("implementation") != VERSION
            or meta.get("volume_l_kg") != volume
            or any(meta["runtime"][k] != protocol["runtime"][branch][k] for k in ("numpy", "scipy"))
        ):
            raise ValueError("Wrong kinetic worker identity or runtime")
        expected_order = (
            ["Ip", "Il", "hepatic_loss", "peripheral_loss", "input"]
            if branch == "insulin"
            else ["central", "peripheral", "eliminated", "input"]
        )
        if meta.get("state_order") != expected_order:
            raise ValueError("Wrong kinetic state interpretation")
        if (
            branch == "insulin"
            and meta.get("native_identity")
            != read(directory / "reference" / "insulin" / "worker.json")["native_identity"]
        ):
            raise ValueError("Native insulin source identity changed")
        cases = {}
        for case_id in CASES:
            request = candidate_request(directory, case_id, context=(protocol, source, base))
            item = read(directory / branch / f"{case_id}.json")
            if (
                item.get("schema") != "m4-external-case/1"
                or item.get("branch") != branch
                or item.get("case_id") != case_id
                or item.get("request") != request
                or item.get("times_min") != source["times_min"]
                or item.get("volume_l_kg") != volume
            ):
                raise ValueError("Candidate kinetic case differs from input or grid")
            if set(item["states"]) != {"tight", "reference"}:
                raise ValueError("Missing kinetic solver comparison")
            count = 5 if branch == "insulin" else 4
            states = {
                name: matrix(value, len(source["times_min"]), count)
                for name, value in item["states"].items()
            }
            oracle = matrix(item["oracle"], len(source["times_min"]), count)
            initial = request["initial"][branch]
            forcing = Forcing(**request["forcing"])
            metrics = {
                "oracle_state_error_pmol_kg": maxdiff(states["reference"], oracle),
                "solver_concentration_error_pmol_l": max(
                    abs(a[0] - b[0]) / volume
                    for a, b in zip(states["tight"], states["reference"], strict=True)
                ),
            }
            for values in (*states.values(), oracle):
                if values[0] != initial:
                    raise ValueError("Kinetic initial state changed")
                for key, value in state_checks(
                    values, source["times_min"], forcing, initial
                ).items():
                    metrics[key] = max(metrics.get(key, 0), value)
            ref_item = read(directory / "reference" / branch / f"{case_id}.json")
            ref_states = matrix(ref_item["states"]["reference"], len(source["times_min"]), count)
            candidate = states["reference"]
            contrast = [
                a[0] / volume - b[0] / volume for a, b in zip(candidate, ref_states, strict=True)
            ]
            cases[case_id] = {
                "metrics": metrics,
                "passed": all(value <= protocol["criteria"][key] for key, value in metrics.items()),
                "input_amount_candidate_pmol_kg": forcing.integral(),
                "input_amount_reference_pmol_kg": Forcing(
                    **ref_item["request"]["forcing"]
                ).integral(),
                "candidate_peak_pmol_l": max(row[0] / volume for row in candidate),
                "reference_peak_pmol_l": max(row[0] / volume for row in ref_states),
                "maximum_absolute_concentration_difference_pmol_l": max(map(abs, contrast)),
                "final_concentration_difference_pmol_l": contrast[-1],
            }
        branches[branch] = cases
    for case_id in CASES:
        if (
            read(directory / "insulin" / f"{case_id}.json")["request"]["forcing"]
            != read(directory / "cpeptide" / f"{case_id}.json")["request"]["forcing"]
        ):
            raise ValueError("Insulin and C-peptide branches received different input")
    result = {
        "schema": "m4-external-report/1",
        "implementation": VERSION,
        "model_id": declared["model_id"],
        "model_source_sha256": declared["source_sha256"],
        "reference_manifest_sha256": sha256(directory / "reference" / "manifest.json"),
        "reference_protocol": reference_report["protocol"],
        "evoked_amount_candidate_pmol_kg": evoked.integral(),
        "branches": branches,
        "passed": all(case["passed"] for cases in branches.values() for case in cases.values()),
        "claim": (
            "synthetic prescribed glucose comparison of supplied secretion "
            "and unchanged BC-007 reference"
        ),
        "limitations": [
            "No glucose feedback",
            "No human or T1D validity",
            "No therapeutic interpretation",
            "Researcher source and dependencies are trusted local code",
        ],
    }
    if not allow_pending and read(directory / "report.json") != result:
        raise ValueError("Saved report differs from artifact reconstruction")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    result = reconstruct(args.directory)
    from experiments.m4.paired_kinetics.common import dump

    dump(args.output, result)
    if not result["passed"]:
        raise SystemExit("Candidate kinetic verification failed")


if __name__ == "__main__":
    main()
