"""Create and verify local evidence bundles outside Git; never extract archives."""

import argparse
import hashlib
import json
import tarfile
from pathlib import Path


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify(destination):
    manifest = json.loads((destination / "archive.json").read_text())
    archive = destination / "evidence.tar.gz"
    if manifest.get("status") != "completed" or digest(archive) != manifest["archive_sha256"]:
        raise ValueError("Archive status or checksum differs")
    observed = {}
    with tarfile.open(archive, "r:gz") as tar:
        for member in tar:
            if not member.isfile() or member.name in observed:
                raise ValueError("Unexpected archive member")
            with tar.extractfile(member) as stream:
                observed[member.name] = hashlib.file_digest(stream, "sha256").hexdigest()
    if observed != manifest["files_sha256"]:
        raise ValueError("Archived files differ from inventory")
    return manifest


def verify_index(destination, index_path):
    index = json.loads(index_path.read_text())
    seen = set()
    for entry in index["archives"]:
        name = entry["directory"]
        if name in seen or Path(name).name != name or name in {".", ".."}:
            raise ValueError("Invalid archive directory in index")
        seen.add(name)
        folder = destination / name
        if digest(folder / "archive.json") != entry["inventory_sha256"]:
            raise ValueError(f"Inventory differs from tracked index: {name}")
        manifest = verify(folder)
        if (
            manifest["archive_sha256"] != entry["archive_sha256"]
            or len(manifest["files_sha256"]) != entry["file_count"]
        ):
            raise ValueError(f"Archive differs from tracked index: {name}")
    return {"status": "completed", "verified_archives": len(seen)}


def create(source, destination):
    source, destination = source.resolve(), destination.resolve()
    if not source.is_dir() or destination.is_relative_to(source):
        raise ValueError("Use an existing source and a destination outside it")
    paths = sorted(source.rglob("*"))
    if any(p.is_symlink() or not (p.is_file() or p.is_dir()) for p in paths):
        raise ValueError("Evidence sources must contain only regular files and directories")
    files = [p for p in paths if p.is_file()]
    if not files:
        raise ValueError("No evidence files")
    inventory = {str(p.relative_to(source)): digest(p) for p in files}
    destination.mkdir(parents=True, exist_ok=False)
    manifest = {"schema_version": 1, "status": "started", "files_sha256": inventory}
    metadata = destination / "archive.json"
    metadata.write_text(json.dumps(manifest, indent=2) + "\n")
    try:
        with tarfile.open(destination / "evidence.tar.gz", "w:gz") as tar:
            for path in files:
                tar.add(path, arcname=str(path.relative_to(source)), recursive=False)
        manifest.update(status="completed", archive_sha256=digest(destination / "evidence.tar.gz"))
        metadata.write_text(json.dumps(manifest, indent=2) + "\n")
        verify(destination)
    except BaseException as error:
        manifest.update(status="failed", error=str(error))
        metadata.write_text(json.dumps(manifest, indent=2) + "\n")
        raise
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--destination", required=True, type=Path)
    parser.add_argument("--index", type=Path)
    args = parser.parse_args()
    if args.index:
        if args.source:
            parser.error("--index verifies an existing store; do not combine with --source")
        print(json.dumps(verify_index(args.destination, args.index)))
    else:
        result = create(args.source, args.destination) if args.source else verify(args.destination)
        print(json.dumps({"status": result["status"], "archive_sha256": result["archive_sha256"]}))
