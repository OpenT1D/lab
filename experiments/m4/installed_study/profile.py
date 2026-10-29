"""Explicit local dependency overlays; archived descriptors never select execution."""

import hashlib
import importlib.metadata
import json
import os
import platform
import re
import stat
import sys
from pathlib import Path, PurePosixPath

SCHEMA = "opent1d.m4-runtime-attachment/1"
MAX_FILES = 40000
MAX_BYTES = 2 * 1024 * 1024 * 1024


def require(value, message):
    if not value:
        raise ValueError(message)


def canonical(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def read_bytes(filename, limit=16 * 1024 * 1024):
    filename = path(filename)
    descriptor = os.open(filename, os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0))
    try:
        before = os.fstat(descriptor)
        require(
            stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_size <= limit,
            "Bounded regular runtime input required",
        )
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            raw = stream.read(limit + 1)
        after, current = os.fstat(descriptor), filename.stat(follow_symlinks=False)
        require(
            len(raw) <= limit
            and (
                before.st_dev,
                before.st_ino,
                before.st_size,
                before.st_mtime_ns,
                before.st_ctime_ns,
            )
            == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
            == (
                current.st_dev,
                current.st_ino,
                current.st_size,
                current.st_mtime_ns,
                current.st_ctime_ns,
            ),
            "Runtime input changed while reading",
        )
        return raw
    finally:
        os.close(descriptor)


def path(value, *, directory=False):
    result = Path(value).absolute()
    require(".." not in result.parts, "Normalized absolute runtime path required")
    require(not any(p.is_symlink() for p in (result, *result.parents)), "Linked runtime path")
    if directory:
        require(result.is_dir(), "Runtime dependency directory missing")
    return result


def relative(value):
    require(isinstance(value, str), "Runtime relative name required")
    result = PurePosixPath(value)
    require(
        result.parts
        and result.as_posix() == value
        and not result.is_absolute()
        and not any(p in {".", ".."} for p in result.parts)
        and not any(c in value for c in ("\\", ":", "\0")),
        "Unsafe runtime file name",
    )
    return result


def file_record(filename):
    filename = path(filename)
    descriptor = os.open(filename, os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0))
    try:
        before = os.fstat(descriptor)
        require(
            stat.S_ISREG(before.st_mode)
            and before.st_nlink == 1
            and before.st_size <= 512 * 1024 * 1024,
            "Runtime requires bounded regular copies; install with --link-mode=copy",
        )
        digest = hashlib.sha256()
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            while block := stream.read(1024 * 1024):
                digest.update(block)
        after, current = os.fstat(descriptor), filename.stat(follow_symlinks=False)

        def signature(s):
            return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)

        require(
            signature(before) == signature(after) == signature(current),
            "Runtime file changed during verification",
        )
        return {"sha256": digest.hexdigest(), "bytes": before.st_size}
    finally:
        os.close(descriptor)


def inventory(directory):
    directory = path(directory, directory=True)
    files, total = {}, 0
    for item in sorted(directory.rglob("*")):
        require(not item.is_symlink(), "Linked dependency entry refused")
        if item.is_dir():
            continue
        name = item.relative_to(directory).as_posix()
        relative(name)
        record = file_record(item)
        total += record["bytes"]
        require(len(files) < MAX_FILES and total <= MAX_BYTES, "Runtime inventory exceeds limits")
        files[name] = record
    require(files, "Empty dependency directory")
    return files


def distributions(directory, expected):
    observed, revisions = {}, {}
    for distribution in importlib.metadata.distributions(path=[str(directory)]):
        name = re.sub(r"[-_.]+", "-", distribution.metadata["Name"]).lower()
        require(name not in observed, "Duplicate installed distribution")
        observed[name] = distribution.version
        if name in expected and "git" in expected[name]["source"]:
            direct = json.loads(distribution.read_text("direct_url.json") or "null")
            wanted = expected[name]["source"]["git"].rsplit("#", 1)[1]
            require(
                isinstance(direct, dict) and direct.get("vcs_info", {}).get("commit_id") == wanted,
                "Wrong upstream installation revision: " + name,
            )
            revisions[name] = wanted
    require(
        observed == {name: item["version"] for name, item in expected.items()},
        "Complete installed distribution roster differs from reviewed lock",
    )
    return {"distributions": observed, "upstream_revisions": revisions}


def interpreter():
    require(
        sys.implementation.name == "cpython" and sys.version_info[:2] == (3, 12),
        "CPython 3.12 required",
    )
    return {
        "executable": str(Path(sys.executable).absolute()),
        "python": sys.version,
        "implementation": sys.implementation.name,
        "version": platform.python_version(),
        "base_executable_sha256": hashlib.sha256(
            Path(sys.executable).resolve().read_bytes()
        ).hexdigest(),
    }


def source_records():
    from .common import ROOT, source_paths

    return {name: file_record(ROOT / name) for name in source_paths()}


def create(native, observer, output, application):
    from .common import NATIVE_PROJECT, OBSERVER_PROJECT, ROOT, package_records, protocol

    protocol()
    roles = {}
    for role, project, site in (
        ("native", NATIVE_PROJECT, native),
        ("observer", OBSERVER_PROJECT, observer),
    ):
        site = path(site, directory=True)
        files = inventory(site)
        roles[role] = {
            "project": project,
            "site_packages": str(site),
            "selectors": {
                n: file_record(ROOT / project / n)["sha256"] for n in ("pyproject.toml", "uv.lock")
            },
            **distributions(site, package_records(project)),
            "files": files,
        }
    require(
        roles["native"]["site_packages"] != roles["observer"]["site_packages"],
        "Two separate dependency directories required",
    )
    result = {
        "schema": SCHEMA,
        "interpreter": interpreter(),
        "application": application,
        "source_files": source_records(),
        "roles": roles,
    }
    evidence(result)
    destination = path(output)
    require(destination.parent.is_dir(), "Attachment parent must exist")
    with destination.open("xb") as stream:
        stream.write(canonical(result))
    return {"attachment": str(destination), "sha256": hashlib.sha256(canonical(result)).hexdigest()}


def evidence(record):
    """Validate recorded identity without inspecting old dependency locations."""
    from .common import NATIVE_PROJECT, OBSERVER_PROJECT, package_records, protocol

    require(
        isinstance(record, dict)
        and set(record) == {"schema", "interpreter", "application", "source_files", "roles"}
        and record["schema"] == SCHEMA,
        "Unsupported attachment evidence",
    )
    require(
        set(record["interpreter"])
        == {"executable", "python", "implementation", "version", "base_executable_sha256"}
        and record["interpreter"]["implementation"] == "cpython"
        and re.fullmatch(r"3\.12\.[0-9]+", record["interpreter"]["version"])
        and record["interpreter"]["python"].split()[0] == record["interpreter"]["version"]
        and re.fullmatch("[a-f0-9]{64}", record["interpreter"]["base_executable_sha256"]),
        "Incomplete interpreter evidence",
    )
    require(
        Path(record["interpreter"]["executable"]).is_absolute(), "Absolute interpreter required"
    )
    application = record["application"]
    require(
        isinstance(application, dict)
        and set(application)
        == {"schema", "descriptor_sha256", "source", "build_label", "tasks", "native_execution"}
        and application["schema"] == "opent1d.sdk-application/1"
        and re.fullmatch("[a-f0-9]{64}", application["descriptor_sha256"])
        and set(application["source"]) == {"revision", "dirty"}
        and re.fullmatch("[a-f0-9]{40}", application["source"]["revision"])
        and type(application["source"]["dirty"]) is bool
        and isinstance(application["build_label"], str)
        and application["build_label"]
        and application["tasks"] == ["mmtt-sensitivity", "m4-study-secure", "m4-study-installed"]
        and application["native_execution"] == "explicit-reviewed-attachment/1",
        "Invalid current application evidence",
    )
    require(record["source_files"] == source_records(), "Attached source payload changed")
    require(set(record["roles"]) == {"native", "observer"}, "Two explicit roles required")
    p = protocol()
    for role, project in (("native", NATIVE_PROJECT), ("observer", OBSERVER_PROJECT)):
        item = record["roles"][role]
        require(
            set(item)
            == {
                "project",
                "site_packages",
                "selectors",
                "distributions",
                "upstream_revisions",
                "files",
            }
            and item["project"] == project,
            "Runtime role binding differs",
        )
        require(Path(item["site_packages"]).is_absolute(), "Absolute dependency location required")
        require(
            item["selectors"]
            == {
                n: p["conditions"]["runtime_files_sha256"][project + "/" + n]
                for n in ("pyproject.toml", "uv.lock")
            },
            "Runtime selectors differ from reviewed protocol",
        )
        expected = package_records(project)
        require(
            item["distributions"] == {n: v["version"] for n, v in expected.items()}
            and item["upstream_revisions"]
            == {
                n: v["source"]["git"].rsplit("#", 1)[1]
                for n, v in expected.items()
                if "git" in v["source"]
            },
            "Runtime evidence differs",
        )
        require(
            isinstance(item["files"], dict) and 0 < len(item["files"]) <= MAX_FILES,
            "Bounded dependency evidence required",
        )
        for name, value in item["files"].items():
            relative(name)
            require(
                set(value) == {"sha256", "bytes"}
                and re.fullmatch("[a-f0-9]{64}", value["sha256"])
                and type(value["bytes"]) is int
                and 0 <= value["bytes"] <= 512 * 1024 * 1024,
                "Invalid dependency file identity",
            )
    require(
        record["roles"]["native"]["site_packages"] != record["roles"]["observer"]["site_packages"],
        "Distinct dependency roles required",
    )
    return record


def load(filename, expected_sha=None, *, verify_dependencies=True):
    from .common import NATIVE_PROJECT, OBSERVER_PROJECT, package_records

    filename = path(filename)
    raw = read_bytes(filename)
    parsed = json.loads(raw)
    require(raw == canonical(parsed), "Canonical runtime attachment bytes required")
    record = evidence(parsed)
    identity = hashlib.sha256(raw).hexdigest()
    require(expected_sha is None or identity == expected_sha, "Attachment identity changed")
    require(record["interpreter"] == interpreter(), "Current trusted SDK interpreter required")
    for role, project in (("native", NATIVE_PROJECT), ("observer", OBSERVER_PROJECT)):
        item = record["roles"][role]
        if verify_dependencies:
            site = path(item["site_packages"], directory=True)
            require(item["files"] == inventory(site), "Runtime byte/file roster changed")
            require(
                {k: item[k] for k in ("distributions", "upstream_revisions")}
                == distributions(site, package_records(project)),
                "Runtime metadata changed",
            )
    return record, identity


def archive(directory):
    """Refuse special entries before any inherited blocking reader opens a file."""
    directory = path(directory, directory=True)
    files = inventory(directory)
    require("manifest.json" in files, "Archive manifest missing")
    return directory
