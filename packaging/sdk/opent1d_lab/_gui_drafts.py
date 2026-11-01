"""Bounded revisioned concepts; never authoritative experiment evidence."""

import os
import re
import uuid
from datetime import UTC, datetime

from ._gui_files import decode, encoded, outside_projects, path, read, require, sha256

SCHEMA = "opent1d.gui-draft/1"
LIMITS = {
    "package.json": 128 * 1024,
    "observations.csv": 512 * 1024,
    "settings.json": 128 * 1024,
    "design.json": 128 * 1024,
    "development-package.json": 128 * 1024,
    "development-observations.csv": 512 * 1024,
    "config.json": 128 * 1024,
}
FILES = {
    "mmtt-sensitivity": {"package.json", "observations.csv", "settings.json"},
    "mmtt-sampling": set(LIMITS) - {"config.json"},
    "m4-study-installed": {"config.json"},
    "m3-compare": {"config.json"},
}
MAX_REVISIONS = 1024


def identity(value, size=32):
    require(
        isinstance(value, str) and re.fullmatch(r"[a-f0-9]{" + str(size) + "}", value),
        "Invalid concept identity",
    )
    return value


def raw_files(task, files):
    require(
        task in FILES and isinstance(files, dict) and set(files) == FILES[task],
        "Exact supported concept file roster required",
    )
    result = {}
    for name, value in files.items():
        require(isinstance(value, str), "UTF-8 input text required")
        try:
            raw = value.encode("utf-8", errors="strict")
        except UnicodeError:
            raise ValueError("Input contains an invalid Unicode surrogate") from None
        require(len(raw) <= LIMITS[name], "Concept input exceeds byte limit: " + name)
        result[name] = raw
    return result


def metadata(name, parent):
    require(
        isinstance(name, str)
        and 1 <= len(name.strip()) <= 100
        and all(c.isprintable() for c in name),
        "Enter a concept name (1–100 characters)",
    )
    if parent is not None:
        identity(parent, 64)
    return name.strip()


def content(record):
    return sha256(encoded({k: record[k] for k in ("task", "name", "parent", "files")}))


def sync(directory):
    descriptor = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def put(filename, raw):
    """Publish complete regular bytes; an interrupted temporary is diagnostic."""
    filename = outside_projects(filename)
    path(filename.parent, directory=True)
    if filename.exists():
        require(read(filename, 2 * 1024 * 1024) == raw, "Immutable concept file changed")
        return
    temporary = filename.with_name("pending-" + uuid.uuid4().hex)
    try:
        with temporary.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, filename)
        sync(filename.parent)
    finally:
        temporary.unlink(missing_ok=True)


class Drafts:
    def __init__(self, root):
        self.root = outside_projects(root)
        self.root.mkdir(exist_ok=True)
        path(self.root, directory=True)
        self.records, self.issues = {}, []
        entries = sorted(self.root.iterdir())
        require(len(entries) <= 200, "Concept catalog limit exceeded")
        for folder in entries:
            try:
                record = self.get(folder.name)
                self.remember(record)
            except (ValueError, OSError, KeyError, TypeError) as error:
                self.issues.append({"id": folder.name[:64], "error": str(error)[:500]})

    def chain(self, key):
        folder = path(self.root / identity(key), directory=True)
        head = decode(read(folder / "head.json", 4096))
        require(set(head) == {"version", "sha256"}, "Invalid concept head")
        pointer, records, seen = head, [], set()
        while pointer is not None:
            require(len(records) < MAX_REVISIONS, "Concept revision limit exceeded")
            version = identity(pointer["version"])
            require(
                version not in seen and set(pointer) == {"version", "sha256"},
                "Invalid concept revision chain",
            )
            seen.add(version)
            raw = read(folder / "versions" / (version + ".json"), 1024 * 1024)
            require(sha256(raw) == pointer["sha256"], "Concept revision changed")
            record = decode(raw)
            require(
                set(record)
                == {
                    "schema",
                    "id",
                    "project",
                    "task",
                    "origin",
                    "name",
                    "parent",
                    "revision",
                    "previous",
                    "files",
                    "validation",
                    "frozen_plan",
                    "saved_at",
                }
                and record["schema"] == SCHEMA
                and record["id"] == key,
                "Unsupported concept revision",
            )
            identity(record["project"])
            metadata(record["name"], record["parent"])
            require(
                record["task"] in FILES
                and isinstance(record["origin"], dict)
                and type(record["revision"]) is int
                and record["revision"] >= 1,
                "Invalid concept metadata",
            )
            require(
                isinstance(record["files"], dict) and set(record["files"]) == FILES[record["task"]],
                "Concept file roster differs",
            )
            for name, blob in record["files"].items():
                require(
                    set(blob) == {"sha256", "bytes"}
                    and type(blob["bytes"]) is int
                    and 0 <= blob["bytes"] <= LIMITS[name],
                    "Invalid concept blob",
                )
                identity(blob["sha256"], 64)
            require(
                record["validation"] is None or isinstance(record["validation"], dict),
                "Invalid saved concept validation",
            )
            if record["frozen_plan"] is not None:
                identity(record["frozen_plan"], 64)
            if records:
                require(
                    records[-1][1]["revision"] == record["revision"] + 1
                    and all(
                        records[0][1][name] == record[name]
                        for name in ("project", "task", "origin")
                    ),
                    "Concept revision association differs",
                )
            records.append((pointer, record))
            pointer = record["previous"]
        require(records[-1][1]["revision"] == 1, "Concept revision history incomplete")
        return folder, records

    def get(self, key, revision=None):
        folder, chain = self.chain(key)
        committed = len(chain)
        if revision is not None:
            indices = [i for i, (_, record) in enumerate(chain) if record["revision"] == revision]
            require(len(indices) == 1, "Unknown saved concept revision")
            chain = chain[indices[0] :]
        record = dict(chain[0][1])
        record["content_sha256"] = content(record)
        record["files"] = {
            name: self.blob(folder, blob).decode("utf-8", errors="strict")
            for name, blob in record["files"].items()
        }
        record["history"] = [
            {name: item[name] for name in ("revision", "name", "saved_at", "frozen_plan")}
            for _, item in chain
        ]
        versions = list((folder / "versions").iterdir())
        require(len(versions) <= MAX_REVISIONS + 64, "Concept orphan limit exceeded")
        record["uncommitted_versions"] = len(versions) - committed
        return record

    def blob(self, folder, blob):
        raw = read(folder / "blobs" / blob["sha256"], 512 * 1024)
        require(
            len(raw) == blob["bytes"] and sha256(raw) == blob["sha256"],
            "Concept input bytes changed",
        )
        return raw

    def summaries(self):
        return list(self.records.values())

    def remember(self, record):
        summary = {
            name: record[name]
            for name in (
                "id",
                "project",
                "task",
                "name",
                "parent",
                "revision",
                "saved_at",
                "frozen_plan",
                "uncommitted_versions",
            )
        }
        summary["validation"] = (
            {key: value for key, value in record["validation"].items() if key != "result"}
            if record["validation"]
            else None
        )
        self.records[record["id"]] = summary

    def create(self, project, task, name, files, *, parent=None, origin=None):
        require(len(list(self.root.iterdir())) < 200, "Concept catalog is full")
        identity(project)
        metadata(name, parent)
        raw_files(task, files)
        key = uuid.uuid4().hex
        folder = self.root / key
        folder.mkdir()
        for child in ("blobs", "versions"):
            (folder / child).mkdir()
        base = {
            "schema": SCHEMA,
            "id": key,
            "project": project,
            "task": task,
            "origin": origin or {"kind": "custom"},
            "revision": 0,
        }
        return self.commit(base, files, name, parent)

    def commit(self, current, files, name, parent, *, validation=None, frozen_plan=None):
        folder = path(self.root / current["id"], directory=True)
        require(current["revision"] < MAX_REVISIONS, "Concept revision limit; start a new concept")
        raw = raw_files(current["task"], files)
        blobs = list((folder / "blobs").iterdir())
        require(
            all(path(item).is_file() and item.stat().st_nlink == 1 for item in blobs),
            "Nonregular concept blob refused",
        )
        existing = {item.name for item in blobs}
        new = {sha256(value): value for value in raw.values() if sha256(value) not in existing}
        require(
            len(blobs) + len(new) <= 4096
            and sum(p.stat().st_size for p in blobs) + sum(map(len, new.values()))
            <= 64 * 1024 * 1024,
            "Concept storage limit exceeded",
        )
        references = {}
        for filename, value in raw.items():
            digest = sha256(value)
            put(folder / "blobs" / digest, value)
            references[filename] = {"sha256": digest, "bytes": len(value)}
        previous = decode(read(folder / "head.json", 4096)) if current["revision"] else None
        record = {k: current[k] for k in ("schema", "id", "project", "task", "origin")}
        record.update(
            name=metadata(name, parent),
            parent=parent,
            revision=current["revision"] + 1,
            previous=previous,
            files=references,
            validation=validation,
            frozen_plan=frozen_plan,
            saved_at=datetime.now(UTC).isoformat(),
        )
        if validation is not None:
            record["validation"] = {
                **validation,
                "revision": record["revision"],
                "content_sha256": content(record),
            }
        version, raw_record = uuid.uuid4().hex, encoded(record)
        require(
            len(raw_record) <= 1024 * 1024,
            "Concept revision exceeds its byte limit; the last saved revision remains intact",
        )
        put(folder / "versions" / (version + ".json"), raw_record)
        from ._gui_files import write

        write(folder / "head.json", {"version": version, "sha256": sha256(raw_record)})
        sync(folder)
        value = self.get(current["id"])
        self.remember(value)
        return value

    def current(self, key, revision, project):
        record = self.get(key)
        require(record["project"] == project, "Concept belongs to another project")
        require(
            type(revision) is int and record["revision"] == revision,
            "Concept changed in another tab. Reload its saved revision before saving",
        )
        return record

    def save(self, key, revision, project, name, parent, files):
        record = self.current(key, revision, project)
        metadata(name, parent)
        raw_files(record["task"], files)
        if all(record[k] == v for k, v in (("name", name), ("parent", parent), ("files", files))):
            return record
        # Editing a concept already frozen explicitly derives from that freeze.
        parent = record["frozen_plan"] or parent
        return self.commit(record, files, name, parent)

    def annotate(self, key, revision, project, validation, frozen_plan=None):
        record = self.current(key, revision, project)
        return self.commit(
            record,
            record["files"],
            record["name"],
            record["parent"],
            validation=validation,
            frozen_plan=frozen_plan,
        )

    def restore(self, key, revision, project, selected):
        record = self.current(key, revision, project)
        folder, chain = self.chain(key)
        candidates = [item for _, item in chain if item["revision"] == selected]
        require(len(candidates) == 1, "Unknown saved concept revision")
        previous = candidates[0]
        files = {
            name: self.blob(folder, blob).decode("utf-8", errors="strict")
            for name, blob in previous["files"].items()
        }
        return self.commit(
            record, files, previous["name"], record["frozen_plan"] or previous["parent"]
        )

    def clone_project(self, original, copied):
        for item in list(self.records.values()):
            if item["project"] == original:
                folder, chain = self.chain(item["id"])
                cloned = None
                for _, previous in reversed(chain):
                    files = {
                        name: self.blob(folder, blob).decode("utf-8", errors="strict")
                        for name, blob in previous["files"].items()
                    }
                    if cloned is None:
                        cloned = self.create(
                            copied,
                            previous["task"],
                            previous["name"],
                            files,
                            parent=previous["parent"],
                            origin={"kind": "project-copy", "draft": item["id"]},
                        )
                    else:
                        cloned = self.commit(
                            cloned,
                            files,
                            previous["name"],
                            previous["parent"],
                            frozen_plan=previous["frozen_plan"],
                        )
