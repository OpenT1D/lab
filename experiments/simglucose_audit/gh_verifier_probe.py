"""Bounded startup/help probe controller, without artifact verification authority.

Actual paths, versions, digests and consent are externally held private plan data.
Only internally minted invented contexts enter the public fixture facade. Ordinary
entry refuses before argument/source/path access. OS containment qualification is
separate from controller fixtures and from actual selected-binary compatibility.
"""

import base64
import hashlib
import json
import os
import queue
import re
import selectors
import stat
import subprocess
import sys
import threading
import time
from datetime import timedelta
from pathlib import Path

from experiments import platform_process

from . import intake_collector as core
from . import retained_source_review as previous
from .contract import AUTHORITY, decode, digest, encode, fields, require

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "opent1d.gh-startup-probe/1"
SANDBOX = Path("/usr/bin/sandbox-exec")
DYLD = Path("/System/Library/Sandbox/Profiles/dyld-support.sb")
SYSTEM_READ_ROOTS = ("/System/Library", "/usr/lib")
SYSCTL_READ_NAMES = ("hw.pagesize",)
ARGVS = (("--version",), ("attestation", "verify", "--help"))
HELP_MARKERS = (
    "--bundle",
    "--custom-trusted-root",
    "--cert-identity",
    "--cert-oidc-issuer",
    "--signer-workflow",
    "--predicate-type",
    "--deny-self-hosted-runners",
)
LIMITS = {
    "binary_max_bytes": 67108864,
    "binary_passes": 1,
    "probe_count": 2,
    "probe_seconds": 10,
    "whole_seconds": 60,
    "start_headroom_seconds": 80,
    "stdout_bytes_each": 8192,
    "stderr_bytes_each": 8192,
    "pipe_application_bytes": 32772,
    "stored_raw_bytes": 32768,
    "report_bytes": 65536,
    "receipt_bytes": 32768,
    "root_regular_files": 2,
    "root_regular_bytes": 98304,
    "root_directories_including_root": 6,
    "parent_marker_bytes": 128,
    "outer_observation_bytes": 16384,
    "action_output_bytes": 114816,
}
CASES = (
    "ok",
    "nonzero",
    "version-mismatch",
    "help-mismatch",
    "stdout-overflow",
    "stderr-overflow",
    "probe-stall",
    "fsync-stall",
    "finalize-stall",
    "exit-survivor",
    "invalidUTF8",
    "drip",
    "fullpipe",
    "hash-stall",
    "write-stall",
    "receipt-then-error",
    "receipt-then-nonzero",
    "spawn-stall",
    "help-prefix-only",
)
FRAME_LIMIT = 8
_FIXTURES = set()


def run_probe(*_args, **_kwargs):
    raise PermissionError("selected-tool probe closed without exact new consent")


def _identity(expiry=None):
    return previous._identity(expiry) | {
        "gh_verifier_probe.py": _source_hash(Path(__file__), expiry)
    }


def _owner(expiry=None):
    return previous._owner(expiry)


def _token(info):
    return previous._token(info)


def _path(value):
    return previous._path(value)


def _retention(value):
    return previous._retention(value)


def _policy_identity(expiry=None):
    if expiry is not None:
        require(core._now() < expiry, "OS-policy-window")
    fd = os.open(DYLD, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        require(
            stat.S_ISREG(before.st_mode) and before.st_uid == 0 and before.st_size <= 65536,
            "bounded-trusted-OS-policy",
        )
        raw = bytearray()
        while len(raw) <= before.st_size:
            if expiry is not None:
                require(core._now() < expiry, "OS-policy-chunk-window")
            part = os.read(fd, min(4096, before.st_size + 1 - len(raw)))
            if not part:
                break
            raw += part
        require(
            len(raw) == before.st_size
            and _token(before) == _token(os.fstat(fd)) == _token(DYLD.lstat()),
            "stable-OS-policy",
        )
        require(
            re.search(r"\((?:import|load)\s", bytes(raw).decode("utf-8")) is None,
            "reviewed-nontransitive-OS-policy",
        )
        return {
            "dyld_path": str(DYLD),
            "dyld_sha256": digest(bytes(raw)),
            "dyld_token": _token(before),
            "transitive_imports": [],
            "sandbox_path": str(SANDBOX),
            "sandbox_token": _token(SANDBOX.lstat()),
            "system_read_roots": list(SYSTEM_READ_ROOTS),
            "global_sysctl_read": False,
            "sysctl_read_names": list(SYSCTL_READ_NAMES),
            "fork_allowed": False,
            "mach_lookup_allowed": False,
        }
    finally:
        os.close(fd)


def _profile(plan, fixture=False, *, control=None):
    binary = Path(sys.executable).resolve() if fixture else _path(plan["binary"]["path"])

    def q(p):
        return json.dumps(str(p))

    rules = [
        "(version 1)",
        "(deny default)",
        f"(import {q(DYLD)})",
        f"(allow process-exec (literal {q(binary)}))",
        "(allow file-read* file-map-executable "
        + " ".join(f"(subpath {q(p)})" for p in SYSTEM_READ_ROOTS)
        + f" (literal {q(binary)}))",
        '(allow file-read* (literal "/dev/null"))',
        '(allow file-write-data (literal "/dev/null"))',
        '(allow sysctl-read (sysctl-name "hw.pagesize"))',
    ]
    if fixture:
        rules.append(f"(allow file-read* file-map-executable (subpath {q(binary.parent.parent)}))")
    # Counterprofile additions exist only for internally minted invented controls.
    if control is not None:
        require(fixture and type(control) is tuple, "invented-counterprofile")
        kind, path = control
        if kind == "read":
            rules.append(f"(allow file-read* (literal {q(path)}))")
        elif kind == "write":
            rules.append(f"(allow file-write* (literal {q(path)}))")
        elif kind == "fork":
            rules.append("(allow process-fork)")
        elif kind == "exec":
            rules.append(f"(allow process-exec (literal {q(path)}))")
            rules.append(f"(allow file-read* file-map-executable (literal {q(path)}))")
        elif kind == "sysctl-baseline":
            require(path is None, "fixed-baseline-control")
            rules.remove('(allow sysctl-read (sysctl-name "hw.pagesize"))')
        elif kind == "sysctl-neighbor":
            require(path is None, "fixed-neighbor-control")
            rules.append('(allow sysctl-read (sysctl-name "hw.ncpu"))')
        elif kind == "network":
            require(type(path) is int and 0 < path < 65536, "invented-loopback-port")
            rules.append(f'(allow network-outbound (remote ip "localhost:{path}"))')
        else:
            raise ValueError("fixed-control-kind")
    return "\n".join(rules) + "\n"


def _gate(
    plan_raw, approval_raw, origin_raw, held, fixture=False, headroom=False, historical_at=None
):
    fields(
        held,
        (
            "plan_sha256 approval_sha256 origin_sha256 source_sha256 owne"
            "r_sha256 rights_basis_sha256 profile_sha256 binary_identity_"
            "sha256 output_root"
        ),
        "held-fields",
    )
    for name, raw in (("plan", plan_raw), ("approval", approval_raw), ("origin", origin_raw)):
        require(
            type(raw) is bytes and 0 < len(raw) <= 32768 and digest(raw) == held[name + "_sha256"],
            "held-document",
        )
    plan, approval, origin = map(decode, (plan_raw, approval_raw, origin_raw))
    fields(
        plan,
        (
            "schema kind binary expected_version limits source owner OS_p"
            "olicy profile_sha256 rights_basis_sha256 qualification_sha25"
            "6 origin_sha256 output_root parent_identity retention contex"
            "t"
        ),
        "plan-fields",
    )
    require(
        plan["schema"] == SCHEMA
        and plan["kind"] == ("invented" if fixture else "private-startup-probe-plan"),
        "plan-kind",
    )
    fields(plan["binary"], "path bytes sha256 token parent_path parent_identity", "binary-fields")
    binary = plan["binary"]
    path = _path(binary["path"])
    require(
        _path(binary["parent_path"]) == path.parent
        and type(binary["bytes"]) is int
        and 0 < binary["bytes"] <= LIMITS["binary_max_bytes"]
        and type(binary["sha256"]) is str
        and core.HEX.fullmatch(binary["sha256"]),
        "binary-typed-identity",
    )
    token = binary["token"]
    require(
        type(token) is list
        and len(token) == 9
        and all(type(v) is int for v in token)
        and token[4] == 1
        and token[5] == binary["bytes"],
        "binary-token",
    )
    for identity in (plan["parent_identity"], binary["parent_identity"]):
        fields(identity, "dev ino uid mode", "physical-parent-fields")
        require(all(type(v) is int for v in identity.values()), "typed-parent")
    require(
        digest(encode(binary)) == held["binary_identity_sha256"]
        and type(plan["expected_version"]) is str
        and re.fullmatch(r"[0-9A-Za-z.+_-]{1,64}", plan["expected_version"]),
        "held-binary-version",
    )
    output = _path(plan["output_root"])
    require(
        str(output) == held["output_root"]
        and output.name == ("invented-gh-probe" if fixture else "proposed-gh-startup-probe")
        and plan["parent_identity"]["uid"] == os.getuid()
        and plan["parent_identity"]["mode"] == 0o700,
        "fixed-private-output",
    )
    require(
        plan["context"]
        == {
            "cwd_role": "home",
            "empty_directories": [
                ".environment",
                ".environment/home",
                ".environment/config",
                ".environment/cache",
                ".environment/tmp",
            ],
            "writes_allowed": False,
        },
        "fixed-environment-shape",
    )
    if fixture:
        require(path == output.parent / "invented-binary.bin", "fixed-fixture-binary")
    require(
        encode(plan["limits"]) == encode(LIMITS)
        and plan["origin_sha256"] == held["origin_sha256"]
        and plan["rights_basis_sha256"] == held["rights_basis_sha256"],
        "scope-pins-limits",
    )
    for key in ("rights_basis_sha256", "qualification_sha256"):
        require(type(plan[key]) is str and core.HEX.fullmatch(plan[key]), "required-policy-pin")
    now = core._now() if historical_at is None else historical_at
    retention_end = _retention(plan["retention"])
    fields(
        origin,
        (
            "schema kind recorded_new_fact_utc not_after_UTC retention ol"
            "d_origins_reset unknown_older_origins_timely_claimed evidenc"
            "e_sha256"
        ),
        "origin-fields",
    )
    require(
        origin["schema"] == SCHEMA
        and origin["kind"] == ("invented" if fixture else "private-new-probe-context")
        and encode(origin["retention"]) == encode(plan["retention"])
        and origin["old_origins_reset"] is False
        and origin["unknown_older_origins_timely_claimed"] is False
        and type(origin["evidence_sha256"]) is str
        and core.HEX.fullmatch(origin["evidence_sha256"]),
        "new-fact-origin-only",
    )
    first, end = core._utc(origin["recorded_new_fact_utc"]), core._utc(origin["not_after_UTC"])
    require(first <= now < end <= first + timedelta(days=30), "origin-window")
    fields(
        approval,
        (
            "schema kind plan_sha256 origin_sha256 source_sha256 owner_sh"
            "a256 rights_basis_sha256 profile_sha256 binary_identity_sha2"
            "56 nonce issued_utc expires_utc scope authority"
        ),
        "approval-fields",
    )
    require(
        approval["schema"] == SCHEMA
        and approval["kind"] == ("invented" if fixture else "private-one-shot-approval")
        and all(
            approval[k] == held[k]
            for k in (
                "plan_sha256",
                "origin_sha256",
                "source_sha256",
                "owner_sha256",
                "rights_basis_sha256",
                "profile_sha256",
                "binary_identity_sha256",
            )
        )
        and type(approval["nonce"]) is str
        and re.fullmatch(r"[0-9a-f]{32}", approval["nonce"])
        and approval["scope"] == "one-binary-hash-and-two-startup-help-probes"
        and encode(approval["authority"]) == encode(AUTHORITY),
        "exact-limited-approval",
    )
    issued, expires = core._utc(approval["issued_utc"]), core._utc(approval["expires_utc"])
    expiry = min(expires, end, retention_end)
    read_expiry = expiry if historical_at is None else min(end, retention_end)
    require(
        issued <= now < expires <= issued + timedelta(hours=1)
        and core._now() < read_expiry
        and (not headroom or (expiry - now).total_seconds() >= 80),
        "current-window-headroom",
    )
    require(
        plan["source"] == _identity(read_expiry)
        and plan["owner"] == _owner(read_expiry)
        and digest(encode(plan["source"])) == held["source_sha256"]
        and digest(encode(plan["owner"])) == held["owner_sha256"],
        "current-source-owner",
    )
    require(
        plan["OS_policy"] == _policy_identity(read_expiry)
        and digest(_profile(plan, fixture).encode())
        == plan["profile_sha256"]
        == held["profile_sha256"],
        "current-fixed-OS-profile",
    )
    require(core._now() < read_expiry, "late-source-window")
    return plan, expiry


def _source_hash(path, expiry=None):
    if expiry is not None:
        require(core._now() < expiry, "source-read-before-expiry")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        named_before = Path(path).lstat()
        require(core._fingerprint(before) == core._fingerprint(named_before), "source-before-name")
        require(
            stat.S_ISREG(before.st_mode) and before.st_size <= 1048576, "bounded-regular-source"
        )
        raw = bytearray()
        while len(raw) <= before.st_size:
            if expiry is not None:
                require(core._now() < expiry, "source-chunk-before-expiry")
            part = os.read(fd, min(65536, before.st_size + 1 - len(raw)))
            if not part:
                break
            raw += part
        require(
            len(raw) == before.st_size
            and core._fingerprint(before)
            == core._fingerprint(os.fstat(fd))
            == core._fingerprint(Path(path).lstat())
            and (expiry is None or core._now() < expiry),
            "stable-source-snapshot",
        )
        return digest(bytes(raw))
    finally:
        os.close(fd)


def _parent_identity(fd):
    info = os.fstat(fd)
    return {
        "dev": info.st_dev,
        "ino": info.st_ino,
        "uid": info.st_uid,
        "mode": stat.S_IMODE(info.st_mode),
    }


def _live(expiry, deadline):
    require(core._now() < expiry and time.monotonic() < deadline, "current-deadline")


def _frames(stream, events, maximum=33024):
    try:
        for _ in range(FRAME_LIMIT):
            raw = stream.readline(maximum + 1)
            require(len(raw) <= maximum, "ipc-frame-cap")
            if not raw:
                events.put(("eof", None), timeout=0.1)
                return
            require(raw.endswith(b"\n"), "ipc-line")
            events.put(("frame", decode(raw)), timeout=0.1)
        events.put(("error", None), timeout=0.1)
    except (OSError, ValueError, queue.Full):
        try:
            events.put_nowait(("error", None))
        except queue.Full:
            pass


def _send(stream, raw, result):
    try:
        stream.write(raw)
        stream.close()
        result.append(True)
    except OSError:
        result.append(False)


def _stop(process, reader, writer, owned, deadline):
    errors = []
    forced = process.poll() is None
    try:
        if forced:
            if owned:
                platform_process.force_tree(process)
            else:
                process.kill()
        process.wait(timeout=max(0.001, min(0.5, deadline - time.monotonic())))
    except (OSError, subprocess.TimeoutExpired):
        errors.append("owned-stop")
    for worker in (reader, writer):
        if worker is not None and worker.ident is not None:
            try:
                worker.join(timeout=max(0, min(0.5, deadline - time.monotonic())))
                if worker.is_alive():
                    errors.append("io-not-joined")
            except RuntimeError:
                errors.append("io-join-failed")
    if reader is None or not reader.is_alive():
        try:
            process.stdout.close()
        except OSError:
            errors.append("pipe-close")
    if owned:
        try:
            if platform_process.tree_exists(process):
                forced = True
                platform_process.force_tree(process)
                process.wait(timeout=max(0.001, min(0.5, deadline - time.monotonic())))
        except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired):
            errors.append("owned-tree-stop-error")
        try:
            while platform_process.tree_exists(process) and time.monotonic() < deadline:
                time.sleep(min(0.005, max(0, deadline - time.monotonic())))
            require(not platform_process.tree_exists(process), "owned-tree-stop")
        except (OSError, RuntimeError, ValueError):
            errors.append("owned-tree-unconfirmed")
        try:
            platform_process.close_tree(process)
        except (OSError, RuntimeError, ValueError):
            errors.append("owned-close-error")
    if writer is None or not writer.is_alive():
        try:
            if getattr(process, "stdin", None) is not None:
                process.stdin.close()
        except OSError:
            errors.append("input-pipe-close")
    require(not errors, "owned-cleanup-failed")
    return forced


def _io_threads(process, raw, events, writers):
    return (
        threading.Thread(target=_frames, args=(process.stdout, events), daemon=True),
        threading.Thread(target=_send, args=(process.stdin, raw, writers), daemon=True),
    )


def _supervise(wire, deadline):
    environment = core._environment()
    if wire["fixture"] and "OT062_FIXTURE_FORBIDDEN_PATHS" in os.environ:
        environment["OT062_FIXTURE_FORBIDDEN_PATHS"] = os.environ["OT062_FIXTURE_FORBIDDEN_PATHS"]
    events, writers = queue.Queue(maxsize=8), []
    reader = writer = None
    receipt = None
    clean = False
    started = []
    active = None
    stop_deadline = deadline
    process = platform_process.spawn(
        [sys.executable, "-I", "-S", "-B", "-c", _script("_entry;_entry()")],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        cwd=ROOT,
        env=environment,
    )
    try:
        reader, writer = _io_threads(process, encode(wire), events, writers)
        reader.start()
        writer.start()
        while time.monotonic() < wire["deadline"]:
            active_read = (
                active[1] - min(1, wire["probe_seconds"] / 6) if active else wire["deadline"]
            )
            wait_end = min(wire["deadline"], active_read)
            if time.monotonic() >= wait_end:
                break
            try:
                kind, frame = events.get(timeout=max(0.001, wait_end - time.monotonic()))
            except queue.Empty:
                break
            if kind == "eof":
                process.wait(timeout=max(0.001, wait_end - time.monotonic()))
                clean = process.returncode == 0 and writers == [True] and active is None
                break
            require(kind == "frame" and type(frame) is dict, "fixed-control-frame")
            if set(frame) == {"probe_start", "deadline"}:
                require(
                    receipt is None
                    and active is None
                    and len(started) < 2
                    and frame["probe_start"] == ("version", "help")[len(started)]
                    and type(frame["deadline"]) in (int, float)
                    and time.monotonic()
                    < frame["deadline"]
                    <= time.monotonic() + wire["probe_seconds"]
                    and frame["deadline"] <= wire["deadline"],
                    "ordered-fixed-probe-start",
                )
                started.append(frame["probe_start"])
                active = (frame["probe_start"], frame["deadline"])
                stop_deadline = min(deadline, active[1])
            elif set(frame) == {"probe_end"}:
                require(
                    active is not None
                    and frame["probe_end"] == active[0]
                    and time.monotonic() < active[1],
                    "ordered-fixed-probe-end",
                )
                active = None
                stop_deadline = deadline
            elif set(frame) == {"receipt"}:
                require(
                    receipt is None and active is None and len(started) > 0,
                    "single-postprobe-receipt",
                )
                receipt = frame["receipt"]
            else:
                receipt = None
                break
    finally:
        forced = _stop(process, reader, writer, True, stop_deadline)
    if forced or not clean:
        return None
    require(
        type(receipt) is dict
        and type(receipt.get("probes")) is list
        and [row.get("role") for row in receipt["probes"] if type(row) is dict] == started,
        "receipt-matches-observed-dispatch-prefix",
    )
    return receipt


def _script(call):
    return (
        "import sys;sys.path.insert(0,"
        + repr(str(ROOT))
        + ");from experiments.simglucose_audit.gh_verifier_probe import "
        + call
    )


def _namespace(directory, plan, context=None):
    parent = core._directory(str(Path(plan["output_root"]).parent))
    try:
        require(_parent_identity(parent) == plan["parent_identity"], "output-parent-binding")
        named = os.stat(Path(plan["output_root"]).name, dir_fd=parent, follow_symlinks=False)
        opened = os.fstat(directory)
        require(
            stat.S_ISDIR(named.st_mode) and _token(named)[:4] == _token(opened)[:4],
            "output-root-binding",
        )
        core._private_directory(directory)
        require(
            set(os.listdir(directory))
            <= {".environment", "report.private.json", "receipt.private.json"},
            "fixed-root-membership",
        )
        observed = {}
        environment = os.open(
            ".environment", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory
        )
        try:
            core._private_directory(environment)
            observed[".environment"] = _token(os.fstat(environment))
            require(
                _token(os.fstat(environment))
                == _token(os.stat(".environment", dir_fd=directory, follow_symlinks=False)),
                "named-environment",
            )
            require(
                set(os.listdir(environment)) == {"home", "config", "cache", "tmp"},
                "fixed-environment-membership",
            )
            for name in ("home", "config", "cache", "tmp"):
                fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=environment)
                try:
                    core._private_directory(fd)
                    observed[".environment/" + name] = _token(os.fstat(fd))
                    require(
                        _token(os.fstat(fd))
                        == _token(os.stat(name, dir_fd=environment, follow_symlinks=False)),
                        "named-context-leaf",
                    )
                    require(not os.listdir(fd), "empty-environment")
                finally:
                    os.close(fd)
            require(
                _token(os.fstat(environment))
                == _token(os.stat(".environment", dir_fd=directory, follow_symlinks=False)),
                "late-environment-name",
            )
        finally:
            os.close(environment)
        require(context is None or observed == context, "stable-allocated-context")
        return observed
    finally:
        os.close(parent)


def _binary_context(plan, expiry, deadline, fd=None):
    _live(expiry, deadline)
    binary = plan["binary"]
    path = Path(binary["path"])
    parent = _binary_directory(str(path.parent))
    try:
        require(_parent_identity(parent) == binary["parent_identity"], "binary-parent-binding")
        named = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        require(
            stat.S_ISREG(named.st_mode) and _token(named) == binary["token"], "binary-named-token"
        )
        if fd is not None:
            require(_token(os.fstat(fd)) == binary["token"], "binary-held-FD-token")
    finally:
        os.close(parent)


def _hash_binary(plan, expiry, deadline):
    _binary_context(plan, expiry, deadline)
    binary = plan["binary"]
    _live(expiry, deadline)
    fd = os.open(binary["path"], os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    try:
        _binary_context(plan, expiry, deadline, fd)
        count = 0
        hasher = hashlib.sha256()
        while count < binary["bytes"] + 1:
            _live(expiry, deadline)
            part = os.read(fd, min(65536, binary["bytes"] + 1 - count))
            if not part:
                break
            count += len(part)
            require(count <= binary["bytes"], "binary-overflow-sentinel")
            hasher.update(part)
        _live(expiry, deadline)
        _binary_context(plan, expiry, deadline, fd)
        require(
            count == binary["bytes"] and hasher.hexdigest() == binary["sha256"],
            "fresh-binary-size-hash",
        )
        return fd, {
            "bytes": count,
            "sha256": hasher.hexdigest(),
            "body_passes": 1,
            "OS_exec_mapping_library_IO_included": False,
        }
    except BaseException:
        os.close(fd)
        raise


def _consume(plan, held, expiry, deadline):
    parent = core._directory(str(Path(plan["output_root"]).parent))
    try:
        require(_parent_identity(parent) == plan["parent_identity"], "marker-parent-binding")
        raw = encode({"approval_sha256": held["approval_sha256"], "kind": "GHprobe"})
        require(len(raw) <= 128, "marker-cap")
        previous._write_checked(
            parent, ".gh-probe-consumed-" + held["approval_sha256"], raw, expiry, deadline
        )
    finally:
        os.close(parent)


def _allocate(plan, expiry, deadline):
    _live(expiry, deadline)
    path = Path(plan["output_root"])
    require(not path.exists() and not path.is_symlink(), "fresh-absent-output")
    parent = core._directory(str(path.parent))
    try:
        require(_parent_identity(parent) == plan["parent_identity"], "allocation-parent-binding")
        os.mkdir(path.name, 0o700, dir_fd=parent)
        _live(expiry, deadline)
        os.fsync(parent)
        directory = os.open(path.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
    finally:
        os.close(parent)
    try:
        os.mkdir(".environment", 0o700, dir_fd=directory)
        environment = os.open(
            ".environment", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory
        )
        try:
            for name in ("home", "config", "cache", "tmp"):
                _live(expiry, deadline)
                os.mkdir(name, 0o700, dir_fd=environment)
            _live(expiry, deadline)
            os.fsync(environment)
        finally:
            os.close(environment)
        _live(expiry, deadline)
        os.fsync(directory)
        _namespace(directory, plan)
        return directory
    except BaseException:
        os.close(directory)
        raise


def _environment(plan):
    base = Path(plan["output_root"]) / ".environment"
    return {
        "PATH": "/usr/bin:/bin",
        "HOME": str(base / "home"),
        "XDG_CONFIG_HOME": str(base / "config"),
        "XDG_CACHE_HOME": str(base / "cache"),
        "TMPDIR": str(base / "tmp"),
        "GH_CONFIG_DIR": str(base / "config"),
        "GH_NO_UPDATE_NOTIFIER": "1",
        "GH_NO_EXTENSION_UPDATE_NOTIFIER": "1",
        "GH_PROMPT_DISABLED": "1",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "LANG": "C",
        "LC_ALL": "C",
    }


STANDIN_CODE = """import os,subprocess,sys,time
role,case,version=sys.argv[1:]
if case=="probe-stall":time.sleep(30)
if case=="fullpipe":
 while True:os.write(1,b"x"*65536)
if case=="drip":
 for _ in range(200):os.write(1,b"x");time.sleep(0.05)
if case=="exit-survivor":
 subprocess.Popen([sys.executable,"-I","-S","-B","-c",
                   "import time;time.sleep(30)"])
if case=="nonzero":sys.exit(7)
if case=="stdout-overflow":os.write(1,b"x"*9000);sys.exit(0)
if case=="stderr-overflow":os.write(2,b"x"*9000);sys.exit(0)
if case=="invalidUTF8":os.write(1,b"\\xff");sys.exit(0)
if role=="version":print("gh version "+("invented-wrong"if case=="version-mismatch"else version))
else:
 text=("--bundle --custom-trusted-root --cert-identity --cert-oidc-issuer "
       "--signer-workflow --predicate-type --deny-self-hosted-runners")
 if case=="help-prefix-only":text=text.replace("--cert-identity ","--cert-identity-regex ")
 print("invented help"if case=="help-mismatch"else text)
"""


def _run_probe(plan, role, expiry, whole_deadline, fixture=False, case=None, probe_seconds=10):
    index = ("version", "help").index(role)
    argv = (
        [sys.executable, "-I", "-S", "-B", "-c", STANDIN_CODE, role, case, plan["expected_version"]]
        if fixture
        else [str(SANDBOX), "-p", _profile(plan), plan["binary"]["path"], *ARGVS[index]]
    )
    _live(expiry, whole_deadline)
    probe_end = min(whole_deadline, time.monotonic() + probe_seconds)
    deadline = probe_end - min(2, probe_seconds / 3)
    selector = None
    streams = {"stdout": bytearray(), "stderr": bytearray()}
    consumed = {"stdout": 0, "stderr": 0}
    error = None
    _emit({"probe_start": role, "deadline": probe_end})
    if fixture and case == "spawn-stall":
        time.sleep(30)
    process = subprocess.Popen(
        argv,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=Path(plan["output_root"]) / ".environment/home",
        env=_environment(plan),
        close_fds=True,
    )
    try:
        selector = selectors.DefaultSelector()
        for name, stream in (("stdout", process.stdout), ("stderr", process.stderr)):
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, name)
        while selector.get_map():
            _live(expiry, deadline)
            for key, _mask in selector.select(
                timeout=max(0, min(0.05, deadline - time.monotonic()))
            ):
                name = key.data
                remaining = 8193 - consumed[name]
                require(remaining > 0, "pipe-sentinel-budget")
                part = os.read(key.fileobj.fileno(), min(4096, remaining))
                if not part:
                    selector.unregister(key.fileobj)
                    continue
                consumed[name] += len(part)
                streams[name] += part[: max(0, 8192 - len(streams[name]))]
                if consumed[name] > 8192:
                    raise ValueError("probe-output-overflow")
        _live(expiry, deadline)
        process.wait(timeout=max(0.001, deadline - time.monotonic()))
    except (OSError, ValueError, subprocess.TimeoutExpired):
        error = "probe-refused-or-timeout"
    finally:
        cleanup = []
        if selector is not None:
            try:
                selector.close()
            except OSError:
                cleanup.append("selector-close")
        if process.poll() is None:
            error = error or "probe-forced-stop"
            try:
                process.kill()
            except OSError:
                cleanup.append("leaf-stop")
        try:
            process.wait(timeout=max(0.001, probe_end - time.monotonic()))
        except (OSError, subprocess.TimeoutExpired):
            cleanup.append("leaf-wait")
        for stream in (process.stdout, process.stderr):
            try:
                stream.close()
            except OSError:
                cleanup.append("leaf-pipe-close")
        require(not cleanup and time.monotonic() < probe_end, "probe-cleanup-unconfirmed")
    stdout, stderr = (bytes(streams[n]) for n in ("stdout", "stderr"))
    version_ok = False
    markers = []
    try:
        text = stdout.decode("utf-8", "strict")
        if role == "version":
            version_ok = text.startswith(
                "gh version " + plan["expected_version"] + "\n"
            ) or text.startswith("gh version " + plan["expected_version"] + " (")
        else:
            markers = [
                marker
                for marker in HELP_MARKERS
                if re.search(r"(?<![A-Za-z0-9_-])" + re.escape(marker) + r"(?=[\s=,]|$)", text)
            ]
    except UnicodeError:
        error = error or "probe-invalid-UTF8"
    accepted = (
        error is None
        and process.returncode == 0
        and not stderr
        and (version_ok if role == "version" else markers == list(HELP_MARKERS))
    )
    result = {
        "role": role,
        "status": "accepted" if accepted else "rejected",
        "exit_code": process.returncode,
        "error": error,
        "consumed_application_bytes": consumed,
        "stored_bytes": {n: len(streams[n]) for n in streams},
        "stored_sha256": {n: digest(bytes(streams[n])) for n in streams},
        "raw_base64": {n: base64.b64encode(bytes(streams[n])).decode() for n in streams},
        "parsed": {"version_matches": version_ok, "observed_help_markers": markers},
        "real_selected_tool_invocation": not fixture,
        "real_crypto_or_artifact_verification": False,
    }
    _live(expiry, probe_end)
    _emit({"probe_end": role})
    return result


def _wire_inputs(wire, headroom=False):
    return _gate(
        *(base64.b64decode(wire[n], validate=True) for n in ("plan", "approval", "origin")),
        wire["held"],
        wire["fixture"],
        headroom,
    )


def _emit(value):
    raw = encode(value)
    require(len(raw) <= 33024, "metadata-frame-cap")
    sys.stdout.buffer.write(raw + b"\n")
    sys.stdout.buffer.flush()


def _produce(wire):
    plan, expiry = _wire_inputs(wire, True)
    deadline = wire["deadline"]
    output = Path(plan["output_root"])
    require(not output.exists() and not output.is_symlink(), "fresh-output-before-binary")
    _consume(plan, wire["held"], expiry, deadline)
    if wire["fixture"] and wire["case"] == "hash-stall":
        time.sleep(30)
    binary, observation = _hash_binary(plan, expiry, deadline)
    directory = None
    try:
        directory = _allocate(plan, expiry, deadline)
        context = _namespace(directory, plan)
        rows = []
        for role in ("version", "help"):
            _live(expiry, deadline)
            _binary_context(plan, expiry, deadline, binary)
            _namespace(directory, plan, context)
            _wire_inputs(wire)
            row = _run_probe(
                plan, role, expiry, deadline, wire["fixture"], wire["case"], wire["probe_seconds"]
            )
            rows.append(row)
            _binary_context(plan, expiry, deadline, binary)
            _namespace(directory, plan, context)
            _wire_inputs(wire)
            if row["status"] != "accepted":
                break
        complete = len(rows) == 2 and all(row["status"] == "accepted" for row in rows)
        report = {
            "schema": SCHEMA,
            "kind": "private-startup-output-report",
            "pins": wire["held"],
            "binary_hash_observation": observation,
            "probes": rows,
            "fixture_only": wire["fixture"],
            "authentication_or_runtime_admission": False,
        }
        raw = encode(report)
        require(len(raw) <= 65536, "report-representation-cap")
        _live(expiry, deadline)
        _write_output(directory, raw, expiry, deadline, wire["case"] if wire["fixture"] else None)
        _binary_context(plan, expiry, deadline, binary)
        _namespace(directory, plan, context)
        _wire_inputs(wire)
        receipt = {
            "schema": SCHEMA,
            "kind": "invented" if wire["fixture"] else "startup-probe-receipt",
            "status": "completed" if complete else "rejected",
            "pins": wire["held"],
            "binary_hash_observation": observation,
            "environment_identities": context,
            "probes": [{k: v for k, v in row.items() if k != "raw_base64"} for row in rows],
            "report_sha256": digest(raw),
            "report_bytes": len(raw),
            "report_readback_passes": 0,
            "raw_outputs_in_receipt": False,
            "ended_utc": core._stamp(core._now()),
            "authority": dict(AUTHORITY),
            "retention": plan["retention"],
        }
        encoded = encode(receipt)
        require(len(encoded) <= 32768, "receipt-cap")
        if wire["fixture"] and wire["case"] == "finalize-stall":
            time.sleep(30)
        _live(expiry, deadline)
        previous._write_checked(directory, "receipt.private.json", encoded, expiry, deadline)
        _binary_context(plan, expiry, deadline, binary)
        _namespace(directory, plan, context)
        _wire_inputs(wire)
        _live(expiry, deadline)
        _emit({"receipt": receipt})
    finally:
        if directory is not None:
            os.close(directory)
        os.close(binary)


def _entry():
    try:
        raw = sys.stdin.buffer.read(131073)
        require(len(raw) <= 131072, "worker-wire-cap")
        wire = decode(raw)
        fields(
            wire,
            "plan approval origin held fixture case deadline probe_seconds",
            "fixed-worker-wire",
        )
        require(
            type(wire["fixture"]) is bool
            and (wire["case"] in CASES if wire["fixture"] else wire["case"] is None),
            "fixed-worker-mode",
        )
        require(
            type(wire["probe_seconds"]) in (int, float) and 0 < wire["probe_seconds"] <= 10,
            "fixed-probe-time",
        )
        if wire["fixture"]:
            forbidden = decode(os.environ.get("OT062_FIXTURE_FORBIDDEN_PATHS", "[]").encode())

            def deny(event, args):
                if event in ("socket.connect", "socket.getaddrinfo"):
                    raise PermissionError("fixture-network-denied")
                if (
                    event == "open"
                    and args
                    and isinstance(args[0], (str, bytes))
                    and os.fsdecode(args[0]) in forbidden
                ):
                    raise PermissionError("actual-material-denied")

            sys.addaudithook(deny)
        _produce(wire)
        if wire["fixture"] and wire["case"] == "receipt-then-error":
            _emit({"error": "invented-late-protocol-error"})
        if wire["fixture"] and wire["case"] == "receipt-then-nonzero":
            raise SystemExit(7)
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired):
        _emit({"error": "probe-worker-rejected"})


def _validate_receipt(receipt, plan, held, fixture, issued, expiry):
    fields(
        receipt,
        (
            "schema kind status pins binary_hash_observation environment_identities probes repor"
            "t_sha256 report_bytes report_readback_passes raw_outputs_in_"
            "receipt ended_utc authority retention"
        ),
        "receipt-fields",
    )
    require(
        receipt["schema"] == SCHEMA
        and receipt["kind"] == ("invented" if fixture else "startup-probe-receipt")
        and receipt["pins"] == held
        and encode(receipt["authority"]) == encode(AUTHORITY)
        and encode(receipt["retention"]) == encode(plan["retention"]),
        "receipt-bindings-authority",
    )
    fields(
        receipt["binary_hash_observation"],
        "bytes sha256 body_passes OS_exec_mapping_library_IO_included",
        "binary-hash-observation",
    )
    identities = receipt["environment_identities"]
    fields(
        identities,
        ".environment .environment/home .environment/config .environment/cache .environment/tmp",
        "environment-identities",
    )
    for token in identities.values():
        require(
            type(token) is list
            and len(token) == 9
            and all(type(v) is int for v in token)
            and token[2] == os.getuid()
            and token[3] == 0o700,
            "private-context-token",
        )
    observed = receipt["binary_hash_observation"]
    require(
        type(observed["bytes"]) is int
        and observed["bytes"] == plan["binary"]["bytes"]
        and observed["sha256"] == plan["binary"]["sha256"]
        and type(observed["body_passes"]) is int
        and observed["body_passes"] == 1
        and observed["OS_exec_mapping_library_IO_included"] is False,
        "one-bound-binary-pass",
    )
    require(
        type(receipt["report_sha256"]) is str
        and core.HEX.fullmatch(receipt["report_sha256"])
        and type(receipt["report_bytes"]) is int
        and 0 < receipt["report_bytes"] <= 65536
        and type(receipt["report_readback_passes"]) is int
        and receipt["report_readback_passes"] == 0
        and receipt["raw_outputs_in_receipt"] is False,
        "bounded-no-raw-receipt",
    )
    rows = receipt["probes"]
    require(type(rows) is list and 1 <= len(rows) <= 2, "ordered-probe-prefix")
    for i, row in enumerate(rows):
        fields(
            row,
            (
                "role status exit_code error consumed_application_bytes store"
                "d_bytes stored_sha256 parsed real_selected_tool_invocation r"
                "eal_crypto_or_artifact_verification"
            ),
            "probe-observation-fields",
        )
        require(
            row["role"] == ("version", "help")[i]
            and row["status"] in ("accepted", "rejected")
            and type(row["exit_code"]) is int
            and row["error"]
            in (None, "probe-refused-or-timeout", "probe-forced-stop", "probe-invalid-UTF8")
            and row["real_selected_tool_invocation"] is (not fixture)
            and row["real_crypto_or_artifact_verification"] is False,
            "probe-scope-types",
        )
        for key in ("consumed_application_bytes", "stored_bytes", "stored_sha256"):
            fields(row[key], "stdout stderr", "two-streams")
        for stream in ("stdout", "stderr"):
            consumed, stored = (
                row["consumed_application_bytes"][stream],
                row["stored_bytes"][stream],
            )
            require(
                type(consumed) is int
                and 0 <= consumed <= 8193
                and type(stored) is int
                and stored == min(consumed, 8192)
                and type(row["stored_sha256"][stream]) is str
                and core.HEX.fullmatch(row["stored_sha256"][stream]),
                "stream-caps",
            )
            if stored == 0:
                require(row["stored_sha256"][stream] == digest(b""), "empty-stream-hash")
        fields(row["parsed"], "version_matches observed_help_markers", "parsed-observations")
        parsed = row["parsed"]
        require(
            type(parsed["version_matches"]) is bool
            and type(parsed["observed_help_markers"]) is list
            and parsed["observed_help_markers"]
            == [v for v in HELP_MARKERS if v in parsed["observed_help_markers"]],
            "parsed-marker-subset",
        )
        require(
            not parsed["observed_help_markers"] if i == 0 else parsed["version_matches"] is False,
            "role-specific-parser",
        )
        required_stdout = (
            len(("gh version " + plan["expected_version"] + "\n").encode())
            if i == 0
            else sum(len(marker) for marker in HELP_MARKERS) + len(HELP_MARKERS) - 1
        )
        require(
            row["status"] != "accepted" or row["stored_bytes"]["stdout"] >= required_stdout,
            "parsed-output-minimum-size",
        )
        accepted = (
            row["error"] is None
            and row["exit_code"] == 0
            and row["stored_bytes"]["stderr"] == 0
            and all(v <= 8192 for v in row["consumed_application_bytes"].values())
            and (
                parsed["version_matches"]
                if i == 0
                else parsed["observed_help_markers"] == list(HELP_MARKERS)
            )
        )
        require((row["status"] == "accepted") == accepted, "observed-status-reconstruction")
        require(row["status"] == "accepted" or i == len(rows) - 1, "stop-after-first-rejection")
    complete = len(rows) == 2 and all(row["status"] == "accepted" for row in rows)
    require(
        receipt["status"] == ("completed" if complete else "rejected")
        and (complete or rows[-1]["status"] == "rejected"),
        "receipt-status-reconstruction",
    )
    require(
        issued <= core._utc(receipt["ended_utc"]) < expiry
        and core._utc(receipt["ended_utc"]) <= core._now(),
        "historical-execution-window",
    )


def _execute(
    plan_raw,
    approval_raw,
    origin_raw,
    held,
    fixture=False,
    case=None,
    whole_seconds=60,
    probe_seconds=10,
):
    start = time.monotonic()
    deadline = start + whole_seconds
    plan, expiry = _gate(plan_raw, approval_raw, origin_raw, held, fixture, True)
    output = Path(plan["output_root"])
    require(not output.exists() and not output.is_symlink(), "preflight-absent-output")
    _live(expiry, deadline)
    wire = {
        key: base64.b64encode(raw).decode()
        for key, raw in (("plan", plan_raw), ("approval", approval_raw), ("origin", origin_raw))
    }
    wire.update(
        held=held,
        fixture=fixture,
        case=case,
        deadline=deadline - min(3, whole_seconds / 3),
        probe_seconds=probe_seconds,
    )
    result = _supervise(wire, deadline)
    _live(expiry, deadline)
    _gate(plan_raw, approval_raw, origin_raw, held, fixture)
    if result is None:
        return {
            "schema": SCHEMA,
            "status": "incomplete",
            "error": "owned-worker-failure",
            "authority": dict(AUTHORITY),
        }
    require(len(encode(result)) <= 32768, "metadata-return-cap")
    _validate_receipt(
        result, plan, held, fixture, core._utc(decode(approval_raw)["issued_utc"]), expiry
    )
    _live(expiry, deadline)
    return result


def probe_approved(plan_raw, approval_raw, origin_raw, held):
    """Trusted caller only; fixed external consent/qualified snapshot are mandatory."""
    return _execute(plan_raw, approval_raw, origin_raw, held)


def _fixture_key(inputs):
    require(
        type(inputs) is tuple
        and len(inputs) == 4
        and all(type(raw) is bytes for raw in inputs[:3])
        and type(inputs[3]) is dict,
        "minted-fixture-tuple",
    )
    return digest(
        b"".join(len(raw).to_bytes(4, "big") + raw for raw in (*inputs[:3], encode(inputs[3])))
    )


def fixture_inputs(parent):
    parent = Path(parent)
    fd = core._directory(str(parent))
    try:
        with os.scandir(fd) as entries:
            require(next(entries, None) is None, "fresh-empty-owned-fixture-parent")
        parent_identity = _parent_identity(fd)
        raw = b"INVENTED nonexecutable candidate bytes, never a real tool.\n"
        previous._write_checked(
            fd,
            "invented-binary.bin",
            raw,
            core._now() + timedelta(seconds=20),
            time.monotonic() + 10,
        )
    finally:
        os.close(fd)
    candidate = parent / "invented-binary.bin"
    now = core._now()
    end = now + timedelta(days=1)
    retention = {
        "max_days_new_facts": 30,
        "not_after_UTC": core._stamp(end),
        "earlier_limits_win": True,
        "old_origins_reset": False,
        "unknown_older_origins_timely_claimed": False,
        "automatic_cleanup_or_extension": False,
    }
    source, owner = _identity(), _owner()
    origin = {
        "schema": SCHEMA,
        "kind": "invented",
        "recorded_new_fact_utc": core._stamp(now),
        "not_after_UTC": core._stamp(end),
        "retention": retention,
        "old_origins_reset": False,
        "unknown_older_origins_timely_claimed": False,
        "evidence_sha256": digest(b"INVENTED fresh proposal"),
    }
    origin_raw = encode(origin)
    binary = {
        "path": str(candidate),
        "bytes": len(raw),
        "sha256": digest(raw),
        "token": _token(candidate.lstat()),
        "parent_path": str(parent),
        "parent_identity": parent_identity,
    }
    plan = {
        "schema": SCHEMA,
        "kind": "invented",
        "binary": binary,
        "expected_version": "0.0.0-invented",
        "limits": dict(LIMITS),
        "source": source,
        "owner": owner,
        "OS_policy": _policy_identity(),
        "profile_sha256": "pending",
        "rights_basis_sha256": digest(b"INVENTED probe-only rights"),
        "qualification_sha256": digest(b"INVENTED only, not actual OS admission"),
        "origin_sha256": digest(origin_raw),
        "output_root": str(parent / "invented-gh-probe"),
        "parent_identity": parent_identity,
        "retention": retention,
        "context": {
            "cwd_role": "home",
            "empty_directories": [
                ".environment",
                ".environment/home",
                ".environment/config",
                ".environment/cache",
                ".environment/tmp",
            ],
            "writes_allowed": False,
        },
    }
    plan["profile_sha256"] = digest(_profile(plan, True).encode())
    plan_raw = encode(plan)
    held = {
        "plan_sha256": digest(plan_raw),
        "origin_sha256": digest(origin_raw),
        "source_sha256": digest(encode(source)),
        "owner_sha256": digest(encode(owner)),
        "rights_basis_sha256": plan["rights_basis_sha256"],
        "profile_sha256": plan["profile_sha256"],
        "binary_identity_sha256": digest(encode(binary)),
        "output_root": plan["output_root"],
    }
    approval = {
        "schema": SCHEMA,
        "kind": "invented",
        **{
            k: held[k]
            for k in (
                "plan_sha256",
                "origin_sha256",
                "source_sha256",
                "owner_sha256",
                "rights_basis_sha256",
                "profile_sha256",
                "binary_identity_sha256",
            )
        },
        "nonce": "2" * 32,
        "issued_utc": core._stamp(now),
        "expires_utc": core._stamp(now + timedelta(minutes=30)),
        "scope": "one-binary-hash-and-two-startup-help-probes",
        "authority": dict(AUTHORITY),
    }
    approval_raw = encode(approval)
    held["approval_sha256"] = digest(approval_raw)
    inputs = (plan_raw, approval_raw, origin_raw, held)
    _FIXTURES.add(_fixture_key(inputs))
    return inputs


def run_fixture_probe(inputs, case="ok", *, whole_seconds=60, probe_seconds=10):
    require(_fixture_key(inputs) in _FIXTURES and case in CASES, "minted-fixed-fixture")
    require(
        type(whole_seconds) in (int, float)
        and 0 < whole_seconds <= 60
        and type(probe_seconds) in (int, float)
        and 0 < probe_seconds <= 10,
        "bounded-fixture-time",
    )
    return _execute(*inputs, True, case, whole_seconds, probe_seconds)


def inspect_receipt_metadata(
    plan_raw, approval_raw, origin_raw, held, *, held_receipt_sha256, fixture=False
):
    require(
        type(approval_raw) is bytes
        and len(approval_raw) <= 32768
        and digest(approval_raw) == held["approval_sha256"],
        "held-approval-before-decode",
    )
    issued = core._utc(decode(approval_raw)["issued_utc"])
    plan, expiry = _gate(plan_raw, approval_raw, origin_raw, held, fixture, historical_at=issued)
    retained = min(_retention(plan["retention"]), core._utc(decode(origin_raw)["not_after_UTC"]))
    deadline = time.monotonic() + 10
    directory = core._directory(plan["output_root"])
    try:
        _namespace(directory, plan)
        raw = previous._load_file(directory, "receipt.private.json", 32768, retained, deadline)
        require(digest(raw) == held_receipt_sha256, "held-producer-receipt")
        receipt = decode(raw)
        _validate_receipt(receipt, plan, held, fixture, issued, expiry)
        _namespace(directory, plan, receipt["environment_identities"])
        _gate(plan_raw, approval_raw, origin_raw, held, fixture, historical_at=issued)
        return receipt
    finally:
        os.close(directory)


def _binary_directory(path):
    path = _path(path)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = os.open(path.anchor, flags)
    try:
        for part in path.parts[1:]:
            nxt = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = nxt
        require(
            stat.S_ISDIR(os.fstat(fd).st_mode)
            and _token(os.fstat(fd))[:4] == _token(path.lstat())[:4],
            "binary-directory-name-binding",
        )
        return fd
    except BaseException:
        os.close(fd)
        raise


def _write_output(directory, raw, expiry, deadline, case=None):
    require(len(raw) <= 65536, "bounded-report")
    _live(expiry, deadline)
    fd = os.open(
        "report.private.json",
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
        dir_fd=directory,
    )
    try:
        core._regular(fd)
        count = 0
        hasher = hashlib.sha256()
        while count < len(raw):
            _live(expiry, deadline)
            if case == "write-stall":
                time.sleep(30)
            part = raw[count : count + 65536]
            n = os.write(fd, part)
            require(0 < n <= len(part), "write-progress")
            hasher.update(part[:n])
            count += n
        _live(expiry, deadline)
        if case == "fsync-stall":
            time.sleep(30)
        _live(expiry, deadline)
        os.fsync(fd)
        _live(expiry, deadline)
        require(
            _token(os.fstat(fd))
            == _token(os.stat("report.private.json", dir_fd=directory, follow_symlinks=False)),
            "written-report-name-binding",
        )
        require(
            count == len(raw) and hasher.hexdigest() == digest(raw), "acknowledged-report-digest"
        )
    finally:
        os.close(fd)
