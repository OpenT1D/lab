"""Single-use synthetic runs and source-free numerical reconstruction."""

import json
import subprocess
import sys
import time
from pathlib import Path

from experiments.m0.simglucose.recording import RunInterrupted, interruption
from experiments.m1.artifacts import strict_json
from experiments.m1.validation import Snapshot
from experiments.m3.azt1d.data import history, target, validate_observations
from experiments.m3.common import SHA, encoded
from experiments.platform_files import is_link
from experiments.platform_process import close_tree, force_tree, spawn

from .common import (
    ROOT,
    SCHEMA,
    digest,
    finite,
    fresh_directory,
    provenance,
    read,
    require,
    save,
    validate_config,
)
from .intake import load_declaration, read_regular, validate_bundle
from .metrics import summarize_case, summarize_study

ARTIFACTS = {"manifest.json", "report.json", "report.md"}
CASE_FILES = {
    "state.json",
    "input-access.json",
    "observations.json",
    "worker-claim.json",
    "trace.jsonl",
    "result.json",
    "worker-error.json",
    "result.json.tmp",
    "worker-error.json.tmp",
}


def inventory(folder):
    files = {}
    require(not is_link(folder), "Study cannot be a symlink or reparse point")
    snapshots = {}
    for path in sorted(folder.rglob("*")):
        require(not is_link(path), "Artifact symlinks or reparse points are not supported")
        if path.is_file() and path.relative_to(folder).as_posix() not in ARTIFACTS:
            snapshot = snapshots.setdefault(path.parent, Snapshot(path.parent))
            files[path.relative_to(folder).as_posix()] = snapshot.read(path.name)
    return files, snapshots


def seal(folder):
    files, snapshots = inventory(folder)
    for snapshot in snapshots.values():
        snapshot.verify_unchanged()
    save(
        folder / "manifest.json",
        {"schema": SCHEMA, "files": {name: digest(raw) for name, raw in files.items()}},
    )


def checked_rows(raw, person):
    require(digest(raw) == person["input"]["sha256"], "Input hash differs")
    rows = validate_observations(strict_json(raw), person["id"], *person["bounds_us"])
    require(sorted(rows) == person["origins_us"], "Registered input schedule differs")
    return rows


def _stop(child):
    if child is not None:
        try:
            force_tree(child)
            child.wait()
        finally:
            close_tree(child)


def run_study(config_path, output, timeout=120):
    """Freeze source before reading observations and retain every planned person."""
    finite(timeout, "worker timeout", 0)
    require(timeout > 0, "Positive timeout required")
    config, _ = read(config_path)
    validate_config(config)
    declaration, source, settings = load_declaration(config["predictor"])
    output = fresh_directory(output)
    (output / "predictor").mkdir()
    (output / "cases").mkdir()
    save(output / "predictor/declaration.json", declaration)
    (output / "predictor/source.py").write_bytes(source)
    (output / "predictor/settings.json").write_bytes(settings)
    save(
        output / "plan.json",
        {
            "schema": SCHEMA,
            "config": config,
            "config_sha256": digest(encoded(config)),
            "predictor": declaration,
            "timeout_seconds": timeout,
            "provenance": provenance(),
        },
    )
    stopped = False
    for person in config["people"]:
        folder = output / "cases" / person["id"]
        folder.mkdir()
        state = {
            "status": "not_attempted",
            "stage": "input",
            "error_type": None,
            "worker_error_type": None,
            "elapsed_seconds": 0.0,
        }
        save(folder / "state.json", state)
        if stopped:
            continue
        started, child = time.monotonic(), None
        try:
            save(
                folder / "input-access.json",
                {
                    "person": person["id"],
                    "event": "before_input_read",
                    "input_sha256": person["input"]["sha256"],
                },
            )
            original = Path(person["input"]["file"])
            raw = read_regular(original, 64 * 1024 * 1024, "synthetic observation")
            (folder / "observations.json").write_bytes(raw)
            checked_rows(raw, person)
            state.update(status="started", stage="execution")
            save(folder / "state.json", state)
            with interruption(timeout, arm_timer=False):
                child = spawn(
                    [
                        sys.executable,
                        "-B",
                        "-S",
                        "-m",
                        "experiments.m3.researcher.worker",
                        str(output),
                        person["id"],
                    ],
                    cwd=ROOT,
                    start_new_session=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                code = child.wait(timeout=timeout)
            require(code == 0, "Candidate worker failed")
            result, _ = read(folder / "result.json")
            require(
                isinstance(result, dict)
                and type(result.get("rows")) is int
                and result
                == {
                    "person": person["id"],
                    "status": "completed",
                    "rows": len(person["origins_us"]),
                    "input_sha256": person["input"]["sha256"],
                },
                "Candidate worker completion differs",
            )
            state["status"] = "completed"
        except BaseException as error:
            _stop(child)
            child = None
            interrupted = isinstance(
                error, (KeyboardInterrupt, RunInterrupted, subprocess.TimeoutExpired)
            )
            state.update(
                status="interrupted" if interrupted else "failed", error_type=type(error).__name__
            )
            if (folder / "worker-error.json").is_file():
                detail, _ = read(folder / "worker-error.json")
                state["worker_error_type"] = detail["type"]
                if not interrupted:
                    state["error_type"] = detail["type"]
            stopped = isinstance(error, (KeyboardInterrupt, RunInterrupted))
        finally:
            _stop(child)
            state["elapsed_seconds"] = time.monotonic() - started
            save(folder / "state.json", state)
    seal(output)
    return reconstruct(output, write_to=output)


def _case(files, person):
    prefix = f"cases/{person['id']}/"
    local = {
        name.removeprefix(prefix): raw for name, raw in files.items() if name.startswith(prefix)
    }
    require(set(local) <= CASE_FILES and "state.json" in local, "Invalid person inventory")
    state = strict_json(local["state.json"])
    require(
        isinstance(state, dict)
        and set(state) == {"status", "stage", "error_type", "worker_error_type", "elapsed_seconds"},
        "Invalid execution state",
    )
    status = state["status"]
    require(
        status in ("completed", "failed", "interrupted", "not_attempted")
        and state["stage"] in ("input", "execution"),
        "Unknown saved execution state",
    )
    finite(state["elapsed_seconds"], "elapsed seconds", 0)
    if status in ("failed", "interrupted"):
        require(
            isinstance(state["error_type"], str) and state["error_type"], "Failure reason missing"
        )
    else:
        require(state["error_type"] is None, "Unexpected failure reason")
    if status == "not_attempted":
        require(
            set(local) == {"state.json"}
            and state["stage"] == "input"
            and state["elapsed_seconds"] == 0,
            "Unattempted person contains execution",
        )
    else:
        require("input-access.json" in local, "Input-access receipt missing")
        require(
            strict_json(local["input-access.json"])
            == {
                "person": person["id"],
                "event": "before_input_read",
                "input_sha256": person["input"]["sha256"],
            },
            "Input-access receipt differs",
        )
    rows = None
    if "observations.json" in local:
        try:
            rows = checked_rows(local["observations.json"], person)
        except (ValueError, TypeError, KeyError, OverflowError):
            require(
                status in ("failed", "interrupted") and state["stage"] == "input",
                "Invalid input cannot support execution",
            )
    if state["stage"] == "input":
        require(
            status != "completed"
            and not (
                set(local)
                & {
                    "trace.jsonl",
                    "result.json",
                    "worker-claim.json",
                    "worker-error.json",
                    "result.json.tmp",
                    "worker-error.json.tmp",
                }
            ),
            "Input failure contains model execution",
        )
    else:
        require(rows is not None, "Execution observations missing")
    traces = []
    if "trace.jsonl" in local:
        raw = local["trace.jsonl"]
        if raw and not raw.endswith(b"\n"):
            require(status in ("failed", "interrupted"), "Incomplete completed trace row")
            # Keep the original bytes in the inventory; score only complete lines.
            last_newline = raw.rfind(b"\n")
            raw = raw[: last_newline + 1] if last_newline >= 0 else b""
        traces = [strict_json(line) for line in raw.splitlines()]
    require(len(traces) <= len(person["origins_us"]), "Unexpected trace origins")
    for trace, origin in zip(traces, person["origins_us"]):
        features, reason = history(rows, origin, person["bounds_us"][0], "evaluation")
        require(
            trace.get("origin_us") == origin
            and trace.get("features") == features
            and trace.get("reason") == reason,
            "Trace causal history or exclusion differs from saved observations",
        )
        require(
            trace.get("target") == target(rows, origin, person["bounds_us"][1]),
            "Trace target differs from saved observations",
        )
    execution_files = {
        "trace.jsonl",
        "result.json",
        "worker-error.json",
        "result.json.tmp",
        "worker-error.json.tmp",
    }
    if "worker-claim.json" in local:
        try:
            claim = strict_json(local["worker-claim.json"])
        except ValueError:
            require(
                status in ("failed", "interrupted") and not (set(local) & execution_files),
                "Partial claim cannot support execution artifacts",
            )
        else:
            require(claim == {"person": person["id"]}, "Worker claim differs")
    require(
        not (set(local) & execution_files) or "worker-claim.json" in local,
        "Execution artifacts have no exclusive worker claim",
    )
    if status == "completed":
        require(
            "worker-claim.json" in local
            and "result.json" in local
            and "worker-error.json" not in local,
            "Completion artifacts missing",
        )
    if "result.json" in local:
        require(len(traces) == len(person["origins_us"]), "Result has incomplete saved trace")
        result = strict_json(local["result.json"])
        require(
            isinstance(result, dict)
            and type(result.get("rows")) is int
            and result
            == {
                "person": person["id"],
                "status": "completed",
                "rows": len(person["origins_us"]),
                "input_sha256": person["input"]["sha256"],
            },
            "Completion result differs",
        )
    if set(local) & {"result.json.tmp", "worker-error.json.tmp"}:
        require(status in ("failed", "interrupted"), "Completed worker has uncommitted metadata")
    if "worker-error.json" in local:
        require(
            status in ("failed", "interrupted")
            and isinstance(state["worker_error_type"], str)
            and state["worker_error_type"]
            and strict_json(local["worker-error.json"]) == {"type": state["worker_error_type"]}
            and (status != "failed" or state["error_type"] == state["worker_error_type"]),
            "Worker failure changed",
        )
    else:
        require(state["worker_error_type"] is None, "Worker error receipt missing")
    case = summarize_case(
        person["origins_us"], traces, execution_status=status, bounds_us=person["bounds_us"]
    )
    return dict(case, execution=state)


def reconstruct(study, output=None, *, write_to=None):
    """Recompute only causal checks, persistence and metrics; never import source."""
    study = Path(study).absolute()
    manifest_snapshot = Snapshot(study)
    manifest = strict_json(manifest_snapshot.read("manifest.json"))
    require(
        isinstance(manifest, dict)
        and set(manifest) == {"schema", "files"}
        and manifest["schema"] == SCHEMA
        and isinstance(manifest["files"], dict),
        "Invalid study manifest",
    )
    files, snapshots = inventory(study)
    require(
        {name: digest(raw) for name, raw in files.items()} == manifest["files"],
        "Saved artifact inventory changed",
    )
    plan = strict_json(files["plan.json"])
    require(
        isinstance(plan, dict)
        and set(plan)
        == {"schema", "config", "config_sha256", "predictor", "timeout_seconds", "provenance"}
        and plan["schema"] == SCHEMA,
        "Invalid saved plan",
    )
    config = validate_config(plan["config"], archived=True)
    require(plan["config_sha256"] == digest(encoded(config)), "Configuration changed")
    finite(plan["timeout_seconds"], "worker timeout", 0)
    require(plan["timeout_seconds"] > 0, "Invalid saved timeout")
    prov = plan["provenance"]
    require(
        isinstance(prov, dict)
        and set(prov) == {"revision", "dirty", "sources", "python", "platform"}
        and isinstance(prov["revision"], str)
        and len(prov["revision"]) == 40
        and all(c in "0123456789abcdef" for c in prov["revision"])
        and type(prov["dirty"]) is bool
        and isinstance(prov["sources"], dict)
        and prov["sources"]
        and all(isinstance(v, str) and SHA.fullmatch(v) for v in prov["sources"].values())
        and all(isinstance(prov[key], str) and prov[key] for key in ("python", "platform")),
        "Invalid source provenance",
    )
    require(
        prov["sources"] == provenance()["sources"],
        "Implementation or protocol changed; reconstruct with the recorded source",
    )
    declaration = strict_json(files["predictor/declaration.json"])
    require(declaration == plan["predictor"], "Predictor declaration differs")
    validate_bundle(declaration, files["predictor/source.py"], files["predictor/settings.json"])
    expected = {
        "plan.json",
        "predictor/declaration.json",
        "predictor/source.py",
        "predictor/settings.json",
    }
    for person in config["people"]:
        expected.update(f"cases/{person['id']}/{name}" for name in CASE_FILES)
    require(set(files) <= expected, "Unexpected saved artifact")
    evaluation = summarize_study({p["id"]: _case(files, p) for p in config["people"]})
    report = {
        "schema": SCHEMA,
        "kind": "synthetic",
        "predictor": declaration,
        "source": config["source"],
        "prior_access": config["prior_access"],
        "provenance": prov,
        "evaluation": evaluation,
        "reconstruction_scope": "saved causal windows, persistence and metric arithmetic; "
        "candidate outputs retained, not independently re-executed",
        "human_evaluation": False,
    }
    for snap in snapshots.values():
        snap.verify_unchanged()
    manifest_snapshot.verify_unchanged()
    if output is not None:
        write_to = fresh_directory(output)
    if write_to is not None:
        save(Path(write_to) / "report.json", report)
        (Path(write_to) / "report.md").write_bytes(markdown(report).encode("utf-8"))
    return report


def markdown(report):
    evaluation = report["evaluation"]
    primary = evaluation["primary"]
    lines = [
        "# Synthetic researcher forecast comparison",
        "",
        f"Predictor: `{report['predictor']['id']}`. Forecast horizon: 30 minutes; CGM: mg/dL.",
        "",
        "These invented observations verify software mechanics. No human accuracy "
        "or clinical benefit is established.",
        "",
        f"Contributing people: {evaluation['contributing_people']}/"
        f"{evaluation['planned_people']}. Complete cohort: {evaluation['complete_cohort']}.",
        "",
        f"Equal-person candidate minus persistence MAE: "
        f"{primary['mean_person_mae_difference']} mg/dL. Negative favors the candidate.",
        f"Participant bootstrap interval: {primary['participant_bootstrap_95']}.",
        "",
        "| Person | Status | Planned | Attempted | Paired targets | Candidate MAE | "
        "Persistence MAE |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for pid, case in evaluation["people"].items():
        lines.append(
            f"| {pid} | {case['execution_status']} | {case['planned']} | "
            f"{case['attempted']} | {case['paired']['scored']} | "
            f"{case['candidate']['mae']} | {case['persistence']['mae']} |"
        )
    lines += ["", "## Coverage, exclusions and failures", ""]
    for pid, case in evaluation["people"].items():
        lines += [
            f"- **{pid}**: history exclusions `{json.dumps(case['history_exclusions'])}`; "
            f"target statuses `{json.dumps(case['target_status_counts'])}`; "
            f"unattempted origins {case['not_attempted']}; "
            f"primary exclusions `{json.dumps(case['ineligibility_reasons'])}`; "
            f"supervisor error `{case['execution']['error_type']}`; "
            f"worker error `{case['execution']['worker_error_type']}`."
        ]
    lines += [
        "",
        "## Source identity and reconstruction",
        "",
        f"Revision: `{report['provenance']['revision']}`; "
        f"dirty checkout: `{report['provenance']['dirty']}`.",
        f"Predictor source SHA-256: `{report['predictor']['source']['sha256']}`.",
        f"Settings SHA-256: `{report['predictor']['settings']['sha256']}`.",
        "",
        report["reconstruction_scope"] + ". Hashes bind retained bytes; they are not "
        "signatures or proof of independent training or unchanged model behavior.",
        "",
    ]
    return "\n".join(lines)
