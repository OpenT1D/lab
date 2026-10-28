"""Synthetic OT-027 visit-linkage rehearsal; no human-data intake or model fitting."""

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARCHIVE_FILES = {"intent.json", "packet.json", "report.json", "source-run.py"}
ALIAS = re.compile(r"SYN[0-9]{3}")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 100_000:
        raise ValueError("Input must be a regular JSON file of at most 100 kB")
    return json.loads(path.read_text())


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def exact(value, fields, label):
    if not isinstance(value, dict) or set(value) != set(fields):
        raise ValueError(f"{label} must have exactly: {', '.join(fields)}")


def day(value, label, *, minimum=0):
    if type(value) is not int or value < minimum or value > 10000:
        raise ValueError(f"{label} must be an integer day between {minimum} and 10000")


def alias(value):
    if not isinstance(value, str) or not ALIAS.fullmatch(value):
        raise ValueError("Only invented SYNnnn aliases are accepted")


def validate_intent(intent):
    exact(intent, ("schema", "data_kind", "clock", "source"), "Intent")
    if (
        intent["schema"] != "ot027-synthetic-intent/1"
        or intent["data_kind"] != "synthetic"
        or intent["clock"] != "days_since_first_infusion"
        or intent["source"] != "invented"
    ):
        raise ValueError("Only the invented, first-infusion-clock rehearsal is supported")


def validate_packet(packet):
    exact(packet, ("schema", "participants", "infusions", "mmtt", "insulin"), "Packet")
    if packet["schema"] != "ot027-synthetic-packet/1":
        raise ValueError("Wrong synthetic packet schema")
    if any(
        not isinstance(packet[name], list)
        for name in ("participants", "infusions", "mmtt", "insulin")
    ):
        raise ValueError("Packet tables must be lists")
    if len(packet["participants"]) > 100 or any(
        len(packet[name]) > 500 for name in ("infusions", "mmtt", "insulin")
    ):
        raise ValueError("Synthetic rehearsal exceeds its bounded table size")
    for person in packet["participants"]:
        exact(person, ("alias",), "Participant")
        alias(person["alias"])
    names = [person["alias"] for person in packet["participants"]]
    if len(names) != len(set(names)):
        raise ValueError("Duplicate roster alias")
    known = set(names)
    for infusion in packet["infusions"]:
        exact(infusion, ("alias", "day"), "Infusion")
        alias(infusion["alias"])
        day(infusion["day"], "Infusion day")
        if infusion["alias"] not in known:
            raise ValueError("Infusion references an alias outside the roster")
    for visit in packet["mmtt"]:
        exact(visit, ("alias", "visit_id", "day", "challenge", "samples"), "MMTT visit")
        alias(visit["alias"])
        day(visit["day"], "MMTT day")
        if visit["alias"] not in known:
            raise ValueError("MMTT references an alias outside the roster")
        if not isinstance(visit["visit_id"], str) or not re.fullmatch(
            r"V[0-9]{1,3}", visit["visit_id"]
        ):
            raise ValueError("MMTT visit_id must be a synthetic Vn key")
        if visit["challenge"] != "MMTT" or not isinstance(visit["samples"], list):
            raise ValueError("Only named MMTT sample sets are supported")
        if len(visit["samples"]) > 20:
            raise ValueError("Too many MMTT samples")
        for sample in visit["samples"]:
            exact(sample, ("minute", "c_peptide", "glucose"), "MMTT sample")
            day(sample["minute"], "Sample minute")
            if sample["c_peptide"] not in ("observed", "below_limit", "missing"):
                raise ValueError("Invalid C-peptide availability")
            if sample["glucose"] not in ("observed", "missing"):
                raise ValueError("Invalid glucose availability")
    for outcome in packet["insulin"]:
        exact(
            outcome,
            (
                "alias",
                "visit_id",
                "day",
                "semantics",
                "diary_days",
                "mean_summary_available",
                "weight_available",
            ),
            "Insulin visit",
        )
        alias(outcome["alias"])
        day(outcome["day"], "Insulin visit day")
        if outcome["alias"] not in known:
            raise ValueError("Insulin visit references an alias outside the roster")
        if not isinstance(outcome["visit_id"], str) or not re.fullmatch(
            r"V[0-9]{1,3}", outcome["visit_id"]
        ):
            raise ValueError("Insulin visit_id must be a synthetic Vn key")
        if outcome["semantics"] != "reported_daily_total_u":
            raise ValueError("Insulin amount must be labelled as reported daily total units")
        if not isinstance(outcome["diary_days"], list) or len(outcome["diary_days"]) > 30:
            raise ValueError("Invalid diary day list")
        for entry in outcome["diary_days"]:
            day(entry, "Diary day")
        for field in ("mean_summary_available", "weight_available"):
            if type(outcome[field]) is not bool:
                raise ValueError(f"{field} must be boolean")


def assess(intent, packet):
    validate_intent(intent)
    validate_packet(packet)
    records = []
    for person in packet["participants"]:
        name = person["alias"]
        issues = []
        infusions = [item["day"] for item in packet["infusions"] if item["alias"] == name]
        if infusions.count(0) != 1 or len(infusions) != len(set(infusions)):
            issues.append("first_or_duplicate_infusion")
        landmarks = [
            item for item in packet["mmtt"] if item["alias"] == name and 70 <= item["day"] <= 80
        ]
        if len(landmarks) != 1:
            issues.append("missing_or_ambiguous_day75_mmtt")
        else:
            samples = landmarks[0]["samples"]
            minutes = [sample["minute"] for sample in samples]
            if len(minutes) != len(set(minutes)):
                issues.append("duplicate_mmtt_sample_minute")
            if not all(
                any(
                    sample["minute"] == minute
                    and sample["c_peptide"] == "observed"
                    and sample["glucose"] == "observed"
                    for sample in samples
                )
                for minute in (0, 90)
            ):
                issues.append("missing_observed_paired_mmtt_samples")
        outcomes = [
            item
            for item in packet["insulin"]
            if item["alias"] == name and 351 <= item["day"] <= 379
        ]
        if len(outcomes) != 1:
            issues.append("missing_or_ambiguous_day365_insulin_visit")
        else:
            outcome = outcomes[0]
            days = outcome["diary_days"]
            if (
                len(days) != 7
                or sorted(days) != list(range(min(days, default=0), min(days, default=0) + 7))
                or max(days, default=0) > outcome["day"]
            ):
                issues.append("seven_consecutive_previsit_diary_days_unverified")
            if not outcome["mean_summary_available"]:
                issues.append("seven_day_mean_summary_missing")
        for visits, label in ((packet["mmtt"], "mmtt"), (packet["insulin"], "insulin")):
            ids = [item["visit_id"] for item in visits if item["alias"] == name]
            if len(ids) != len(set(ids)):
                issues.append(f"duplicate_{label}_visit_id")
        intervening = (
            sorted(
                day_
                for day_ in infusions
                if landmarks and outcomes and landmarks[0]["day"] < day_ < outcomes[0]["day"]
            )
            if len(landmarks) == len(outcomes) == 1
            else []
        )
        records.append(
            {
                "alias": name,
                "candidate_linkage": not issues,
                "issues": sorted(set(issues)),
                "intervening_infusion_days": intervening,
                "weight_available_at_outcome": outcomes[0]["weight_available"]
                if len(outcomes) == 1
                else None,
            }
        )
    return {
        "schema": "ot027-synthetic-preflight-report/1",
        "claim": "synthetic_linkage_rehearsal_only",
        "human_execution_authorized": False,
        "participant_count": len(records),
        "candidate_linkage_count": sum(item["candidate_linkage"] for item in records),
        "intervening_infusion_count": sum(
            bool(item["intervening_infusion_days"]) for item in records
        ),
        "participants": records,
    }


def execute(intent_path, packet_path, output):
    intent = read(intent_path)
    validate_intent(intent)  # Reject human intent before opening the packet.
    packet = read(packet_path)
    report = assess(intent, packet)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    try:
        write(output / "intent.json", intent)
        write(output / "packet.json", packet)
        shutil.copyfile(__file__, output / "source-run.py")
        write(output / "report.json", report)
        write(
            output / "manifest.json",
            {
                "schema": "ot027-synthetic-archive/1",
                "files": {name: digest(output / name) for name in sorted(ARCHIVE_FILES)},
            },
        )
        reconstruct(output)
    except BaseException:
        shutil.rmtree(output)
        raise
    return report


def reconstruct(directory):
    directory = Path(directory)
    if directory.is_symlink() or {item.name for item in directory.iterdir()} != ARCHIVE_FILES | {
        "manifest.json"
    }:
        raise ValueError("Incomplete synthetic archive")
    manifest = read(directory / "manifest.json")
    if (
        manifest.get("schema") != "ot027-synthetic-archive/1"
        or set(manifest.get("files", {})) != ARCHIVE_FILES
    ):
        raise ValueError("Wrong synthetic archive manifest")
    for name, expected in manifest["files"].items():
        if digest_checked(directory / name) != expected:
            raise ValueError(f"Changed synthetic artifact: {name}")
    if digest(directory / "source-run.py") != digest(__file__):
        raise ValueError("Archive was created by a different preflight implementation")
    report = assess(read(directory / "intent.json"), read(directory / "packet.json"))
    if report != read(directory / "report.json"):
        raise ValueError("Report differs from synthetic reconstruction")
    return report


def digest_checked(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError("Archive artifacts must be regular files")
    return digest(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("intent", type=Path)
    run.add_argument("packet", type=Path)
    run.add_argument("output", type=Path)
    replay = sub.add_parser("reconstruct")
    replay.add_argument("archive", type=Path)
    args = parser.parse_args()
    result = (
        execute(args.intent, args.packet, args.output)
        if args.command == "run"
        else reconstruct(args.archive)
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
