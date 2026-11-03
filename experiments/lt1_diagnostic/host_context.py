"""Fixed read-only OS/process observations, not login or native qualification.

Return values contain private host/session data; callers must keep them private.
No CLI, candidate runtime, sandbox policy or caller-selected command is provided.
"""

import hashlib
import os
import platform
import re
import socket
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

from experiments.gui.ownership import ProcessTable
from experiments.lt1_diagnostic.control_identity import ROOT, identity

SCHEMA = "opent1d.lt1-readonly-host-context/1"
SYSCTL = Path("/usr/sbin/sysctl")
KEYS = ("kern.bootsessionuuid", "kern.uuid", "kern.osversion", "kern.osrelease")
ENVIRONMENT = {"LANG": "C", "LC_ALL": "C", "PATH": "/usr/bin:/bin"}


def need(ok, reason):
    if not ok:
        raise ValueError("LT1 host context refused: " + reason)


def fields(value, keys):
    need(isinstance(value, dict) and set(value) == set(keys.split()), "fields")


def stamp(value):
    need(isinstance(value, str) and len(value) <= 40, "UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("LT1 host context refused: UTC timestamp") from error
    need(parsed.tzinfo is not None and parsed.utcoffset().total_seconds() == 0, "UTC timestamp")
    return parsed


def sha(value):
    return isinstance(value, str) and re.fullmatch("[a-f0-9]{64}", value) is not None


def valid_value(key, value):
    if not isinstance(value, str) or len(value) > 128:
        return False
    if key in KEYS[:2]:
        try:
            parsed = uuid.UUID(value)
            return parsed.int != 0 and str(parsed) == value.lower()
        except ValueError:
            return False
    pattern = r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}" if key == KEYS[2] else r"\d+(?:\.\d+){1,3}"
    return re.fullmatch(pattern, value) is not None


def _query(key):
    need(key in KEYS, "fixed query")
    try:
        result = subprocess.run(
            [str(SYSCTL), "-n", key],
            env=ENVIRONMENT,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=2,
            check=False,
        )
        if len(result.stdout) > 4096 or len(result.stderr) > 4096:
            return {"returncode": result.returncode, "value": None, "error": "output-bound"}
        value = result.stdout.decode("ascii", "strict").strip()
        error = (
            None if result.returncode == 0 and valid_value(key, value) else "unavailable-or-invalid"
        )
        return {
            "returncode": result.returncode,
            "value": value if error is None else None,
            "error": error,
        }
    except (OSError, subprocess.SubprocessError, UnicodeError) as error:
        return {"returncode": None, "value": None, "error": type(error).__name__}


def _observer():
    pid = os.getpid()
    row = ProcessTable().one(pid)
    return {
        "pid": pid,
        "ppid": os.getppid(),
        "posix_session": os.getsid(0),
        "start": row["start"] if row and row["alive"] and row["pid"] == pid else None,
    }


def _tool_digest():
    return hashlib.sha256(SYSCTL.read_bytes()).hexdigest()


def _source_identity():
    return identity(__file__)


def unknown_fields(value):
    unknown = []
    if value["host"]["platform"] != "darwin" or value["host"]["machine"] != "arm64":
        unknown.append("supported-platform")
    if value["observer"]["start"] is None:
        unknown.append("observer-start")
    if value["sysctl_sha256"] is None:
        unknown.append("sysctl-identity")
    for key in KEYS:
        query = value["queries"][key]
        if (
            type(query["returncode"]) is not int
            or query["returncode"] != 0
            or query["error"] is not None
            or not valid_value(key, query["value"])
        ):
            unknown.append("query:" + key)
    return sorted(unknown)


def validate(value):
    """Validate supplied observation data, not their truth or current OS state."""
    fields(
        value,
        "schema kind host observer collector_identity sysctl_sha256 queries "
        "observed_from observed_to status unknown",
    )
    need(value["schema"] == SCHEMA and value["kind"] == "read-only-observation", "schema")
    fields(value["host"], "platform machine hostname uid")
    host = value["host"]
    need(
        all(
            isinstance(host[k], str) and 0 < len(host[k]) <= 255
            for k in ("platform", "machine", "hostname")
        ),
        "host labels",
    )
    need(type(host["uid"]) is int and host["uid"] >= 0, "UID")
    fields(value["observer"], "pid ppid posix_session start")
    observer = value["observer"]
    need(
        all(type(observer[k]) is int and observer[k] > 0 for k in ("pid", "ppid", "posix_session")),
        "process identity",
    )
    need(
        observer["start"] is None
        or isinstance(observer["start"], str)
        and 0 < len(observer["start"]) <= 128,
        "process start",
    )
    fields(value["collector_identity"], "implementation python executable_sha256")
    collector = value["collector_identity"]
    need(
        isinstance(collector["implementation"], dict)
        and 0 < len(collector["implementation"]) <= 512
        and "experiments/lt1_diagnostic/host_context.py" in collector["implementation"]
        and all(
            isinstance(k, str)
            and k.startswith("experiments/")
            and not any(p in ("", ".", "..") for p in k.split("/"))
            and "\\" not in k
            and sha(v)
            for k, v in collector["implementation"].items()
        )
        and isinstance(collector["python"], str)
        and sha(collector["executable_sha256"]),
        "collector identity",
    )
    need(value["sysctl_sha256"] is None or sha(value["sysctl_sha256"]), "tool identity")
    fields(value["queries"], " ".join(KEYS))
    for query in value["queries"].values():
        fields(query, "returncode value error")
        need(query["returncode"] is None or type(query["returncode"]) is int, "query exit")
        need(
            query["value"] is None
            or isinstance(query["value"], str)
            and len(query["value"]) <= 128,
            "query value",
        )
        need(
            query["error"] is None
            or isinstance(query["error"], str)
            and len(query["error"]) <= 128,
            "query error",
        )
    need(stamp(value["observed_from"]) <= stamp(value["observed_to"]), "observation interval")
    unknown = unknown_fields(value)
    need(
        value["unknown"] == unknown
        and value["status"] == ("observed" if not unknown else "unavailable"),
        "unknown state",
    )
    return value


def capture():
    """Explicit canonical-source capture only; never called by the assessor."""
    need(
        Path(__file__).resolve() == ROOT / "experiments/lt1_diagnostic/host_context.py",
        "canonical collector required",
    )
    started = datetime.now(UTC).isoformat()
    collector = _source_identity()
    observer = _observer()
    try:
        tool = _tool_digest()
    except OSError:
        tool = None
    supported = sys.platform == "darwin" and platform.machine() == "arm64"
    queries = {
        key: _query(key)
        if supported and tool
        else {"returncode": None, "value": None, "error": "unsupported-or-tool-unavailable"}
        for key in KEYS
    }
    need(
        observer == _observer() and collector == _source_identity(), "collector or observer changed"
    )
    if tool is not None:
        try:
            need(tool == _tool_digest(), "sysctl changed")
        except OSError as error:
            raise ValueError("LT1 host context refused: sysctl disappeared") from error
    result = {
        "schema": SCHEMA,
        "kind": "read-only-observation",
        "host": {
            "platform": sys.platform,
            "machine": platform.machine(),
            "hostname": socket.gethostname(),
            "uid": os.getuid(),
        },
        "observer": observer,
        "collector_identity": collector,
        "sysctl_sha256": tool,
        "queries": queries,
        "observed_from": started,
        "observed_to": datetime.now(UTC).isoformat(),
    }
    result["unknown"] = unknown_fields(result)
    result["status"] = "observed" if not result["unknown"] else "unavailable"
    return validate(result)
