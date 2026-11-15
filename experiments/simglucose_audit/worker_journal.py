"""Exclusive durable invented-worker evidence; never authenticated OS evidence.

Saved PIDs are observations only. Neither readers nor this journal act on saved
PIDs. Byte/hash chains detect changes against caller-held pins, not fabrication
by an actor able to rewrite the entire evidence and the caller's trusted pins.
"""

import os
import re
import stat
import threading
import time
from pathlib import Path

from . import worker_fixture as worker
from .contract import AUTHORITY, decode, digest, encode, fields, require

SCHEMA = "opent1d.simglucose-audit1-worker-journal/1"
NAMES = {
    "request.bin",
    "events.jsonl",
    "report.json",
    "outer.json",
    "manifest.json",
    "completion-intent.json",
    "completed.json",
    "finalization-error.json",
}
MAX_BYTES = worker.MAX_BYTES


def _valid_name(name):
    return type(name) is str and (name in NAMES or re.fullmatch(r"frame-[0-3]\.bin", name))


def _identity():
    return worker._identity() | {"worker_journal.py": digest(Path(__file__).read_bytes())}


def _directory(path, create=False):
    """Traverse caller-trusted absolute directories without symlink traversal."""
    path = Path(path)
    require(
        path.is_absolute() and ".." not in path.parts and len(path.parts) > 1,
        "fresh-private-absolute-destination",
    )
    require(hasattr(os, "O_NOFOLLOW") and hasattr(os, "O_DIRECTORY"), "nofollow-directory-required")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = os.open(path.anchor, flags)
    try:
        for index, component in enumerate(path.parts[1:]):
            if create and index == len(path.parts) - 2:
                os.mkdir(component, 0o700, dir_fd=fd)  # Exclusive: never reuse.
                os.fsync(fd)
            next_fd = os.open(component, flags, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        return fd
    except BaseException:
        os.close(fd)
        raise


def _write(fd, raw):
    view = memoryview(raw)
    while view:
        count = os.write(fd, view)
        require(count > 0, "journal-short-write")
        view = view[count:]


class _JournalSink:
    """Concrete internal sink, not a supplied callback/factory interface."""

    def __init__(self, destination, raw):
        self.error = None
        self.lock = threading.Lock()
        self.fd = _directory(destination, create=True)
        self.events_fd = None
        self.events_raw = b""
        self.files = {}
        self.sequence = 0
        self.previous = None
        self.frame_count = 0
        self.launch = None
        self.joined = None
        try:
            self.source = _identity()
            self.owner = worker._owner_identity()
            self._file("request.bin", raw)
            self.events_fd = os.open(
                "events.jsonl",
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
                dir_fd=self.fd,
            )
            os.fsync(self.fd)
            self._record(
                "header",
                {
                    "schema": SCHEMA,
                    "kind": "invented",
                    "request_sha256": digest(raw),
                    "source_identity": self.source,
                    "process_owner_source_identity": self.owner,
                    "parent_pid": os.getpid(),
                    "authority": dict(AUTHORITY),
                },
            )
        except BaseException:
            self._close()
            raise

    def _file(self, name, raw):
        require(_valid_name(name), "fixed-journal-filename")
        fd = os.open(
            name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=self.fd
        )
        try:
            _write(fd, raw)
            os.fsync(fd)
        finally:
            os.close(fd)
        os.fsync(self.fd)
        self.files[name] = raw

    def _record(self, event, data):
        with self.lock:
            if self.error:
                return
            try:
                if event == "raw-frame":
                    require(self.frame_count < 4, "bounded-journal-frames")
                    raw = data["raw"]
                    name = f"frame-{self.frame_count}.bin"
                    self._file(name, raw)
                    self.frame_count += 1
                    data = {"name": name, "bytes": len(raw), "sha256": digest(raw)}
                row = {
                    "sequence": self.sequence,
                    "previous_sha256": self.previous,
                    "monotonic_ns": time.monotonic_ns(),
                    "event": event,
                    "data": data,
                }
                raw = encode(row) + b"\n"
                require(len(self.events_raw) + len(raw) <= MAX_BYTES, "bounded-journal-events")
                _write(self.events_fd, raw)
                os.fsync(self.events_fd)
                self.events_raw += raw
                self.previous = digest(raw)
                self.sequence += 1
                if event == "launch":
                    self.launch = data
                if event == "io-joined":
                    self.joined = data
            except (OSError, ValueError):
                self.error = "journal-write-failed"

    def _finish_events(self):
        if self.events_fd is not None:
            try:
                os.fsync(self.events_fd)
            except OSError:
                self.error = self.error or "journal-write-failed"
            finally:
                fd, self.events_fd = self.events_fd, None
                try:
                    os.close(fd)
                except OSError:
                    self.error = self.error or "journal-close-failed"
        self.files["events.jsonl"] = self.events_raw

    def _close(self):
        for name in ("events_fd", "fd"):
            fd = getattr(self, name)
            if fd is not None:
                setattr(self, name, None)
                try:
                    os.close(fd)
                except OSError:
                    self.error = self.error or "journal-close-failed"


def run_journal_fixture(request_raw, destination):
    """Create one fresh private attempt after strict invented-only intake."""
    worker._request(request_raw)
    sink = _JournalSink(destination, request_raw)
    report, result = None, None
    try:
        if sink.error:
            result = {
                "kind": "invented",
                "status": "failed",
                "worker_report": None,
                "manifest_sha256": None,
                "request_sha256": digest(request_raw),
                "journal_error": sink.error,
                "host_or_process_qualified": False,
            }
            return result
        report = worker._run_worker_fixture(request_raw, _sink=sink)
        report_raw = encode(report)
        sink._record("worker-report", {"sha256": digest(report_raw)})
        sink._finish_events()
        joined = sink.joined
        eligible = (
            report["status"] == "completed"
            and report["primary_error"] is None
            and report["cleanup_error"] is None
            and report["owned_stop_observed"] is True
            and joined is not None
            and joined["reader_joined"] is True
            and joined["writer_joined"] is True
            and type(joined["returncode"]) is int
            and joined["returncode"] == 0
            and joined["cleanup_error"] is None
            and sink.error is None
            and _identity() == sink.source
            and worker._owner_identity() == sink.owner
        )
        status = (
            "failed"
            if sink.error
            else report["status"]
            if report["status"] != "completed"
            else "completed"
            if eligible
            else "incomplete"
        )
        outer = {
            "schema": SCHEMA,
            "kind": "invented",
            "status": status,
            "parent_pid": os.getpid(),
            "child_pid": sink.launch["child_pid"] if sink.launch else None,
            "io_joined": joined,
            "journal_error": sink.error,
            "worker_report_sha256": digest(report_raw),
            "host_or_process_qualified": False,
            "authority": dict(AUTHORITY),
        }
        if sink.error is None:
            try:
                sink._file("report.json", report_raw)
                sink._file("outer.json", encode(outer))
                marker_raw = None
                if eligible:
                    marker_raw = encode(
                        {
                            "schema": SCHEMA,
                            "kind": "invented",
                            "request_sha256": digest(request_raw),
                            "events_sha256": digest(sink.events_raw),
                            "report_sha256": digest(report_raw),
                            "outer_sha256": digest(encode(outer)),
                        }
                    )
                    sink._file("completion-intent.json", marker_raw)
                roster = {
                    name: {"sha256": digest(raw), "bytes": len(raw)}
                    for name, raw in sink.files.items()
                }
                if marker_raw:
                    roster["completed.json"] = {
                        "sha256": digest(marker_raw),
                        "bytes": len(marker_raw),
                    }
                manifest = {
                    "schema": SCHEMA,
                    "kind": "invented",
                    "status": status,
                    "source_identity": sink.source,
                    "request_sha256": digest(request_raw),
                    "files": roster,
                }
                manifest_raw = encode(manifest)
                sink._file("manifest.json", manifest_raw)
                if marker_raw:
                    os.link(
                        "completion-intent.json",
                        "completed.json",
                        src_dir_fd=sink.fd,
                        dst_dir_fd=sink.fd,
                        follow_symlinks=False,
                    )
                    os.fsync(sink.fd)
                result = {
                    "kind": "invented",
                    "status": status,
                    "worker_report": report,
                    "manifest_sha256": digest(manifest_raw),
                    "request_sha256": digest(request_raw),
                    "journal_error": None,
                    "host_or_process_qualified": False,
                }
                return result
            except (OSError, ValueError):
                sink.error = "journal-write-failed"
                try:
                    sink._file(
                        "finalization-error.json", encode({"kind": "invented", "error": sink.error})
                    )
                except (OSError, ValueError):
                    pass  # Preserve available prefix; never remove a file.
        # Best effort independent diagnostics after a sticky recording failure.
        # Exclusive writes never replace partially written evidence.
        for name, raw in (("report.json", report_raw), ("outer.json", encode(outer))):
            if name not in sink.files:
                try:
                    sink._file(name, raw)
                except (OSError, ValueError):
                    pass
        result = {
            "kind": "invented",
            "status": "failed",
            "worker_report": report,
            "manifest_sha256": None,
            "request_sha256": digest(request_raw),
            "journal_error": sink.error,
            "host_or_process_qualified": False,
        }
        return result
    finally:
        sink._close()
        if result is not None and sink.error:
            result.update(status="failed", manifest_sha256=None, journal_error=sink.error)


def read_journal(destination):
    """Bounded fixed-roster byte loader only; supplies no validated completion."""
    directory = _directory(destination)
    try:
        names = os.listdir(directory)
        require(
            len(names) <= 12 and all(_valid_name(name) for name in names), "fixed-journal-roster"
        )
        result = {}
        for name in names:
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
            try:
                require(stat.S_ISREG(os.fstat(fd).st_mode), "journal-regular-file")
                raw = os.read(fd, MAX_BYTES + 2)
                require(len(raw) <= MAX_BYTES + 1 and not os.read(fd, 1), "bounded-journal-file")
                result[name] = raw
            finally:
                os.close(fd)
        _buffers(result)
        return result
    finally:
        os.close(directory)


def _buffers(files):
    require(
        type(files) is dict
        and len(files) <= 12
        and all(
            _valid_name(name) and type(raw) is bytes and len(raw) <= MAX_BYTES + 1
            for name, raw in files.items()
        ),
        "bounded-journal-buffers",
    )
    require(sum(map(len, files.values())) <= 8 * MAX_BYTES, "bounded-journal-total")
    require("request.bin" in files and "events.jsonl" in files, "journal-prefix-files")


def _events(files, expected_request_sha256):
    _buffers(files)
    raw = files["request.bin"]
    require(digest(raw) == expected_request_sha256, "external-journal-request-pin")
    request = worker._request(raw)
    lines = files["events.jsonl"].splitlines(keepends=True)
    require(len(lines) <= 32, "bounded-journal-sequence")
    torn = bool(lines and not lines[-1].endswith(b"\n"))
    if torn:
        lines.pop()
    previous, rows, frames, launch, joined, report_pin = None, [], [], None, None, None
    seen = {}
    for sequence, line in enumerate(lines):
        row = decode(line)
        fields(row, "sequence previous_sha256 monotonic_ns event data", "journal-event-fields")
        require(
            type(row["sequence"]) is int
            and row["sequence"] == sequence
            and row["previous_sha256"] == previous,
            "journal-sequence-chain",
        )
        require(
            type(row["monotonic_ns"]) is int
            and row["monotonic_ns"] >= 0
            and (not rows or row["monotonic_ns"] >= rows[-1]["monotonic_ns"]),
            "journal-observation-clock",
        )
        event, data = row["event"], row["data"]
        require(type(event) is str and type(data) is dict, "journal-event-data")
        require(report_pin is None, "journal-report-is-last")
        if sequence:
            require(event != "header", "single-journal-header")
            if event != "raw-frame":
                require(event not in seen, "single-journal-observation")
            if event not in ("launch", "launch-refused", "worker-report"):
                require(launch is not None, "journal-observation-after-launch")
            if event in ("raw-frame", "input-closed", "stdout-eof"):
                require(joined is None, "journal-io-before-join")
        seen[event] = data
        if sequence == 0:
            fields(
                data,
                "schema kind request_sha256 source_identity process_owner_source_identity "
                "parent_pid authority",
                "journal-header-fields",
            )
            require(
                event == "header"
                and data["schema"] == SCHEMA
                and data["kind"] == "invented"
                and data["request_sha256"] == digest(raw)
                and data["source_identity"] == _identity()
                and data["process_owner_source_identity"] == worker._owner_identity()
                and encode(data["authority"]) == encode(AUTHORITY)
                and type(data["parent_pid"]) is int
                and data["parent_pid"] > 0,
                "journal-header-binding",
            )
        elif event == "launch":
            fields(data, "parent_pid child_pid", "journal-launch-fields")
            require(
                launch is None
                and data["parent_pid"] == rows[0]["data"]["parent_pid"]
                and type(data["child_pid"]) is int
                and data["child_pid"] > 0
                and data["child_pid"] != data["parent_pid"],
                "journal-launch-observation",
            )
            launch = data
        elif event == "raw-frame":
            fields(data, "name bytes sha256", "journal-frame-fields")
            require(
                launch is not None
                and data["name"] == f"frame-{len(frames)}.bin"
                and data["name"] in files
                and type(data["bytes"]) is int
                and data["bytes"] == len(files[data["name"]])
                and data["sha256"] == digest(files[data["name"]]),
                "journal-raw-frame-binding",
            )
            frames.append(files[data["name"]])
        elif event == "input-closed":
            fields(data, "attempted_bytes error", "journal-input-fields")
            require(
                launch is not None
                and type(data["attempted_bytes"]) is int
                and data["attempted_bytes"] == len(raw)
                and data["error"] in (None, "worker-input-failed"),
                "journal-input-observation",
            )
        elif event in ("stdout-eof", "force-request", "launch-refused"):
            require(data == {}, "journal-empty-event")
            if event == "force-request":
                require(
                    "stop-poll" in seen and seen["stop-poll"]["returncode"] is None,
                    "no-force-after-exit",
                )
            if event == "launch-refused":
                require(launch is None, "no-refusal-after-launch")
        elif event in ("stop-poll", "wait-return"):
            fields(data, "returncode", "journal-return-fields")
            require(
                data["returncode"] is None or type(data["returncode"]) is int,
                "journal-return-observation",
            )
        elif event == "group-observation":
            require("stop-poll" in seen, "group-after-stop-poll")
            fields(data, "remaining", "journal-group-fields")
            require(type(data["remaining"]) is bool, "journal-group-observation")
        elif event == "io-joined":
            require("stop-poll" in seen, "join-after-stop")
            fields(
                data, "reader_joined writer_joined returncode cleanup_error", "journal-join-fields"
            )
            require(
                joined is None
                and type(data["reader_joined"]) is bool
                and type(data["writer_joined"]) is bool
                and (data["returncode"] is None or type(data["returncode"]) is int)
                and data["cleanup_error"]
                in (
                    None,
                    "owned-tree-remains",
                    "owned-stop-failed",
                    "worker-reader-not-joined",
                    "worker-writer-not-joined",
                ),
                "journal-join-observation",
            )
            joined = data
        elif event == "worker-report":
            fields(data, "sha256", "journal-report-fields")
            require(
                report_pin is None and (joined is not None or "launch-refused" in seen),
                "journal-report-after-cleanup",
            )
            report_pin = data["sha256"]
        else:
            raise ValueError("fixed-journal-event")
        rows.append(row)
        previous = digest(line)
    require(rows, "journal-header-required")
    return request, rows, frames, launch, joined, report_pin, torn


def inspect_journal_prefix(files, expected_events_sha256, expected_request_sha256):
    """Check a pinned crash prefix; its status always remains incomplete."""
    _buffers(files)
    require(digest(files["events.jsonl"]) == expected_events_sha256, "external-journal-events-pin")
    identity = _identity()
    _request, rows, frames, _launch, _joined, _report_pin, torn = _events(
        files, expected_request_sha256
    )
    require(_identity() == identity, "journal-prefix-source-changed")
    return {
        "kind": "invented",
        "status": "incomplete",
        "events": len(rows),
        "raw_frames": len(frames),
        "torn_tail": torn,
        "host_or_process_qualified": False,
        "authority": dict(AUTHORITY),
    }


def inspect_journal(files, expected_manifest_sha256, expected_request_sha256):
    """Inspect with a caller-held producer pin from successful finalization.

    Computing a new pin from a found marker/manifest does not establish that
    finalization returned successfully. This is a cooperative trust assumption.
    Persisted PIDs never authorize process control.
    """
    _buffers(files)
    require("finalization-error.json" not in files, "journal-finalization-error")
    identity = _identity()
    require(
        "manifest.json" in files and digest(files["manifest.json"]) == expected_manifest_sha256,
        "external-journal-manifest-pin",
    )
    manifest = decode(files["manifest.json"])
    fields(
        manifest,
        "schema kind status source_identity request_sha256 files",
        "journal-manifest-fields",
    )
    require(
        manifest["schema"] == SCHEMA
        and manifest["kind"] == "invented"
        and manifest["source_identity"] == _identity()
        and manifest["request_sha256"] == expected_request_sha256,
        "journal-manifest-binding",
    )
    roster = manifest["files"]
    require(
        type(roster) is dict
        and all(_valid_name(name) and name != "manifest.json" for name in roster),
        "fixed-manifest-roster",
    )
    missing_marker = "completed.json" in roster and "completed.json" not in files
    require(
        set(files) - {"manifest.json"}
        == set(roster) - ({"completed.json"} if missing_marker else set()),
        "journal-roster-closure",
    )
    for name, pin in roster.items():
        fields(pin, "sha256 bytes", "journal-member-pin-fields")
        if name not in files:
            continue
        require(
            type(pin["bytes"]) is int
            and pin["bytes"] == len(files[name])
            and pin["sha256"] == digest(files[name]),
            "journal-member-pin",
        )
    request, rows, frames, launch, joined, report_pin, torn = _events(
        files, expected_request_sha256
    )
    require(
        not torn and "report.json" in files and "outer.json" in files, "finalized-journal-required"
    )
    report = decode(files["report.json"])
    worker.inspect_worker_fixture(
        files["report.json"],
        digest(files["report.json"]),
        files["request.bin"],
        expected_request_sha256,
    )
    require(report_pin == digest(files["report.json"]), "journal-report-event-binding")
    expected = [
        {
            "phase": "ready",
            "request_sha256": expected_request_sha256,
            "source_identity": worker._identity(),
        },
        worker._expected_result(request, worker._identity()),
        {"phase": "finished"},
    ]
    for index, phase in enumerate(report["frames_received"]):
        require(
            index < len(frames)
            and frames[index] == encode(expected[index]) + b"\n"
            and phase == expected[index]["phase"],
            "journal-report-frame-binding",
        )
    outer = decode(files["outer.json"])
    fields(
        outer,
        "schema kind status parent_pid child_pid io_joined journal_error "
        "worker_report_sha256 host_or_process_qualified authority",
        "journal-outer-fields",
    )
    require(
        outer["schema"] == SCHEMA
        and outer["kind"] == "invented"
        and outer["parent_pid"] == rows[0]["data"]["parent_pid"]
        and outer["child_pid"] == (launch["child_pid"] if launch else None)
        and encode(outer["io_joined"]) == encode(joined)
        and outer["journal_error"] is None
        and outer["worker_report_sha256"] == report_pin
        and outer["host_or_process_qualified"] is False
        and encode(outer["authority"]) == encode(AUTHORITY)
        and outer["status"] == manifest["status"]
        and (
            manifest["status"] == report["status"]
            or report["status"] == "completed"
            and manifest["status"] == "incomplete"
        ),
        "journal-outer-binding",
    )
    marker_present = "completed.json" in files
    if marker_present:
        observations = {row["event"]: row["data"] for row in rows}
        require(
            len(frames) == 3
            and "force-request" not in observations
            and observations.get("stdout-eof") == {}
            and observations.get("input-closed")
            == {"attempted_bytes": len(files["request.bin"]), "error": None}
            and observations.get("wait-return") == {"returncode": 0}
            and observations.get("stop-poll") == {"returncode": 0}
            and observations.get("group-observation") == {"remaining": False},
            "journal-complete-lifecycle-sequence",
        )
        require(
            manifest["status"] == report["status"] == "completed"
            and report["primary_error"] is None
            and report["cleanup_error"] is None
            and report["owned_stop_observed"] is True
            and joined is not None
            and joined["reader_joined"] is True
            and joined["writer_joined"] is True
            and type(joined["returncode"]) is int
            and joined["returncode"] == 0
            and joined["cleanup_error"] is None,
            "journal-completion-observations",
        )
        marker = {
            "schema": SCHEMA,
            "kind": "invented",
            "request_sha256": expected_request_sha256,
            "events_sha256": digest(files["events.jsonl"]),
            "report_sha256": report_pin,
            "outer_sha256": digest(files["outer.json"]),
        }
        require(
            files["completed.json"] == files.get("completion-intent.json") == encode(marker),
            "journal-completion-marker",
        )
    require(_identity() == identity, "journal-readback-source-changed")
    return {
        "kind": "invented",
        "status": "completed"
        if marker_present
        else "incomplete"
        if report["status"] == "completed"
        else report["status"],
        "worker_status": report["status"],
        "completion_marker": marker_present,
        "host_or_process_qualified": False,
        "authority": dict(AUTHORITY),
    }
