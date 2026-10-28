"""Replay one fixed M1 native trajectory in each locked M0/M1 and C1 environment."""

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from experiments.m1.contracts import MEALS, Action

from .g2p2c_training_preflight import (
    M1_HASHES,
    M1_REV,
    _check_equations,
    _check_hashes,
    _check_lock,
)
from .g2p2c_training_run import ROOT

PROFILE = "adult#001"
SEED = 101
BASAL_U_MIN = 0.02
END_MIN = 600


def run():
    import simglucose

    from experiments.m1.adapter import Simglucose

    if [(minute, grams) for minute, grams in MEALS if minute <= END_MIN] != [(420, 45)]:
        raise ValueError("M1 meal scenario changed inside the fixed trajectory window")
    m0 = ROOT / "experiments/m0/simglucose"
    c1 = ROOT / "experiments/c1/g2p2c_training_source"
    if Path(sys.prefix).resolve() not in ((m0 / ".venv").resolve(), (c1 / ".venv").resolve()):
        raise ValueError("Expected one of the two locked M1-engine environments")
    package = Path(simglucose.__file__).resolve().parent
    if not package.is_relative_to(Path(sys.prefix).resolve()):
        raise ValueError("Simglucose was imported outside the locked environment")
    _check_lock(c1, ROOT)
    _check_hashes(package, M1_HASHES)
    _check_equations(package, m1=True)

    engine = Simglucose(PROFILE, SEED)
    snapshots = [asdict(engine.reset())]
    action = Action(BASAL_U_MIN, 0.0)
    for minute in range(3, END_MIN + 1, 3):
        snapshot = engine.step(action)
        if snapshot.time_min != minute or snapshot.terminal:
            raise ValueError(f"Fixed native trajectory stopped before minute {END_MIN}")
        snapshots.append(asdict(snapshot))
    if not any(snapshot["true_meal_g"] > 0 for snapshot in snapshots):
        raise ValueError("Fixed native trajectory did not exercise a meal")
    return {
        "schema": "opent1d.c1.g2p2c-engine-trajectory-parity/1",
        "m1_simglucose_commit": M1_REV,
        "profile": PROFILE,
        "seed": SEED,
        "basal_u_min": BASAL_U_MIN,
        "bolus_u_min": 0.0,
        "end_min": END_MIN,
        "snapshots": snapshots,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"Trajectory output already exists: {args.output}")
    report = run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(f"{args.output}: {len(report['snapshots'])} native snapshots")


if __name__ == "__main__":
    main()
