"""Export, verify, restore and explicitly reconstruct immutable directory packages."""

import hashlib
from pathlib import Path, PurePosixPath

from experiments.platform_files import native_absolute, recorded_path

from . import reader, storage

TOOLING_ROOT = native_absolute(Path(__file__).resolve().parents[2])
SCHEMA = "opent1d.durable-archive/1"
RESULT_SCHEMA = "opent1d.durable-archive-result/1"
TOP_LEVEL = {"manifest.json", "archive", "reader", "evidence"}
MANIFEST_KEYS = {
    "schema",
    "task",
    "origin",
    "reader",
    "reconstruction",
    "files",
    "directories",
    "totals",
}


def _identity(raw):
    return hashlib.sha256(raw).hexdigest()


def _result(operation, manifest, raw, *, reconstructed=False, output=None):
    result = {
        "schema": RESULT_SCHEMA,
        "operation": operation,
        "status": "completed",
        "task": manifest["task"],
        "package_identity": _identity(raw),
        "integrity_verified": True,
        "reconstruction_verified": reconstructed,
        "complete": manifest["reconstruction"]["complete"],
        "reader_revision": manifest["reader"]["revision"],
        "interpretation": (
            "Byte integrity only; numerical completeness is the recorded original reader outcome. "
            "Hashes do not establish authenticity or model validity."
            if not reconstructed
            else "Fixed trusted reader reconstruction verified; numerical completeness is separate "
            "from biological validity and authenticity."
        ),
    }
    if output is not None:
        result["output"] = str(Path(output).absolute())
    return result


def _original_reports(task, files, reconstruction, *, prefix=""):
    if task in reader.M3_TASKS:
        for name in reader.REPORTS[task]:
            saved = files.get(prefix + name)
            storage.require(
                saved is None or saved == reconstruction["artifacts"].get(name),
                "Saved M3 native report differs from authoritative reconstruction",
            )


def _validate_manifest(manifest, budget=None):
    budget = storage.Budget() if budget is None else budget
    budget.check()
    storage.require(
        isinstance(manifest, dict)
        and set(manifest) == MANIFEST_KEYS
        and manifest["schema"] == SCHEMA
        and manifest["task"] in reader.TASKS,
        "Unsupported durable archive manifest",
    )
    files, directories = manifest["files"], manifest["directories"]
    storage.require(
        isinstance(files, dict)
        and len(files) <= storage.FILES_LIMIT
        and isinstance(directories, list)
        and len(directories) <= storage.ENTRIES_LIMIT,
        "Invalid package inventory",
    )
    aliases = set()
    for name, value in files.items():
        budget.check()
        storage.relative_name(name)
        storage.require(
            name.split("/", 1)[0] in {"archive", "reader", "evidence"}
            and isinstance(value, dict)
            and set(value) == {"sha256", "size"}
            and isinstance(value["sha256"], str)
            and storage.SHA.fullmatch(value["sha256"])
            and type(value["size"]) is int
            and 0 <= value["size"] <= storage.FILE_LIMIT,
            "Invalid package file descriptor",
        )
        storage.require(name.casefold() not in aliases, "Package path alias")
        aliases.add(name.casefold())
    storage.require(
        all(isinstance(name, str) for name in directories), "Directory names must be strings"
    )
    directory_set = set(directories)
    storage.require(
        directories == sorted(directory_set)
        and {"archive", "reader", "evidence"} <= set(directories),
        "Invalid directory inventory",
    )
    for name in directories:
        budget.check()
        storage.relative_name(name)
        storage.require(
            name.split("/", 1)[0] in {"archive", "reader", "evidence"}
            and name.casefold() not in aliases,
            "Package directory alias",
        )
        aliases.add(name.casefold())
    for name in files.keys() | directory_set:
        budget.check()
        storage.require(
            all(
                str(parent) in directory_set
                for parent in PurePosixPath(name).parents
                if str(parent) != "."
            ),
            "Package inventory omits a parent directory",
        )
    totals = {
        "files": len(files),
        "entries": len(files) + len(directories),
        "bytes": sum(value["size"] for value in files.values()),
    }
    storage.require(
        manifest["totals"] == totals
        and totals["bytes"] <= storage.TOTAL_LIMIT
        and totals["entries"] + 1 <= storage.ENTRIES_LIMIT
        and totals["files"] + 1 <= storage.FILES_LIMIT,
        "Package totals differ or exceed limits",
    )
    origin = manifest["origin"]
    storage.require(
        isinstance(origin, dict)
        and set(origin) == {"archive_path", "archive_inventory_sha256"}
        and isinstance(origin["archive_path"], str)
        and recorded_path(origin["archive_path"]).is_absolute()
        and isinstance(origin["archive_inventory_sha256"], str)
        and storage.SHA.fullmatch(origin["archive_inventory_sha256"]),
        "Invalid original archive provenance",
    )
    recorded = manifest["reader"]
    storage.require(
        isinstance(recorded, dict)
        and set(recorded) == {"revision", "checkout_path", "files"}
        and isinstance(recorded["revision"], str)
        and storage.REVISION.fullmatch(recorded["revision"])
        and isinstance(recorded["checkout_path"], str)
        and recorded_path(recorded["checkout_path"]).is_absolute()
        and isinstance(recorded["files"], dict)
        and recorded["files"],
        "Invalid trusted reader identity",
    )
    preserved = {
        name.removeprefix("reader/"): value
        for name, value in files.items()
        if name.startswith("reader/")
    }
    storage.require(recorded["files"] == preserved, "Reader snapshot differs from reader identity")
    result = manifest["reconstruction"]
    storage.require(
        isinstance(result, dict)
        and result.get("status") == "verified_reconstruction"
        and type(result.get("complete")) is bool
        and result.get("allow_failed") is True
        and result.get("exit_code") == 0
        and isinstance(result.get("artifacts"), dict)
        and set(result["artifacts"]) == set(reader.REPORTS[manifest["task"]]),
        "Invalid recorded reconstruction",
    )
    _original_reports(manifest["task"], files, result, prefix="archive/")
    storage.require(
        all(
            files.get("evidence/reconstructed/" + name) == value
            for name, value in result["artifacts"].items()
        )
        and "evidence/reader-receipt.json" in files
        and "evidence/reader-stdout.log" in files
        and "evidence/reader-stderr.log" in files,
        "Recorded reconstruction evidence differs from package inventory",
    )


def _verified(package, budget):
    package = storage.safe_path(package)
    raw = storage.read_file(package, "manifest.json", budget)
    manifest = storage.strict_json(raw)
    _validate_manifest(manifest, budget)
    view, signatures = storage.inventory(package, budget, exclude_manifest=True)
    storage.require(
        view == {key: manifest[key] for key in ("files", "directories", "totals")},
        "Package byte or directory inventory differs from manifest",
    )
    storage.require(
        view["totals"]["bytes"] + len(raw) <= storage.TOTAL_LIMIT,
        "Total package byte limit exceeded",
    )
    storage.require(
        storage.read_file(package, "manifest.json", budget) == raw,
        "Package manifest changed during verification",
    )
    receipt = storage.strict_json(
        storage.read_file(package, "evidence/reader-receipt.json", budget)
    )
    storage.require(
        receipt == manifest["reconstruction"], "Recorded reader receipt differs from manifest"
    )
    archive_view = {
        "files": {
            name.removeprefix("archive/"): value
            for name, value in view["files"].items()
            if name.startswith("archive/")
        },
        "directories": [
            name.removeprefix("archive/")
            for name in view["directories"]
            if name.startswith("archive/")
        ],
    }
    archive_view["totals"] = {
        "files": len(archive_view["files"]),
        "entries": len(archive_view["files"]) + len(archive_view["directories"]),
        "bytes": sum(value["size"] for value in archive_view["files"].values()),
    }
    storage.require(
        _identity(storage.encoded(archive_view)) == manifest["origin"]["archive_inventory_sha256"],
        "Original archive inventory binding differs",
    )
    return manifest, raw, view, signatures


@storage.cancellable
def verify_package(package):
    """Check only preserved bytes. This never imports a model or runs a reader."""
    manifest, raw, _, _ = _verified(package, storage.Budget())
    return _result("verify", manifest, raw)


@storage.cancellable
def export_archive(task, archive, checkout, revision, output, *, timeout_seconds=120):
    """Preserve the whole archive and exact trusted reader, without changing either."""
    storage.require(task in reader.TASKS, "Unsupported durable archive task")
    budget = storage.Budget()
    archive, checkout = storage.safe_path(archive), storage.safe_path(checkout)
    before, before_signatures = storage.inventory(archive, budget)
    trusted, trusted_signatures = reader.checkout_identity(checkout, revision, budget)
    with storage.staging(output, (archive, checkout, TOOLING_ROOT)) as stage:
        original = reader.reconstruct(
            task, archive, checkout, stage / "evidence", budget, timeout_seconds
        )
        _original_reports(task, before["files"], original)
        after, after_signatures = storage.inventory(archive, budget)
        storage.require(
            (after, after_signatures) == (before, before_signatures),
            "Source archive changed during reconstruction",
        )
        evidence, _ = storage.inventory(stage / "evidence", budget)
        preview_files = {
            **{"archive/" + name: value for name, value in before["files"].items()},
            **{"reader/" + name: value for name, value in trusted["files"].items()},
            **{"evidence/" + name: value for name, value in evidence["files"].items()},
        }
        reader_directories = {
            str(parent)
            for name in trusted["files"]
            for parent in PurePosixPath(name).parents
            if str(parent) != "."
        }
        preview_directories = sorted(
            {"archive", "reader", "evidence"}
            | {"archive/" + name for name in before["directories"]}
            | {"reader/" + name for name in reader_directories}
            | {"evidence/" + name for name in evidence["directories"]}
        )
        preview = {
            "files": preview_files,
            "directories": preview_directories,
            "totals": {
                "files": len(preview_files),
                "entries": len(preview_files) + len(preview_directories),
                "bytes": sum(value["size"] for value in preview_files.values()),
            },
        }
        provisional = {
            "schema": SCHEMA,
            "task": task,
            "origin": {
                "archive_path": str(archive),
                "archive_inventory_sha256": _identity(storage.encoded(before)),
            },
            "reader": trusted | {"checkout_path": str(checkout)},
            "reconstruction": original,
            **preview,
        }
        _validate_manifest(provisional, budget)
        provisional_raw = storage.encoded(provisional)
        storage.require(
            len(provisional_raw) <= storage.MANIFEST_LIMIT, "Manifest exceeds byte limit"
        )
        storage.require(
            preview["totals"]["bytes"] + len(provisional_raw) <= storage.TOTAL_LIMIT,
            "Total package byte limit exceeded",
        )
        (stage / "archive").mkdir()
        copied, copied_signatures = storage.inventory(
            archive, budget, destination=stage / "archive"
        )
        storage.require(
            (copied, copied_signatures) == (before, before_signatures),
            "Source archive changed during export",
        )
        (stage / "reader").mkdir()
        preserved, preserved_signatures = reader.checkout_identity(
            checkout, revision, budget, destination=stage / "reader"
        )
        storage.require(
            (preserved, preserved_signatures) == (trusted, trusted_signatures),
            "Trusted reader changed during export",
        )
        payload, _ = storage.inventory(stage, budget)
        storage.require(
            payload == preview, "Preserved payload differs from bounded preflight inventory"
        )
        manifest = {
            "schema": SCHEMA,
            "task": task,
            "origin": {
                "archive_path": str(archive),
                "archive_inventory_sha256": _identity(storage.encoded(before)),
            },
            "reader": trusted | {"checkout_path": str(checkout)},
            "reconstruction": original,
            **payload,
        }
        _validate_manifest(manifest, budget)
        raw = storage.encoded(manifest)
        storage.require(len(raw) <= storage.MANIFEST_LIMIT, "Manifest exceeds byte limit")
        storage.require(
            payload["totals"]["bytes"] + len(raw) <= storage.TOTAL_LIMIT,
            "Total package byte limit exceeded",
        )
        (stage / "manifest.json").write_bytes(raw)
        _verified(stage, budget)
        final, final_signatures = storage.inventory(archive, budget)
        final_reader, final_reader_signatures = reader.checkout_identity(checkout, revision, budget)
        storage.require(
            (final, final_signatures) == (before, before_signatures),
            "Source archive changed before publication",
        )
        storage.require(
            (final_reader, final_reader_signatures) == (trusted, trusted_signatures),
            "Trusted reader changed before publication",
        )
        budget.check()
    return _result("export", manifest, raw, reconstructed=True, output=output)


@storage.cancellable
def restore_package(package, output):
    """Copy an integrity-verified whole package to a fresh destination; no execution."""
    budget = storage.Budget()
    package = storage.safe_path(package)
    manifest, raw, before, signatures = _verified(package, budget)
    storage.separate_recorded(str(Path(output).absolute()), manifest["origin"]["archive_path"])
    storage.separate_recorded(str(Path(output).absolute()), manifest["reader"]["checkout_path"])
    with storage.staging(output, (package, TOOLING_ROOT)) as stage:
        # Copy manifest as well, but verify the original immutable identity again.
        copied, _ = storage.inventory(package, budget, destination=stage)
        storage.require("manifest.json" in copied["files"], "Missing copied manifest")
        restored, restored_raw, restored_view, _ = _verified(stage, budget)
        storage.require(
            (restored, restored_raw, restored_view) == (manifest, raw, before),
            "Restored package differs",
        )
        current, current_raw, current_view, current_signatures = _verified(package, budget)
        storage.require(
            (current, current_raw, current_view, current_signatures)
            == (manifest, raw, before, signatures),
            "Source package changed during restore",
        )
        budget.check()
    return _result("restore", manifest, raw, output=output)


@storage.cancellable
def reconstruct_package(package, checkout, revision, output, *, timeout_seconds=120):
    """Run only fixed trusted checkout code, then compare its report to retained evidence."""
    budget = storage.Budget()
    package, checkout = storage.safe_path(package), storage.safe_path(checkout)
    manifest, raw, before, signatures = _verified(package, budget)
    storage.require(
        revision == manifest["reader"]["revision"],
        "Reader revision differs; use an explicit compatible clean checkout",
    )
    trusted, trusted_signatures = reader.checkout_identity(checkout, revision, budget)
    storage.require(
        trusted["files"] == manifest["reader"]["files"],
        "Trusted reader bytes differ from preserved reader identity",
    )
    output_path = native_absolute(output)
    for known_checkout in {checkout, TOOLING_ROOT}:
        if known_checkout in output_path.parents:
            from . import installed

            storage.require(
                installed.package_manifest(known_checkout, budget) is None,
                "Keep reconstructed output outside installed application sources",
            )
            allowed = known_checkout / "results"
            storage.require(
                allowed in output_path.parents,
                "Derived output inside checkout must be under results/",
            )
            storage.require(
                reader.git(
                    known_checkout,
                    "check-ignore",
                    "--no-index",
                    "--",
                    str(output_path),
                    budget=budget,
                ).strip(),
                "Derived output must be Git ignored",
            )
        else:
            storage.separate(output_path, known_checkout)
    with storage.staging(output, (package,)) as stage:
        actual = reader.reconstruct(
            manifest["task"],
            package / "archive",
            checkout,
            stage / "evidence",
            budget,
            timeout_seconds,
        )
        storage.require(
            actual["artifacts"] == manifest["reconstruction"]["artifacts"]
            and actual["complete"] == manifest["reconstruction"]["complete"],
            "Relocated fixed reader report differs from preserved reconstruction",
        )
        final_reader, final_reader_signatures = reader.checkout_identity(checkout, revision, budget)
        storage.require(
            (final_reader, final_reader_signatures) == (trusted, trusted_signatures),
            "Trusted reader changed during reconstruction",
        )
        current, current_raw, current_view, current_signatures = _verified(package, budget)
        storage.require(
            (current, current_raw, current_view, current_signatures)
            == (manifest, raw, before, signatures),
            "Package changed during reconstruction",
        )
        result = _result("reconstruct", manifest, raw, reconstructed=True, output=output)
        (stage / "result.json").write_bytes(storage.encoded(result))
        budget.check()
    return result
