"""Prepare selected package bytes in memory; never extracts an environment."""

import gzip
import io
import json

from experiments.lt1_diagnostic.archive_preflight import (
    EXPANDED_LIMIT,
    digest,
    inspect_archive,
    regular_members,
    unique_object,
)
from experiments.lt1_diagnostic.payload_selection import select_payload


def package_blobs(archives, inventory_raw, profile_raw, expected_profile_sha256):
    inventory = json.loads(inventory_raw, object_pairs_hook=unique_object)
    expected = {row["archive_sha256"]: row for row in inventory["packages"]}
    if (
        not 0 < len(expected) == len(inventory["packages"]) == len(archives) <= 64
        or expected.keys() != archives.keys()
    ):
        raise ValueError("Exact package archive roster required")
    if sum(len(raw) for raw in archives.values()) > 512 * 1024 * 1024:
        raise ValueError("Package acquisition bytes exceed bound")
    reports = [inspect_archive(archives[sha], row) for sha, row in expected.items()]
    selected = select_payload(reports, inventory_raw, profile_raw, expected_profile_sha256)
    payload = {}
    for sha, package in expected.items():
        with gzip.GzipFile(fileobj=io.BytesIO(archives[sha])) as compressed:
            expanded = compressed.read(EXPANDED_LIMIT + 1)
        if len(expanded) > EXPANDED_LIMIT:
            raise ValueError("Expanded package exceeds bound")
        for member, raw in regular_members(expanded):
            if member.isdir():
                continue
            target = (
                "toolchain/" + package["lock_path"] + "/" + member.name[len(package["root"]) + 1 :]
            )
            if target in selected["files"]:
                if {"bytes": len(raw), "sha256": digest(raw)} != selected["files"][target]:
                    raise ValueError("Selected package bytes changed")
                payload[target] = raw
    if payload.keys() != selected["files"].keys():
        raise ValueError("Selected package member missing")
    return payload, selected
