"""BC-004 dimensional boundary preflight. No ODE, patient data or parameter fitting."""

import math
from numbers import Real

from experiments.m4.kinetic_inlet.forcing import Forcing

VERSION = "bc004-paired-boundary/1"


def keys(value, expected, name):
    if not isinstance(value, dict) or set(value) != set(expected.split()):
        raise ValueError(f"Missing or unexpected {name} fields")


def number(value, name, *, positive=False):
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
        raise ValueError(f"{name} must be finite numeric")
    if (value <= 0) if positive else (value < 0):
        raise ValueError(f"Invalid {name} sign")
    return float(value)


def validate(p):
    keys(
        p,
        "schema id base_commit specified_before_execution status question evidence_kind "
        "body_weight_kg scale_interpretation time_unit insulin_molar_mass_g_mol "
        "cpeptide_per_insulin_molar_ratio appearance_assumption route insulin cpeptide cases "
        "acceptance source_locations excluded",
        "protocol",
    )
    required = {
        "schema": "bc004-boundary-protocol/1",
        "id": "BC-004/1",
        "status": "frozen_synthetic_contract_only",
        "evidence_kind": "synthetic_boundary_verification",
        "scale_interpretation": "declared_whole_body_synthetic",
        "time_unit": "min",
        "appearance_assumption": "equimolar_without_extra_delay_or_hepatic_cp_extraction",
        "route": "liver",
    }
    if any(p[k] != v for k, v in required.items()) or p["specified_before_execution"] is not True:
        raise ValueError("Unsupported scope, source interpretation, units or route")
    if number(p["cpeptide_per_insulin_molar_ratio"], "molar ratio", positive=True) != 1:
        raise ValueError("This version requires the explicit equimolar assumption")
    if number(p["insulin_molar_mass_g_mol"], "molar mass", positive=True) != 5808:
        raise ValueError("Unexpected insulin molar mass")
    weight = number(p["body_weight_kg"], "body mass", positive=True)
    keys(p["insulin"], "reference revision body_weight_kg m1 m2 m30 m4 volume_l_kg", "insulin")
    keys(p["cpeptide"], "reference k1 k2 k3 volume_l_kg", "C-peptide")
    for name, values in (("insulin", p["insulin"]), ("C-peptide", p["cpeptide"])):
        for key, value in values.items():
            if key not in {"reference", "revision"}:
                number(value, f"{name}.{key}", positive=True)
    if weight != p["insulin"]["body_weight_kg"]:
        raise ValueError("Body mass differs from the insulin profile; no implicit rescaling")
    if p["insulin"]["revision"] != "a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc":
        raise ValueError("Unsupported upstream insulin revision")
    keys(
        p["acceptance"],
        "paired_input_relative_error input_accounting_relative_error "
        "equilibrium_derivative_pmol_kg_min repeat_absolute_error expected_integrals_pmol_kg",
        "criteria",
    )
    for key, value in p["acceptance"].items():
        if key != "expected_integrals_pmol_kg":
            number(value, key)
    expected_ids = {
        "zero_increment",
        "pulse_increment",
        "pulse_synthetic_total",
        "mass_ramp_increment",
    }
    if len(p["cases"]) != 4 or {c["id"] for c in p["cases"]} != expected_ids:
        raise ValueError("Missing or duplicate boundary case")
    if set(p["acceptance"]["expected_integrals_pmol_kg"]) != expected_ids:
        raise ValueError("Missing independent expected input amounts")
    for value in p["acceptance"]["expected_integrals_pmol_kg"].values():
        number(value, "expected amount")
    for c in p["cases"]:
        keys(c, "id baseline_mode basal_pmol_min evoked_unit edges_min left right", "case")
        if c["evoked_unit"] not in {"pmol/min", "ug/min"}:
            raise ValueError("Evoked input must be whole-body pmol/min or ug/min")
        basal = number(c["basal_pmol_min"], "basal secretion")
        if c["baseline_mode"] == "incremental_zero":
            if basal != 0:
                raise ValueError("Incremental baseline must be zero")
        elif c["baseline_mode"] == "synthetic_equilibrium":
            if basal <= 0 or not c["left"] or c["left"][0] != 0:
                raise ValueError(
                    "Synthetic equilibrium needs positive basal and zero initial evoked input"
                )
        else:
            raise ValueError("Unknown baseline interpretation")
        # Validate finite nonnegative edges/rates and strictly ordered complete segments.
        Forcing(c["edges_min"], c["left"], c["right"])


def prepare_case(p, case):
    """Normalize once; preserve source components and distinct proposed initial states."""
    validate(p)
    if case not in p["cases"]:
        raise ValueError("Case must belong to the validated protocol")
    weight = p["body_weight_kg"]
    factor = 1 if case["evoked_unit"] == "pmol/min" else 1e6 / p["insulin_molar_mass_g_mol"]
    basal = case["basal_pmol_min"] / weight
    evoked = Forcing(
        case["edges_min"],
        [v * factor / weight for v in case["left"]],
        [v * factor / weight for v in case["right"]],
    )
    total = Forcing(
        evoked.edges, [v + basal for v in evoked.left], [v + basal for v in evoked.right]
    )
    i, cp = p["insulin"], p["cpeptide"]
    il = basal / (i["m30"] + i["m1"] * i["m4"] / (i["m2"] + i["m4"]))
    ip = i["m1"] * il / (i["m2"] + i["m4"])
    q1 = basal / cp["k3"]
    q2 = cp["k1"] * q1 / cp["k2"]
    output = {
        "id": case["id"],
        "baseline_mode": case["baseline_mode"],
        "source_unit": case["evoked_unit"],
        "body_weight_kg": weight,
        "basal_pmol_kg_min": basal,
        "evoked": evoked.to_dict(),
        "insulin": {
            "forcing": total.to_dict(),
            "route": "liver",
            "state_order": ["Ip", "Il", "hepatic_loss", "peripheral_loss", "input"],
            "initial": [ip, il, 0, 0, 0],
            "initial_concentration_pmol_l": ip / i["volume_l_kg"],
            "current_bc002_initial_state_supported": basal == 0,
        },
        "cpeptide": {
            "forcing": total.to_dict(),
            "route": "central",
            "state_order": ["central", "peripheral", "eliminated", "input"],
            "initial": [q1, q2, 0, 0],
            "initial_concentration_pmol_l": q1 / cp["volume_l_kg"],
        },
        "integrated_evoked_pmol_kg": evoked.integral(),
        "integrated_basal_pmol_kg": basal * total.horizon,
        "integrated_each_branch_pmol_kg": total.integral(),
        "claim": "input and initial-state request only; no paired solver execution",
    }
    if not all(
        math.isfinite(v) for v in [ip, il, q1, q2, output["integrated_each_branch_pmol_kg"]]
    ):
        raise ValueError("Nonfinite derived boundary state")
    return output


def evaluate(p):
    validate(p)
    bundles, checks = [], {}
    limits = p["acceptance"]
    for case in p["cases"]:
        bundle = prepare_case(p, case)
        bundles.append(bundle)
        insulin = Forcing(**bundle["insulin"]["forcing"])
        cp_force = Forcing(**bundle["cpeptide"]["forcing"])
        pair_error = max(
            abs(a - b) / max(abs(a), 1)
            for a, b in zip(
                (*insulin.left, *insulin.right), (*cp_force.left, *cp_force.right), strict=True
            )
        )
        expected = limits["expected_integrals_pmol_kg"][case["id"]]
        actual = bundle["integrated_each_branch_pmol_kg"]
        amount_error = max(
            abs(actual - expected),
            abs(actual - bundle["integrated_evoked_pmol_kg"] - bundle["integrated_basal_pmol_kg"]),
        ) / max(expected, 1)
        ip, il = bundle["insulin"]["initial"][:2]
        q1, q2 = bundle["cpeptide"]["initial"][:2]
        i, cp, basal = p["insulin"], p["cpeptide"], bundle["basal_pmol_kg_min"]
        residual = max(
            abs(v)
            for v in (
                -(i["m2"] + i["m4"]) * ip + i["m1"] * il,
                i["m2"] * ip - (i["m1"] + i["m30"]) * il + basal,
                -(cp["k1"] + cp["k3"]) * q1 + cp["k2"] * q2 + basal,
                cp["k1"] * q1 - cp["k2"] * q2,
            )
        )
        repeat_error = 0 if prepare_case(p, case) == bundle else 1
        values = {
            "paired_input_relative_error": pair_error,
            "input_accounting_relative_error": amount_error,
            "equilibrium_derivative_pmol_kg_min": residual,
            "repeat_absolute_error": repeat_error,
        }
        checks[case["id"]] = {
            "values": values,
            "passed": all(v <= limits[k] for k, v in values.items()),
        }
    return {
        "schema": "bc004-preflight/1",
        "protocol": p["id"],
        "implementation": VERSION,
        "passed": all(c["passed"] for c in checks.values()),
        "checks": checks,
        "bundles": bundles,
        "empirical_freeze": "pending_authorized_data_and_domain_review",
        "coupled_trajectory_executed": False,
    }
