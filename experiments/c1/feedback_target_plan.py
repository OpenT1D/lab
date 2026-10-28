"""Materialize the declared C1 target-alignment follow-up before native work.

This module creates a plan only. It never opens a simulator or scores cases.
"""

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from experiments.m1.artifacts import digest, strict_json
from experiments.m1.contracts import Config as M1Config

from .feedback import FeedbackSettings, without_rise
from .feedback_study import METHODS
from .simglucose_dev import Config as C1Config

ROOT = Path(__file__).resolve().parents[2]
DECLARATION = ROOT / "experiments/c1/feedback-target-alignment.json"
PRIOR = ROOT / "experiments/c1/feedback-development.json"
SCHEMA = "opent1d.c1-feedback-target-plan/1"


def plan():
    value = strict_json(DECLARATION.read_bytes())
    prior = strict_json(PRIOR.read_bytes())
    evidence = strict_json((ROOT / "experiments/c1/evidence-index.json").read_bytes())[
        "feedback_matrix"
    ]
    expected = {
        "schema",
        "source_report_sha256",
        "new_setting_attempts_per_feedback_method",
        "cumulative_setting_attempts_per_feedback_method",
        "profiles",
        "seeds",
        "conditions",
        "candidate_settings",
    }
    if (
        set(value) != expected
        or value["schema"] != "opent1d.c1-feedback-target-alignment/1"
        or value["source_report_sha256"]
        != "a2fc313c38ad17012856c7b4e26ad5cb96f6c057606855b7be24c575f4b99fd6"
        or value["source_report_sha256"] != evidence["report_sha256"]
        or digest(PRIOR) != evidence["settings_sha256"]
        or type(value["new_setting_attempts_per_feedback_method"]) is not int
        or value["new_setting_attempts_per_feedback_method"] != 1
        or type(value["cumulative_setting_attempts_per_feedback_method"]) is not int
        or value["cumulative_setting_attempts_per_feedback_method"] != 2
        or value["profiles"] != ["adult#001", "adult#002"]
        or value["seeds"] != [101, 102]
        or value["conditions"] != list("ABCD")
        or set(value["candidate_settings"]) != set(FeedbackSettings.__dataclass_fields__)
    ):
        raise ValueError("Unsupported target-alignment declaration")
    prior_settings = prior["candidate_settings"]
    changed = {
        name for name in prior_settings if prior_settings[name] != value["candidate_settings"][name]
    }
    if changed != {"target_mg_dl"} or (
        prior_settings["target_mg_dl"],
        value["candidate_settings"]["target_mg_dl"],
    ) != (160, 140):
        raise ValueError("Target alignment must change only 160 to 140 mg/dL")
    candidate = FeedbackSettings(**value["candidate_settings"])
    comparator = without_rise(candidate)
    cases = []
    for profile in value["profiles"]:
        for seed in value["seeds"]:
            for condition in value["conditions"]:
                for method in METHODS:
                    if method == "basal_bolus":
                        config = M1Config(profile, seed, method, condition).to_dict()
                    else:
                        config = {
                            "profile": profile,
                            "seed": seed,
                            "condition": condition,
                            "method": method,
                            "settings": asdict(
                                candidate if method == "feedback_trend" else comparator
                            ),
                        }
                        C1Config.parse(config)
                    cases.append(
                        {
                            "id": f"{profile}-{seed}-{condition}-{method}",
                            "method": method,
                            "config": config,
                        }
                    )
    return {
        "schema": SCHEMA,
        "purpose": "One-factor target alignment on previously inspected synthetic cells",
        "source_report_sha256": value["source_report_sha256"],
        "declaration_sha256": digest(DECLARATION),
        "new_setting_attempts_per_feedback_method": 1,
        "cumulative_setting_attempts_per_feedback_method": 2,
        "cases": cases,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(plan(), sort_keys=True, indent=2) + "\n")


if __name__ == "__main__":
    main()
