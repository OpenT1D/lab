"""Bounded in-memory package inspection; no extraction, setup or authorization."""

import gzip
import hashlib
import io
import json
import tarfile

COMPRESSED_LIMIT = 32 * 1024 * 1024
EXPANDED_LIMIT = 64 * 1024 * 1024
MEMBER_LIMIT = 2048
FILE_LIMIT = 32 * 1024 * 1024


def require(ok, reason):
    if not ok:
        raise ValueError("LT1 archive preflight: " + reason)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate metadata key")
        result[key] = value
    return result


def regular_members(expanded):
    """Check raw headers before tarfile can hide GNU/PAX extension records.

    TarInfo.frombuf supplies stdlib checksum/header decoding. No filesystem
    extraction or metadata-extension processing is performed.
    """
    offset, count = 0, 0
    while offset + 512 <= len(expanded):
        block = expanded[offset : offset + 512]
        if block == bytes(512):
            require(len(expanded) - offset >= 1024 and not any(expanded[offset:]), "tar terminator")
            return
        member = tarfile.TarInfo.frombuf(block, "utf-8", "strict")
        count += 1
        require(count <= MEMBER_LIMIT, "member bound")
        require(
            member.type in {tarfile.REGTYPE, tarfile.AREGTYPE, tarfile.DIRTYPE},
            "member type or metadata",
        )
        require(0 <= member.size <= FILE_LIMIT, "member size")
        require(not member.isdir() or member.size == 0, "directory data")
        start = offset + 512
        end = start + member.size
        require(end <= len(expanded), "member truncation")
        yield member, expanded[start:end]
        offset = start + ((member.size + 511) // 512) * 512
    raise ValueError("LT1 archive preflight: missing tar terminator")


def inspect_archive(raw, expected):
    """Compare data against a reviewed inventory; success never grants admission.

    ``expected`` is a notice-inventory entry, not an execution grant. The caller
    supplies bounded archive bytes; no supplied paths/code are opened or run.
    Recognized notice members do not establish a complete inlined-license closure.
    """
    require(isinstance(raw, bytes) and len(raw) <= COMPRESSED_LIMIT, "compressed bound")
    require(digest(raw) == expected["archive_sha256"], "archive identity")
    root = expected["root"]
    require(root in {"package", "node"}, "archive root")
    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as compressed:
        expanded = compressed.read(EXPANDED_LIMIT + 1)
    require(len(expanded) <= EXPANDED_LIMIT, "expanded bound")
    files, directories = {}, set()
    metadata = None
    for member, payload in regular_members(expanded):
        name = member.name
        if member.isdir() and name.endswith("/"):
            name = name[:-1]
        require(
            isinstance(name, str)
            and "\\" not in name
            and "\x00" not in name
            and name.split("/")[0] == root
            and all(part and part not in {".", ".."} for part in name.split("/")),
            "member path",
        )
        require(name not in files and name not in directories, "duplicate member")
        parents = ["/".join(name.split("/")[:i]) for i in range(1, len(name.split("/")))]
        require(not any(parent in files for parent in parents), "file parent collision")
        if member.isdir():
            directories.add(name)
            continue
        require(name != root, "file at root")
        require(
            not any(path.startswith(name + "/") for path in (*files, *directories)),
            "file child collision",
        )
        files[name] = {"bytes": len(payload), "sha256": digest(payload)}
        if name == root + "/package.json":
            require(len(payload) <= 1024 * 1024, "package metadata bound")
            metadata = json.loads(payload, object_pairs_hook=unique_object)
            require(isinstance(metadata, dict), "package metadata")
    require(metadata is not None, "missing package metadata")
    for key, expected_key in (
        ("name", "name"),
        ("version", "version"),
        ("license", "declared_license"),
    ):
        require(metadata.get(key) == expected[expected_key], "package " + key)
    require(
        files[root + "/package.json"]["sha256"] == expected["package_json_sha256"], "package bytes"
    )
    require(bool(expected["notices"]), "notice roster")
    for notice in expected["notices"]:
        require(
            files.get(notice["path"]) == {"bytes": notice["bytes"], "sha256": notice["sha256"]},
            "notice bytes",
        )
    return {
        "schema": "opent1d.lt1-package-preflight/1",
        "archive_sha256": digest(raw),
        "name": metadata["name"],
        "version": metadata["version"],
        "declared_license": metadata["license"],
        "files": dict(sorted(files.items())),
        "directories": sorted(directories),
        "recognized_notices": expected["notices"],
        "complete_license_closure": False,
        "setup_authorized": False,
        "execution_authorized": False,
    }
