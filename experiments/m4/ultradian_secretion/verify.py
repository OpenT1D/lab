"""High-precision published-amount equation oracle, without a simulator."""

import argparse
from decimal import Decimal, localcontext
from pathlib import Path

from experiments.m4.causal_secretion.common import declaration, load_model, preflight, sha256
from experiments.m4.paired_kinetics.common import dump, read

HERE = Path(__file__).resolve().parent


def published_rate(glucose_mg_dl):
    """Independent direct f1 in mU/min using original whole-space glucose units.

    Nominal Vg=10 L, Rm=209 mU/min, C1=300 mg/L, a1=6.6 (Table I).
    The amount-space formula includes Vg, which cancels after concentration
    conversion. This oracle deliberately does not import the model function.
    """
    with localcontext() as ctx:
        ctx.prec = 60
        volume = Decimal(10)
        amount_mg = Decimal(str(glucose_mg_dl)) * Decimal(10) * volume
        return Decimal(209) / (1 + (-amount_mg / (volume * Decimal(300)) + Decimal("6.6")).exp())


def verify():
    declared = declaration(read(HERE / "model.json"))
    if declared["source_sha256"] != sha256(HERE / "model.py"):
        raise ValueError("Source differs from the declared model hash")
    if declared["parameters"] != {"a1": 6.6, "C1_mg_l": 300.0}:
        raise ValueError("Published nominal shape changed; specify a separate verification")
    model = load_model(HERE / "model.py")
    task = read(HERE.parent / "causal_secretion/protocol.json")
    basal, threshold = 0.8, 138.56  # Explicitly invented molar amplitude fixture.
    checks = preflight(model, basal, threshold, declared["parameters"], task)
    points = []
    for glucose in (0, 30, 100, threshold, 198, 300, 600, 10000):
        with localcontext() as ctx:
            ctx.prec = 60
            expected = float(
                Decimal(str(basal)) * published_rate(glucose) / published_rate(threshold)
            )
        dz, rate = model(0, glucose, 0, basal, basal, threshold, declared["parameters"])
        points.append(
            {
                "glucose_mg_dl": glucose,
                "original_f1_mU_min": float(published_rate(glucose)),
                "expected_normalized_pmol_kg_min": expected,
                "actual_pmol_kg_min": rate,
                "error_pmol_kg_min": abs(expected - rate),
                "state_derivative_pmol_kg_min2": dz,
            }
        )
    error = max(point["error_pmol_kg_min"] for point in points)
    return {
        "schema": "m4-ultradian-equation-verification/1",
        "model_id": declared["model_id"],
        "source_sha256": declared["source_sha256"],
        "declaration_sha256": sha256(HERE / "model.json"),
        "source_register_sha256": sha256(HERE / "sources.json"),
        "fixture": {"basal_pmol_kg_min": basal, "threshold_mg_dl": threshold},
        "oracle": "60-digit Decimal direct published amount-space f1 with Table I values",
        "points": points,
        "callback_preflight": checks,
        "max_rate_error_pmol_kg_min": error,
        "limit_pmol_kg_min": 1e-12,
        "passed": error <= 1e-12
        and all(point["state_derivative_pmol_kg_min2"] == 0 for point in points),
        "scope": "equation and synthetic normalization verification, not human validity",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Verification output already exists")
    result = verify()
    dump(args.output, result)
    if not result["passed"]:
        raise RuntimeError("Equation verification failed")
    print("Ultradian f1 equation verification passed")


if __name__ == "__main__":
    main()
