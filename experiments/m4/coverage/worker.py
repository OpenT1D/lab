"""Run fresh BC-014 observations and targeted gain profiles in the native lock."""

import platform
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import scipy

from experiments.m4.profile_likelihood import verify as profile_verify
from experiments.m4.profile_likelihood.common import best, profile_starts
from experiments.m4.profile_likelihood.optimizer import Problem, solve
from experiments.m4.volume_sensitivity import verify as volume_verify
from experiments.m4.volume_sensitivity.model import Model
from experiments.m4.volume_sensitivity.worker import plain

from .common import adapted_profile, dump, observation_specs, read, specifications, validate


def generate(model, protocol, spec):
    """One new independent noise draw, shared across its observation designs."""
    truth = protocol["design"][spec["group"]]["truth"]
    output = model.simulate(truth, solver="reference")
    reference = np.asarray(output["observations"])
    if reference.shape != (241, 3) or not np.array_equal(output["times"], np.arange(241)):
        raise RuntimeError("Incomplete generating trajectory")
    sd = np.asarray(model.protocol["observation"]["synthetic_sd"])
    noise = np.random.default_rng(spec["seed"]).normal(size=(241, 3)) * sd
    noise[0, :2] = 0
    return plain(
        {
            **spec,
            "status": "completed",
            "truth": truth,
            "times": list(range(241)),
            "reference": reference,
            "error": noise,
            "observed": reference + noise,
            "sd": sd,
            "generator": "unchanged BC-012 reference solver; independent seeded Gaussian errors",
        }
    )


def fit_one(arguments):
    source, directory, protocol, parent, spec = arguments
    source, directory = Path(source), Path(directory)
    path = directory / "cases" / (spec["id"] + ".json")
    record = {
        **spec,
        "status": "started",
        "truth": protocol["design"][spec["group"]]["truth"],
        "baseline": [],
        "constrained": [],
        "reference": None,
        "covered": False,
    }
    dump(path, record)

    def save():
        dump(path, plain(record))

    try:
        data = read(directory / "observations" / (f"{spec['group']}-{spec['seed']}.json"))
        model = Model(read(source / "parent-volume.json"))
        adapted = adapted_profile(parent)
        observations = {"times": data["times"], "datasets": {"assessment": data["observed"]}}
        design = adapted["designs"][spec["design"]]
        problem = Problem(model, observations, design, adapted, data="assessment")
        for start in adapted["inference"]["unrestricted_starts"]:
            record["baseline"].append(solve(problem, start))
            record["status"] = "partial"
            save()
        baseline = best(record["baseline"])
        target = (protocol["design"]["interest_parameter"], record["truth"][0])
        for start in profile_starts(adapted, spec, baseline, target[0]):
            record["constrained"].append(solve(problem, start, target))
            save()
        constrained = best(record["constrained"])
        delta = constrained["objective"] - baseline["objective"]
        cutoff = protocol["analysis"]["cutoff"]
        reference_problem = Problem(
            model, observations, design, adapted, solver="reference", data="assessment"
        )
        reference = {
            "baseline_at_fit": reference_problem.evaluate(baseline["evaluated_parameters"]),
            "constrained_at_fit": reference_problem.evaluate(constrained["evaluated_parameters"]),
            "refit": None,
        }
        reference_delta = (
            reference["constrained_at_fit"]["objective"] - reference["baseline_at_fit"]["objective"]
        )
        need_refit = abs(delta - cutoff) <= protocol["analysis"]["reference_refit_margin"] or (
            delta <= cutoff
        ) != (reference_delta <= cutoff)
        if need_refit:
            base_refits = [
                solve(reference_problem, start)
                for start in adapted["inference"]["unrestricted_starts"]
            ]
            best_reference = best(base_refits)
            fixed_refits = [
                solve(reference_problem, start, target)
                for start in profile_starts(adapted, spec, best_reference, target[0])
            ]
            reference["refit"] = {"baseline": base_refits, "constrained": fixed_refits}
        record["reference"] = reference
        record["delta_q"] = delta
        record["covered"] = delta <= cutoff
        refit_agrees = True
        if need_refit:
            refit = reference["refit"]
            ref_base, ref_fixed = best(refit["baseline"]), best(refit["constrained"])
            refit_delta = ref_fixed["objective"] - ref_base["objective"]
            refit_agrees = (
                all(r["status"] == "completed" for r in (*refit["baseline"], *refit["constrained"]))
                and abs(ref_base["objective"] - baseline["objective"])
                <= protocol["analysis"]["reference_objective_tolerance"]
                and abs(ref_fixed["objective"] - constrained["objective"])
                <= protocol["analysis"]["reference_objective_tolerance"]
                and abs(refit_delta - delta)
                <= protocol["analysis"]["reference_objective_tolerance"]
                and (refit_delta <= cutoff) == record["covered"]
            )
        tolerance = protocol["analysis"]["reference_objective_tolerance"]
        record["gates"] = {
            "all_starts_completed": all(
                r["status"] == "completed" for r in (*record["baseline"], *record["constrained"])
            ),
            "constrained_not_below_baseline": delta
            >= -protocol["analysis"]["lower_delta_tolerance"],
            "reference_objectives": all(
                abs(reference[key]["objective"] - fit["objective"]) <= tolerance
                for key, fit in (
                    ("baseline_at_fit", baseline),
                    ("constrained_at_fit", constrained),
                )
            )
            and abs(reference_delta - delta) <= tolerance,
            "reference_inclusion": (reference_delta <= cutoff) == record["covered"],
            "reference_refit": refit_agrees,
        }
        record["status"] = "completed" if all(record["gates"].values()) else "failed"
        if record["status"] != "completed":
            record["covered"] = False
        save()
    except BaseException as exc:
        record.update(
            status="failed",
            covered=False,
            error={"type": type(exc).__name__, "message": str(exc)},
        )
        save()
    return spec["id"]


def run(source, directory):
    source, directory = Path(source), Path(directory)
    if source != directory:
        directory.mkdir(exist_ok=False)
    (directory / "observations").mkdir(exist_ok=False)
    (directory / "cases").mkdir(exist_ok=False)
    protocol, parent = read(source / "protocol.json"), read(source / "parent-profile.json")
    validate(protocol)
    adapted_profile(parent)
    runtime = {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
    }
    if not runtime["python"].startswith("3.12.") or any(
        runtime[key] != protocol["runtime"][key] for key in ("numpy", "scipy")
    ):
        raise RuntimeError("Wrong locked numerical runtime")
    model = Model(read(source / "parent-volume.json"))
    dump(directory / "worker.json", plain({"runtime": runtime, "native": model.identity}))
    verification = {
        "parent": volume_verify.run(model),
        "profile_oracles": profile_verify.run(parent),
    }
    dump(directory / "verification.json", plain(verification))
    if not all(part["passed"] for part in verification.values()):
        raise RuntimeError("Inherited numerical gate failed before assessment")
    for spec in observation_specs(protocol):
        dump(directory / "observations" / (spec["id"] + ".json"), generate(model, protocol, spec))
    print(f"Numerical gates passed; starting {len(specifications(protocol))} analyses", flush=True)
    with ProcessPoolExecutor(max_workers=protocol["execution"]["workers"]) as pool:
        futures = [
            pool.submit(fit_one, (str(source), str(directory), protocol, parent, spec))
            for spec in specifications(protocol)
        ]
        for future in as_completed(futures):
            print(future.result(), flush=True)


if __name__ == "__main__":
    import sys

    run(Path(sys.argv[1]), Path(sys.argv[2]))
