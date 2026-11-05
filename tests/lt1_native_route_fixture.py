"""Fresh fixed packet for the real v2 process path; declared facts are invented."""

import json
import os
import secrets
import shutil
import subprocess
from pathlib import Path

from experiments.gui.ownership import ProcessTable
from experiments.lt1_diagnostic import native_route as route


def prepare(
    parent,
    *,
    case_id="attempt",
    slot="complete",
    mode="wrapped",
    timeout=10,
    _observed_tooling=None,
    _shared=None,
):
    parent = Path(parent)
    route.need(parent.resolve() == parent and not any(parent.iterdir()), "fresh empty fixture")
    roots = {k: str(parent / k) for k in ("staging", "packet", "output", "evidence")}
    if _shared is not None:
        route.need(
            case_id == "C19" and set(_shared) == {"staging", "evidence"},
            "fixed shared C19 fixture roles",
        )
        roots.update(_shared)
    for key, path in roots.items():
        if _shared is None or key not in _shared:
            Path(path).mkdir(mode=0o500 if key in ("staging", "packet") else 0o700)
    source = route.source_identity()
    code = route.prior.grant_sources(source)
    policy = route.profile(roots, source, case_id=case_id, slot=slot)
    owner = ProcessTable().one(os.getpid())
    if _observed_tooling is None:
        node = str(Path(shutil.which("node")).resolve())
    else:
        route.storage.fields(_observed_tooling, "path sha256")
        node = _observed_tooling["path"]
        route.need(
            Path(node).is_absolute()
            and str(Path(node).resolve()) == node
            and route.storage.digest(Path(node).read_bytes()) == _observed_tooling["sha256"],
            "unchanged parent-observed fixture tooling",
        )
    runtime = json.loads(
        subprocess.check_output(
            [
                node,
                "-p",
                "JSON.stringify({node:process.version,platform:process.platform,arch:process.arch,environment:{...process.env}})",
            ],
            env=dict(route.transport.owner.ENVIRONMENT),
        )
    )
    runtime_environment = runtime.pop("environment")
    runtime["executable_sha256"] = route.storage.digest(Path(node).read_bytes())
    plan = json.loads((route.HERE / "plan.json").read_bytes())
    if case_id == "C15":
        plan.update(meals=[], announcements=[], release_rules=[])
    if case_id == "C16" and "fractional" not in slot:
        plan["meals"][0].update(
            start_ms=900000, duration_ms=900000, grams=80 if "future80" in slot else 40
        )
        plan["announcements"][0].update(start_ms=900000, available_ms=900000)
        if "unfiltered" in slot:
            plan["release_rules"] = []
    plan_raw = route.encoded(plan)
    host = {
        "schema": "opent1d.lt1-native-route-host/2",
        "kind": "invented",
        "purpose": "qualification-only",
        "entry_sources": code,
        "roots": {
            k: {"path": p, "identity": list(route.legacy._signature(Path(p).stat()))}
            for k, p in roots.items()
        },
        "profile_sha256": route.storage.digest(policy.encode()),
        "owner_context": {"observer": {"pid": os.getpid(), "start": owner["start"]}},
        "timeout_seconds": timeout,
        "grace_seconds": 0.2,
        "max_context_age_seconds": 3600,
        "sandbox_sha256": "0" * 64,
        "dyld_sha256": "0" * 64,
        "materialization_request_sha256": "0" * 64,
        "materialization_manifest_sha256": "0" * 64,
        "runtime_environment": runtime_environment,
    }
    blobs = {n: route.encoded({"kind": "invented", "role": n}) for n in route.PACKET}
    blobs["plan.json"] = plan_raw
    blobs["integration_host_receipt.json"] = route.encoded(host)
    dig = route.storage.digest
    files = {n: dig(("invented " + n).encode()) for n in route.legacy.ENTRIES}
    files["runtime/bin/node"] = route.prior.base.preflight.RUNTIME["executable_sha256"]
    engine = {
        "schema": "opent1d.lt1-native-grant/1",
        "source_revision": route.prior.base.preflight.REVISION,
        **{k: route.prior.base.preflight.RUNTIME[k] for k in ("node", "platform", "arch")},
        "host": "invented-host",
        "staging_root": roots["staging"],
        "mode": mode,
        **{n + "_sha256": dig(blobs[n + ".json"]) for n in route.legacy.RECEIPTS},
        "files": files,
        "worker_files": route.legacy._worker(route.legacy.WORKER),
    }
    blobs["grant.json"] = route.encoded(engine)
    attempt = "fixture-" + case_id.lower() + "-" + slot
    integration = {
        "schema": "opent1d.lt1-integration-grant/1",
        "engine_grant_sha256": dig(blobs["grant.json"]),
        "host_receipt_sha256": dig(blobs["integration_host_receipt.json"]),
        "output_root": roots["output"],
        "attempt": attempt,
        "owner_pid": os.getpid(),
        "reader_identity": route.legacy.journal_reader.identity(plan_raw),
        "implementation": route.legacy._worker(route.legacy.INTEGRATION),
    }
    blobs["integration-grant.json"] = route.encoded(integration)
    argv = [node, str(route.FIXTURE), *(roots[k] for k in ("staging", "packet", "output"))]
    observation = {
        "schema": "opent1d.lt1-route-observation-grant/2",
        "packet_sha256": {n: dig(raw) for n, raw in blobs.items()},
        "runtime": runtime,
        "entry_executable": node,
        "owner_pid": os.getpid(),
        "owner_start": owner["start"],
        "attempt": attempt,
        "nonce_sha256": secrets.token_hex(32) if case_id == "C19" else "a" * 64,
        "profile_sha256": host["profile_sha256"],
        "producer_sha256": source["implementation"][
            "experiments/lt1_diagnostic/native_route_observation.mjs"
        ],
        "reader_identity": integration["reader_identity"],
        "process_argv": argv,
        "runtime_environment": runtime_environment,
    }
    obs_raw = route.encoded(observation)
    entry = {
        "schema": "opent1d.lt1-native-route-grant/2",
        "kind": "invented",
        "observation_sha256": dig(obs_raw),
        "engine_sha256": dig(blobs["grant.json"]),
        "integration_sha256": dig(blobs["integration-grant.json"]),
        "setup_sha256": dig(blobs["setup_receipt.json"]),
        "entry_sources": code,
        "roots": roots,
        "profile_sha256": host["profile_sha256"],
        "owner_pid": os.getpid(),
        "owner_start": owner["start"],
        "attempt": attempt,
        "nonce_sha256": observation["nonce_sha256"],
        "process_argv": argv,
        "case_id": case_id,
        "slot": slot,
    }
    packet = Path(roots["packet"])
    packet.chmod(0o700)
    for name, raw in blobs.items():
        (packet / name).write_bytes(raw)
        (packet / name).chmod(0o400)
    packet.chmod(0o500)
    return {
        "entry_raw": route.encoded(entry),
        "observation_raw": obs_raw,
        "expected_identity": source,
        "packet": blobs,
        "roots": roots,
    }
