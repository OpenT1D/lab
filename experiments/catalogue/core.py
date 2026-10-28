"""Passive indexing, explicit native verification and conservative repeat eligibility."""

import copy
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from experiments.platform_process import SOURCE_FILES as PROCESS_SOURCES

from .claims import hash_checks
from .formats import TASKS, metadata, reconstruction_args, report_complete
from .storage import (
    ID,
    ROOT,
    decode,
    digest,
    dump,
    encoded,
    fresh,
    inventory,
    load_sealed,
    read,
    regular,
    require,
    seal,
    source_hashes,
    supervise,
    text,
)

VERSION = "opent1d.local-catalogue/1"
REQUEST = "opent1d.catalogue-request/1"
SOURCES = (
    (
        "experiments/catalogue/__init__.py",
        "experiments/catalogue/__main__.py",
        "experiments/catalogue/contract.json",
        "experiments/catalogue/storage.py",
        "experiments/catalogue/formats.py",
        "experiments/catalogue/core.py",
        "experiments/catalogue/claims.py",
    )
    + ("experiments/platform_files.py",)
    + PROCESS_SOURCES
)


def request(value, base):
    require(
        isinstance(value, dict)
        and set(value) == {"schema", "entries"}
        and value["schema"] == REQUEST,
        "Unsupported catalogue request",
    )
    require(
        isinstance(value["entries"], list) and 1 <= len(value["entries"]) <= 128, "Invalid roster"
    )
    result, seen = [], set()
    for item in value["entries"]:
        require(
            isinstance(item, dict) and set(item) == {"id", "task", "archive", "tags"},
            "Invalid entry",
        )
        identity = item["id"]
        require(
            isinstance(identity, str) and ID.fullmatch(identity) and identity not in seen,
            "Invalid or duplicate id",
        )
        seen.add(identity)
        require(item["task"] in TASKS, "Unsupported catalogue task")
        require(isinstance(item["archive"], str) and item["archive"], "Missing archive path")
        require(
            isinstance(item["tags"], list)
            and len(item["tags"]) <= 16
            and all(isinstance(tag, str) and 0 < len(tag) <= 128 for tag in item["tags"])
            and len(set(item["tags"])) == len(item["tags"]),
            "Invalid local tags",
        )
        path = Path(item["archive"])
        if not path.is_absolute():
            path = Path(base) / path
        require(not path.is_symlink(), "Archive pointer cannot be a symlink")
        result.append({**item, "archive": str(path.resolve())})
    return {"schema": REQUEST, "entries": result}


def entry(item):
    result = {
        **item,
        "inventory": None,
        "archive_sha256": None,
        "hash_checks": None,
        "metadata": None,
        "metadata_status": "unavailable",
        "metadata_error": None,
        "verification": {"status": "not_requested", "complete": False},
    }
    path = Path(item["archive"])
    try:
        files = inventory(path)
        result.update(inventory=files, archive_sha256=digest(encoded(files)))
        result["hash_checks"] = hash_checks(path, files)
        result["metadata"] = metadata(path, item["task"], files)
        require(inventory(path) == files, "Archive changed during metadata reading")
        result["metadata_status"] = "metadata_read"
    except (OSError, ValueError, KeyError, TypeError, RecursionError) as error:
        result["metadata_error"] = type(error).__name__ + ": " + str(error)[:300]
    return result


def markdown(data):
    lines = [
        "# Local experiment catalogue",
        "",
        "Metadata and recorded digest agreement do not establish reconstruction, "
        "model validity or source rights.",
        "",
        "| ID | Task | Protocol | Models | Recorded status | Metadata | "
        "Reconstruction | Complete |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in data["entries"]:
        meta, verified = item["metadata"] or {}, item["verification"]
        lines.append(
            "| "
            + " | ".join(
                text(value)
                for value in (
                    item["id"],
                    item["task"],
                    meta.get("protocol"),
                    ", ".join(model["id"] for model in meta.get("models", [])),
                    meta.get("recorded_status", "unavailable"),
                    item["metadata_status"],
                    verified["status"],
                    verified["complete"],
                )
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "Source archives remain authoritative and unchanged. Verification checks saved "
            "evidence with each route's registered reader; arbitrary supplied algorithms "
            "are not independently reproduced.",
            "",
            "Cross-archive eligibility is limited to complete repeats of the same experiment. "
            "Native comparison tasks own comparisons between different methods.",
            "",
        ]
    )
    return "\n".join(lines)


def save(output, data, original_request):
    dump(output / "request.json", original_request)
    dump(output / "catalogue.json", data)
    (output / "report.md").write_bytes(markdown(data).encode("utf-8"))
    seal(output)


def index(config, output):
    config = regular(config)
    raw = config.read_bytes()
    normalized_request = request(decode(raw), config.parent)
    entries = [entry(item) for item in normalized_request["entries"]]
    output = fresh(output, [item["archive"] for item in entries])
    data = {
        "schema": VERSION,
        "operation": "index",
        "request": normalized_request,
        "request_sha256": digest(encoded(normalized_request)),
        "source_sha256": source_hashes(SOURCES),
        "entries": entries,
    }
    save(output, data, normalized_request)
    return data


def load(directory):
    directory = load_sealed(directory)
    data = read(directory / "catalogue.json")
    require(
        isinstance(data, dict)
        and set(data)
        == {"schema", "operation", "request", "request_sha256", "source_sha256", "entries"}
        and data["schema"] == VERSION
        and data["operation"] in {"index", "verify"},
        "Unsupported catalogue archive",
    )
    require(
        data["source_sha256"] == source_hashes(SOURCES), "Catalogue implementation identity differs"
    )
    normalized_request = request(data["request"], directory)
    require(
        normalized_request == data["request"]
        and len(data["entries"]) == len(normalized_request["entries"]),
        "Catalogue roster differs",
    )
    require(
        read(directory / "request.json") == normalized_request
        and data["request_sha256"] == digest(encoded(normalized_request)),
        "Saved catalogue request differs",
    )
    require(
        (directory / "report.md").read_bytes() == markdown(data).encode(),
        "Catalogue report differs",
    )
    for item, declared in zip(data["entries"], normalized_request["entries"], strict=True):
        require(
            isinstance(item, dict)
            and set(item)
            == {
                "id",
                "task",
                "archive",
                "tags",
                "inventory",
                "archive_sha256",
                "hash_checks",
                "metadata",
                "metadata_status",
                "metadata_error",
                "verification",
            },
            "Invalid catalogue entry",
        )
        require(
            all(item[key] == value for key, value in declared.items()),
            "Catalogue pointer differs from request",
        )
        require(
            item["archive_sha256"] is None
            or item["archive_sha256"] == digest(encoded(item["inventory"])),
            "Catalogue inventory fingerprint differs",
        )
        require(
            item["verification"]["status"]
            in {"not_requested", "verified_reconstruction", "failed"},
            "Invalid verification state",
        )
        require(type(item["verification"]["complete"]) is bool, "Invalid completeness state")
        require(
            not item["verification"]["complete"]
            or item["verification"]["status"] == "verified_reconstruction",
            "Unverified entry claims completeness",
        )
        if item["metadata"] is not None:
            require(isinstance(item["metadata"], dict), "Invalid saved metadata")
            coverage = item["metadata"].get("repeat_condition_coverage")
            require(
                isinstance(coverage, dict)
                and set(coverage) == {"complete", "reasons"}
                and type(coverage["complete"]) is bool
                and isinstance(coverage["reasons"], list)
                and all(isinstance(reason, str) and reason for reason in coverage["reasons"])
                and (not coverage["complete"] or not coverage["reasons"]),
                "Invalid repeat-condition coverage",
            )
    return directory, data


def environment():
    return {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("UV_")
        and key not in {"VIRTUAL_ENV", "PYTHONHOME", "PYTHONPATH", "__PYVENV_LAUNCHER__"}
    } | {"PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1"}


def verify_one(item, output, allow_failed=False):
    result = {
        "status": "failed",
        "complete": False,
        "reader_exit_code": None,
        "error": None,
        "source_archive_sha256": item["archive_sha256"],
    }
    archive = Path(item["archive"])
    try:
        require(item["metadata_status"] == "metadata_read", "Metadata unavailable")
        require(inventory(archive) == item["inventory"], "Source archive changed since indexing")
        require(
            metadata(archive, item["task"], item["inventory"]) == item["metadata"],
            "Indexed scientific metadata differs",
        )
        args = [
            sys.executable,
            "-B",
            "-E",
            "-s",
            "-S",
            *reconstruction_args(item["task"], archive, output, allow_failed),
        ]
        operation = supervise(
            args, output.parent / (output.name + ".log"), ROOT, environment(), 120
        )
        code = operation["exit_code"]
        if operation["status"] == "interrupted":
            result["interruption_signal"] = operation["signal"]
        result["reader_exit_code"] = code
        require(inventory(archive) == item["inventory"], "Reader changed source archive")
        require(code == 0, "Authoritative reconstruction failed")
        report_path = archive if item["task"] == "m5-prognosis" else output
        complete = report_complete(item["task"], read(report_path / "report.json"))
        result.update(status="verified_reconstruction", complete=complete)
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        result["error"] = type(error).__name__ + ": " + str(error)[:300]
    return result


def verify(catalogue, output, allow_failed=False):
    directory, data = load(catalogue)
    data = copy.deepcopy(data)
    output = fresh(output, [directory, *(item["archive"] for item in data["entries"])])
    reconstructions = output / "reconstruction"
    reconstructions.mkdir()
    for item in data["entries"]:
        item["verification"] = verify_one(item, reconstructions / item["id"], allow_failed)
        if item["verification"].get("interruption_signal") is not None:
            remaining = data["entries"][data["entries"].index(item) + 1 :]
            for unattempted in remaining:
                unattempted["verification"] = {
                    "status": "failed",
                    "complete": False,
                    "error": "global verification interruption; entry not attempted",
                }
            break
    data["operation"] = "verify"
    save(output, data, read(directory / "request.json"))
    return data


def listing(catalogue, **filters):
    _, data = load(catalogue)
    result = []
    for item in data["entries"]:
        meta = item["metadata"] or {}
        values = {
            "task": [item["task"]],
            "protocol": [meta.get("protocol")],
            "model": [value["id"] for value in meta.get("models", [])],
            "status": [
                meta.get("recorded_status"),
                item["verification"]["status"],
                item["metadata_status"],
            ],
            "tag": item["tags"],
        }
        if all(value is None or value in values[key] for key, value in filters.items()):
            result.append(item)
    return {
        "schema": VERSION,
        "verification_scope": "recorded_verification_receipt",
        "entries": result,
    }


def compare(catalogue, left, right):
    _, data = load(catalogue)
    entries = {item["id"]: item for item in data["entries"]}
    require(
        left in entries and right in entries and left != right,
        "Choose two distinct catalogue entries",
    )
    a, b = entries[left], entries[right]
    reasons = []
    if a["task"] != b["task"]:
        reasons.append("different tasks")
    for item in (a, b):
        if item["verification"]["status"] != "verified_reconstruction":
            reasons.append(item["id"] + ": reconstruction not verified")
        elif not item["verification"]["complete"]:
            reasons.append(item["id"] + ": experiment incomplete or failed")
        coverage = (item["metadata"] or {}).get("repeat_condition_coverage", {})
        if coverage.get("complete") is not True:
            reasons.append(item["id"] + ": saved repeat conditions incomplete")
            reasons.extend(item["id"] + ": " + reason for reason in coverage.get("reasons", []))
    if not reasons:
        with tempfile.TemporaryDirectory(prefix="opent1d-catalogue-repeat-") as directory:
            for item in (a, b):
                current = verify_one(item, Path(directory) / item["id"], allow_failed=True)
                if current["status"] != "verified_reconstruction" or not current["complete"]:
                    reasons.append(
                        item["id"] + ": current native reconstruction failed or incomplete"
                    )
        for key in ("protocol", "configuration_sha256", "conditions_sha256", "models"):
            if a["metadata"][key] != b["metadata"][key]:
                reasons.append("different " + key)
    return {
        "schema": VERSION,
        "left": left,
        "right": right,
        "eligible": not reasons,
        "scope": "same_experiment_repeat_only",
        "native_readers_revalidated": not reasons,
        "reasons": reasons,
        "metrics": None,
    }
