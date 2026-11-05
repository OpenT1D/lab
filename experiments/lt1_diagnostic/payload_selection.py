"""Pure proposed-payload selection; never stages files or grants authority."""

import json
import re

from experiments.lt1_diagnostic.archive_preflight import digest, require, unique_object


def filemap_digest(files):
    return digest(
        json.dumps(
            files, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
        ).encode()
    )


def relative_path(path):
    return (
        isinstance(path, str)
        and "\\" not in path
        and all(part and part not in {".", ".."} for part in path.split("/"))
    )


def summary_matches(files, expected, prefix):
    require(len(files) == expected[prefix + "files"], prefix + "file count")
    require(
        sum(value["bytes"] for value in files.values()) == expected[prefix + "payload_bytes"],
        prefix + "payload bytes",
    )
    require(
        filemap_digest(files) == expected[prefix + "filemap_sha256"], prefix + "filemap identity"
    )


def select_payload(reports, inventory_raw, profile_raw, expected_profile_sha256):
    """Require a trusted frozen profile and authentic preflight reports as inputs.

    Matching hashes of producer-supplied reports alone do not authenticate actual
    archive intake. The caller must retain archive_preflight evidence and review
    the expected profile digest. This function only transforms metadata in memory.
    """
    require(digest(profile_raw) == expected_profile_sha256, "selection profile bytes")
    profile = json.loads(profile_raw, object_pairs_hook=unique_object)
    require(profile["schema"] == "opent1d.lt1-headless-selection-proposal/1", "selection schema")
    require(
        profile["setup_authorized"] is False and profile["execution_authorized"] is False,
        "proposal authority",
    )
    require(
        profile["complete_remaining_embedded_license_closure"] is False
        and profile["functional_loader_qualification"] == "unrun",
        "proposal limits",
    )
    require(digest(inventory_raw) == profile["notice_inventory_sha256"], "notice inventory bytes")
    inventory = json.loads(inventory_raw, object_pairs_hook=unique_object)
    require(inventory["lock_sha256"] == profile["historical_lock_sha256"], "historical lock")
    packages = inventory["packages"]
    expected = {p["archive_sha256"]: p for p in packages}
    by_archive = {r["archive_sha256"]: r for r in reports}
    configured = {p["archive_sha256"]: p for p in profile["packages"]}
    require(
        len(expected)
        == len(packages)
        == len(by_archive)
        == len(reports)
        == len(configured)
        == len(profile["packages"]),
        "duplicate or missing package",
    )
    require(expected.keys() == by_archive.keys() == configured.keys(), "package roster")
    files, notices = {}, {}
    for sha, package in expected.items():
        report, selection = by_archive[sha], configured[sha]
        require(report["schema"] == "opent1d.lt1-package-preflight/1", "preflight schema")
        require(
            report["setup_authorized"] is False and report["execution_authorized"] is False,
            "preflight authority",
        )
        for key in ("name", "version"):
            require(report[key] == package[key] == selection[key], "package " + key)
        for key in ("lock_path", "root"):
            require(package[key] == selection[key], "package " + key)
        require(
            relative_path(package["lock_path"])
            and package["lock_path"].startswith("node_modules/"),
            "placement",
        )
        require(report["recognized_notices"] == package["notices"], "notice roster")
        require(report["declared_license"] == package["declared_license"], "declared license")
        mapped = {}
        for source, value in report["files"].items():
            require(
                relative_path(source) and source.startswith(package["root"] + "/"), "source path"
            )
            require(isinstance(value, dict) and set(value) == {"bytes", "sha256"}, "file metadata")
            require(
                type(value["bytes"]) is int
                and value["bytes"] >= 0
                and isinstance(value["sha256"], str)
                and re.fullmatch("[a-f0-9]{64}", value["sha256"]),
                "file identity",
            )
            target = "toolchain/" + package["lock_path"] + "/" + source[len(package["root"]) + 1 :]
            require(target not in files and target not in mapped, "placement collision")
            mapped[target] = dict(value)
        summary_matches(mapped, selection, "")
        files.update(mapped)
        for notice in package["notices"]:
            source = notice["path"]
            require(
                relative_path(source) and source.startswith(package["root"] + "/"), "notice path"
            )
            target = "toolchain/" + package["lock_path"] + "/" + source[len(package["root"]) + 1 :]
            value = {"bytes": notice["bytes"], "sha256": notice["sha256"]}
            require(files.get(target) == value and target not in notices, "notice bytes")
            notices[target] = value
    summary_matches(files, profile, "source_")
    excluded = profile["excluded"]
    require(set(excluded) == {"path", "bytes", "sha256"}, "exclusion fields")
    require(excluded["path"] not in notices, "notice exclusion")
    require(
        files.get(excluded["path"]) == {"bytes": excluded["bytes"], "sha256": excluded["sha256"]},
        "excluded bytes",
    )
    selected = {path: value for path, value in files.items() if path != excluded["path"]}
    summary_matches(selected, profile, "selected_")
    require(
        len(notices) == profile["recognized_notice_files"]
        and filemap_digest(notices) == profile["retained_notice_filemap_sha256"],
        "retained notice identity",
    )
    return {
        "schema": "opent1d.lt1-selected-headless-payload/1",
        "profile": profile["profile"],
        "profile_sha256": digest(profile_raw),
        "files": dict(sorted(selected.items())),
        "retained_notices": dict(sorted(notices.items())),
        "excluded": dict(excluded),
        "complete_remaining_embedded_license_closure": False,
        "functional_loader_qualification": "unrun",
        "setup_authorized": False,
        "execution_authorized": False,
    }
