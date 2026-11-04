"""Explicit engine-free tooling-Node host probe; no native candidate admission."""

import argparse
import hashlib
import json
import os
import platform
import secrets
import shutil
import socket
import stat
import subprocess
import sys
import threading
import time
from pathlib import Path

from experiments.gui.ownership import ProcessTable
from experiments.lt1_diagnostic import entry_transport as transport
from experiments.lt1_diagnostic import host_boundary_probe as storage
from experiments.lt1_diagnostic import native_preflight, reader
from experiments.lt1_diagnostic import review_bundle as packet_storage
from experiments.lt1_diagnostic.control_identity import ROOT, identity

HERE = ROOT / "experiments/lt1_diagnostic"
ENTRY = HERE / "host_entry_fixture.mjs"
SANDBOX = Path("/usr/bin/sandbox-exec")
DYLD = Path("/System/Library/Sandbox/Profiles/dyld-support.sb")
JS = ("host_entry_fixture.mjs", "entry_channels.mjs", "entry_handoff.mjs", "entry_observation.mjs")
DENIALS = ("outside_read", "outside_write", "network", "nonallowlisted_exec")
MODES = ("complete", "cancel")
AUTHORITY = {**transport.AUTHORITY, "selected_candidate_started": False}


class Unsupported(ValueError):
    """An unsupported host is not a successful denial."""


def need(ok, reason):
    if not ok:
        raise ValueError("LT1 tooling-host probe refused: " + reason)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def host_identity():
    return {
        "platform": sys.platform,
        "arch": platform.machine(),
        "os": platform.mac_ver()[0],
        "hostname": socket.gethostname(),
        "uid": os.getuid(),
    }


def source_identity():
    result = identity(__file__)
    result["implementation"].update(transport.source_identity()["implementation"])
    for name in JS:
        result["implementation"][(HERE / name).relative_to(ROOT).as_posix()] = digest(HERE / name)
    return result


def profile(node, inputs, output):
    def q(p):
        return json.dumps(str(p))

    return "\n".join(
        [
            "(version 1)",
            "(deny default)",
            f"(import {q(DYLD)})",
            "(allow process-fork)",
            f"(allow process-exec (literal {q(node)}))",
            "(allow sysctl-read)",
            "(allow mach-lookup)",
            "(allow file-read-metadata)",
            '(allow file-read* (subpath "/System/Library") (subpath "/usr/lib") '
            '(subpath "/Library/Apple") '
            '(literal "/dev/null") (literal "/dev/random") (literal "/dev/urandom"))',
            '(allow file-map-executable (subpath "/System/Library") (subpath "/usr/lib"))',
            f"(allow file-map-executable (literal {q(node)}))",
            f"(allow file-read* (literal {q(node)}) (subpath {q(inputs)}) (subpath {q(output)}) "
            + " ".join(f"(literal {q(HERE / name)})" for name in JS)
            + ")",
            f"(allow file-write* (subpath {q(output)}))",
            "",
        ]
    )


def acknowledge(raw, nonce, profile_sha, mode):
    parts = raw.split(b"\n")
    need(len(parts) == 3 and parts[0] == b"OPENT1D-LT1-ENTRY-1" and not parts[2], "frame EOF")
    value = reader.decode(parts[1])
    need(
        value["kind"] == "invented"
        and value["nonce_sha256"] == nonce
        and value["attempt"] == "tooling-host-" + mode
        and value["phase"] == "unqualified-current-process-observation",
        "invented frame binding",
    )
    need(
        all(
            value[k] is False
            for k in (
                "native_host_qualified",
                "native_acceptance",
                "setup_admitted",
                "native_execution_authorized",
            )
        ),
        "frame authority",
    )
    pid = value["facts"]["pid"]
    need(
        type(pid) is int and 1 < pid <= 2**31 - 1 and value["facts"]["ppid"] == os.getpid(),
        "typed entry PID",
    )
    actual = ProcessTable().one(pid)
    need(
        type(pid) is int
        and actual
        and actual["alive"]
        and actual["ppid"] == os.getpid()
        and actual["pgid"] == pid
        and value["facts"]["ppid"] == os.getpid(),
        "live owned entry",
    )
    # Profile bytes are independently pinned by actual supervisor argv, not by invented facts.
    need(len(profile_sha) == 64, "profile digest")
    ack = {
        "schema": "opent1d.lt1-entry-ack/1",
        "kind": "invented",
        "frame_sha256": reader.digest(raw),
        "grant_sha256": value["grant_sha256"],
        "attempt": value["attempt"],
        "nonce_sha256": nonce,
    }
    return b"OPENT1D-LT1-ACK-1\n" + json.dumps(ack, separators=(",", ":")).encode() + b"\n"


def validate_group(group, *, confined):
    need(isinstance(group, dict), "boundary group")
    for name in DENIALS:
        item = group.get(name)
        need(
            isinstance(item, dict) and item.get("denied") is confined, "expected operation outcome"
        )
        if confined:
            need(item.get("code") in {"EPERM", "EACCES"}, "actual permission denial")
        else:
            need(set(item) == {"denied"}, "successful unconfined operation")
    need(
        all(
            group.get(k) is True
            for k in ("allowed_input", "allowed_scratch", "clean_declared_environment")
        ),
        "successful allowed controls",
    )
    need(
        type(group.get("pid")) is int
        and 1 < group["pid"] <= 2**31 - 1
        and type(group.get("ppid")) is int
        and 0 < group["ppid"] <= 2**31 - 1,
        "process observations",
    )


def validate_controls(control):
    need(
        control["status"] == "completed"
        and type(control["exit_code"]) is int
        and control["exit_code"] == 0
        and control["error"] is None
        and control["received_signals"] == []
        and control["remaining_owned_processes"] == []
        and not control.get("cleanup_error")
        and not control.get("signal_error"),
        "unconfined controls",
    )


def validate_case(mode, result, output, controls, unrelated_alive):
    need(mode in MODES and unrelated_alive is True, "case/unrelated process")
    validate_group(controls, confined=False)
    outer, exchange = result["outer"], result["exchange"]
    need(all(result.get(k) is False for k in transport.AUTHORITY), "unchanged authority")
    need(
        result["source_stable"] is True
        and not result["resource_close_errors"]
        and exchange["thread_finished"] is True
        and exchange["status"] == "ack-sent"
        and exchange["frame_eof"] is True
        and exchange["ack_sent"] is True
        and exchange["ack_eof_sent"] is True
        and exchange["ack_raw"] == exchange["ack_sent_raw"],
        "complete local protocol",
    )
    need(
        outer["remaining_owned_processes"] == []
        and outer["received_signals"] == []
        and not outer.get("cleanup_error")
        and not outer.get("signal_error")
        and type(outer.get("exit_code")) is int,
        "owned cleanup",
    )
    need(
        outer["status"] == ("completed" if mode == "complete" else "interrupted")
        and outer["error"] == (None if mode == "complete" else "Cancelled")
        and (mode != "complete" or outer["exit_code"] == 0),
        "owned terminal outcome",
    )
    groups = [
        json.loads((output / (role + "-boundary.json")).read_bytes())
        for role in ("parent", "child")
    ]
    records = outer["owned_processes"]
    need(type(records) is list and 2 <= len(records) <= 512, "bounded owned lineage")
    for record in records:
        need(
            type(record.get("pid")) is int
            and 1 < record["pid"] <= 2**31 - 1
            and type(record.get("ppid")) is int
            and 0 < record["ppid"] <= 2**31 - 1
            and type(record.get("start")) is str
            and 0 < len(record["start"]) <= 128,
            "typed owned lineage",
        )
    owned = {p["pid"]: p for p in records}
    need(len(owned) == len(records), "distinct owned lineage")
    for group in groups:
        validate_group(group, confined=True)
    need(
        groups[0]["pid"] in owned
        and groups[0]["ppid"] == os.getpid()
        and groups[1]["pid"] in owned
        and groups[0]["pid"] != groups[1]["pid"]
        and groups[1]["ppid"] == groups[0]["pid"],
        "same owned parent/child",
    )
    for group in groups:
        need(owned[group["pid"]]["ppid"] == group["ppid"], "observed owned parent")
        live = ProcessTable().one(group["pid"])
        need(
            live is None or not live["alive"] or live["start"] != owned[group["pid"]]["start"],
            "entry/child remains",
        )
    first = (output / "heartbeat.txt").read_bytes()
    time.sleep(0.08)
    need(first and (output / "heartbeat.txt").read_bytes() == first, "child activity stopped")
    handshake = json.loads((output / "handshake.json").read_bytes())
    need(handshake["status"] == "acknowledged" and handshake["kind"] == "invented", "entry ACK")
    return {
        "status": "passed",
        "boundary_groups": 2,
        "denials_per_group": len(DENIALS),
        **AUTHORITY,
    }


def qualify(output):
    if sys.platform != "darwin" or platform.machine() != "arm64" or not SANDBOX.is_file():
        raise Unsupported("Explicit Darwin arm64 tooling host required")
    need(Path(__file__).resolve() == HERE / "host_entry_probe.py", "canonical probe")
    output = Path(output)
    need(
        output.is_absolute()
        and output.parent.resolve() == output.parent
        and not os.path.lexists(output)
        and not output.is_relative_to(ROOT),
        "fresh private output",
    )
    need(
        output.parent.stat().st_uid == os.getuid()
        and stat.S_IMODE(output.parent.stat().st_mode) == 0o700,
        "owner-only parent",
    )
    with packet_storage._opened(output.parent):
        pass
    selected = shutil.which("node")
    if not selected:
        raise Unsupported("Installed ordinary tooling Node required")
    node = Path(selected).resolve(strict=True)
    node_sha = digest(node)
    need(node_sha != native_preflight.RUNTIME["executable_sha256"], "selected candidate excluded")
    sources = source_identity()
    host = host_identity()
    version = subprocess.run(
        [str(node), "--version"],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        timeout=2,
        env=dict(transport.owner.ENVIRONMENT),
    )
    need(
        version.returncode == 0
        and len(version.stdout) <= 128
        and version.stdout.startswith(b"v")
        and not version.stderr,
        "tooling runtime version",
    )
    runtime = {
        "node_path": str(node),
        "node_sha256": node_sha,
        "node_version": version.stdout.decode("ascii").strip(),
        "sandbox_sha256": digest(SANDBOX),
        "dyld_sha256": digest(DYLD),
        "shell_sha256": digest(Path("/bin/sh").resolve()),
    }
    output.mkdir(mode=0o700)
    report = {
        "schema": "opent1d.lt1-tooling-host-entry/1",
        "kind": "invented",
        "origin": "observed-tooling-host-fixture",
        "status": "failed",
        "source_identity": sources,
        "host": host,
        "runtime": runtime,
        "cases": {mode: {"status": "not_run"} for mode in MODES},
        **AUTHORITY,
    }
    old_umask = os.umask(0o077)
    unrelated = None
    try:
        inputs, outside = output / "input", output / "outside"
        inputs.mkdir(mode=0o700)
        outside.mkdir(mode=0o700)
        storage.private_bytes(inputs / "invented.txt", b"invented input\n")
        storage.private_bytes(outside / "secret.txt", b"invented sentinel\n")
        unrelated = subprocess.Popen(
            [str(node), "-e", "setInterval(()=>{},1000)"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=transport.owner.ENVIRONMENT,
            start_new_session=True,
        )
        with socket.socket() as server:
            server.bind(("127.0.0.1", 0))
            server.listen(16)
            port = server.getsockname()[1]
            for mode in MODES:
                controls, target = output / (mode + "-controls"), output / mode
                controls.mkdir(mode=0o700)
                target.mkdir(mode=0o700)
                nonce = secrets.token_hex(32)
                command = [
                    str(node),
                    str(ENTRY),
                    "controls",
                    str(inputs),
                    str(controls),
                    str(outside),
                    str(port),
                    nonce,
                    "0" * 64,
                ]
                control = transport.owner.canonical.supervise(
                    command,
                    controls / "process.log",
                    timeout=5,
                    grace=0.2,
                    environment=dict(transport.owner.ENVIRONMENT),
                )
                validate_controls(control)
                checks = json.loads((controls / "control-boundary.json").read_bytes())
                validate_group(checks, confined=False)
                policy = profile(node, inputs, target)
                storage.private_bytes(output / (mode + ".sb"), policy.encode())
                policy_sha = reader.digest(policy.encode())
                stopped, done = threading.Event(), threading.Event()

                def watch():
                    while not done.wait(0.01):
                        if (target / "ready.json").is_file():
                            if not done.wait(0.15):
                                stopped.set()
                            return

                watcher = threading.Thread(target=watch) if mode == "cancel" else None
                if watcher:
                    watcher.start()
                try:
                    result = transport.supervise_entry(
                        [
                            str(SANDBOX),
                            "-p",
                            policy,
                            str(node),
                            str(ENTRY),
                            mode,
                            str(inputs),
                            str(target),
                            str(outside),
                            str(port),
                            nonce,
                            policy_sha,
                        ],
                        target / "process.log",
                        expected_identity=transport.source_identity(),
                        verify_frame=lambda raw: acknowledge(raw, nonce, policy_sha, mode),
                        timeout=6,
                        handoff_timeout=3,
                        grace=0.3,
                        cancel=stopped,
                    )
                finally:
                    done.set()
                    if watcher:
                        watcher.join(timeout=1)
                        need(not watcher.is_alive(), "watcher stopped")
                stored = {
                    **result,
                    "exchange": {
                        **result["exchange"],
                        "frame_raw": result["exchange"]["frame_raw"].hex(),
                        "ack_raw": result["exchange"]["ack_raw"].hex(),
                        "ack_sent_raw": result["exchange"]["ack_sent_raw"].hex(),
                    },
                }
                storage.save(target / "transport.json", stored)
                report["cases"][mode] = validate_case(
                    mode, result, target, checks, unrelated.poll() is None
                )
                need(
                    (outside / "secret.txt").read_bytes() == b"invented sentinel\n"
                    and not (outside / "parent-new.txt").exists()
                    and not (outside / "child-new.txt").exists(),
                    "outside unchanged",
                )
        report["status"] = "passed"
    except Exception as error:
        report.update(status="failed", error_type=type(error).__name__, error=str(error)[:1000])
    finally:
        try:
            if unrelated:
                if unrelated.poll() is not None:
                    report.update(status="failed", unrelated_died=True)
                unrelated.terminate()
                unrelated.wait(timeout=5)
                report["unrelated_reaped"] = True
        except (OSError, subprocess.SubprocessError) as error:
            report.update(status="failed", unrelated_cleanup_error=type(error).__name__)
            try:
                if unrelated.poll() is None:
                    unrelated.kill()
                unrelated.wait(timeout=2)
                report["unrelated_reaped"] = True
            except (OSError, subprocess.SubprocessError) as final:
                report["unrelated_cleanup_final_error"] = type(final).__name__
        try:
            need(
                source_identity() == sources
                and all(
                    digest(Path(runtime[k])) == runtime[k.replace("_path", "_sha256")]
                    for k in ("node_path",)
                ),
                "final source/runtime",
            )
            need(
                digest(SANDBOX) == runtime["sandbox_sha256"]
                and digest(DYLD) == runtime["dyld_sha256"]
                and digest(Path("/bin/sh").resolve()) == runtime["shell_sha256"]
                and host_identity() == host,
                "host mechanism changed",
            )
        except Exception as error:
            report.update(status="failed", source_error=type(error).__name__)
        try:
            storage.save(output / "qualification.json", report)
        finally:
            os.umask(old_umask)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = qualify(args.output)
    print(json.dumps({"status": report["status"], **AUTHORITY}))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
