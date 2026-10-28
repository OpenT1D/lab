"""Reconstruct external predictions from saved artifacts without fitting/runtime packages."""

from pathlib import Path

from experiments.m3.azt1d.analysis import _expected, _hashes, _Snapshot, _trace
from experiments.m3.azt1d.ledger import verify_snapshot
from experiments.m3.common import digest, finite, require

from .common import METRIC, PROTOCOL, SCHEMA, validate_provenance
from .metrics import summarize_case, summarize_study
from .model import FILES, load_model
from .study import access_check, model_cohort_check, observations, validate_plan


def failure_check(record):
    if record["status"] in ("failed", "interrupted"):
        require(
            isinstance(record.get("error"), dict)
            and isinstance(record["error"].get("type"), str)
            and record["error"]["type"],
            "Missing original external failure",
        )


def reconstruct(study_folder):
    study_folder = Path(study_folder)
    with _Snapshot(study_folder) as snapshot:
        inventory = _hashes(snapshot.parsed("inventory.json"))
        require(
            set(inventory) == snapshot.names - {"inventory.json", "report.json"},
            "External inventory membership changed",
        )
        for name, sha in inventory.items():
            require(digest(snapshot.read(name)) == sha, "External artifact bytes changed")
        plan = snapshot.parsed("plan.json")
        validate_plan(plan)
        plan_sha = digest(snapshot.read("plan.json"))
        model, origin, bundle_sha = load_model(study_folder / "model")
        require(
            bundle_sha == plan["model_bundle_sha256"] and origin["kind"] == plan["kind"],
            "Reconstructed model changed",
        )
        model_cohort_check(plan["registry"], origin)
        study = snapshot.parsed("study.json")
        require(
            isinstance(study, dict)
            and study.get("schema") == SCHEMA
            and study.get("plan_sha256") == plan_sha,
            "Study differs from external freeze",
        )
        validate_provenance(study.get("provenance"))
        require(
            study["status"]
            in ("completed", "finished_with_failures", "failed", "interrupted", "started"),
            "Unknown external study status",
        )
        failure_check(study)
        people = plan["registry"]["people"]
        cases = study["cases"]
        require(
            isinstance(cases, list) and [p["id"] for p in people] == [c["id"] for c in cases],
            "Planned external cohort changed",
        )
        ledger, anchor = snapshot.read("ledger.jsonl"), snapshot.parsed("ledger-anchor.json")
        require(
            anchor.get("event") == "created" and anchor.get("sequence") == 0,
            "External ledger anchor is not its creation",
        )
        context = verify_snapshot(ledger, plan["identity"], anchor)
        require(
            context["kind"] == plan["kind"]
            and context["prior_access"] == plan["registry"]["prior_access"],
            "External access disclosure changed",
        )
        expected_files = {"plan.json", "study.json", "ledger-anchor.json", "ledger.jsonl"} | {
            "model/" + n for n in FILES | {"bundle.json"}
        }
        summaries = {}
        for person, case in zip(people, cases, strict=True):
            pid, status = person["id"], case["status"]
            require(
                status in ("completed", "failed", "interrupted", "not_attempted"),
                "Unknown external case status",
            )
            failure_check(case)
            prefix = pid + "/"
            names = {n[len(prefix) :] for n in inventory if n.startswith(prefix)}
            require(status != "not_attempted" or not names, "Unattempted person has artifacts")
            require(
                names
                <= {
                    "input-access.json",
                    "execution-access.json",
                    "observations.json",
                    "run/state.json",
                    "run/trace.jsonl",
                    "run/result.json",
                    "run/worker.log",
                    "run/worker-access.json",
                },
                "Unexpected external case artifact",
            )
            expected_files |= {prefix + n for n in names}
            first = second = None
            if "input-access.json" in names:
                first = snapshot.parsed(prefix + "input-access.json")
                access_check(
                    plan, plan_sha, anchor, first, pid, "before_normalization", raw_ledger=ledger
                )
            if "execution-access.json" in names:
                require(first is not None, "Execution has no prior input receipt")
                second = snapshot.parsed(prefix + "execution-access.json")
                access_check(
                    plan, plan_sha, anchor, second, pid, "before_execution", raw_ledger=ledger
                )
                require(first["sequence"] < second["sequence"], "External access order changed")
            rows = None
            if "observations.json" in names:
                require(first is not None, "Observations lack prior access evidence")
                rows = observations(snapshot.read(prefix + "observations.json"), person)
            traces, fragment = [], 0
            if any(n.startswith("run/") for n in names):
                require(rows is not None and second is not None, "Run lacks source/access evidence")
                require(
                    "run/state.json" in names and "run/trace.jsonl" in names,
                    "Incomplete run evidence",
                )
                state = snapshot.parsed(prefix + "run/state.json")
                require(
                    state.get("schema") == SCHEMA and state.get("status") == status,
                    "Saved run status differs",
                )
                validate_provenance(state.get("provenance"))
                failure_check(state)
                finite(state.get("elapsed_seconds"), "External elapsed seconds", 0)
                files = _hashes(state.get("files"))
                require(
                    set(files) == {n[4:] for n in names if n.startswith("run/")} - {"state.json"},
                    "Run inventory membership differs",
                )
                for name, sha in files.items():
                    require(
                        digest(snapshot.read(prefix + "run/" + name)) == sha,
                        "Saved run artifact changed",
                    )
                expected = [
                    _expected(rows, pid, "evaluation", person["bounds_us"], model, t)
                    for t in person["origins_us"]
                ]
                traces, fragment = _trace(
                    snapshot.read(prefix + "run/trace.jsonl"),
                    expected,
                    completed=status == "completed",
                )
                if "run/worker-access.json" in names:
                    require(
                        snapshot.parsed(prefix + "run/worker-access.json")
                        == {"execution_event_sha256": second["event_sha256"]},
                        "External worker access claim changed",
                    )
                else:
                    require(
                        not traces and not fragment and status != "completed",
                        "Missing external worker access claim",
                    )
                if "run/result.json" in names:
                    result = snapshot.parsed(prefix + "run/result.json")
                    require(
                        result
                        == {
                            "schema": SCHEMA,
                            "status": "completed",
                            "person": pid,
                            "planned": len(person["origins_us"]),
                            "model_bundle_sha256": bundle_sha,
                            "trace_sha256": digest(snapshot.read(prefix + "run/trace.jsonl")),
                        },
                        "External worker result changed",
                    )
                if status == "completed":
                    require(
                        {"run/result.json", "run/worker.log"} <= names,
                        "Completed run has no result or worker log",
                    )
            else:
                require(status != "completed", "Completed person has no execution")
            summary = summarize_case(
                person["origins_us"], traces, execution_status=status, bounds_us=person["bounds_us"]
            )
            summary.update(
                partial_fragment=bool(fragment),
                partial_fragment_bytes=fragment,
                access={"input": first, "execution": second},
            )
            summaries[pid] = summary
        require(expected_files == set(inventory), "Unrecognized external artifacts")
        statuses = [c["status"] for c in cases]
        if study["status"] == "completed":
            require(all(s == "completed" for s in statuses), "False external completion")
        if study["status"] == "finished_with_failures":
            require(
                all(s in ("completed", "failed", "interrupted") for s in statuses)
                and any(s != "completed" for s in statuses),
                "False finished failure accounting",
            )
        report = {
            "schema": "opent1d.m3.external.report/1",
            "protocol": PROTOCOL,
            "metric": METRIC,
            "kind": plan["kind"],
            "study_status": study["status"],
            "evidence_scope": "synthetic external-transfer software mechanics only",
            "refitted_on_external_cohort": False,
            "model_bundle_sha256": bundle_sha,
            "evaluation": summarize_study(summaries),
            "evaluation_access": {
                "prior_access": context["prior_access"],
                "snapshot_event_count": context["event_count"],
                "snapshot_head_sha256": context["head_sha256"],
                "live_ledger_head_verified": False,
            },
            "artifacts_sha256": {
                "inventory.json": digest(snapshot.read("inventory.json")),
                "plan.json": plan_sha,
                "ledger.jsonl": digest(ledger),
            },
        }
        snapshot.verify()
        return report
