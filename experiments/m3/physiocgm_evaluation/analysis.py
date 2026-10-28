"""Private offline reconstruction of the separately authorized PhysioCGM evaluation.

Only retained snapshots are read. The original donor, conversion and live ledger
paths are never reopened. Reconstruction itself recomputes forecasts and is a
recorded health-data access, not the earlier score-free freeze verification.
"""

from pathlib import Path

from experiments.m1.artifacts import strict_json
from experiments.m3.azt1d.analysis import _equal, _expected, _hashes, _Snapshot, _trace
from experiments.m3.azt1d.ledger import verify_snapshot
from experiments.m3.azt1d.study import private_directory
from experiments.m3.common import digest, encoded, finite, require
from experiments.m3.external import human_freeze
from experiments.m3.external.metrics import METRIC, summarize_case, summarize_study
from experiments.m3.physiocgm import human as conversion
from experiments.m3.physiocgm.access import record_access
from experiments.m3.workflow import failure

from . import common

_VERIFICATION_FILES = {"state.json", "access.jsonl", "summary.json", "manifest.json"}
_CASE_FILES = {
    "input-access.json",
    "execution-access.json",
    "observations.json",
    "run/state.json",
    "run/trace.jsonl",
    "run/result.json",
    "run/worker.log",
    "run/worker-access.json",
}


def _failure(record):
    if record["status"] in ("failed", "interrupted"):
        require(
            type(record.get("error")) is dict
            and type(record["error"].get("type")) is str
            and record["error"]["type"],
            "Missing original execution failure",
        )


def _case(snapshot, plan, plan_sha, anchor, ledger, person, case, model, previous_sequence):
    """Validate one retained prefix while preserving its whole planned denominator."""
    pid, status = person["id"], case["status"]
    require(
        status in ("completed", "failed", "interrupted", "not_attempted"),
        "Unknown evaluation case status",
    )
    _failure(case)
    prefix = pid + "/"
    names = {name[len(prefix) :] for name in snapshot.names if name.startswith(prefix)}
    require(names <= _CASE_FILES, "Unexpected evaluation case artifact")
    require(status != "not_attempted" or not names, "Unattempted case contains artifacts")
    first = second = None
    if "input-access.json" in names:
        first = snapshot.parsed(prefix + "input-access.json")
        common.access_check(
            plan, plan_sha, anchor, first, pid, "before_normalization", raw_ledger=ledger
        )
        require(first["sequence"] > previous_sequence, "Evaluation input access order changed")
        previous_sequence = first["sequence"]
    if "execution-access.json" in names:
        require(first is not None, "Execution has no prior input receipt")
        second = snapshot.parsed(prefix + "execution-access.json")
        common.access_check(
            plan, plan_sha, anchor, second, pid, "before_execution", raw_ledger=ledger
        )
        require(second["sequence"] > previous_sequence, "Evaluation execution order changed")
        previous_sequence = second["sequence"]
    rows = None
    if "observations.json" in names:
        require(first is not None, "Observation snapshot has no access receipt")
        rows = common.observations(snapshot.read(prefix + "observations.json"), person)
    traces, fragment = [], 0
    if any(name.startswith("run/") for name in names):
        require(rows is not None and second is not None, "Run has no source/access evidence")
        require({"run/state.json", "run/trace.jsonl"} <= names, "Incomplete run evidence")
        state = snapshot.parsed(prefix + "run/state.json")
        require(
            state.get("schema") == common.SCHEMA and state.get("status") == status,
            "Saved run status differs",
        )
        common.validate_provenance(state.get("provenance"))
        _failure(state)
        finite(state.get("elapsed_seconds"), "Execution elapsed seconds", 0)
        files = _hashes(state.get("files"))
        require(
            set(files) == {name[4:] for name in names if name.startswith("run/")} - {"state.json"},
            "Run inventory membership differs",
        )
        for name, sha in files.items():
            require(digest(snapshot.read(prefix + "run/" + name)) == sha, "Run artifact changed")
        raw_trace = snapshot.read(prefix + "run/trace.jsonl")
        if "run/worker-access.json" in names:
            require(
                _equal(
                    snapshot.parsed(prefix + "run/worker-access.json"),
                    {"execution_event_sha256": second["event_sha256"]},
                ),
                "Worker execution claim changed",
            )
        else:
            require(not raw_trace and status != "completed", "Missing worker execution claim")
        # A failed run's unattempted suffix is not silently evaluated by replay.
        # Only newline-terminated records are available for reconstruction.
        retained = sum(line.endswith(b"\n") for line in raw_trace.splitlines(keepends=True))
        require(retained <= len(person["origins_us"]), "Unexpected forecast origins")
        replay_origins = (
            person["origins_us"] if status == "completed" else person["origins_us"][:retained]
        )
        # Check claim/access evidence before recomputing any forecast arithmetic.
        expected = [
            _expected(rows, pid, "evaluation", person["bounds_us"], model, origin)
            for origin in replay_origins
        ]
        traces, fragment = _trace(raw_trace, expected, completed=status == "completed")
        if "run/result.json" in names:
            require(
                _equal(
                    snapshot.parsed(prefix + "run/result.json"),
                    {
                        "schema": common.SCHEMA,
                        "status": "completed",
                        "person": pid,
                        "planned": len(person["origins_us"]),
                        "model_sha256": plan["model_sha256"],
                        "trace_sha256": digest(raw_trace),
                    },
                ),
                "Worker result changed",
            )
        if status == "completed":
            require(
                {"run/result.json", "run/worker.log", "run/worker-access.json"} <= names,
                "Completed run lacks result, log or execution claim",
            )
    else:
        require(status != "completed", "Completed case has no execution")
    summary = summarize_case(
        person["origins_us"], traces, execution_status=status, bounds_us=person["bounds_us"]
    )
    summary.update(
        partial_fragment=bool(fragment),
        partial_fragment_bytes=fragment,
        access={"input": first, "execution": second},
    )
    return summary, previous_sequence


def _reconstruct(folder, inventory_raw, output):
    """Called only after the output's durable whole-bundle read receipt."""
    with _Snapshot(folder) as snapshot:
        require(snapshot.read("inventory.json") == inventory_raw, "Inventory changed before read")
        inventory = _hashes(strict_json(inventory_raw))
        require(
            set(inventory) == snapshot.names - {"inventory.json"},
            "Evaluation inventory membership changed",
        )
        prepared = folder / "prepared"
        # The old verifier checks complete saved membership before broad hashing;
        # its own access receipt is also retained in this reconstruction output.
        human_freeze.verify(prepared / "freeze", output / "freeze-verification")
        common.verify_prepared(prepared)
        plan, plan_sha = common.read_plan(prepared / "plan.json")
        require(plan_sha == inventory["prepared/plan.json"], "Prepared execution plan changed")
        prepared_inventory = snapshot.parsed("prepared/manifest.json")
        prepared_names = set(_hashes(prepared_inventory["files"])) | {"manifest.json"}
        people = plan["registry"]["people"]
        allowed = {
            "inventory.json",
            "study.json",
            "ledger.jsonl",
            "source-access.json",
            "execution-claim.json",
        }
        allowed.update("prepared/" + name for name in prepared_names)
        allowed.update("verification/" + name for name in _VERIFICATION_FILES)
        for person in people:
            allowed.update(person["id"] + "/" + name for name in _CASE_FILES)
        require(snapshot.names <= allowed, "Unexpected saved evaluation artifact")
        require(
            {
                "study.json",
                "ledger.jsonl",
                "source-access.json",
                "execution-claim.json",
            }
            <= snapshot.names,
            "Incomplete original evaluation controls",
        )
        for name, sha in inventory.items():
            conversion._private(folder / name, existing=True)
            require(digest(snapshot.read(name)) == sha, "Saved evaluation artifact changed")
        common.verify_verification(folder / "verification", plan["freeze_manifest_sha256"])
        summary = snapshot.parsed("prepared/freeze/summary.json")
        require(
            _equal(snapshot.parsed("prepared/verification/summary.json"), summary)
            and _equal(snapshot.parsed("verification/summary.json"), summary),
            "Saved verification summary differs from frozen cohort",
        )
        request_sha = digest(snapshot.read("prepared/freeze/request.json"))
        require(
            snapshot.parsed("prepared/verification/state.json")["request_sha256"] == request_sha
            and snapshot.parsed("verification/state.json")["request_sha256"] == request_sha,
            "Saved verification request identity changed",
        )
        study = snapshot.parsed("study.json")
        require(
            study.get("schema") == common.SCHEMA
            and study.get("kind") == "human"
            and study.get("plan_sha256") == plan_sha,
            "Study differs from execution plan",
        )
        common.validate_provenance(study.get("provenance"))
        require(
            study.get("status")
            in ("started", "completed", "finished_with_failures", "failed", "interrupted"),
            "Unknown evaluation study status",
        )
        _failure(study)
        cases = study.get("cases")
        require(
            type(cases) is list
            and [person["id"] for person in people] == [case.get("id") for case in cases],
            "Planned evaluation cohort changed",
        )
        claim = snapshot.parsed("execution-claim.json")
        require(
            type(claim) is dict
            and set(claim) == {"schema", "plan_sha256", "output"}
            and claim["schema"] == common.SCHEMA
            and claim["plan_sha256"] == plan_sha
            and type(claim["output"]) is str
            and Path(claim["output"]).is_absolute(),
            "Invalid exclusive execution claim",
        )
        # Saved claim paths remain historical metadata; a copied offline bundle
        # may move, and reconstructing it must not contact the original path.
        ledger = snapshot.read("ledger.jsonl")
        anchor = snapshot.parsed("prepared/ledger-anchor.json")
        require(
            anchor.get("event") == "created" and anchor.get("sequence") == 0,
            "Evaluation ledger anchor is not its creation",
        )
        context = verify_snapshot(ledger, plan["identity"], anchor)
        source_access = snapshot.parsed("source-access.json")
        common.access_check(
            plan,
            plan_sha,
            anchor,
            source_access,
            "cohort",
            "before_normalization",
            raw_ledger=ledger,
        )
        previous_sequence = source_access["sequence"]
        model = common.model(prepared)
        summaries = {}
        for person, case in zip(people, cases, strict=True):
            summaries[person["id"]], previous_sequence = _case(
                snapshot, plan, plan_sha, anchor, ledger, person, case, model, previous_sequence
            )
        statuses = [case["status"] for case in cases]
        if study["status"] == "completed":
            require(all(status == "completed" for status in statuses), "False study completion")
        if study["status"] == "finished_with_failures":
            require(
                all(status in ("completed", "failed", "interrupted") for status in statuses)
                and any(status != "completed" for status in statuses),
                "False finished failure accounting",
            )
        report = {
            "schema": common.SCHEMA,
            "protocol": common.PROTOCOL,
            "metric": METRIC,
            "kind": "human",
            "study_status": study["status"],
            "evidence_scope": "retrospective CGM forecast comparison under observed treatment",
            "interpretation_limits": [
                "Internal artifact reconstruction, not independent human reproduction",
                "Different source studies; participant overlap remains unverified",
                "No physiological-model, controller-counterfactual or clinical-safety validation",
            ],
            "refitted_on_external_cohort": False,
            "donor_verification": human_freeze.VERIFICATION,
            "model_sha256": plan["model_sha256"],
            "freeze_manifest_sha256": plan["freeze_manifest_sha256"],
            "evaluation": summarize_study(summaries),
            "evaluation_access": {
                "prior_access": context["prior_access"],
                "source_access": source_access,
                "snapshot_event_count": context["event_count"],
                "snapshot_head_sha256": context["head_sha256"],
                "live_ledger_head_verified": False,
            },
            "artifacts_sha256": {
                "inventory.json": digest(inventory_raw),
                "prepared/plan.json": plan_sha,
                "ledger.jsonl": digest(ledger),
            },
        }
        snapshot.verify()
        return report


def reconstruct(study, output):
    """Write a fresh private reconstruction, with access recorded before reads."""
    study = conversion._private(study, existing=True)
    output = conversion._private(output)
    require(not output.resolve().is_relative_to(study.resolve()), "Output must be outside study")
    # The fixed hash inventory supplies the plan identity before health-data access.
    inventory_raw = conversion._read_private(study / "inventory.json")
    inventory = _hashes(strict_json(inventory_raw))
    require("prepared/plan.json" in inventory, "Execution plan identity missing")
    state = {
        "schema": common.SCHEMA,
        "kind": "human",
        "status": "started",
        "study_inventory_sha256": digest(inventory_raw),
        "plan_sha256": inventory["prepared/plan.json"],
        "recomputes_forecasts": True,
    }
    with private_directory(output):
        conversion._state(output / "state.json", state)
        try:
            record_access(
                output / "access.jsonl",
                inventory["prepared/plan.json"],
                "before_bundle_read",
                "evaluation",
                digest(inventory_raw),
            )
            report = _reconstruct(study, inventory_raw, output)
            conversion._write(output / "report.json", encoded(report))
            state["status"] = "completed"
        except BaseException as error:
            state.update(status="failed", error=failure(error))
            raise
        finally:
            conversion._state(output / "state.json", state)
            common.seal_output(output)
    return report
