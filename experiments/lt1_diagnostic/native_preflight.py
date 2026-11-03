"""Pure native launch preparation; never spawn, load engines or grant admission.

External expected identities and review states must come from trusted review.
Opaque receipt bytes are bound here, not reclassified as semantic approvals.
"""

import hashlib
import json
import math
from pathlib import PurePosixPath

from experiments.lt1_diagnostic import host_context
from experiments.lt1_diagnostic.archive_preflight import unique_object
from experiments.lt1_diagnostic.control_identity import ROOT

LIMIT = 1024 * 1024
TOTAL_LIMIT = 8 * LIMIT
ENTRY = "experiments/lt1_diagnostic/integration_worker.mjs"
REVISION = "9a6092065bd821f88691cd8d03b0550acd665573"
CANDIDATE = "lt1-cambridge-audit1-node22.23.4-darwin-arm64-preparation-1"
RUNTIME = {
    "node": "v22.23.4",
    "platform": "darwin",
    "arch": "arm64",
    "artifact_sha256": "c9e1dbc748b33ed2d14f42445191ecaf14c56259c7a9a26d0042c49ec2b66428",
    "executable_sha256": "2cc28a1880d0774616959f2210ee739bffa6ac695c887e8988a496a21271f6c0",
}
INPUTS = (
    "source_inventory",
    "reader_identity",
    "plan",
    "setup_receipt",
    "runtime_review",
    "rights_review",
    "security_review",
    "host_profile",
    "host_context",
)
GATES = ("runtime_security", "rights", "harness", "setup", "execution")
NATIVE_CASES = (
    "native_bootstrap",
    "native_modules",
    "native_addons",
    "native_process",
    "native_file_network",
    "native_host_mechanism",
)
AUTHORITY = {
    "setup_admitted": False,
    "execution_authorized": False,
    "candidate_started": False,
    "native_host_qualified": False,
    "new_authority_granted": False,
}


def need(ok, reason):
    if not ok:
        raise ValueError("LT1 native preparation refused: " + reason)


def fields(value, keys):
    need(isinstance(value, dict) and set(value) == set(keys.split()), "fields")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def decoded(raw, expected):
    need(
        isinstance(raw, bytes)
        and 0 < len(raw) <= LIMIT
        and host_context.sha(expected)
        and digest(raw) == expected,
        "external byte identity",
    )
    return json.loads(raw, object_pairs_hook=unique_object)


def source_map(value):
    need(isinstance(value, dict) and 0 < len(value) <= 1024, "source map")
    need(
        all(
            isinstance(k, str)
            and k.startswith("experiments/")
            and len(k) <= 512
            and "\0" not in k
            and PurePosixPath(k).as_posix() == k
            and "\\" not in k
            and all(p not in ("", ".", "..") for p in k.split("/"))
            and host_context.sha(v)
            for k, v in value.items()
        ),
        "public canonical source identity",
    )
    return value


def absolute(value):
    need(
        isinstance(value, str)
        and 0 < len(value) <= 1024
        and "\0" not in value
        and value.startswith("/")
        and not value.startswith("//")
        and PurePosixPath(value).as_posix() == value
        and all(p not in ("", ".", "..") for p in value.split("/")[1:]),
        "absolute lexical path",
    )
    return PurePosixPath(value)


def launch(value):
    fields(
        value,
        "argv cwd staging_root packet_root output_root exec_argv environment "
        "timeout_seconds grace_seconds stdio_policy resource_policy",
    )
    roots = [absolute(value[k]) for k in ("staging_root", "packet_root", "output_root")]
    current = PurePosixPath(str(ROOT))
    need(value["cwd"] == str(ROOT), "actual shared supervisor cwd")
    need(
        all(
            not a.is_relative_to(b) and not b.is_relative_to(a)
            for i, a in enumerate(roots)
            for b in roots[i + 1 :]
        ),
        "separate launch roots",
    )
    need(
        all(not p.is_relative_to(current) and not current.is_relative_to(p) for p in roots),
        "private roots outside checkout",
    )
    expected = [str(roots[0] / "runtime/bin/node"), str(current / ENTRY), *map(str, roots)]
    need(value["argv"] == expected and value["exec_argv"] == [], "fixed native argv without flags")
    need(value["environment"] == host_context.ENVIRONMENT, "fixed clean environment")
    for key, maximum in (("timeout_seconds", 3600), ("grace_seconds", 60)):
        v = value[key]
        need(
            type(v) in (int, float)
            and math.isfinite(v)
            and 0 <= v <= maximum
            and (key != "timeout_seconds" or v > 0),
            "deadline/grace",
        )
    need(
        value["stdio_policy"] == "shared-supervisor-defaults-unqualified"
        and value["resource_policy"] == "deadline-grace-only-no-rlimit-or-rss-claim",
        "honest launcher limits",
    )


def assess(raw, expected_sha256, policy_raw, expected_policy_sha256, inputs, *, as_of):
    """Validate a closed byte packet; never read a path or call host capture.

    Bytes, the observation clock and expected identities are trusted caller
    inputs. Current filesystem/OS state and actual decision truth are not inferred.
    """
    policy = decoded(policy_raw, expected_policy_sha256)
    fields(policy, "schema runtime worker_entry max_context_age_seconds")
    need(
        policy["schema"] == "opent1d.lt1-launch-review-policy/1"
        and policy["runtime"] == RUNTIME
        and policy["worker_entry"] == ENTRY
        and type(policy["max_context_age_seconds"]) is int
        and 0 < policy["max_context_age_seconds"] <= 3600,
        "review policy",
    )
    spec = decoded(raw, expected_sha256)
    fields(spec, "schema kind runtime launch input_sha256 gate_states native_cases")
    need(
        spec["schema"] == "opent1d.lt1-native-launch-preparation/1"
        and isinstance(spec["kind"], str)
        and spec["kind"] in {"invented", "native-preparation"}
        and spec["runtime"] == RUNTIME,
        "selected runtime/schema",
    )
    launch(spec["launch"])
    fields(inputs, " ".join(INPUTS))
    fields(spec["input_sha256"], " ".join(INPUTS))
    need(
        all(isinstance(v, bytes) and 0 < len(v) <= LIMIT for v in inputs.values())
        and sum(map(len, inputs.values())) <= TOTAL_LIMIT,
        "input bounds",
    )
    for name in INPUTS:
        need(
            host_context.sha(spec["input_sha256"][name])
            and digest(inputs[name]) == spec["input_sha256"][name],
            "bound input bytes: " + name,
        )
    source = json.loads(inputs["source_inventory"], object_pairs_hook=unique_object)
    fields(source, "schema files")
    need(source["schema"] == "opent1d.lt1-launch-source-inventory/1", "source schema")
    files = source_map(source["files"])
    need(
        {
            ENTRY,
            "experiments/lt1_diagnostic/native_loader.mjs",
            "experiments/lt1_diagnostic/host_context.py",
            "experiments/lt1_diagnostic/native_preflight.py",
            "experiments/lt1_diagnostic/journal_reader.py",
            "experiments/lt1_diagnostic/reader.py",
        }
        <= files.keys(),
        "required sources",
    )
    reader = json.loads(inputs["reader_identity"], object_pairs_hook=unique_object)
    fields(reader, "protocol implementation")
    fields(
        reader["protocol"],
        "source_revision runtime_candidate selected_runtime_artifact_sha256 "
        "plan_bytes_sha256 implementation_sha256",
    )
    protocol = reader["protocol"]
    need(
        protocol["source_revision"] == REVISION
        and protocol["runtime_candidate"] == CANDIDATE
        and protocol["selected_runtime_artifact_sha256"] == RUNTIME["artifact_sha256"]
        and protocol["plan_bytes_sha256"] == digest(inputs["plan"]),
        "reader/plan/runtime binding",
    )
    for mapping in (reader["implementation"], protocol["implementation_sha256"]):
        need(
            all(files.get(k) == v for k, v in source_map(mapping).items()), "reader source binding"
        )
    need(
        "experiments/lt1_diagnostic/journal_reader.py" in reader["implementation"]
        and "experiments/lt1_diagnostic/reader.py" in protocol["implementation_sha256"],
        "required reader sources",
    )
    context = host_context.validate(
        json.loads(inputs["host_context"], object_pairs_hook=unique_object)
    )
    need(
        all(files.get(k) == v for k, v in context["collector_identity"]["implementation"].items()),
        "collector source binding",
    )
    fields(spec["gate_states"], " ".join(GATES))
    need(
        all(
            isinstance(v, str) and v in {"pending", "accepted", "rejected"}
            for v in spec["gate_states"].values()
        ),
        "review gate states",
    )
    fields(spec["native_cases"], " ".join(NATIVE_CASES))
    for case in spec["native_cases"].values():
        fields(case, "state origin")
        need(
            isinstance(case["state"], str)
            and case["state"] in {"not_run", "passed", "failed"}
            and isinstance(case["origin"], str)
            and case["origin"] in {"none", "invented", "actual-native"}
            and (case["state"] == "not_run") == (case["origin"] == "none")
            and not (spec["kind"] == "invented" and case["origin"] == "actual-native"),
            "native case evidence origin",
        )
    oldest = host_context.stamp(context["observed_from"])
    observed, now = host_context.stamp(context["observed_to"]), host_context.stamp(as_of)
    blockers = list(context["unknown"])
    if observed > now or (now - oldest).total_seconds() > policy["max_context_age_seconds"]:
        blockers.append("host-context-future-or-stale")
    if spec["kind"] == "invented":
        blockers.append("packet-is-invented")
    blockers.extend(
        "gate:" + key for key, state in spec["gate_states"].items() if state != "accepted"
    )
    blockers.extend(
        "case:" + key
        for key, case in spec["native_cases"].items()
        if case != {"state": "passed", "origin": "actual-native"}
    )
    return {
        "schema": "opent1d.lt1-native-preparation-assessment/1",
        "kind": spec["kind"],
        "structural_spec_valid": True,
        "status": "blocked" if blockers else "ready-for-independent-review",
        "blockers": sorted(blockers),
        "native_cases": spec["native_cases"],
        "spec_sha256": expected_sha256,
        "policy_sha256": expected_policy_sha256,
        "input_sha256": spec["input_sha256"],
        **AUTHORITY,
    }
