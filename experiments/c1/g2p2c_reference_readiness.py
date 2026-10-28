"""Audit both frozen G2P2C native smokes and their fresh-process repeats."""

import argparse
import hashlib
import json
from pathlib import Path

from .g2p2c_native_smoke import PLAN, validated_plan, verify_saved
from .g2p2c_training_run import _sha

PROFILES = ("adult#001", "adult#002")


def _digest(report):
    canonical = json.dumps(report, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def audit(source):
    plan = validated_plan()
    if tuple(case["profile"] for case in plan["cases"]) != PROFILES:
        raise ValueError("Native smoke profile roster changed")
    profiles = []
    for profile in PROFILES:
        attempts = []
        reports = []
        for repeated in (False, True):
            try:
                report = verify_saved(source, profile, repeat=repeated)
                if (
                    not isinstance(report, dict)
                    or type(report.get("integration_gate_pass")) is not bool
                ):
                    raise ValueError("Native smoke verifier returned an invalid report")
                report_digest = _digest(report)
            except Exception as error:
                attempts.append(
                    {
                        "repeat": repeated,
                        "status": "unverifiable",
                        "error_type": type(error).__name__,
                        "integration_gate_pass": False,
                        "report_digest": None,
                    }
                )
                reports.append(None)
            else:
                attempts.append(
                    {
                        "repeat": repeated,
                        "status": "verified",
                        "error_type": None,
                        "integration_gate_pass": report["integration_gate_pass"],
                        "report_digest": report_digest,
                    }
                )
                reports.append(report)
        identical = reports[0] is not None and reports[0] == reports[1]
        profiles.append(
            {
                "profile": profile,
                "attempts": attempts,
                "fresh_process_repeat_identical": identical,
                "technical_gate_pass": identical
                and all(attempt["integration_gate_pass"] for attempt in attempts),
            }
        )
    return {
        "schema": "opent1d.c1.g2p2c-reference-readiness/1",
        "native_smoke_plan_sha256": _sha(PLAN),
        "profiles": profiles,
        "technical_m1_boundary_pass": all(item["technical_gate_pass"] for item in profiles),
        "matched_development_comparison_run": False,
        "eligible_m1_comparator": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"Readiness report already exists: {args.output}")
    report = audit(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
