"""Prepare sealed, unanswered formative materials from actual SDK references."""

import platform
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from . import api
from ._gui_files import decode, encoded, outside_projects, path, read, require, sha256, write

SCHEMA = "opent1d.formative-study-packet/1"
SCOPE = "internal-local-research; installation usability not assessed"
ROLES = ("mmtt", "fasting", "load15", "failed")
TASKS = (
    (
        "mmtt",
        "Investigate the supplied invented paired meal tests. Assess how the estimated "
        "secretion change depends on the supplied assumptions. Keep and explain the report.",
    ),
    (
        "m4",
        "Investigate the two supplied secretion sources under fasting. Derive a related "
        "15 g condition, preserve the original and explain the resulting evidence and its limits.",
    ),
    (
        "recovery",
        "Investigate an unsuccessful attempt. Explain what happened, recover when "
        "possible and retain the original evidence alongside the new attempt.",
    ),
    (
        "handoff",
        "Keep a complete project at a new location. Have the intended recipient reopen "
        "it and verify both task reports. Explain what was preserved and what was verified.",
    ),
)


def inventory(root):
    """Hash bounded ordinary copies without following links or importing archived code."""
    root = path(root, directory=True)
    files, total = {}, 0
    for entry in root.rglob("*"):
        require(not entry.is_symlink(), "Linked packet/project entry refused")
        if entry.is_dir():
            continue
        require(len(files) < 50000, "Too many reference files")
        raw = read(entry, 128 * 1024 * 1024)
        total += len(raw)
        require(total <= 2 * 1024**3, "Reference project exceeds the preparation bound")
        files[entry.relative_to(root).as_posix()] = {"bytes": len(raw), "sha256": sha256(raw)}
    return files


def html(title, paragraphs):
    from html import escape

    return (
        "<!doctype html><html lang=en><meta charset=utf-8>"
        "<meta name=viewport content='width=device-width,initial-scale=1'>"
        "<meta http-equiv=Content-Security-Policy content=\"default-src 'none'; "
        "style-src 'unsafe-inline'\"><title>" + escape(title) + "</title>"
        "<style>body{font:18px/1.6 system-ui;max-width:48rem;margin:3rem auto;"
        "padding:0 1rem;color:#17313a}h1{line-height:1.2}li{margin:1rem 0}"
        "@media print{body{font-size:12pt;margin:0}}</style><h1>"
        + escape(title)
        + "</h1>"
        + "".join("<p>" + escape(text) + "</p>" for text in paragraphs)
        + "</html>"
    )


def materials(identity):
    participant = html(
        "Shared project research exercise",
        [
            "Use only the supplied invented examples. Explain your reasoning as you work. "
            "You may use the supplied guide and ask for help; assistance will be recorded.",
            *[f"{index}. {text}" for index, (_, text) in enumerate(TASKS, 1)],
            "Explain your conclusions, quantities, units, time window, uncertainty "
            "and limitations. "
            "These tasks provide no basis for clinical decisions. Leave health records out.",
        ],
    )
    guide = html(
        "Facilitator key — do not give to participant",
        [
            "Prepared technical materials only. No human session, independent assessment, "
            "installation usability or performance advantage has been established.",
            "Give only participant/ to the participant. Keep this key, reference answers and "
            "observations separately. Directory names do not enforce confidentiality.",
            "Recruit an actual intended analyst who did not build this candidate. A distinct "
            "actual recipient is needed for a handoff claim. Obtain permission for "
            "any recording; "
            "use participant codes and no personal health data.",
            "Freeze this packet, host, candidate, documentation, task order, runtime "
            "attachment "
            "and reference answers before observing. Read goals neutrally, not "
            "button sequences. "
            "Record first answers before help. Separate navigation help, scientific "
            "content help "
            "and takeover. Preserve blocked tasks before offering a saved report fallback.",
            "Reference failure causes are unassessed by this packet. Inspect the retained "
            "attempt before choosing a remedy. For a separate controlled attachment exercise, "
            "use the current candidate's reviewed runtimes and start with "
            "no attachment, attempt native execution, retain the registered failure, "
            "explicitly "
            "attach the prepared runtimes and retry. A validation refusal is a "
            "different outcome.",
            "MMTT key: whole-body total endogenous secretion including basal, "
            "observed 0–120 min, "
            "pmol; follow-up minus baseline, three required assumption variants, 128 "
            "perturbations "
            "seed 117. Uncertainty is conditional on assumptions. Use the actual "
            "reference report "
            "for values; preserve missing and censored observations and failed denominators.",
            "M4 key: two supplied sources, adult #001 where applicable, 240 minutes, 961 "
            "quarter-minute outputs. The 15 g condition is an initial gastric load, "
            "not a timed "
            "meal. Preserve both plans and their parent link. These synthetic traces "
            "do not rank "
            "biological accuracy or establish treatment effects.",
            "Process completion, scientific completeness and report reconstruction differ. "
            "Reconstruction verifies saved evidence without rerunning the "
            "physiological models. "
            "Copy the entire project; a PDF or report alone is not a project handoff.",
            "Mark critical errors: wrong quantity/unit/window/direction, missing-as-zero, "
            "passing-subset inference, success equated to validity, reconstruction "
            "as simulation, "
            "15 g as timed meal, clinical claims, lost plans or attempts. Keep first "
            "submission "
            "and retest separate. An independent adjudicator records interpretation "
            "assessment.",
            "Record active work, unattended compute and total elapsed separately. Native work "
            "may need split sessions; retain the established deadlines. A stopped or blocked "
            "run is not a completed task. Same-person reopening is not recipient handoff.",
            "Observe at least one actual intended analyst before making formative findings. "
            "Keep every assisted, blocked and missing task. This pilot does not replace the "
            "historical OT-056 comparison, independent replication or broader OT-072 "
            "acceptance.",
        ],
    )
    observations = {
        "schema": "opent1d.formative-observations/1",
        "packet_id": identity,
        "participant_code": None,
        "intended_role": None,
        "facilitator": None,
        "recipient_code": None,
        "adjudicator": None,
        "session_started": None,
        "runtime_attachment_sha256": None,
        "consent_record": None,
        "deviations": [],
        "tasks": [
            {
                "id": key,
                "status": None,
                "started": None,
                "finished": None,
                "active_seconds": None,
                "unattended_compute_seconds": None,
                "elapsed_seconds": None,
                "first_submission_sha256": None,
                "interpretation": None,
                "assistance": [],
                "critical_errors": [],
                "adjudication": None,
                "retests": [],
            }
            for key, _ in TASKS
        ],
    }
    return {
        "participant/Tasks.html": participant.encode("utf-8"),
        "facilitator/Guide.html": guide.encode("utf-8"),
        "facilitator/observations.template.json": encoded(observations),
    }


def create(project_path, attempts, output, *, sdk=api):
    require(
        set(attempts) == set(ROLES) and len(set(attempts.values())) == 4,
        "Four distinct reference attempt IDs required",
    )
    source = path(project_path, directory=True)
    destination = outside_projects(output)
    path(destination, fresh=True)
    require(not source.is_relative_to(destination), "Packet cannot contain the source project")
    installation = sdk.installation()
    require(not installation["source"]["dirty"], "Freeze a clean installed candidate first")
    require(len(installation["descriptor_sha256"]) == 64, "Full artifact identity required")
    project = sdk.Project(source)
    before = project.info()
    original = inventory(source)
    recorded = {item["id"]: item for item in before["attempts"]}
    references = {}
    for role in ROLES:
        attempt = recorded[attempts[role]]
        outcome = attempt["outcome"]
        require(isinstance(outcome, dict), "Reference attempts must have terminal evidence")
        require(outcome["payload"] in {"native", "forensic"}, "Unsupported reference payload")
        detail = project.plan(attempt["plan"])
        if role == "mmtt":
            require(detail["task"] == "mmtt-sensitivity", "MMTT reference required")
        else:
            require(detail["task"] == "m4-study-installed", "Installed M4 reference required")
        if role != "failed":
            require(
                outcome["completeness"] == "complete" and outcome["payload"] == "native",
                "Complete native reference required",
            )
        else:
            require(outcome["completeness"] == "incomplete", "Unsuccessful reference required")
        if role in {"fasting", "load15"}:
            case = "fasting" if role == "fasting" else "gastric_load_15g"
            require(
                detail["boundary"]["planned_slots"] == ["dalla_man/" + case, "ultradian/" + case],
                "Wrong M4 condition reference",
            )
        references[role] = {
            "attempt": attempt,
            "plan": detail,
            "kind": "forensic-only" if outcome["payload"] == "forensic" else "native-reconstructed",
            "report_sha256": {},
        }
    require(
        references["load15"]["plan"]["parent"] == references["fasting"]["plan"]["plan"],
        "15 g reference must derive from the selected fasting plan",
    )
    with tempfile.TemporaryDirectory(prefix="opent1d-pilot-inputs-") as temporary:
        for role, reference in references.items():
            detail = reference["plan"]
            cases = (
                ("complete", "censored")
                if role == "mmtt"
                else (
                    "fasting"
                    if detail["boundary"]["planned_slots"]
                    == ["dalla_man/fasting", "ultradian/fasting"]
                    else "gastric_load_15g",
                )
            )
            supplied = []
            for case in cases:
                inputs = sdk.example(
                    detail["task"], Path(temporary).resolve() / (role + case), case=case
                )["inputs"]
                supplied.append({name: sha256(read(filename)) for name, filename in inputs.items()})
            require(
                detail["original_sha256"] in supplied,
                "Reference inputs differ from the supplied frozen exercise",
            )
    destination.mkdir(parents=True)
    # Only the disposable SDK copy gets reconstruction events. It and all
    # upstream source/table bytes stay out of the transferable packet.
    with tempfile.TemporaryDirectory(prefix="opent1d-pilot-reference-") as temporary:
        copied = Path(temporary).resolve() / "project"
        project.relocate(copied)
        reader = sdk.Project(copied)
        for role, reference in references.items():
            if reference["kind"] == "forensic-only":
                continue
            result = reader.reconstruct(
                attempts[role], Path(temporary).resolve() / role, allow_failed=role == "failed"
            )
            require(
                result["report_sha256"] == reference["attempt"]["outcome"]["report_sha256"],
                "Reconstructed and recorded report hashes differ",
            )
            expected_names = {"report.json", "report.md"}
            if role != "mmtt":
                expected_names.add("figure.svg")
            require(
                set(result["report_sha256"]) == expected_names,
                "Unexpected authoritative report roster",
            )
            folder = destination / "facilitator" / "references" / role
            folder.mkdir(parents=True)
            for name, expected in result["report_sha256"].items():
                raw = read(Path(temporary).resolve() / role / name, 64 * 1024 * 1024)
                require(sha256(raw) == expected, "Reference report identity changed")
                (folder / name).write_bytes(raw)
            reference["report_sha256"] = result["report_sha256"]
    require(
        project.info() == before and inventory(source) == original,
        "Original reference project changed during preparation",
    )
    identity = "packet-" + uuid.uuid4().hex
    for name, raw in materials(identity).items():
        filename = destination / name
        filename.parent.mkdir(parents=True, exist_ok=True)
        filename.write_bytes(raw)
    packet = {
        "schema": SCHEMA,
        "packet_id": identity,
        "exercise": "shared-project-mmtt-m4/1",
        "evidence_kind": "preparation",
        "human_sessions": "not_recorded",
        "prepared_at": datetime.now(UTC).isoformat(),
        "candidate": installation,
        "host": {
            "system": platform.system(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "scope": SCOPE,
        "reference_project": {
            "head": before["head"],
            "inventory_sha256": sha256(encoded(original)),
        },
        "references": references,
        "files": inventory(destination),
    }
    write(destination / "packet.json", packet)
    return {
        "status": "prepared",
        "packet": str(destination),
        "packet_id": identity,
        "manifest_sha256": sha256(read(destination / "packet.json")),
        "human_sessions": "not_recorded",
    }


def verify(packet_path, *, sdk=api):
    root = path(packet_path, directory=True)
    packet = decode(read(root / "packet.json"))
    require(
        packet["schema"] == SCHEMA
        and packet["evidence_kind"] == "preparation"
        and packet["human_sessions"] == "not_recorded",
        "Unsupported preparation packet",
    )
    require(packet["candidate"] == sdk.installation(), "Packet belongs to a different candidate")
    require(
        set(packet)
        == {
            "schema",
            "packet_id",
            "exercise",
            "evidence_kind",
            "human_sessions",
            "prepared_at",
            "candidate",
            "host",
            "scope",
            "reference_project",
            "references",
            "files",
        }
        and packet["exercise"] == "shared-project-mmtt-m4/1"
        and packet["scope"] == SCOPE
        and set(packet["references"]) == set(ROLES),
        "Incomplete preparation structure",
    )
    expected = set(materials(packet["packet_id"]))
    seen = set()
    for role, reference in packet["references"].items():
        require(
            set(reference) == {"attempt", "plan", "kind", "report_sha256"},
            "Invalid reference structure",
        )
        attempt, detail = reference["attempt"], reference["plan"]
        outcome = attempt["outcome"]
        require(outcome["payload"] in {"native", "forensic"}, "Unsupported reference payload")
        require(
            outcome["report_sha256"] == reference["report_sha256"],
            "Recorded and copied report hashes differ",
        )
        require(
            attempt["id"] not in seen
            and attempt["plan"] == detail["plan"]
            and detail["task"] == ("mmtt-sensitivity" if role == "mmtt" else "m4-study-installed"),
            "Reference identity mismatch",
        )
        seen.add(attempt["id"])
        require(
            outcome["completeness"] == ("incomplete" if role == "failed" else "complete"),
            "Reference terminal state mismatch",
        )
        forensic = outcome["payload"] == "forensic"
        require(
            reference["kind"] == ("forensic-only" if forensic else "native-reconstructed")
            and (not forensic or role == "failed"),
            "Reference payload mismatch",
        )
        names = set() if forensic else {"report.json", "report.md"}
        if not forensic and role != "mmtt":
            names.add("figure.svg")
        require(set(reference["report_sha256"]) == names, "Incomplete reference reports")
        for name, value in reference["report_sha256"].items():
            filename = "facilitator/references/" + role + "/" + name
            expected.add(filename)
            require(
                packet["files"][filename]["sha256"] == value,
                "Reference and file inventory hashes differ",
            )
        if role in {"fasting", "load15"}:
            case = "fasting" if role == "fasting" else "gastric_load_15g"
            require(
                detail["boundary"]["planned_slots"] == ["dalla_man/" + case, "ultradian/" + case],
                "Wrong reference condition",
            )
    require(
        packet["references"]["load15"]["plan"]["parent"]
        == packet["references"]["fasting"]["plan"]["plan"],
        "Wrong reference parent",
    )
    require(set(packet["files"]) == expected, "Preparation file roster changed")
    for name, raw in materials(packet["packet_id"]).items():
        require(read(root / name) == raw, "Canonical tasks/key or blank observations changed")
    for name in packet["files"]:
        relative = PurePosixPath(name)
        require(
            not relative.is_absolute()
            and relative.as_posix() == name
            and not any(part in {".", ".."} for part in relative.parts)
            and "\\" not in name
            and ":" not in name,
            "Unsafe packet filename",
        )
    actual = inventory(root)
    actual.pop("packet.json")
    require(actual == packet["files"], "Preparation packet bytes changed")
    return {
        "status": "verified-preparation",
        "packet_id": packet["packet_id"],
        "manifest_sha256": sha256(read(root / "packet.json")),
        "human_sessions": "not_recorded",
    }
