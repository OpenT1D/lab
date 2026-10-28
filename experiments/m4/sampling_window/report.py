"""Reconstruct BC-015-P4 summaries without importing the numerical model."""

import argparse
import hashlib
import json
import math
import statistics
from pathlib import Path

RAW = ("protocol.json", "checks.json", "sensitivities.json", "observations.json", "cases.json")
SOURCES = (
    "source-analysis.py",
    "source-report.py",
    "source-run.py",
    "source-plot.py",
    "source-test_numerical.py",
    "source-cpeptide-model.py",
    "source-cpeptide-reference.py",
    "source-forcing.py",
    "runtime-uv.lock",
    "runtime-pyproject.toml",
)
PROTOCOL_SHA256 = "cf91630b4d0717d58a90257dbb5e097076b2e793c698b643bb255066d0c0c727"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def read_json(path):
    return json.loads(Path(path).read_text())


def percentile(values, fraction):
    ordered = sorted(values)
    point = (len(ordered) - 1) * fraction
    low = int(point)
    return ordered[low] + (ordered[min(low + 1, len(ordered) - 1)] - ordered[low]) * (point - low)


def check_information(matrix, saved, cutoff):
    if not matrix or any(len(row) != 2 or not all(math.isfinite(x) for x in row) for row in matrix):
        raise ValueError("Incomplete sensitivity matrix")
    aa = sum(row[0] ** 2 for row in matrix)
    ab = sum(row[0] * row[1] for row in matrix)
    bb = sum(row[1] ** 2 for row in matrix)
    high = (aa + bb + math.hypot(aa - bb, 2 * ab)) / 2
    low = max(0, (aa * bb - ab * ab) / high)
    singular = [math.sqrt(high), math.sqrt(low)]
    if any(
        abs(a - b) > 1e-7 * max(1, a)
        for a, b in zip(singular, saved["singular_values"], strict=True)
    ):
        raise ValueError("Saved singular values disagree with sensitivity matrix")
    rank = sum(value > singular[0] * cutoff for value in singular)
    if rank != saved["rank"] or abs(saved["condition_number"] - singular[0] / singular[-1]) > 1e-6:
        raise ValueError("Saved rank or condition number disagrees")
    return {
        "singular_values": singular,
        "rank": rank,
        "condition_number": singular[0] / singular[-1],
    }


def summarize(protocol, checks, sensitivities, observations, cases):
    if protocol.get("schema") != "bc015-sampling-window-protocol/1":
        raise ValueError("Unexpected sampling protocol")
    obs = protocol["observation"]
    model = protocol["model"]
    shift = obs["injection_clock_shift_min"]
    early = [value + shift for value in obs["protocol_early_clock_min"]]
    full = early + [value + shift for value in obs["hypothetical_late_clock_min"]]
    if observations.get("times_min_after_injection") != full:
        raise ValueError("Archived sampling grid differs from the protocol")
    truth = observations.get("reference_pmol_l", [])
    if len(truth) != len(full) or not all(math.isfinite(x) and x >= 0 for x in truth):
        raise ValueError("Incomplete reference C-peptide series")
    expected_draws = {"noiseless"} | {
        str(seed)
        for seed in range(
            obs["noise_seed_first"], obs["noise_seed_first"] + obs["noise_seed_count"]
        )
    }
    if set(observations.get("draws", {})) != expected_draws:
        raise ValueError("Missing or extra synthetic observation draw")
    for key, draw in observations["draws"].items():
        noise, values = draw.get("noise_pmol_l", []), draw.get("observed_pmol_l", [])
        if (
            len(noise) != len(full)
            or len(values) != len(full)
            or not all(math.isfinite(x) for x in noise + values)
        ):
            raise ValueError("Incomplete synthetic observation series")
        if key == "noiseless" and any(x != 0 for x in noise):
            raise ValueError("Noiseless draw has nonzero error")
        if any(abs(a + b - c) > 1e-9 for a, b, c in zip(truth, noise, values, strict=True)):
            raise ValueError("Synthetic observations do not match reference plus error")
    if set(checks) != {"truth", "low_gain_high_k3", "high_gain_low_k3"}:
        raise ValueError("Missing independent numerical comparison")
    for value in checks.values():
        if (
            not math.isfinite(value["max_ode_analytical_error_pmol_l"])
            or value["max_ode_analytical_error_pmol_l"]
            > protocol["verification"]["ode_analytical_max_error_pmol_l"]
            or value["final_mass_balance_pmol_kg"] > 1e-7
        ):
            raise ValueError("Independent forward verification failed")
    designs = ("early", "early_plus_hypothetical_late")
    if set(sensitivities) != set(designs):
        raise ValueError("Missing local sensitivity design")
    information = {}
    for design, times in (("early", early), ("early_plus_hypothetical_late", full)):
        item = sensitivities[design]
        if (
            len(item.get("jacobian_scaled", [])) != len(times)
            or item["relative_refinement"]
            > protocol["verification"]["jacobian_refinement_relative_max"]
        ):
            raise ValueError("Incomplete or unstable sensitivity")
        information[design] = {
            **check_information(
                item["jacobian_scaled"], item, protocol["analysis"]["svd_relative_cutoff"]
            ),
            "relative_refinement": item["relative_refinement"],
        }
    expected_cases = {f"{key}-{design}" for key in expected_draws for design in designs}
    if set(cases) != expected_cases:
        raise ValueError("Missing or extra planned fit case")
    summaries = {}
    best_fits = {}
    for design, times in (("early", early), ("early_plus_hypothetical_late", full)):
        n = len(times)
        errors = [[], []]
        failed, bound_hits = 0, [0, 0]
        for key in sorted(expected_draws):
            case = cases[f"{key}-{design}"]
            if case.get("design") != design or case.get("seed") != (
                None if key == "noiseless" else int(key)
            ):
                raise ValueError("Fit case identity mismatch")
            starts = case.get("starts", [])
            if len(starts) != len(protocol["analysis"]["starts"]):
                raise ValueError("Incomplete multistart fit case")
            observed = observations["draws"][key]["observed_pmol_l"][:n]
            for candidate, expected_start in zip(
                starts, protocol["analysis"]["starts"], strict=True
            ):
                if candidate.get("start") != expected_start or candidate.get("status") not in (
                    "completed",
                    "failed",
                ):
                    raise ValueError("Fit start identity or status mismatch")
                if candidate["status"] == "completed":
                    theta, predicted = (
                        candidate.get("parameters", []),
                        candidate.get("predicted_pmol_l", []),
                    )
                    if (
                        len(theta) != 2
                        or len(predicted) != n
                        or not all(math.isfinite(x) for x in theta + predicted)
                    ):
                        raise ValueError("Incomplete fitted trajectory")
                    if any(
                        not lo - 1e-10 <= x <= hi + 1e-10
                        for x, lo, hi in zip(theta, model["lower"], model["upper"], strict=True)
                    ):
                        raise ValueError("Fitted parameter outside bounds")
                    objective = sum(
                        ((a - b) / obs["noise_sd_pmol_l"]) ** 2
                        for a, b in zip(predicted, observed, strict=True)
                    )
                    if abs(objective - candidate["objective"]) > 1e-8:
                        raise ValueError("Fitted objective disagrees with saved trajectory")
                    hits = [
                        abs(x - lo) < 1e-5 or abs(x - hi) < 1e-5
                        for x, lo, hi in zip(theta, model["lower"], model["upper"], strict=True)
                    ]
                    if hits != candidate["bound_hits"]:
                        raise ValueError("Fitted bound flags disagree")
            completed = [candidate for candidate in starts if candidate["status"] == "completed"]
            if not completed:
                failed += 1
                if key == "noiseless":
                    raise ValueError("Noiseless recovery failed")
                continue
            best = min(completed, key=lambda item: item["objective"])
            best_fits[(key, design)] = best
            if key == "noiseless":
                for item in completed:
                    if any(
                        abs(a / b - 1)
                        > protocol["verification"]["noiseless_relative_parameter_error_max"]
                        for a, b in zip(item["parameters"], model["truth"], strict=True)
                    ):
                        raise ValueError("Noiseless recovery exceeded declared criterion")
                continue
            for j, (estimate, actual) in enumerate(
                zip(best["parameters"], model["truth"], strict=True)
            ):
                errors[j].append(abs(estimate / actual - 1))
                bound_hits[j] += int(best["bound_hits"][j])
        summaries[design] = {
            "planned_noisy": obs["noise_seed_count"],
            "completed_noisy": obs["noise_seed_count"] - failed,
            "failed_noisy": failed,
            "best_bound_hits": bound_hits,
            "median_abs_relative_error": [
                statistics.median(column) if column else None for column in errors
            ],
            "p90_abs_relative_error": [
                percentile(column, 0.9) if column else None for column in errors
            ],
            "max_abs_relative_error": [max(column) if column else None for column in errors],
        }
    paired = [
        seed
        for seed in range(
            obs["noise_seed_first"], obs["noise_seed_first"] + obs["noise_seed_count"]
        )
        if (str(seed), "early") in best_fits
        and (str(seed), "early_plus_hypothetical_late") in best_fits
    ]
    late_better_k3 = sum(
        abs(
            best_fits[(str(seed), "early_plus_hypothetical_late")]["parameters"][1]
            - model["truth"][1]
        )
        < abs(best_fits[(str(seed), "early")]["parameters"][1] - model["truth"][1])
        for seed in paired
    )
    return {
        "schema": "bc015-sampling-window-report/1",
        "claim": "conditional_synthetic_sampling_window_only",
        "parameter_order": model["parameter_order"],
        "sampling_clock": "minutes after nominal glucose injection; C-peptide values synthetic",
        "sample_counts": {"early": len(early), "early_plus_hypothetical_late": len(full)},
        "information": information,
        "numerical_checks": checks,
        "noisy_results": summaries,
        "paired_completed_draws": len(paired),
        "extended_smaller_k3_error_count": late_better_k3,
        "human_validation": False,
    }


def reconstruct(output):
    output = Path(output)
    manifest = read_json(output / "manifest.json")
    if (
        manifest.get("schema") != "bc015-sampling-window-archive/1"
        or manifest.get("status") != "completed"
    ):
        raise ValueError("Sampling-window archive is incomplete")
    required = set(RAW + SOURCES + ("report.json", "figure.svg"))
    if set(manifest.get("files", {})) != required:
        raise ValueError("Sampling-window archive inventory differs")
    for name, expected in manifest["files"].items():
        if (output / name).is_symlink() or digest(output / name) != expected:
            raise ValueError(f"Changed or linked archived file: {name}")
    if manifest["files"]["protocol.json"] != PROTOCOL_SHA256:
        raise ValueError("Archived sampling protocol differs from BC-015-P4/1")
    protocol = read_json(output / "protocol.json")
    runtime = manifest.get("runtime", {})
    if not runtime.get("python", "").startswith(protocol["runtime"]["python"] + ".") or any(
        runtime.get(key) != protocol["runtime"][key] for key in ("numpy", "scipy")
    ):
        raise ValueError("Archived model runtime differs from protocol")
    return summarize(*(read_json(output / name) for name in RAW))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Choose a new report output")
    write_json(args.output, reconstruct(args.archive))
