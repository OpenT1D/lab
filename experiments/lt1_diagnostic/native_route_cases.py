"""Fixed C15-C18 invocations, never an arbitrary command or an admission.

All slots are gated before any private root or process resource. Native outcomes
are not_run until separately admitted. Fixture outcomes cannot become native.
"""

import copy
import json
import os
import subprocess
import sys

from experiments.gui.ownership import ProcessTable
from experiments.lt1_diagnostic import native_route as route
from experiments.lt1_diagnostic import native_route_reader as readback
from experiments.platform_process import spawn

_definition = json.loads((route.HERE / "native_route_cases.json").read_bytes())
route.need(_definition["schema"] == "opent1d.lt1-native-route-cases/2", "fixed case contract")
SLOTS = {k: tuple(v) for k, v in _definition["slots"].items() if k != "attempt"}


def planned_native_cases():
    return {
        name: {"state": "not_run", "origin": "none", "slots": list(slots)}
        for name, slots in SLOTS.items()
    }


def validate_plan(case, slot, plan, mode):
    route.legacy.reader.validate_plan(plan)
    if case == "attempt":
        route.need(slot == "complete", "fixed ordinary attempt")
        return
    route.need(case in SLOTS and slot in SLOTS[case], "fixed case/slot")
    if case in ("C15", "C16"):
        route.need(mode == slot.split("-")[0], "fixed case mode")
    if case == "C15":
        route.need(
            plan["meals"] == plan["announcements"] == plan["release_rules"] == [],
            "C15 fasting plan",
        )
    else:
        template = json.loads((route.HERE / "plan.json").read_bytes())
        template["basal_u_h"] = plan["basal_u_h"]  # Never fit or substitute a native basal.
        if case == "C16" and "fractional" not in slot:
            template["meals"][0].update(
                start_ms=900000, duration_ms=900000, grams=80 if "future80" in slot else 40
            )
            template["announcements"][0].update(start_ms=900000, available_ms=900000)
            if "unfiltered" in slot:
                template["release_rules"] = []
        route.need(plan == template, "fixed case scientific plan")


def _run(case, attempts, expected_identity, cancel, *, invented=False):
    if not invented:
        registry = route.legacy._admissions()
        route.need(registry["setup"] and registry["execution"], "no reviewed qualification grants")
    route.need(
        case in SLOTS and isinstance(attempts, (tuple, list)) and len(attempts) == len(SLOTS[case]),
        "complete fixed case denominator",
    )
    owned = copy.deepcopy(attempts)
    # Validate every opaque grant before the first slot acquires resources.
    for (entry_raw, observation_raw), slot in zip(owned, SLOTS[case]):
        if invented:
            e = route.decode(entry_raw)
            registry = {
                "schema": "opent1d.lt1-native-admissions/1",
                "setup": [e["setup_sha256"]],
                "execution": [
                    route.storage.digest(entry_raw),
                    route.storage.digest(observation_raw),
                    e["engine_sha256"],
                    e["integration_sha256"],
                ],
            }
        entry, _, _ = route.admit(entry_raw, observation_raw, registry, invented)
        route.need(entry["case_id"] == case and entry["slot"] == slot, "preselected case slot")
        route.need(
            entry["entry_sources"] == route.prior.grant_sources(expected_identity),
            "case source pin",
        )
    route.need(route.source_identity() == expected_identity, "current case consumer source")
    own = ProcessTable().one(os.getpid())
    route.need(
        own
        and all(
            route.decode(e)["owner_pid"] == os.getpid()
            and route.decode(e)["owner_start"] == own["start"]
            for e, _ in owned
        ),
        "case live owner",
    )
    sentinel, sentinel_fact = None, None
    try:
        if case == "C18":
            sentinel = spawn(
                [sys.executable, "-I", "-S", "-B", str(route.HERE / "native_route_sentinel.py")],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=dict(route.transport.owner.ENVIRONMENT),
            )
            sentinel_fact = {
                "identity": ProcessTable().one(sentinel.pid),
                "alive_after_cases": False,
                "cleanup_confirmed": False,
            }
            route.need(sentinel_fact["identity"] is not None, "actual unrelated sentinel identity")
        records = []
        for entry_raw, observation_raw in owned:
            entry = route.decode(entry_raw)
            captured = {}
            if cancel is not None and cancel.is_set():
                records.append(
                    {
                        "slot": entry["slot"],
                        "status": "not-started-cancelled",
                        "receipt": None,
                        "readback": None,
                        "error": None,
                    }
                )
                continue
            try:
                receipt = route._launch(
                    entry_raw,
                    observation_raw,
                    expected_identity,
                    cancel,
                    invented=invented,
                    _captured=captured,
                )
            except (ValueError, OSError) as error:
                records.append(
                    {
                        "slot": entry["slot"],
                        "status": "preflight-refused",
                        "receipt": None,
                        "readback": None,
                        "error": str(error),
                    }
                )
                continue
            raw = route.encoded(receipt)
            try:
                result = readback.inspect(
                    raw,
                    route.storage.digest(raw),
                    entry_raw,
                    observation_raw,
                    captured["packet"],
                    captured["output_files"],
                    expected_identity=expected_identity,
                )
                error = None
            except ValueError as refused:
                result = None
                error = str(refused)
            records.append(
                {
                    "slot": entry["slot"],
                    "status": result["status"] if result else "forensic-refusal",
                    "receipt": receipt,
                    "readback": result,
                    "error": error,
                }
            )
        if sentinel:
            sentinel_fact["alive_after_cases"] = sentinel.poll() is None
        comparisons = {}
        if case == "C15":
            sessions = [
                s
                for record in records
                if record["readback"]
                for s in record["readback"]["sessions"]
            ]
            comparisons["same_instance_and_fresh_exact_rows"] = len(sessions) == 8 and all(
                s["status"] == "completed" and s["rows"] == sessions[0]["rows"] for s in sessions
            )
            pids = [
                (
                    r["receipt"]["entry_identity"].get("pid"),
                    r["receipt"]["entry_identity"].get("start"),
                )
                for r in records
                if r["receipt"]
            ]
            comparisons["four_distinct_processes"] = len(pids) == 4 and len(set(pids)) == 4
        if case == "C16":
            comparisons.update(compare_C16(records))
        if case == "C17":
            comparisons["failure_slots_never_complete"] = all(
                r["status"] != "completed" for r in records if r["slot"] != "complete"
            )
            diagnostic = next((r for r in records if r["slot"] == "diagnostic-error"), None)
            comparisons["primary_diagnostic_preserved"] = bool(
                diagnostic
                and diagnostic["readback"]
                and diagnostic["readback"]["sessions"]
                and diagnostic["readback"]["sessions"][0]["primary_error"]
                and diagnostic["readback"]["sessions"][0]["diagnostic_error"]
            )
        if case == "C18":
            comparisons["unrelated_sentinel_survived"] = sentinel_fact["alive_after_cases"]
            comparisons["owned_cleanup_resolved"] = all(
                r["receipt"] is not None
                and r["receipt"]["transport"]["outer"]["remaining_owned_processes"] == []
                for r in records
            )
        return {
            "schema": "opent1d.lt1-native-case-observation/2",
            "case_id": case,
            "kind": "invented" if invented else "native-unadmitted",
            "planned_slots": list(SLOTS[case]),
            "records": records,
            "comparisons": comparisons,
            "all_slots_accounted": len(records) == len(SLOTS[case]),
            "unrelated_sentinel": sentinel_fact,
            "native_acceptance": False,
            "native_execution_authorized": False,
            "new_authority_granted": False,
        }
    finally:
        if sentinel:
            if sentinel.poll() is None:
                sentinel.terminate()
            try:
                sentinel.wait(timeout=3)
            except subprocess.TimeoutExpired:
                sentinel.kill()
                sentinel.wait(timeout=3)
            sentinel_fact["cleanup_confirmed"] = sentinel.poll() is not None


def run(case, attempts, *, expected_identity, cancel=None):
    return _run(case, attempts, expected_identity, cancel)


def compare_C16(records):
    """No vacuous equality: every side needs a full validated scientific grid."""
    byslot = {}
    for record in records:
        result = record.get("readback")
        if (
            record.get("status") != "completed"
            or not result
            or result.get("status") != "completed"
            or len(result.get("sessions", [])) != 1
        ):
            continue
        session = result["sessions"][0]
        slot = record["slot"]
        plan = json.loads((route.HERE / "plan.json").read_bytes())
        if "fractional" not in slot:
            plan["meals"][0].update(start_ms=900000, duration_ms=900000)
        grid = route.legacy.reader.native_grid(plan)
        rows = session.get("rows", [])
        if (
            session.get("status") == "completed"
            and len(rows) == len(grid)
            and [v.get("time_ms") for v in rows] == grid
        ):
            byslot[slot] = session
    complete = set(byslot) == set(SLOTS["C16"])
    pairs = complete and all(
        byslot["direct-" + v]["rows"] == byslot["wrapped-" + v]["rows"]
        for v in ("filtered", "unfiltered", "fractional", "future80")
    )
    prefix = complete
    for mode in ("direct", "wrapped"):
        a = [v for v in byslot.get(mode + "-filtered", {}).get("rows", []) if v["time_ms"] < 900000]
        b = [v for v in byslot.get(mode + "-future80", {}).get("rows", []) if v["time_ms"] < 900000]
        prefix = (
            prefix
            and len(a) == len(b) == 15
            and [v["time_ms"] for v in a] == list(range(0, 900000, 60000))
            and a == b
        )
    return {
        "exact_direct_wrapped_pairs": bool(pairs),
        "future_meal_prefix_unchanged": bool(prefix),
        "not_demonstrated_slots": sorted(set(SLOTS["C16"]) - set(byslot)),
    }
