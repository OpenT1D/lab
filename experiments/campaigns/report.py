"""Authoritative campaign coverage and immutable attempt-chain reconstruction."""

import copy
from pathlib import Path

from experiments.m1.artifacts import strict_json

from . import common, native


def metadata_signature(value):
    return {
        key: value[key]
        for key in (
            "schema",
            "source_order",
            "scenarios",
            "protocol",
            "protocol_sha256",
            "runtime_files_sha256",
            "implementation_sources_sha256",
        )
    } | {
        "sources": {
            identity: {
                key: item[key]
                for key in (
                    "declaration",
                    "source_sha256",
                    "declaration_sha256",
                )
            }
            for identity, item in value["sources"].items()
        }
    }


def _root(campaign):
    files = common.root_inventory(campaign)
    manifest = common.read(campaign / "manifest.json")
    common.require(
        isinstance(manifest, dict)
        and set(manifest) == {"schema", "files"}
        and manifest["schema"] == common.VERSION
        and manifest["files"] == {name: common.digest(raw) for name, raw in files.items()},
        "Frozen campaign inventory changed",
    )
    plan = strict_json(files["plan.json"])
    common.require(
        isinstance(plan, dict)
        and set(plan)
        == {
            "schema",
            "protocol",
            "configuration",
            "config_sha256",
            "cells",
            "slots",
            "source_sha256",
            "runtime_identity",
        }
        and plan["schema"] == common.VERSION,
        "Invalid frozen campaign plan",
    )
    common.require(
        common.encoded(plan["protocol"]) == common.encoded(common.protocol()),
        "Campaign protocol differs",
    )
    config = common.validate_config(plan["configuration"])
    common.require(
        common.digest(files["config.json"]) == plan["config_sha256"]
        and common.encoded(strict_json(files["config.json"])) == common.encoded(config),
        "Frozen campaign config differs",
    )
    common.require(
        plan["slots"] == common.slots(config), "Frozen slot order or denominator differs"
    )
    order = [cell["id"] for cell in config["cells"]]
    common.require(set(plan["cells"]) == set(order), "Frozen cell roster differs")
    expected_sources = set(common.SELF_SOURCES)
    allowed = {"plan.json", "config.json"}
    for identity in order:
        cell = plan["cells"][identity]
        common.require(
            isinstance(cell, dict)
            and set(cell)
            == {
                "native_metadata",
                "effective_config",
                "effective_config_sha256",
                "planned_source_scenarios",
            },
            "Invalid frozen cell descriptor",
        )
        prefix = f"frozen/{identity}/"
        original = strict_json(files[prefix + "original-config.json"])
        metadata = cell["native_metadata"]
        common.require(
            common.digest(files[prefix + "original-config.json"]) == metadata["config_sha256"]
            and common.encoded(original) == common.encoded(metadata["configuration"]),
            "Original native configuration differs",
        )
        effective = copy.deepcopy(original)
        for source in effective["sources"]:
            source_id = source["id"]
            source.update(
                model=f"sources/{source_id}/model.py", declaration=f"sources/{source_id}/model.json"
            )
            for name, hash_key in (
                ("model.py", "source_sha256"),
                ("model.json", "declaration_sha256"),
            ):
                relative = prefix + f"sources/{source_id}/{name}"
                common.require(
                    common.digest(files[relative]) == metadata["sources"][source_id][hash_key],
                    "Frozen supplied source/declaration changed",
                )
                allowed.add(relative)
        common.require(
            common.encoded(effective)
            == common.encoded(cell["effective_config"])
            == common.encoded(strict_json(files[prefix + "config.json"]))
            and common.digest(files[prefix + "config.json"]) == cell["effective_config_sha256"],
            "Frozen effective native configuration differs",
        )
        prepared = native.prepare(campaign / prefix / "config.json")
        common.require(
            common.encoded(metadata_signature(prepared))
            == common.encoded(metadata_signature(metadata)),
            "Native source/protocol/runtime identity differs from frozen cell",
        )
        common.require(
            type(cell["planned_source_scenarios"]) is int
            and cell["planned_source_scenarios"]
            == len(effective["sources"]) * len(effective["scenarios"]),
            "Native planned denominator differs",
        )
        for group in ("implementation_sources_sha256", "runtime_files_sha256"):
            expected_sources.update(metadata[group])
        allowed.update(prefix + name for name in ("original-config.json", "config.json"))
    common.require(
        set(plan["source_sha256"]) == expected_sources,
        "Incomplete or unexpected implementation inventory",
    )
    for name, expected in plan["source_sha256"].items():
        path = Path(name)
        common.require(
            not path.is_absolute()
            and ".." not in path.parts
            and str(path) == name
            and isinstance(expected, str)
            and common.SHA.fullmatch(expected),
            "Invalid source snapshot identity",
        )
        relative = "implementation/" + name
        common.require(
            common.digest(files[relative])
            == expected
            == common.digest((common.ROOT / name).read_bytes()),
            "Implementation/protocol/lock source changed: " + name,
        )
        allowed.add(relative)
    common.require(set(files) == allowed, "Unexpected frozen campaign artifact")
    common.require(
        isinstance(plan["runtime_identity"], dict)
        and set(plan["runtime_identity"])
        == {
            ".",
            "experiments/m0/simglucose",
            "experiments/m4/beta_cell/runtime",
        },
        "Incomplete installed runtime identity",
    )
    return plan


def _outcome(value):
    common.require(
        isinstance(value, dict)
        and set(value)
        == {
            "status",
            "error_type",
            "exit_code",
            "native_manifest_sha256",
        }
        and value["status"] in common.STATES
        and value["status"] != "started",
        "Invalid terminal attempt outcome",
    )
    common.require(
        value["exit_code"] is None or type(value["exit_code"]) is int, "Invalid native exit"
    )
    common.require(
        value["native_manifest_sha256"] is None
        or isinstance(value["native_manifest_sha256"], str)
        and common.SHA.fullmatch(value["native_manifest_sha256"]),
        "Invalid native manifest identity",
    )
    if value["status"] == "not_attempted":
        common.require(
            all(value[key] is None for key in value if key != "status"),
            "Unattempted slot has terminal evidence",
        )
    elif value["status"] == "completed":
        common.require(
            value["exit_code"] == 0
            and value["error_type"] is None
            and value["native_manifest_sha256"] is not None,
            "Completed slot lacks successful evidence",
        )
    else:
        common.require(
            isinstance(value["error_type"], str) and value["error_type"],
            "Failed attempt lacks reason",
        )


def _summary(plan, sessions, slots):
    latest = sessions[-1]["status"] if sessions else "not_attempted"
    accepted = sum(slot["accepted"] for slot in slots)
    passed = accepted == len(slots) and latest == "completed"
    return {
        "schema": common.VERSION,
        "protocol": plan["protocol"]["id"],
        "task": "m4-study",
        "status": "completed"
        if passed
        else "interrupted"
        if latest == "interrupted"
        else "failed"
        if sessions
        else "not_attempted",
        "passed": passed,
        "planned_slots": len(slots),
        "accepted_slots": accepted,
        "planned_source_scenarios": sum(slot["planned_source_scenarios"] for slot in slots),
        "accepted_source_scenarios": sum(
            slot["planned_source_scenarios"] for slot in slots if slot["accepted"]
        ),
        "sessions": copy.deepcopy(sessions),
        "slots": copy.deepcopy(slots),
        "interpretation": (
            "Execution and identity accounting only; no pooled scientific metric or source ranking"
        ),
        "limitations": plan["protocol"]["limits"],
    }


def inspect(campaign, active_session=None):
    """Validate immutable root and every prior sealed session; never import a source."""
    from .run import command

    campaign = Path(campaign).absolute()
    plan = _root(campaign)
    slot_rows = [
        {
            **slot,
            "planned_source_scenarios": plan["cells"][slot["cell"]]["planned_source_scenarios"],
            "accepted": False,
            "accepted_attempt": None,
            "attempts": [],
        }
        for slot in plan["slots"]
    ]
    by_id = {slot["id"]: slot for slot in slot_rows}
    sessions = []
    folder = campaign / "sessions"
    common.require(folder.is_dir() and not folder.is_symlink(), "Missing session directory")
    entries = sorted(folder.iterdir())
    for index, directory in enumerate(entries, 1):
        common.require(
            directory.is_dir()
            and not directory.is_symlink()
            and directory.name == f"session-{index:04d}",
            "Unsafe or nonconsecutive session directory",
        )
        if index == active_session:
            common.require(index == len(entries), "Active session must be the final append")
            break
        common.require(
            (directory / "manifest.json").is_file(),
            "Unsealed session cannot be resumed or verified; retain it and start a new campaign",
        )
        files = common.sealed(directory, common.REPORTS)
        session_plan, state = (strict_json(files[name]) for name in ("plan.json", "state.json"))
        common.require(
            set(session_plan)
            == {
                "schema",
                "number",
                "campaign_sha256",
                "previous_session_manifest_sha256",
                "implementation_root",
                "campaign_path",
                "schedule",
            }
            and session_plan["schema"] == common.VERSION
            and session_plan["number"] == index
            and session_plan["campaign_sha256"]
            == common.digest((campaign / "manifest.json").read_bytes())
            and session_plan["previous_session_manifest_sha256"]
            == (sessions[-1]["manifest_sha256"] if sessions else None),
            "Session chain or frozen campaign identity differs",
        )
        expected_schedule = []
        for slot in slot_rows:
            if not slot["accepted"]:
                attempts = slot["attempts"]
                expected_schedule.append(
                    {
                        "id": slot["id"],
                        "cell": slot["cell"],
                        "repeat": slot["repeat"],
                        "attempt": len(attempts) + 1,
                        "previous_attempt_manifest_sha256": attempts[-1]["manifest_sha256"]
                        if attempts
                        else None,
                        "argv": command(
                            session_plan["campaign_path"],
                            index,
                            slot,
                            session_plan["implementation_root"],
                        ),
                    }
                )
        common.require(
            session_plan["schedule"] == expected_schedule,
            "Session dispatch, retry link or accepted-slot reuse differs",
        )
        common.require(
            set(state) == {"status", "interruption_signal", "attempts"}
            and state["status"] in {"completed", "failed", "interrupted"}
            and set(state["attempts"]) == {item["id"] for item in expected_schedule},
            "Invalid session state/denominator",
        )
        received = state["interruption_signal"]
        common.require(
            (state["status"] == "interrupted") == (received is not None)
            and (received is None or type(received) is int and received > 0),
            "Session interruption evidence differs",
        )
        allowed = {"plan.json", "state.json"}
        tail = False
        for item in expected_schedule:
            outcome = state["attempts"][item["id"]]
            _outcome(outcome)
            common.require(
                not tail or outcome["status"] == "not_attempted",
                "Attempt order contradicts unattempted tail",
            )
            tail |= outcome["status"] == "not_attempted"
            common.require(
                outcome["status"] != "interrupted" or state["status"] == "interrupted",
                "Interrupted attempt lacks global signal",
            )
            prefix = "attempts/" + item["id"] + "/"
            subset = {name: raw for name, raw in files.items() if name.startswith(prefix)}
            if outcome["status"] == "not_attempted":
                common.require(not subset, "Unattempted slot has an attempt directory")
                continue
            attempt_folder = directory / "attempts" / item["id"]
            attempt_files = common.sealed(attempt_folder)
            receipt = strict_json(attempt_files["receipt.json"])
            common.require(
                set(receipt)
                == {
                    "schema",
                    "slot",
                    "attempt",
                    "previous_attempt_manifest_sha256",
                    "argv",
                    "timeout_seconds",
                    "started_utc",
                    "finished_utc",
                    "outcome",
                }
                and receipt["schema"] == common.VERSION
                and receipt["slot"] == item["id"]
                and receipt["attempt"] == item["attempt"]
                and receipt["previous_attempt_manifest_sha256"]
                == item["previous_attempt_manifest_sha256"]
                and receipt["argv"] == item["argv"]
                and receipt["timeout_seconds"] == plan["configuration"]["timeout_seconds"]
                and receipt["outcome"] == outcome,
                "Attempt receipt differs from frozen command, budget or outcome",
            )
            archive = attempt_folder / "archive"
            manifest_raw = attempt_files.get("archive/manifest.json")
            common.require(
                (None if manifest_raw is None else common.digest(manifest_raw))
                == outcome["native_manifest_sha256"],
                "Native output identity changed",
            )
            native_report, error = None, None
            if manifest_raw is not None:
                if "archive/config.json" in attempt_files:
                    common.require(
                        attempt_files["archive/config.json"]
                        == (campaign / "frozen" / item["cell"] / "config.json").read_bytes(),
                        "Native output configuration differs from frozen cell",
                    )
                try:
                    native_report = native.reconstruct(archive)
                except (OSError, ValueError, KeyError, TypeError) as exc:
                    error = type(exc).__name__
            accepted = (
                outcome["status"] == "completed"
                and native_report is not None
                and native_report.get("passed") is True
            )
            common.require(
                outcome["status"] != "completed" or accepted,
                "Completed attempt lacks authoritative native acceptance",
            )
            common.require(
                common.sealed(attempt_folder) == attempt_files,
                "Native attempt changed during reconstruction",
            )
            manifest_sha = common.digest((attempt_folder / "manifest.json").read_bytes())
            row = {
                "session": index,
                "attempt": item["attempt"],
                "path": str(attempt_folder.relative_to(campaign)),
                "manifest_sha256": manifest_sha,
                "previous_attempt_manifest_sha256": item["previous_attempt_manifest_sha256"],
                "outcome": outcome,
                "accepted": accepted,
                "native_error_type": error,
                "native_report": None
                if native_report is None
                else {
                    key: native_report[key]
                    for key in (
                        "schema",
                        "passed",
                        "status",
                        "protocol",
                        "configuration",
                        "scenarios",
                        "denominators",
                        "interruption_signal",
                    )
                    if key in native_report
                }
                | {
                    "sources": {
                        identity: {
                            key: source[key]
                            for key in (
                                "status",
                                "accepted",
                                "source_sha256",
                                "declaration_sha256",
                            )
                            if key in source
                        }
                        for identity, source in native_report.get("sources", {}).items()
                    }
                },
                "native_report_sha256": None
                if native_report is None
                else common.digest(common.encoded(native_report)),
            }
            slot = by_id[item["id"]]
            slot["attempts"].append(row)
            if accepted:
                slot.update(
                    accepted=True,
                    accepted_attempt={
                        "session": index,
                        "attempt": item["attempt"],
                        "manifest_sha256": manifest_sha,
                    },
                )
            allowed.update(subset)
        common.require(set(files) == allowed, "Unexpected session/attempt artifact")
        common.require(
            common.sealed(directory, common.REPORTS) == files,
            "Session changed during reconstruction",
        )
        common.require(
            state["status"] != "completed"
            or all(value["status"] == "completed" for value in state["attempts"].values()),
            "Completed session retains incomplete attempts",
        )
        sessions.append(
            {
                "number": index,
                "status": state["status"],
                "interruption_signal": received,
                "manifest_sha256": common.digest((directory / "manifest.json").read_bytes()),
                "scheduled_slots": len(expected_schedule),
            }
        )
        cached = [(directory / name).is_file() for name in common.REPORTS]
        common.require(all(cached) or not any(cached), "Partial session report cache")
        if all(cached):
            summary = _summary(plan, sessions, slot_rows)
            common.require(
                common.read(directory / "report.json") == summary
                and (directory / "report.md").read_text() == markdown(summary),
                "Immutable session report differs from reconstruction",
            )
    common.require(_root(campaign) == plan, "Campaign freeze changed during reconstruction")
    return plan, _summary(plan, sessions, slot_rows)


def reconstruct(campaign, output=None, allow_failed=False):
    campaign = Path(campaign).absolute()
    _, report = inspect(campaign)
    common.require(
        report["passed"] or allow_failed,
        "Campaign failed/incomplete; explicit --allow-failed required",
    )
    if output is not None:
        destination = Path(output).absolute()
        common.require(
            not destination.is_symlink() and not destination.exists(),
            "Report output must be a fresh directory",
        )
        destination = destination.resolve()
        root = campaign.resolve()
        common.require(
            destination != root
            and root not in destination.parents
            and destination not in root.parents,
            "Report output and campaign must be separate",
        )
        destination.mkdir(parents=True, exist_ok=False)
        common.dump(destination / "report.json", report)
        (destination / "report.md").write_text(markdown(report))
    return report


def markdown(report):
    lines = [
        "# Local M4 study campaign",
        "",
        f"Status: **{report['status']}**. "
        f"Accepted slots: {report['accepted_slots']}/{report['planned_slots']}.",
        "",
        "Accepted complete-slot source/scenario cases: "
        f"{report['accepted_source_scenarios']}/{report['planned_source_scenarios']}.",
        "",
        report["interpretation"],
        "",
        "| Cell | Repeat | Accepted | Retained attempts | Latest result | Native report |",
        "| --- | ---: | --- | ---: | --- | --- |",
    ]
    for slot in report["slots"]:
        attempt = slot["attempts"][-1] if slot["attempts"] else None
        status = "not_attempted" if attempt is None else attempt["outcome"]["status"]
        path = "unavailable" if attempt is None else attempt["path"] + "/archive/report.md"
        lines.append(
            f"| {slot['cell']} | {slot['repeat']} | {slot['accepted']} | "
            f"{len(slot['attempts'])} | {status} | {path} |"
        )
    lines += [
        "",
        "## Immutable sessions",
        "",
        "| Session | Status | Scheduled slots | Manifest SHA-256 |",
        "| ---: | --- | ---: | --- |",
    ]
    for session in report["sessions"]:
        lines.append(
            f"| {session['number']} | {session['status']} | {session['scheduled_slots']} | "
            f"`{session['manifest_sha256']}` |"
        )
    lines += ["", report["limitations"], ""]
    return "\n".join(lines)
