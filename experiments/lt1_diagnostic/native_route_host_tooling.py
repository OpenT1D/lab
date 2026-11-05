"""Explicit Mac ordinary-Node I/O experiment; no native bootstrap or admission.

This is deliberately outside automatic tests. It uses a separate small profile,
not a broadened native profile. All targets derive from one fresh private parent.
"""

import json
import os
import secrets
import shutil
import stat
import subprocess
from pathlib import Path

from experiments.lt1_diagnostic import native_route_host as host
from experiments.lt1_diagnostic import native_supervisor as owner

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "native_route_host_tooling.mjs"
CONTROL = "OPENT1D_C19_TOOLING"


def profile(node, roots, slot, log):
    route = host._route()
    route.need(slot in host.SLOTS, "fixed tooling profile")

    def q(p):
        return json.dumps(str(p))

    sources = (SCRIPT, HERE / "native_route_host.mjs")
    base = "\n".join(
        [
            "(version 1)",
            "(deny default)",
            f"(import {q(route.legacy.DYLD)})",
            "(allow process-fork)",
            f"(allow process-exec (literal {q(node)}))",
            "(allow sysctl-read)",
            "(allow mach-lookup)",
            "(allow file-read-metadata)",
            '(allow file-read* (subpath "/System/Library") (subpath "/usr/lib") '
            '(subpath "/Library/Apple") (literal "/dev/null") '
            '(literal "/dev/random") (literal "/dev/urandom"))',
            '(allow file-map-executable (subpath "/System/Library") (subpath "/usr/lib"))',
            f"(allow file-map-executable (literal {q(node)}))",
            f"(allow file-read* (literal {q(node)}) (subpath {q(roots['output'])}) "
            + " ".join(f"(literal {q(p)})" for p in sources)
            + ")",
            f"(allow file-write* (subpath {q(roots['output'])}) (literal {q(log)}))",
            "",
        ]
    )
    return base + host.profile_delta(roots, slot)


def capture(parent, *, expected_identity):
    """Run only when explicitly requested after review of these exact sources.

    Failure to load this ordinary Node under the profile is unavailable evidence,
    never a denial. There is no runtime, command, host, port or policy selector.
    """
    route = host._route()
    route.need(os.sys.platform == "darwin", "explicit Mac tooling experiment only")
    route.need(route.source_identity() == expected_identity, "reviewed tooling source")
    parent = Path(parent)
    info = parent.lstat()
    route.need(
        parent.is_absolute()
        and parent.resolve() == parent
        and stat.S_ISDIR(info.st_mode)
        and info.st_uid == os.getuid()
        and stat.S_IMODE(info.st_mode) == 0o700
        and not any(parent.iterdir())
        and not route.legacy._overlap(parent, route.ROOT),
        "fresh private tooling parent outside checkout",
    )
    selected = shutil.which("node")
    route.need(selected is not None, "ordinary Node available")
    node = Path(selected).resolve(strict=True)
    node_sha = host._digest(node.read_bytes())
    route.need(
        node.name == "node" and node_sha != route.prior.base.preflight.RUNTIME["executable_sha256"],
        "selected native candidate excluded",
    )
    evidence = parent / "evidence"
    evidence.mkdir(mode=0o700)
    entries = []
    for slot in host.SLOTS:
        output = parent / (slot + "-output")
        output.mkdir(mode=0o700)
        entries.append(
            {
                "case_id": "C19",
                "kind": "invented",
                "slot": slot,
                "nonce_sha256": secrets.token_hex(32),
                "roots": {"output": str(output), "evidence": str(evidence)},
            }
        )
    initial = {}
    for entry in entries:
        for name in host.OUTPUT:
            path = Path(entry["roots"]["output"]) / name
            host._create(path, host._seed(entry, name))
            initial[str(path)] = host._snapshot(path)
    for name in host.EVIDENCE:
        path = evidence / name
        host._create(path, host._seed(entries[0], name))
        initial[str(path)] = host._snapshot(path)
    listener = host._Listener(entries)
    records = []
    pair_error = None
    preserved = {}
    try:
        listener.start_listener()
        for entry in entries:
            if pair_error is not None:
                records.append(
                    {
                        "slot": entry["slot"],
                        "outer": None,
                        "probe": None,
                        "profile": None,
                        "profile_sha256": None,
                        "error": pair_error,
                    }
                )
                continue
            for path, seed in initial.items():
                current = host._snapshot(path)
                route.need(
                    current["identity"][:5] == seed["identity"][:5],
                    "same physical tooling canaries",
                )
                allowed = {seed["sha256"]}
                if path in (
                    str(evidence / host.EVIDENCE[1]),
                    str(Path(entries[0]["roots"]["output"]) / host.OUTPUT[1]),
                ):
                    allowed.add(host._digest(host._write_bytes(entries[0])))
                route.need(current["sha256"] in allowed, "unexplained tooling canary change")
            for path, before in preserved.items():
                route.need(host._snapshot(path) == before, "tooling base log changed")
            log = parent / (entry["slot"] + ".log")
            policy = profile(node, entry["roots"], entry["slot"], log)

            def guard(_log):
                route.need(
                    route.source_identity() == expected_identity
                    and host._digest(node.read_bytes()) == node_sha,
                    "tooling source/runtime changed",
                )
                route.need(
                    set(evidence.iterdir()) == {evidence / n for n in host.EVIDENCE},
                    "closed tooling evidence",
                )

            with listener.lock:
                listener.active = entry["slot"]
            command = [str(route.legacy.SANDBOX), "-p", policy, str(node), str(SCRIPT)]
            environment = {**owner.ENVIRONMENT, CONTROL: route.encoded(entry).decode()}
            original_spawn = owner.canonical.spawn

            def fixed_spawn(actual_argv, **kwargs):
                route.need(
                    actual_argv == command
                    and set(kwargs) == {"cwd", "env", "stdout", "stderr"}
                    and kwargs["cwd"] == owner.canonical.ROOT
                    and kwargs["env"] == owner.ENVIRONMENT
                    and kwargs["stderr"] == subprocess.STDOUT,
                    "fixed tooling spawn fields",
                )
                stream = kwargs["stdout"]
                token = owner._log_token(stream, log, private=False)
                os.fchmod(stream.fileno(), 0o600)
                guard(stream)
                route.need(
                    owner._log_token(stream, log, private=True) == token, "tooling log rebound"
                )
                kwargs.update(env=environment, stdin=subprocess.DEVNULL, close_fds=True)
                return original_spawn(actual_argv, **kwargs)

            # A local view uses the unchanged canonical ownership loop. The only
            # substituted global is its fixed spawn; no module is patched.
            view = owner._supervisor_view(fixed_spawn)
            outer = view(command, log, timeout=8, grace=0.2, environment=dict(owner.ENVIRONMENT))
            with listener.lock:
                listener.active = None
            report, error = None, None
            try:
                raw = log.read_bytes()
                route.need(
                    len(raw) <= 65536 and raw.endswith(b"\n") and raw.count(b"\n") == 1,
                    "one bounded actual tooling report",
                )
                report = host.validate_probe(
                    json.loads(raw, object_pairs_hook=route.storage.unique_object), entry
                )
                route.need(
                    outer["status"] == "completed"
                    and outer["exit_code"] == 0
                    and outer.get("error") is None
                    and outer.get("cleanup_error") is None
                    and outer["remaining_owned_processes"] == []
                    and outer["received_signals"] == [],
                    "actual tooling owner completion",
                )
            except (ValueError, KeyError) as failure:
                error = str(failure)
                pair_error = error
            records.append(
                {
                    "slot": entry["slot"],
                    "outer": outer,
                    "probe": report,
                    "profile": policy,
                    "profile_sha256": host._digest(policy.encode()),
                    "error": error,
                }
            )
            preserved[str(log)] = host._snapshot(log)
    except (ValueError, OSError) as failure:
        pair_error = str(failure)
    finally:
        listener.close_listener()
    for entry in entries[len(records) :]:
        records.append(
            {
                "slot": entry["slot"],
                "outer": None,
                "probe": None,
                "profile": None,
                "profile_sha256": None,
                "error": pair_error,
            }
        )
    try:
        route.need(
            set(evidence.iterdir()) == {evidence / n for n in host.EVIDENCE},
            "unexpected final tooling namespace",
        )
        for path, before in preserved.items():
            route.need(host._snapshot(path) == before, "tooling base log changed after twin")
    except (ValueError, OSError) as failure:
        pair_error = str(failure)
    witness = {
        "initial_canaries": initial,
        "final_canaries": {p: host._snapshot(p) for p in initial},
        "listener_records": listener.listener_records,
        "listener_errors": listener.listener_errors,
        "listener_closed": listener.listener_closed,
        "pair_error": pair_error,
    }
    assessment = host._operation_assessment(entries, [r["probe"] for r in records], witness)
    result = {
        "schema": "opent1d.lt1-c19-tooling-experiment/1",
        "kind": "invented",
        "scope": "ordinary-node-file-network-mechanism-only",
        "source_identity": expected_identity,
        "node": {"path": str(node), "sha256": node_sha},
        "sandbox_sha256": host._digest(route.legacy.SANDBOX.read_bytes()),
        "dyld_sha256": host._digest(route.legacy.DYLD.read_bytes()),
        "entries": entries,
        "records": records,
        "parent_witness": witness,
        "assessment": assessment,
        "scientific_sessions_run": False,
        "selected_candidate_started": False,
        "native_host_qualified": False,
        "private_copy_accounting_required": True,
    }
    host._create(parent / "tooling-result.json", route.encoded(result))
    return result
