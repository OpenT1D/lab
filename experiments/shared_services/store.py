"""Exclusive local project ledger with immutable, completely inventoried events."""

import contextlib
import os
import tempfile
from pathlib import Path

from experiments.catalogue.storage import decode, digest, encoded, fresh, load_sealed, seal
from experiments.durable_archives.storage import (
    Budget,
    exclusive_rename,
    inventory,
    safe_path,
)
from experiments.m3.researcher.intake import read_regular
from experiments.shared_contracts.core import require

SCHEMA = "opent1d.project-store/1"


def read(path):
    return decode(read_regular(path, 16 * 1024 * 1024, "project record"))


def write(path, value):
    with Path(path).open("xb") as stream:
        stream.write(encoded(value))
        stream.flush()
        os.fsync(stream.fileno())


def sync_directory(path):
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def snapshot(source, target):
    """Reuse bounded descriptor-based regular-file copying; no code is imported."""
    target = safe_path(target, fresh=True)
    target.mkdir()
    before, _ = inventory(source, Budget(), destination=target)
    after, _ = inventory(source, Budget())
    copied, _ = inventory(target, Budget())
    require(before == after == copied, "Snapshot changed during copy")
    return copied


def create(path, name):
    require(isinstance(name, str) and name.strip(), "Project name required")
    path = fresh(path)
    for child in ("events", "work", "pending"):
        (path / child).mkdir()
    (path / ".lock").touch(exist_ok=False)
    write(path / "HEAD.json", {"schema": SCHEMA, "count": 0, "tip": None})
    with opened(path, write_access=True) as store:
        store.append("project", {"name": name, "rights": "public-synthetic-fixture"})
    return path


@contextlib.contextmanager
def opened(path, *, write_access=False):
    # This first host matrix deliberately uses POSIX flock. Do not silently
    # claim Windows support through a weaker lock implementation.
    require(os.name == "posix", "Project service currently requires a POSIX host")
    import fcntl

    path = safe_path(path)
    read_regular(path / ".lock", 0, "project lock")
    with (path / ".lock").open("rb") as lease:
        try:
            fcntl.flock(lease, (fcntl.LOCK_EX if write_access else fcntl.LOCK_SH) | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("Project is in use; ownership cannot be adopted") from None
        store = Store(path, write_access)
        store._lease = lease
        try:
            store.inspect()
            yield store
        finally:
            store._lease = None
            store.writable = False
            fcntl.flock(lease, fcntl.LOCK_UN)


class Store:
    def __init__(self, path, writable):
        self.path, self.writable = path, writable
        self._lease = None

    def require_lease(self, *, write_access=False):
        require(
            self._lease is not None and not self._lease.closed,
            "An active project lease is required; reopen the project",
        )
        require(not write_access or self.writable, "Writable project lease required")

    def inspect(self):
        self.require_lease()
        require(
            {p.name for p in self.path.iterdir()}
            == {".lock", "HEAD.json", "events", "work", "pending"},
            "Unexpected project entry",
        )
        for name in ("events", "work", "pending"):
            safe_path(self.path / name)
        require(
            not list((self.path / "pending").iterdir()),
            "Uncommitted transaction; retain pending evidence",
        )
        head = read(self.path / "HEAD.json")
        require(
            isinstance(head, dict)
            and set(head) == {"schema", "count", "tip"}
            and head["schema"] == SCHEMA
            and type(head["count"]) is int
            and 0 <= head["count"] <= 100000,
            "Unsupported project head",
        )
        require(
            {p.name for p in (self.path / "events").iterdir()}
            == {f"{i:08d}" for i in range(1, head["count"] + 1)},
            "Lost, duplicate or uncommitted ledger event",
        )
        self.events, self.plans, self.attempts, self.finishes = [], {}, {}, {}
        tip = None
        for sequence in range(1, head["count"] + 1):
            folder = self.path / "events" / f"{sequence:08d}"
            safe_path(folder)
            inventory(folder, Budget())
            load_sealed(folder)
            event = read(folder / "event.json")
            require(
                isinstance(event, dict)
                and set(event) == {"schema", "sequence", "previous", "kind", "data"}
                and event["schema"] == SCHEMA
                and event["sequence"] == sequence
                and event["previous"] == tip,
                "Broken ledger chain",
            )
            tip = digest(read_regular(folder / "manifest.json", 16 * 1024 * 1024, "event seal"))
            self.apply(event, folder, tip)
            self.events.append((tip, event, folder))
        require(head["tip"] == tip, "Lost ledger suffix or changed event identity")
        active = set(self.attempts) - set(self.finishes)
        require(
            {p.name for p in (self.path / "work").iterdir()} <= active,
            "Unaccounted or duplicated attempt workspace",
        )
        for path in (self.path / "work").iterdir():
            safe_path(path)
        self.head = head
        return self

    def apply(self, event, folder, identity):
        data, kind = event["data"], event["kind"]
        require(isinstance(data, dict), "Invalid event data")
        if kind == "project":
            require(event["sequence"] == 1 and set(data) == {"name", "rights"}, "Project event")
            require(data["rights"] == "public-synthetic-fixture", "Unsupported project rights")
        elif kind == "freeze":
            from .routes import validate_freeze

            require(event["sequence"] > 1 and set(data) == {"parent", "descriptor"}, "Freeze event")
            parent = data["parent"]
            require(parent is None or parent in self.plans, "Missing prior parent plan")
            validate_freeze(folder / "plan", data["descriptor"], current=False)
            if parent is not None:
                require(
                    self.plans[parent][0]["task"] == data["descriptor"]["task"],
                    "Derived task differs",
                )
            self.plans[identity] = (data["descriptor"], folder / "plan")
        elif kind == "start":
            require(
                set(data) == {"plan", "ordinal", "retry_of", "mode", "host"}
                and data["plan"] in self.plans
                and data["mode"] in {"execute", "import"},
                "Invalid attempt start",
            )
            prior = [
                (key, row) for key, row in self.attempts.items() if row["plan"] == data["plan"]
            ]
            require(data["ordinal"] == len(prior) + 1, "Lost or duplicate attempt ordinal")
            require(
                data["retry_of"] == (prior[-1][0] if prior else None)
                and (not prior or prior[-1][0] in self.finishes),
                "Explicit retry must name the previous terminal attempt",
            )
            require(isinstance(data["host"], dict) and bool(data["host"]), "Missing attempt host")
            self.attempts[identity] = data
        elif kind == "finish":
            from .routes import validate_finish

            require(
                set(data) == {"attempt", "receipt", "result"}
                and data["attempt"] in self.attempts
                and data["attempt"] not in self.finishes,
                "Lost or duplicate terminal attempt",
            )
            attempt = self.attempts[data["attempt"]]
            descriptor, plan = self.plans[attempt["plan"]]
            validate_finish(folder / "evidence", data, descriptor, plan)
            self.finishes[data["attempt"]] = (data, folder / "evidence")
        elif kind == "reconstruct":
            require(
                set(data) == {"attempt", "status", "reader", "report_sha256"}
                and data["attempt"] in self.finishes
                and data["status"] == "verified",
                "Invalid reconstruction event",
            )
            descriptor = self.plans[self.attempts[data["attempt"]]["plan"]][0]
            result = self.finishes[data["attempt"]][0]["result"]
            require(
                data["reader"] == descriptor["reader"]
                and data["report_sha256"] == result["report_sha256"]
                and result["payload"] == "native",
                "Reconstruction binding differs",
            )
        else:
            raise ValueError("Unsupported ledger event")
        require(event["sequence"] == 1 or self.events, "Missing project genesis")

    def append(self, kind, data, populate=None):
        self.require_lease(write_access=True)
        staging = Path(tempfile.mkdtemp(prefix="event-", dir=self.path / "pending"))
        sequence = self.head["count"] + 1
        event = {
            "schema": SCHEMA,
            "sequence": sequence,
            "previous": self.head["tip"],
            "kind": kind,
            "data": data,
        }
        if populate is not None:
            populate(staging)
        write(staging / "event.json", event)
        inventory(staging, Budget())
        seal(staging)
        # Sync every saved payload before committing its roster. No replacement
        # or pruning API is provided. Failed transactions remain in pending/.
        for path in staging.rglob("*"):
            if path.is_file():
                with path.open("rb") as stream:
                    os.fsync(stream.fileno())
        for directory in sorted(
            (path for path in staging.rglob("*") if path.is_dir()),
            key=lambda path: len(path.parts),
            reverse=True,
        ):
            sync_directory(directory)
        sync_directory(staging)
        identity = digest((staging / "manifest.json").read_bytes())
        destination = self.path / "events" / f"{sequence:08d}"
        exclusive_rename(staging, destination)
        sync_directory(self.path / "events")
        head = {"schema": SCHEMA, "count": sequence, "tip": identity}
        temporary = self.path / "pending" / "HEAD.json"
        write(temporary, head)
        os.replace(temporary, self.path / "HEAD.json")
        sync_directory(self.path)
        self.head = head
        return identity

    def relocate(self, output):
        """Export the entire ledger; native/opaque files remain byte identical."""
        self.require_lease()
        require(
            not (set(self.attempts) - set(self.finishes)),
            "Recover unfinished attempts before export",
        )
        output = safe_path(output, fresh=True)
        require(
            not output.exists() and not output.is_relative_to(self.path),
            "Fresh separate destination required",
        )
        snapshot(self.path, output)
        with opened(output):
            pass
        return output
