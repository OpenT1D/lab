"""Separate coordinator and strict reconstruction of unchanged child M3 studies."""

import copy
import json
import signal
import subprocess
import sys
import time
from pathlib import Path

from experiments.m1.artifacts import strict_json
from experiments.m1.validation import Snapshot
from experiments.m3.common import SHA
from experiments.m3.researcher.common import fresh_directory
from experiments.m3.researcher.study import markdown as child_markdown
from experiments.m3.researcher.study import reconstruct as reconstruct_child
from experiments.platform_files import is_link, recorded_path
from experiments.platform_process import (
    close_tree,
    force_tree,
    handled_signals,
    signal_tree,
    spawn,
)

from .analysis import summarize_common
from .common import (
    ROOT,
    SCHEMA,
    STATES,
    child_config,
    digest,
    encoded,
    metadata,
    provenance,
    require,
    save,
    validate_config,
)

ARTIFACTS = {"manifest.json", "report.json", "report.md"}
FROZEN_FILES = {
    "original-declaration.json",
    "source.py",
    "settings.json",
    "declaration.json",
    "config.json",
}


def inventory(study):
    files, snapshots = {}, {}
    require(not is_link(study), "Comparison archive cannot be a symlink or reparse point")
    for path in sorted(study.rglob("*")):
        require(not is_link(path), "Comparison artifact symlink or reparse point")
        if path.is_file():
            name = path.relative_to(study).as_posix()
            if name not in ARTIFACTS:
                snapshot = snapshots.setdefault(path.parent, Snapshot(path.parent))
                files[name] = snapshot.read(path.name)
    for snapshot in snapshots.values():
        snapshot.verify_unchanged()
    return files, snapshots


def seal(study):
    files, _ = inventory(study)
    save(
        study / "manifest.json",
        {"schema": SCHEMA, "files": {name: digest(raw) for name, raw in files.items()}},
    )


def _freeze(config_path, output):
    config, bundles = metadata(config_path)
    output = fresh_directory(output)
    (output / "frozen").mkdir()
    (output / "children").mkdir()
    (output / "logs").mkdir()
    frozen = {}
    for candidate in config["candidates"]:
        identity = candidate["id"]
        bundle = bundles[identity]
        folder = output / "frozen" / identity
        folder.mkdir()
        for name, raw in (
            ("original-declaration.json", bundle["declaration_raw"]),
            ("source.py", bundle["source"]),
            ("settings.json", bundle["settings"]),
        ):
            (folder / name).write_bytes(raw)
        effective = copy.deepcopy(bundle["declaration"])
        effective["source"]["file"] = str(folder / "source.py")
        effective["settings"]["file"] = str(folder / "settings.json")
        save(folder / "declaration.json", effective)
        save(folder / "config.json", child_config(config, folder / "declaration.json"))
        frozen[identity] = {
            "declaration": bundle["declaration"],
            "declaration_sha256": digest(bundle["declaration_raw"]),
            "effective_declaration": effective,
        }
    plan = {
        "schema": SCHEMA,
        "config": config,
        "config_sha256": digest(encoded(config)),
        "candidates": frozen,
        "provenance": provenance(),
    }
    save(output / "plan.json", plan)
    return output, plan


def run_study(config_path, output):
    output, plan = _freeze(config_path, output)
    order = [candidate["id"] for candidate in plan["config"]["candidates"]]
    state = {
        "status": "started",
        "interruption_signal": None,
        "candidates": {
            identity: {"status": "not_attempted", "error_type": None, "exit_code": None}
            for identity in order
        },
    }
    save(output / "state.json", state)
    active = None
    cancelled = None
    cancelled_at = None

    def stop(signum, _frame):
        nonlocal cancelled, cancelled_at
        if cancelled is None:
            cancelled, cancelled_at = signum, time.monotonic()
            state["interruption_signal"] = signum
        if active is not None and active.poll() is None:
            signal_tree(
                active, signum if signum in (signal.SIGINT, signal.SIGTERM) else signal.SIGTERM
            )

    handled = handled_signals()
    previous = {signum: signal.signal(signum, stop) for signum in handled}
    try:
        for identity in order:
            if cancelled is not None:
                break
            attempt = state["candidates"][identity]
            attempt["status"] = "started"
            save(output / "state.json", state)
            try:
                with (output / "logs" / (identity + ".stdout.log")).open("xb") as stdout:
                    with (output / "logs" / (identity + ".stderr.log")).open("xb") as stderr:
                        active = spawn(
                            [
                                sys.executable,
                                "-B",
                                "-S",
                                "-m",
                                "experiments.m3.researcher",
                                "run",
                                "--config",
                                str(output / "frozen" / identity / "config.json"),
                                "--output",
                                str(output / "children" / identity),
                                "--timeout",
                                str(plan["config"]["timeout_seconds"]),
                            ],
                            cwd=ROOT,
                            stdout=stdout,
                            stderr=stderr,
                            start_new_session=True,
                        )
                        if cancelled is not None:
                            stop(cancelled, None)
                        while active.poll() is None:
                            if cancelled_at is not None and time.monotonic() - cancelled_at >= 10:
                                # Normal cleanup belongs to the original supervisor. This is only
                                # a bounded fallback for an unresponsive supervisor process.
                                force_tree(active)
                            time.sleep(0.02)
                        attempt["exit_code"] = active.wait()
                child = output / "children" / identity
                if (child / "manifest.json").is_file():
                    reconstruct_child(child)
                    attempt["status"] = "finished"
                else:
                    attempt.update(
                        status="interrupted" if cancelled is not None else "failed",
                        error_type="GlobalInterruption"
                        if cancelled is not None
                        else "ChildArchiveUnavailable",
                    )
            except BaseException as error:
                attempt.update(
                    status="interrupted" if cancelled is not None else "failed",
                    error_type=type(error).__name__,
                )
                if isinstance(error, KeyboardInterrupt):
                    cancelled = signal.SIGINT
                    state["interruption_signal"] = int(signal.SIGINT)
            finally:
                if active is not None and active.poll() is None:
                    stop(cancelled or signal.SIGTERM, None)
                    try:
                        active.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        force_tree(active)
                        active.wait()
                if active is not None:
                    close_tree(active)
                active = None
                save(output / "state.json", state)
        state["status"] = (
            "interrupted"
            if cancelled is not None
            else "failed"
            if any(a["status"] == "failed" for a in state["candidates"].values())
            else "finished"
        )
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)
        # Reconcile a signal delivered after the loop's status assignment but
        # before handler restoration; the saved signal and parent state must agree.
        if cancelled is not None:
            state["status"] = "interrupted"
        if state["status"] == "started":
            state["status"] = "failed"
        for attempt in state["candidates"].values():
            if attempt["status"] == "started":
                attempt.update(
                    status="interrupted" if cancelled is not None else "failed",
                    error_type="GlobalInterruption"
                    if cancelled is not None
                    else "UncommittedCandidate",
                )
        save(output / "state.json", state)
        seal(output)
    return reconstruct(output, write_to=output)


def _plan(files):
    require("plan.json" in files and "state.json" in files, "Missing comparison plan/state")
    plan = strict_json(files["plan.json"])
    require(
        isinstance(plan, dict)
        and set(plan) == {"schema", "config", "config_sha256", "candidates", "provenance"}
        and plan["schema"] == SCHEMA,
        "Invalid frozen comparison plan",
    )
    config = validate_config(plan["config"], archived=True)
    require(plan["config_sha256"] == digest(encoded(config)), "Comparison configuration changed")
    order = [candidate["id"] for candidate in config["candidates"]]
    require(set(plan["candidates"]) == set(order), "Frozen candidate roster differs")
    prov = plan["provenance"]
    require(
        isinstance(prov, dict)
        and set(prov) == {"revision", "dirty", "sources", "python", "platform"}
        and isinstance(prov["revision"], str)
        and len(prov["revision"]) == 40
        and all(char in "0123456789abcdef" for char in prov["revision"])
        and type(prov["dirty"]) is bool
        and prov["sources"] == provenance()["sources"]
        and all(isinstance(prov[key], str) and prov[key] for key in ("python", "platform")),
        "Comparison implementation or protocol provenance differs",
    )
    archive_root = None
    from experiments.m3.researcher.intake import validate_bundle

    for identity in order:
        prefix = "frozen/" + identity + "/"
        require(all(prefix + name in files for name in FROZEN_FILES), "Incomplete frozen candidate")
        candidate = plan["candidates"][identity]
        require(
            isinstance(candidate, dict)
            and set(candidate) == {"declaration", "declaration_sha256", "effective_declaration"},
            "Invalid frozen candidate identity",
        )
        requested = strict_json(files[prefix + "original-declaration.json"])
        require(
            candidate["declaration"] == requested
            and candidate["declaration_sha256"]
            == digest(files[prefix + "original-declaration.json"]),
            "Requested declaration changed",
        )
        validate_bundle(requested, files[prefix + "source.py"], files[prefix + "settings.json"])
        require(requested["id"] == identity, "Frozen candidate ID differs")
        effective = candidate["effective_declaration"]
        validate_bundle(effective, files[prefix + "source.py"], files[prefix + "settings.json"])
        source_path = recorded_path(effective["source"]["file"])
        require(
            source_path.name == "source.py"
            and source_path.parent.name == identity
            and source_path.parent.parent.name == "frozen",
            "Effective candidate path differs",
        )
        root = source_path.parents[2]
        if archive_root is None:
            archive_root = root
        require(archive_root == root, "Frozen candidate archive roots differ")
        expected = copy.deepcopy(requested)
        expected["source"]["file"] = str(root / prefix / "source.py")
        expected["settings"]["file"] = str(root / prefix / "settings.json")
        require(
            effective == expected and strict_json(files[prefix + "declaration.json"]) == expected,
            "Effective declaration changed beyond snapshot paths",
        )
        expected_config = child_config(config, root / prefix / "declaration.json")
        require(
            strict_json(files[prefix + "config.json"]) == expected_config,
            "Generated child configuration differs",
        )
    state = strict_json(files["state.json"])
    require(
        isinstance(state, dict)
        and set(state) == {"status", "candidates", "interruption_signal"}
        and state["status"] in ("finished", "failed", "interrupted")
        and isinstance(state["candidates"], dict)
        and set(state["candidates"]) == set(order),
        "Invalid comparison execution state",
    )
    signal_value = state["interruption_signal"]
    require(
        (signal_value is None and state["status"] != "interrupted")
        or (
            type(signal_value) is int
            and signal_value in (1, 2, 15)
            and state["status"] == "interrupted"
        ),
        "Comparison global interruption record differs",
    )
    unattempted_tail = False
    for identity in order:
        attempt = state["candidates"][identity]
        require(
            isinstance(attempt, dict)
            and set(attempt) == {"status", "error_type", "exit_code"}
            and attempt["status"] in STATES
            and attempt["status"] != "started"
            and (attempt["exit_code"] is None or type(attempt["exit_code"]) is int)
            and (
                attempt["error_type"] is None
                or isinstance(attempt["error_type"], str)
                and bool(attempt["error_type"])
            ),
            "Invalid candidate execution state",
        )
        if attempt["status"] == "not_attempted":
            unattempted_tail = True
            require(
                attempt["exit_code"] is None and attempt["error_type"] is None,
                "Unattempted candidate contains execution result",
            )
        else:
            require(not unattempted_tail, "Candidate resumed after unattempted tail")
        if attempt["status"] in ("failed", "interrupted"):
            require(attempt["error_type"] is not None, "Failed attempt lacks error type")
        if attempt["status"] == "interrupted":
            require(
                state["status"] == "interrupted",
                "Interrupted candidate lacks global comparison interruption",
            )
        if attempt["status"] == "finished":
            require(
                attempt["exit_code"] is not None and attempt["error_type"] is None,
                "Finished candidate has no execution result",
            )
    if state["status"] == "finished":
        require(
            all(a["status"] == "finished" for a in state["candidates"].values()),
            "Finished comparison contains unfinished candidate",
        )
    if state["status"] == "failed":
        require(
            any(a["status"] == "failed" for a in state["candidates"].values()),
            "Failed comparison has no failed attempt",
        )
    return plan, state, archive_root


def _traces(raw):
    if raw is None:
        return []
    lines = raw.splitlines(keepends=True)
    return [strict_json(line) for line in lines if line.endswith(b"\n")]


def reconstruct(study, output=None, *, write_to=None):
    study = Path(study).absolute()
    snapshot = Snapshot(study)
    manifest = strict_json(snapshot.read("manifest.json"))
    require(
        isinstance(manifest, dict)
        and set(manifest) == {"schema", "files"}
        and manifest["schema"] == SCHEMA
        and isinstance(manifest["files"], dict)
        and all(isinstance(sha, str) and SHA.fullmatch(sha) for sha in manifest["files"].values()),
        "Invalid comparison manifest",
    )
    files, snapshots = inventory(study)
    require(
        manifest["files"] == {name: digest(raw) for name, raw in files.items()},
        "Comparison artifact inventory changed",
    )
    plan, state, archive_root = _plan(files)
    config = plan["config"]
    order = [candidate["id"] for candidate in config["candidates"]]
    allowed = {"plan.json", "state.json"}
    for identity in order:
        allowed.update("frozen/" + identity + "/" + name for name in FROZEN_FILES)
        allowed.update("logs/" + identity + suffix for suffix in (".stdout.log", ".stderr.log"))
    require(
        all(
            name in allowed
            or any(name.startswith("children/" + identity + "/") for identity in order)
            for name in files
        ),
        "Unexpected parent comparison artifact",
    )
    candidates, cases = {}, {}
    for identity in order:
        prefix = "children/" + identity + "/"
        attempt = state["candidates"][identity]
        child_files = {
            name[len(prefix) :]: raw for name, raw in files.items() if name.startswith(prefix)
        }
        if attempt["status"] == "not_attempted":
            require(not child_files, "Unattempted candidate contains child artifacts")
            require(
                not any(name.startswith("logs/" + identity + ".") for name in files),
                "Unattempted candidate contains execution logs",
            )
        report = None
        if "manifest.json" in child_files:
            require(attempt["status"] == "finished", "Sealed child contradicts coordinator status")
            report = reconstruct_child(study / "children" / identity)
            child_plan = strict_json(child_files["plan.json"])
            expected_config = child_config(
                config, archive_root / "frozen" / identity / "declaration.json"
            )
            require(
                child_plan["config"] == expected_config
                and child_plan["timeout_seconds"] == config["timeout_seconds"]
                and child_plan["predictor"]
                == plan["candidates"][identity]["effective_declaration"],
                "Child roster, observations, origins, phase, budget or predictor differs",
            )
            require(
                child_files["predictor/source.py"] == files["frozen/" + identity + "/source.py"]
                and child_files["predictor/settings.json"]
                == files["frozen/" + identity + "/settings.json"],
                "Child source or settings differs from frozen roster",
            )
            if "report.json" in child_files:
                require(
                    strict_json(child_files["report.json"]) == report, "Saved child report differs"
                )
            if "report.md" in child_files:
                require(
                    child_files["report.md"] == child_markdown(report).encode(),
                    "Saved child Markdown differs",
                )
            cases[identity] = {
                person["id"]: {
                    "status": report["evaluation"]["people"][person["id"]]["execution_status"],
                    "rows": _traces(child_files.get("cases/" + person["id"] + "/trace.jsonl")),
                }
                for person in config["people"]
            }
        else:
            require(
                attempt["status"] != "finished", "Finished candidate lacks sealed child archive"
            )
            status = "not_attempted"
            cases[identity] = {
                person["id"]: {"status": status, "rows": []} for person in config["people"]
            }
        candidates[identity] = {
            "coordinator": {
                **attempt,
                "comparison_status": state["status"],
                "interruption_signal": state["interruption_signal"],
            },
            "single_candidate": report,
            "missing_archive_reason": None
            if report is not None
            else "candidate not attempted"
            if attempt["status"] == "not_attempted"
            else "no validated sealed child archive; retained raw artifacts are diagnostic only",
            "planned_people": len(config["people"]),
            "planned_origins": {p["id"]: len(p["origins_us"]) for p in config["people"]},
        }
    report = {
        "schema": SCHEMA,
        "kind": "synthetic",
        "provenance": plan["provenance"],
        "candidate_order": order,
        "candidates": candidates,
        "common": summarize_common(config["people"], order, cases),
        "human_evaluation": False,
        "reconstruction_scope": "saved common causal windows, persistence and analysis arithmetic; "
        "arbitrary candidate outputs retained, not independently re-executed",
    }
    for value in snapshots.values():
        value.verify_unchanged()
    snapshot.verify_unchanged()
    rendered = markdown(report)
    if output is not None:
        write_to = fresh_directory(output)
    if write_to is not None:
        save(Path(write_to) / "report.json", report)
        (Path(write_to) / "report.md").write_bytes(rendered.encode("utf-8"))
    return report


def markdown(report):
    common = report["common"]
    lines = [
        "# Synthetic frozen-candidate CGM comparison",
        "",
        "Primary support includes every frozen candidate and persistence. "
        "No fitting, automatic winner or human evaluation.",
        "",
        "Candidate order: " + ", ".join(report["candidate_order"]) + ".",
        "Coordinator status: "
        + report["candidates"][report["candidate_order"][0]]["coordinator"]["comparison_status"]
        + ".",
        f"Contributing people: {common['contributing_people']}/{common['planned_people']}. "
        f"Complete cohort: {common['complete_cohort']}.",
        f"Null reason: {common['null_reason']}.",
        "",
        "## Common-support error metrics",
        "",
        "| Method | Equal-person MAE (mg/dL) | Equal-person RMSE (mg/dL) | "
        "Equal-person bias (mg/dL) |",
        "| --- | --- | --- | --- |",
    ]
    for identity in [*report["candidate_order"], "persistence"]:
        metrics = common["equal_person_metrics"][identity]
        lines.append(f"| {identity} | {metrics['mae']} | {metrics['rmse']} | {metrics['bias']} |")
    lines += [
        "",
        "## Common-support contrasts",
        "",
        "| Left | Right | Equal-person MAE difference (mg/dL) | Participant bootstrap 95% |",
        "| --- | --- | --- | --- |",
    ]
    for contrast in common["contrasts"]:
        lines.append(
            f"| {contrast['left']} | {contrast['right']} | "
            f"{contrast['mean_person_mae_difference']} | "
            f"{contrast['participant_bootstrap_95']} |"
        )
    lines += [
        "",
        "## Planned people and coverage",
        "",
        "| Person | Planned origins | Candidate statuses | Candidate scored | "
        "Common scored | Span (minutes) | Eligible | Exclusions |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for pid, person in common["people"].items():
        span = person["common_span_us"]
        lines.append(
            f"| {pid} | {person['planned_origins']} | "
            f"{json.dumps(person['candidate_statuses'], sort_keys=True)} | "
            f"{json.dumps(person['candidate_scored'], sort_keys=True)} | "
            f"{person['common_scored']} | {None if span is None else span / 60_000_000} | "
            f"{person['eligible_for_primary']} | {json.dumps(person['ineligibility_reasons'])} |"
        )
    lines += ["", "## Candidate archives", ""]
    for identity in report["candidate_order"]:
        candidate = report["candidates"][identity]
        lines.append(
            f"- **{identity}**: coordinator "
            f"{json.dumps(candidate['coordinator'], sort_keys=True)}; "
            f"missing-archive reason: {candidate['missing_archive_reason']}. "
            "Original candidate-versus-persistence denominators remain in its child report; "
            "do not rank unmatched subsets."
        )
    lines += [
        "",
        "## Provenance and limitations",
        "",
        f"Revision: {report['provenance']['revision']}; "
        f"dirty checkout: {report['provenance']['dirty']}.",
        report["reconstruction_scope"] + ".",
        "People marked not_attempted for an unavailable archive have zero validated "
        "worker or origin records; attempted process failures remain explicit "
        "in coordinator status.",
        "Failure prefixes are diagnostic only. Hashes establish saved consistency, "
        "not authenticated execution or independent model reproduction.",
        "",
    ]
    return "\n".join(lines)
