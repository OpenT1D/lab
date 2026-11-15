"""Generic streaming gzip/USTAR ceilings qualified only with generated inventions.

Actual inspection refuses before input/source/path access. Fixed fixture workers
never open an input path: they generate their own fresh private synthetic file.
Opaque drains include decompressed member bytes; nothing is extracted or loaded.
"""

import gzip
import hashlib
import json
import math
import os
import stat
import subprocess
import sys
import threading
import time
import unicodedata
import zlib
from datetime import UTC, datetime, timedelta
from pathlib import Path

from experiments import platform_process

from .contract import AUTHORITY, SOURCE_FILES, digest, encode, require

SCHEMA = "opent1d.pbs-production-reader-fixture/1"
LIMITS = {
    "compressed_bytes": 25172086,
    "decompressed_bytes": 512 * 1024 * 1024,
    "members": 20000,
    "member_bytes": 256 * 1024 * 1024,
    "path_utf8_bytes": 4096,
    "path_depth": 32,
    "inventory_bytes": 8 * 1024 * 1024,
}
MAX_REPORT_BYTES = 9 * 1024 * 1024
WHOLE_SECONDS = 300
STOP_SECONDS, JOIN_SECONDS = 2, 1
CAP_UTC = "2026-11-28T18:32:01Z"
SCENARIOS = frozenset(
    (
        "small",
        "member-exact",
        "member-over",
        "expanded-exact",
        "expanded-over",
        "roster-exact",
        "roster-over",
        "inventory-near",
        "inventory-exact",
        "inventory-over",
        "compressed-exact",
        "compressed-over",
        "compressed-gzip-exact",
        "compressed-gzip-over",
        "bad-checksum",
        "bad-gzip-crc",
        "trailing-gzip",
        "pax",
        "unsafe-path",
        "links",
        "deny-auth",
        "stall-generate",
        "stall-storage",
        "stall-report",
        "finish-block",
    )
)


def _decode(raw):
    require(type(raw) is bytes and 0 < len(raw) <= MAX_REPORT_BYTES + 65536, "bounded-json")
    depth, quoted, escaped = 0, False, False
    for value in raw:
        if quoted:
            if escaped:
                escaped = False
            elif value == 92:
                escaped = True
            elif value == 34:
                quoted = False
        elif value == 34:
            quoted = True
        elif value in (91, 123):
            depth += 1
            require(depth <= 64, "JSON-depth")
        elif value in (93, 125):
            depth -= 1

    def unique(pairs):
        result = {}
        for name, value in pairs:
            require(name not in result, "duplicate-JSON-field")
            result[name] = value
        return result

    def constant(_):
        raise ValueError("nonfinite-JSON")

    def finite(text):
        value = float(text)
        require(math.isfinite(value), "nonfinite-JSON")
        return value

    def integer(text):
        require(len(text) <= 20, "JSON-integer-width")
        return int(text)

    try:
        return json.loads(
            raw,
            object_pairs_hook=unique,
            parse_constant=constant,
            parse_float=finite,
            parse_int=integer,
        )
    except (UnicodeDecodeError, RecursionError) as error:
        raise ValueError("strict-JSON") from error


def inspect_archive(*_args, **_kwargs):
    raise PermissionError(
        "actual PBS inspection closed: crypto, custody and exact grant unadmitted"
    )


def _source_bytes(path, deadline):
    require(time.monotonic() < deadline, "source-read-deadline")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        require(
            stat.S_ISREG(before.st_mode) and 0 <= before.st_size <= 1024 * 1024,
            "bounded-regular-source",
        )
        require(
            _token(before) == _token(os.stat(path, follow_symlinks=False)), "source-name-binding"
        )
        chunks, size = [], 0
        while True:
            require(time.monotonic() < deadline, "source-read-deadline")
            raw = os.read(fd, min(65536, 1024 * 1024 - size + 1))
            if not raw:
                break
            chunks.append(raw)
            size += len(raw)
            require(size <= 1024 * 1024, "source-byte-cap")
        require(
            _token(before) == _token(os.fstat(fd)) == _token(os.stat(path, follow_symlinks=False))
            and size == before.st_size,
            "source-fd-name-stability",
        )
        return b"".join(chunks)
    finally:
        os.close(fd)


def _identity(deadline=None):
    deadline = time.monotonic() + 5 if deadline is None else min(deadline, time.monotonic() + 5)
    module = Path(__file__).absolute()
    root, package = module.parents[2], module.parent
    try:
        os.lstat(package.parent / "__init__.py")
    except FileNotFoundError:
        pass
    else:
        raise ValueError("fixed-parent-namespace-without-initializer")
    parent = sys.modules["experiments"]
    require(
        parent.__file__ is None and set(parent.__path__) == {str(package.parent)},
        "fixed-parent-namespace",
    )
    return (
        {name: digest(_source_bytes(package / name, deadline)) for name in SOURCE_FILES}
        | {
            "experiments/__init__.py": "namespace-initializer-absent",
            "pbs_production_inspection.py": digest(_source_bytes(module, deadline)),
        }
        | {
            name: digest(_source_bytes(root / name, deadline))
            for name in platform_process.SOURCE_FILES
        }
    )


def _now():
    return datetime.now(UTC)


def _stamp(value):
    return value.isoformat().replace("+00:00", "Z")


def _guard(deadline, expires):
    require(time.monotonic() < deadline, "whole-work-deadline")
    require(
        _now() < expires <= datetime.fromisoformat(CAP_UTC.replace("Z", "+00:00")),
        "current-retention-window",
    )


def _safe_text(raw):
    head, separator, tail = raw.partition(b"\0")
    require(not separator or not tail.strip(b"\0"), "NUL-field-padding")
    try:
        value = head.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("strict-UTF8-metadata") from error
    require(
        all(unicodedata.category(c) not in ("Cc", "Cf", "Cs", "Zl", "Zp") for c in value),
        "Unicode-control-metadata",
    )
    return value


def _path(value, directory=False):
    require(
        value
        and not value.startswith("/")
        and "\\" not in value
        and ":" not in value
        and "//" not in value
        and unicodedata.normalize("NFC", value) == value
        and all(unicodedata.category(c) not in ("Cc", "Cf", "Cs", "Zl", "Zp") for c in value),
        "canonical-relative-path",
    )
    value = value[:-1] if directory and value.endswith("/") else value
    parts = value.split("/")
    require(
        len(value.encode()) <= LIMITS["path_utf8_bytes"]
        and len(parts) <= LIMITS["path_depth"]
        and all(p not in ("", ".", "..") for p in parts),
        "path-depth-or-size",
    )
    return value


def _octal(raw, blank=False):
    require(raw[0] < 128, "no-base256")
    digits = raw.strip(b"\0 ")
    require((digits or blank) and all(48 <= c <= 55 for c in digits), "strict-octal")
    return int(digits, 8) if digits else 0


def _header(raw):
    require(
        len(raw) == 512 and raw[257:265] == b"ustar\x0000" and raw[500:] == b"\0" * 12,
        "POSIX-ustar-only",
    )
    require(sum(raw[:148]) + 8 * 32 + sum(raw[156:]) == _octal(raw[148:156]), "tar-checksum")
    kinds = {b"0": "file", b"\0": "file", b"5": "directory", b"2": "symlink", b"1": "hardlink"}
    require(raw[156:157] in kinds, "unsupported-extension-sparse-device-type")
    kind = kinds[raw[156:157]]
    name, prefix = _safe_text(raw[:100]), _safe_text(raw[345:500])
    path = _path(prefix + "/" + name if prefix else name, kind == "directory")
    size, mode = _octal(raw[124:136]), _octal(raw[100:108])
    require(size <= LIMITS["member_bytes"] and mode <= 0o777, "member-size-or-mode")
    for start, end in ((108, 116), (116, 124), (136, 148)):
        _octal(raw[start:end])
    require(_octal(raw[329:337], True) == _octal(raw[337:345], True) == 0, "no-device-fields")
    _safe_text(raw[265:297])
    _safe_text(raw[297:329])
    link = _safe_text(raw[157:257])
    require(
        (kind == "file" and not link)
        or (kind == "directory" and not link and size == 0)
        or (kind in ("symlink", "hardlink") and link and size == 0),
        "kind-size-link-fields",
    )
    return {
        "path": path,
        "kind": kind,
        "bytes": size,
        "mode": mode,
        "link_target": _path(link) if link else None,
    }


class _Namespace:
    def __init__(self):
        self.nodes, self.aliases = {}, {}

    def add(self, row):
        path, kind, link = row["path"], row["kind"], row["link_target"]
        if link is not None:
            target = _path(
                path.rsplit("/", 1)[0] + "/" + link if kind == "symlink" and "/" in path else link
            )
            allowed = ("file", "directory") if kind == "symlink" else ("file",)
            require(
                target != path and self.nodes.get(target) in allowed,
                "earlier-direct-link-target-only",
            )
            row["link_target"] = target
        parts = path.split("/")
        for count in range(1, len(parts) + 1):
            current = "/".join(parts[:count])
            folded = unicodedata.normalize("NFC", current.casefold())
            require(
                folded not in self.aliases or self.aliases[folded] == current,
                "case-or-normalization-collision",
            )
            self.aliases[folded] = current
            prior = self.nodes.get(current)
            if count < len(parts):
                require(prior in (None, "implicit", "directory"), "file-or-linked-prefix")
                self.nodes.setdefault(current, "implicit")
            else:
                require(
                    prior is None or prior == "implicit" and kind == "directory", "duplicate-path"
                )
                self.nodes[current] = kind


class _Compressed:
    def __init__(self, fd, guard):
        self.fd, self.guard, self.count, self.eof_probes = fd, guard, 0, 0

    def read(self):
        self.guard()
        raw = os.read(self.fd, min(65536, LIMITS["compressed_bytes"] - self.count + 1))
        if not raw:
            self.eof_probes += 1
        self.count += len(raw)
        require(self.count <= LIMITS["compressed_bytes"], "compressed-sentinel-cap")
        return raw


class _Inflated:
    def __init__(self, compressed):
        self.compressed, self.decoder = compressed, zlib.decompressobj(31)
        self.buffer, self.pending = b"", b""
        self.count, self.finished, self.peak_chunk = 0, False, 0
        self.first = True

    def pump(self):
        if self.pending:
            raw, self.pending = self.pending, b""
        else:
            raw = self.compressed.read()
        if self.first:
            while raw and len(raw) < 10:
                more = self.compressed.read()
                require(more, "truncated-gzip-header")
                raw += more
            require(len(raw) >= 10 and raw[:4] == b"\x1f\x8b\x08\0", "gzip-no-extensions")
            self.first = False
        require(raw, "truncated-gzip")
        try:
            chunk = self.decoder.decompress(
                raw, min(65536, LIMITS["decompressed_bytes"] - self.count + 1)
            )
        except zlib.error as error:
            raise ValueError("gzip-CRC-or-format") from error
        self.pending = self.decoder.unconsumed_tail
        self.count += len(chunk)
        self.peak_chunk = max(self.peak_chunk, len(chunk))
        require(self.count <= LIMITS["decompressed_bytes"], "decompressed-sentinel-cap")
        self.buffer += chunk
        if self.decoder.eof:
            require(
                not self.decoder.unused_data and not self.pending and not self.compressed.read(),
                "single-gzip-no-trailing-bytes",
            )
            self.finished = True

    def read(self, count):
        require(0 < count <= 65536, "bounded-parser-read")
        while not self.buffer and not self.finished:
            self.pump()
        raw, self.buffer = self.buffer[:count], self.buffer[count:]
        return raw

    def exact(self, count):
        parts = []
        while count:
            raw = self.read(count)
            require(raw, "truncated-tar")
            parts.append(raw)
            count -= len(raw)
        return b"".join(parts)


def _inventory(fd, guard, observation):
    compressed = _Compressed(fd, guard)
    stream, namespace = _Inflated(compressed), _Namespace()
    rows, encoded_bytes, member_drains, succeeded = [], 2, 0, False
    try:
        while True:
            guard()
            header = stream.exact(512)
            if header == b"\0" * 512:
                require(stream.exact(512) == b"\0" * 512, "two-tar-end-blocks")
                while tail := stream.read(65536):
                    require(not tail.strip(b"\0"), "nonzero-tar-trailer")
                require(stream.count % 512 == 0, "aligned-tar-trailer")
                break
            require(len(rows) < LIMITS["members"], "member-count-cap")
            row = _header(header)
            namespace.add(row)
            next_bytes = encoded_bytes + len(encode(row)) + bool(rows)
            require(next_bytes <= LIMITS["inventory_bytes"], "inventory-output-cap")
            remaining = row["bytes"]
            while remaining:
                guard()
                chunk = stream.exact(min(65536, remaining))
                remaining -= len(chunk)
                member_drains += len(chunk)
            padding = (-row["bytes"]) % 512
            require(stream.exact(padding) == b"\0" * padding, "zero-member-padding")
            rows.append(row)
            encoded_bytes = next_bytes
        succeeded = True
        return {
            "headers": rows,
            "inventory_bytes": encoded_bytes,
            "decompressed_bytes": stream.count,
            "member_bytes_opaquely_drained": member_drains,
        }
    finally:
        observation.update(
            compressed_bytes=compressed.count,
            EOF_probes=compressed.eof_probes,
            decompressed_bytes=stream.count,
            member_bytes_drained=member_drains,
            completed_members=len(rows),
            inventory_bytes=encoded_bytes,
            headers_prefix=None if succeeded else rows,
            max_decompressed_chunk=stream.peak_chunk,
        )


def _token(value):
    return {
        "dev": value.st_dev,
        "ino": value.st_ino,
        "bytes": value.st_size,
        "mode": stat.S_IMODE(value.st_mode),
        "uid": value.st_uid,
        "nlink": value.st_nlink,
        "mtime_ns": value.st_mtime_ns,
        "ctime_ns": value.st_ctime_ns,
    }


def _observe(fd, directory_fd, parent_fd=None, directory_name=None):
    if parent_fd is not None:
        directory = os.fstat(directory_fd)
        named_directory = os.stat(directory_name, dir_fd=parent_fd, follow_symlinks=False)
        require(
            stat.S_ISDIR(named_directory.st_mode)
            and directory.st_uid == os.getuid()
            and stat.S_IMODE(directory.st_mode) == 0o700
            and _token(directory) == _token(named_directory),
            "directory-name-binding",
        )
    current, named = os.fstat(fd), os.stat("input.gz", dir_fd=directory_fd, follow_symlinks=False)
    require(
        stat.S_ISREG(current.st_mode)
        and stat.S_ISREG(named.st_mode)
        and current.st_uid == os.getuid()
        and current.st_nlink == 1
        and stat.S_IMODE(current.st_mode) == 0o600
        and _token(current) == _token(named),
        "owned-regular-fd-name-binding",
    )
    return _token(current)


def _hash_pass(fd, guard, observation):
    hasher, count, eof = hashlib.sha256(), 0, 0
    try:
        while True:
            guard()
            raw = os.read(fd, min(65536, LIMITS["compressed_bytes"] - count + 1))
            if not raw:
                eof += 1
                break
            # Hash the consumed rejection sentinel too; bytes/SHA cover one prefix.
            hasher.update(raw)
            count += len(raw)
            require(count <= LIMITS["compressed_bytes"], "compressed-sentinel-cap")
        return hasher.hexdigest(), count
    finally:
        observation.update(bytes=count, sha256=hasher.hexdigest(), EOF_probes=eof)


def _header_bytes(path, size=0, flag=b"0", link=""):
    raw = bytearray(512)
    name, prefix = path, ""
    if len(path.encode()) > 100:
        prefix, name = path.rsplit("/", 1)
    require(len(name.encode()) <= 100 and len(prefix.encode()) <= 155, "fixture-ustar-path")
    raw[: len(name.encode())] = name.encode()
    raw[100:108], raw[108:116], raw[116:124] = b"0000644\0", b"0000000\0", b"0000000\0"
    raw[124:136], raw[136:148] = (f"{size:011o}\0").encode(), b"00000000000\0"
    raw[148:156], raw[156:157] = b" " * 8, flag
    raw[157 : 157 + len(link.encode())] = link.encode()
    raw[257:265] = b"ustar\x0000"
    raw[345 : 345 + len(prefix.encode())] = prefix.encode()
    raw[148:156] = (f"{sum(raw):06o}\0 ").encode()
    return bytes(raw)


class _FixtureWriter:
    def __init__(self, fd, guard):
        self.fd, self.guard, self.count, self.hasher = fd, guard, 0, hashlib.sha256()

    def write(self, raw):
        self.guard()
        require(
            self.count + len(raw) <= LIMITS["compressed_bytes"] + 1,
            "fixture-compressed-generation-cap",
        )
        offset = 0
        while offset < len(raw):
            count = os.write(self.fd, raw[offset:])
            require(count > 0, "fixture-write-progress")
            self.hasher.update(raw[offset : offset + count])
            offset += count
            self.count += count
        return len(raw)

    def flush(self):
        pass


def _member(writer, path, size=0, flag=b"0", link=""):
    writer.write(_header_bytes(path, size, flag, link))
    remaining = size
    while remaining:
        count = min(65536, remaining)
        writer.write(b"\0" * count)
        remaining -= count
    writer.write(b"\0" * ((-size) % 512))


def _stored_gzip(writer, target):
    # A fixed generated zero-payload USTAR in uncompressed DEFLATE stored blocks.
    # Solve byte-exact gzip size without allocating the25MB tar or changing caps.
    selected = None
    for blocks in range(1, 2048):
        expanded = target - 18 - 5 * blocks
        if expanded >= 1536 and expanded % 512 == 0 and blocks * 65535 >= expanded:
            selected = blocks, expanded
            break
    require(selected is not None, "fixed-stored-gzip-size")
    blocks, expanded = selected
    header = _header_bytes("invented/stored-zero", expanded - 1536)
    writer.write(b"\x1f\x8b\x08\0\0\0\0\0\0\xff")
    offset, crc = 0, 0
    for block in range(blocks):
        length = min(65535, expanded - offset)
        writer.write(
            bytes((block == blocks - 1,))
            + length.to_bytes(2, "little")
            + (length ^ 65535).to_bytes(2, "little")
        )
        chunk = header[offset : min(512, offset + length)] if offset < 512 else b""
        chunk += b"\0" * (length - len(chunk))
        writer.write(chunk)
        crc = zlib.crc32(chunk, crc)
        offset += length
    require(offset == expanded, "fixed-stored-gzip-expanded-size")
    writer.write(crc.to_bytes(4, "little") + expanded.to_bytes(4, "little"))


def _generate(fd, scenario, guard):
    writer = _FixtureWriter(fd, guard)
    if scenario in ("compressed-gzip-exact", "compressed-gzip-over"):
        _stored_gzip(writer, LIMITS["compressed_bytes"] + (scenario == "compressed-gzip-over"))
        return writer.hasher.hexdigest(), writer.count
    if scenario in ("compressed-exact", "compressed-over"):
        remaining = LIMITS["compressed_bytes"] + (scenario == "compressed-over")
        while remaining:
            count = min(65536, remaining)
            writer.write(b"\0" * count)
            remaining -= count
        return writer.hasher.hexdigest(), writer.count
    with gzip.GzipFile(filename="", mode="wb", fileobj=writer, mtime=0) as compressed:
        if scenario.startswith("expanded-"):
            _member(compressed, "invented/a", LIMITS["member_bytes"])
            _member(compressed, "invented/b", LIMITS["member_bytes"] - 2048)
        elif scenario == "member-exact":
            _member(compressed, "invented/member", LIMITS["member_bytes"])
        elif scenario == "member-over":
            compressed.write(_header_bytes("invented/member", LIMITS["member_bytes"] + 1))
        elif scenario.startswith("roster-"):
            for number in range(LIMITS["members"] + (scenario == "roster-over")):
                _member(compressed, f"invented/f{number:05d}")
        elif scenario.startswith("inventory-"):
            count = 9000 if scenario == "inventory-near" else 15000
            inventory_size = 2
            for number in range(count):
                path = "é" * 75 + "/" + "é" * 45 + f"{number:05d}"
                row_size = len(
                    encode(
                        {
                            "path": path,
                            "kind": "file",
                            "bytes": 0,
                            "mode": 0o644,
                            "link_target": None,
                        }
                    )
                ) + (number > 0)
                if (
                    scenario == "inventory-exact"
                    and inventory_size + row_size > LIMITS["inventory_bytes"]
                ):
                    remaining = LIMITS["inventory_bytes"] - inventory_size - 1
                    selected = None
                    for prefix_chars in range(1, 76):
                        for leaf_chars in range(1, 96):
                            tail = "é" * prefix_chars + "/tail" + "x" * leaf_chars
                            row = {
                                "path": tail,
                                "kind": "file",
                                "bytes": 0,
                                "mode": 0o644,
                                "link_target": None,
                            }
                            if len(encode(row)) == remaining:
                                selected = tail
                                break
                        if selected is not None:
                            break
                    require(selected is not None, "fixture-exact-inventory-tail")
                    _member(compressed, selected)
                    break
                _member(compressed, path)
                inventory_size += row_size
        elif scenario == "pax":
            compressed.write(_header_bytes("invented/pax", flag=b"x"))
        elif scenario == "unsafe-path":
            _member(compressed, "../invented-escape")
        elif scenario == "links":
            _member(compressed, "invented/base")
            _member(compressed, "invented/link", flag=b"2", link="base")
            _member(compressed, "invented/hard", flag=b"1", link="invented/base")
        elif scenario == "bad-checksum":
            header = _header_bytes("invented/bad")
            compressed.write(b"X" + header[1:])
        else:
            _member(compressed, "invented/opaque", 4096)
        compressed.write(b"\0" * (1536 if scenario == "expanded-over" else 1024))
    if scenario == "trailing-gzip":
        writer.write(gzip.compress(b"", mtime=0))
    if scenario == "bad-gzip-crc":
        os.pwrite(fd, b"\xff\xff\xff\xff", writer.count - 8)
        os.lseek(fd, 0, os.SEEK_SET)
        sha, count = _hash_pass(fd, guard, {})
        return sha, count
    return writer.hasher.hexdigest(), writer.count


def _worker(scenario, fresh_root, expected_source, expires, deadline):
    require(
        scenario in SCENARIOS and _identity(deadline) == expected_source, "fixed-source-scenario"
    )

    def guard():
        _guard(deadline, expires)

    result = {
        "schema": SCHEMA,
        "kind": "invented",
        "scenario": scenario,
        "source_identity": expected_source,
        "limits": dict(LIMITS),
        "events": [],
        "status": "incomplete",
        "error": None,
        "cleanup_error": None,
        "output_error": None,
        "tokens": [],
        "input": None,
        "pass1": {},
        "pass2": {},
        "inventory": None,
        "descriptor_closed": False,
        "actual_crypto_verified": False,
        "actual_authentication_admitted": False,
        "actual_inspection_authorized": False,
        "member_text_returned": False,
        "member_hashes_returned": False,
        "selected_notices": [],
        "extraction_performed": False,
        "authority": dict(AUTHORITY),
        "issued_utc": _stamp(_now()),
        "operation_expires_utc": _stamp(expires),
        "retention_not_after_utc": CAP_UTC,
    }
    parent_fd = directory_fd = fd = None
    try:
        guard()
        destination = Path(fresh_root)
        parent_fd = os.open(destination.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        parent = os.fstat(parent_fd)
        require(
            parent.st_uid == os.getuid() and stat.S_IMODE(parent.st_mode) == 0o700,
            "private-owned-fixture-parent",
        )
        os.mkdir(destination.name, 0o700, dir_fd=parent_fd)
        directory_fd = os.open(
            destination.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd
        )
        fd = os.open(
            "input.gz",
            os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=directory_fd,
        )
        if scenario == "stall-generate":
            time.sleep(60)
        sha, count = _generate(fd, scenario, guard)
        result["input"] = {"sha256": sha, "bytes": count}
        if scenario == "stall-storage":
            time.sleep(60)
        os.fsync(fd)
        result["events"].append("generated")
        initial = _observe(fd, directory_fd, parent_fd, destination.name)
        result["tokens"].append(initial)
        guard()
        require(_identity(deadline) == expected_source, "source-drift")
        os.lseek(fd, 0, os.SEEK_SET)
        sha, count = _hash_pass(fd, guard, result["pass1"])
        require(result["input"] == {"sha256": sha, "bytes": count}, "opaque-input-size-digest")
        result["events"].append("pass1")
        token = _observe(fd, directory_fd, parent_fd, destination.name)
        result["tokens"].append(token)
        require(token == initial, "custody-after-pass1")
        require(scenario != "deny-auth", "invented-auth-control-denied")
        result["events"].append("invented-auth-control")
        guard()
        require(_identity(deadline) == expected_source, "source-drift")
        os.lseek(fd, 0, os.SEEK_SET)
        result["events"].append("same-fd-rewind")
        result["inventory"] = _inventory(fd, guard, result["pass2"])
        result["events"].append("inventory")
        token = _observe(fd, directory_fd, parent_fd, destination.name)
        result["tokens"].append(token)
        require(
            token == initial
            and result["pass2"]["compressed_bytes"] == count
            and result["pass2"]["EOF_probes"] == 1,
            "custody-after-pass2",
        )
        guard()
        require(_identity(deadline) == expected_source, "source-drift")
    except (OSError, ValueError) as error:
        result["error"] = (
            type(error).__name__
            + ":"
            + (str(error) if isinstance(error, ValueError) else str(error.errno))
        )
    finally:
        for owned in (fd,):
            if owned is not None:
                try:
                    os.close(owned)
                except OSError as error:
                    result["cleanup_error"] = "close-errno:" + str(error.errno)
        result["descriptor_closed"] = fd is not None and result["cleanup_error"] is None
    if result["error"] is None and result["cleanup_error"] is None:
        result["status"] = "invented-core-completed"
    result["ended_utc"] = _stamp(_now())
    try:
        if scenario == "stall-report":
            time.sleep(60)
        if directory_fd is not None:
            output = None

            def output_guard():
                guard()
                directory = os.fstat(directory_fd)
                named = os.stat(destination.name, dir_fd=parent_fd, follow_symlinks=False)
                require(
                    stat.S_ISDIR(named.st_mode)
                    and _token(directory) == _token(named)
                    and directory.st_uid == os.getuid()
                    and stat.S_IMODE(directory.st_mode) == 0o700,
                    "output-held-directory-binding",
                )
                if output is not None:
                    outstat = os.fstat(output)
                    outname = os.stat("inventory.json", dir_fd=directory_fd, follow_symlinks=False)
                    require(
                        stat.S_ISREG(outstat.st_mode)
                        and stat.S_ISREG(outname.st_mode)
                        and outstat.st_uid == os.getuid()
                        and outstat.st_nlink == 1
                        and stat.S_IMODE(outstat.st_mode) == 0o600
                        and _token(outstat) == _token(outname),
                        "output-fd-name-binding",
                    )
                if result["status"] == "invented-core-completed":
                    require(
                        _token(os.stat("input.gz", dir_fd=directory_fd, follow_symlinks=False))
                        == initial,
                        "output-input-name-binding",
                    )

            output_guard()
            output = os.open(
                "inventory.json",
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
                dir_fd=directory_fd,
            )
            try:
                raw = encode(result)
                require(len(raw) <= MAX_REPORT_BYTES, "bounded-report")
                offset = 0
                while offset < len(raw):
                    output_guard()
                    count = os.write(output, raw[offset : offset + 65536])
                    require(count > 0, "report-write-progress")
                    offset += count
                os.fsync(output)
                os.fsync(directory_fd)
                output_guard()
            finally:
                os.close(output)
        guard()
        require(_identity(deadline) == expected_source, "source-drift")
    except (OSError, ValueError) as error:
        result["output_error"] = (
            type(error).__name__
            + ":"
            + (str(error) if isinstance(error, ValueError) else str(error.errno))
        )
    finally:
        for owned in (directory_fd, parent_fd):
            if owned is not None:
                try:
                    os.close(owned)
                except OSError as error:
                    result["cleanup_error"] = "close-errno:" + str(error.errno)
    if result["output_error"] is not None or result["cleanup_error"] is not None:
        result["status"] = "incomplete"

    return result


def _stop(process, whole_deadline):
    errors = []
    try:
        if process.poll() is None or platform_process.tree_exists(process):
            platform_process.force_tree(process)
    except (OSError, RuntimeError):
        errors.append("owned-force-error")
    try:
        if process.poll() is None:
            process.wait(timeout=max(0.01, min(STOP_SECONDS, whole_deadline - time.monotonic())))
    except (OSError, RuntimeError, subprocess.TimeoutExpired):
        errors.append("owned-wait-error")
    try:
        platform_process.close_tree(process)
    except (OSError, RuntimeError):
        errors.append("owned-tree-close-error")
    try:
        if platform_process.tree_exists(process):
            errors.append("owned-tree-remains")
    except (OSError, RuntimeError):
        errors.append("owned-tree-observation-error")
    return ";".join(errors) or None


def _supervise(scenario, fresh_root, whole_seconds):
    start = time.monotonic()
    whole_deadline = start + whole_seconds
    work_deadline = whole_deadline - STOP_SECONDS - JOIN_SECONDS
    expires = min(
        _now() + timedelta(seconds=WHOLE_SECONDS + 60),
        datetime.fromisoformat(CAP_UTC.replace("Z", "+00:00")),
    )
    require(_now() + timedelta(seconds=whole_seconds) < expires, "retention-headroom")
    source = _identity(work_deadline)
    root = Path(__file__).resolve().parents[2]
    script = (
        "import sys; sys.path.insert(0, " + repr(str(root)) + "); "
        "from experiments.simglucose_audit.pbs_production_inspection import _entry; _entry()"
    )
    command = [
        sys.executable,
        "-I",
        "-S",
        "-B",
        "-c",
        script,
        "--fixed-invented-worker",
        scenario,
        str(fresh_root),
        digest(encode(source)),
        _stamp(expires),
        str(work_deadline),
    ]
    process = platform_process.spawn(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        bufsize=0,
        cwd=root,
        env={"PYTHONDONTWRITEBYTECODE": "1", "LC_ALL": "C"},
    )
    chunks, state = [], {"bytes": 0, "overflow": False, "eof": False, "error": None}
    thread, started = None, False
    primary = cleanup = None
    try:

        def drain():
            try:
                while True:
                    raw = os.read(
                        process.stdout.fileno(), min(65536, MAX_REPORT_BYTES - state["bytes"] + 1)
                    )
                    if not raw:
                        state["eof"] = True
                        break
                    chunks.append(raw)
                    state["bytes"] += len(raw)
                    if state["bytes"] > MAX_REPORT_BYTES:
                        state["overflow"] = True
                        break
            except OSError:
                state["error"] = "reader-OSError"

        thread = threading.Thread(target=drain, daemon=True)
        thread.start()
        started = True
        while process.poll() is None:
            if time.monotonic() >= work_deadline:
                primary = "whole-budget"
                break
            if state["overflow"] or state["error"]:
                primary = "bounded-reader"
                break
            time.sleep(0.01)
    except (OSError, RuntimeError):
        primary = primary or "owned-reader-start-or-monitor-error"
    finally:
        cleanup = _stop(process, whole_deadline)
        started = started or thread is not None and thread.ident is not None
        try:
            if started:
                thread.join(timeout=max(0, min(JOIN_SECONDS, whole_deadline - time.monotonic())))
            joined = not started or not thread.is_alive()
        except RuntimeError:
            joined = False
        if not joined:
            cleanup = (cleanup + ";" if cleanup else "") + "reader-not-joined"
        try:
            process.stdout.close()
        except OSError:
            cleanup = (cleanup + ";" if cleanup else "") + "pipe-close-error"
    outer = {
        "kind": "invented",
        "source_identity": source,
        "scenario": scenario,
        "pid": process.pid,
        "returncode": process.returncode,
        "cleanup_error": cleanup,
        "reader_joined": joined,
        "reader_eof": state["eof"],
        "reader_error": state["error"],
        "reader_overflow": state["overflow"],
        "stdout_bytes": state["bytes"],
        "error": primary,
        "elapsed_ns": int((time.monotonic() - start) * 1e9),
        "whole_budget_seconds": whole_seconds,
        "worker": None,
        "status": "incomplete",
        "issued_completion_pin": None,
        "actual_inspection_authorized": False,
        "physical_history_authenticated": False,
    }
    if joined and state["eof"] and not state["overflow"] and state["error"] is None:
        try:
            outer["worker"] = _decode(b"".join(chunks))
        except ValueError:
            outer["error"] = outer["error"] or "invalid-worker-report"
    worker = outer["worker"]
    if (
        primary is None
        and cleanup is None
        and joined
        and state["eof"]
        and process.returncode == 0
        and time.monotonic() < whole_deadline
        and _identity(whole_deadline) == source
        and type(worker) is dict
        and worker.get("status") == "invented-core-completed"
    ):
        outer["status"] = "invented-owned-route-completed"
        outer["issued_completion_pin"] = digest(encode(worker))
    return outer


def qualify_invented_scenario(scenario, fresh_root):
    """Fixed generated fixtures only; no input archive path/auth boolean exists."""
    require(type(scenario) is str and scenario in SCENARIOS, "fixed-invented-scenario")
    require(hasattr(os, "O_NOFOLLOW") and os.open in os.supports_dir_fd, "dirfd-fixture-support")
    return _supervise(scenario, fresh_root, WHOLE_SECONDS)


def _hex(value):
    return type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _utc(value):
    require(type(value) is str and value.endswith("Z"), "cold-UTC")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("cold-UTC") from error
    require(parsed.tzinfo == UTC and _stamp(parsed) == value, "cold-canonical-UTC")
    return parsed


def _cold_rows(rows):
    require(type(rows) is list and len(rows) <= LIMITS["members"], "cold-member-count")
    namespace, size, drained = _Namespace(), 2, 0
    for index, row in enumerate(rows):
        require(
            type(row) is dict
            and set(row) == {"path", "kind", "bytes", "mode", "link_target"}
            and type(row["path"]) is str
            and type(row["bytes"]) is int
            and 0 <= row["bytes"] <= LIMITS["member_bytes"]
            and type(row["mode"]) is int
            and 0 <= row["mode"] <= 0o777
            and row["kind"] in ("file", "directory", "symlink", "hardlink"),
            "cold-row",
        )
        require(_path(row["path"]) == row["path"], "cold-path")
        if row["kind"] == "file":
            require(row["link_target"] is None, "cold-file-link")
        elif row["kind"] == "directory":
            require(row["bytes"] == 0 and row["link_target"] is None, "cold-directory-payload")
        else:
            require(
                row["bytes"] == 0
                and type(row["link_target"]) is str
                and _path(row["link_target"]) == row["link_target"],
                "cold-link-fields",
            )
            allowed = ("file", "directory") if row["kind"] == "symlink" else ("file",)
            require(namespace.nodes.get(row["link_target"]) in allowed, "cold-direct-link-target")
        plain = dict(row)
        plain["link_target"] = None
        namespace.add(plain)
        size += len(encode(row)) + bool(index)
        drained += row["bytes"]
    require(
        size <= LIMITS["inventory_bytes"] and drained <= LIMITS["decompressed_bytes"],
        "cold-inventory-cap",
    )
    return size, drained


def inspect_fixture_metadata(raw, held_report_sha256, held_completion_pin):
    """Metadata-only cold reader; no third compressed-file pass or producer call."""
    require(
        type(raw) is bytes
        and 0 < len(raw) <= MAX_REPORT_BYTES + 65536
        and digest(raw) == held_report_sha256,
        "held-bounded-report",
    )
    outer = _decode(raw)
    require(
        type(outer) is dict
        and set(outer)
        == {
            "kind",
            "source_identity",
            "scenario",
            "pid",
            "returncode",
            "cleanup_error",
            "reader_joined",
            "reader_eof",
            "reader_error",
            "reader_overflow",
            "stdout_bytes",
            "error",
            "elapsed_ns",
            "whole_budget_seconds",
            "worker",
            "status",
            "issued_completion_pin",
            "actual_inspection_authorized",
            "physical_history_authenticated",
        },
        "cold-exact-outer",
    )
    require(
        encode(outer["source_identity"]) == encode(_identity())
        and outer["kind"] == "invented"
        and type(outer["scenario"]) is str
        and outer["scenario"] in SCENARIOS
        and outer["actual_inspection_authorized"] is False
        and outer["physical_history_authenticated"] is False,
        "cold-source-scope",
    )
    require(
        type(outer["pid"]) is int
        and outer["pid"] > 0
        and (outer["returncode"] is None or type(outer["returncode"]) is int)
        and type(outer["elapsed_ns"]) is int
        and outer["elapsed_ns"] >= 0
        and type(outer["whole_budget_seconds"]) in (int, float)
        and 0 < outer["whole_budget_seconds"] <= WHOLE_SECONDS
        and type(outer["stdout_bytes"]) is int
        and 0 <= outer["stdout_bytes"] <= MAX_REPORT_BYTES + 1,
        "cold-typed-outer-observations",
    )
    require(
        all(
            type(outer[name]) is bool for name in ("reader_joined", "reader_eof", "reader_overflow")
        )
        and all(
            outer[name] is None or type(outer[name]) is str and 0 < len(outer[name]) <= 256
            for name in ("error", "cleanup_error", "reader_error")
        ),
        "cold-outer-diagnostics",
    )
    worker = outer["worker"]
    if worker is not None:
        require(
            type(worker) is dict
            and set(worker)
            == {
                "schema",
                "kind",
                "scenario",
                "source_identity",
                "limits",
                "events",
                "status",
                "error",
                "cleanup_error",
                "output_error",
                "tokens",
                "input",
                "pass1",
                "pass2",
                "inventory",
                "descriptor_closed",
                "actual_crypto_verified",
                "actual_authentication_admitted",
                "actual_inspection_authorized",
                "member_text_returned",
                "member_hashes_returned",
                "selected_notices",
                "extraction_performed",
                "authority",
                "issued_utc",
                "ended_utc",
                "operation_expires_utc",
                "retention_not_after_utc",
            },
            "cold-exact-worker",
        )
        require(
            worker["schema"] == SCHEMA
            and worker["kind"] == "invented"
            and worker["scenario"] == outer["scenario"]
            and encode(worker["source_identity"]) == encode(_identity())
            and encode(worker["limits"]) == encode(LIMITS)
            and all(
                worker[name] is False
                for name in (
                    "actual_crypto_verified",
                    "actual_authentication_admitted",
                    "actual_inspection_authorized",
                    "member_text_returned",
                    "member_hashes_returned",
                    "extraction_performed",
                )
            )
            and worker["selected_notices"] == []
            and encode(worker["authority"]) == encode(AUTHORITY),
            "cold-worker-scope",
        )
        require(outer["stdout_bytes"] == len(encode(worker)), "cold-stdout-byte-binding")
        require(
            worker["retention_not_after_utc"] == CAP_UTC
            and _utc(worker["issued_utc"])
            <= _utc(worker["ended_utc"])
            < _utc(worker["operation_expires_utc"])
            <= _utc(CAP_UTC)
            and _now() < _utc(CAP_UTC),
            "cold-temporal-retention",
        )
        stages = ["generated", "pass1", "invented-auth-control", "same-fd-rewind", "inventory"]
        events = worker["events"]
        require(
            type(events) is list and len(events) <= len(stages) and events == stages[: len(events)],
            "cold-event-prefix",
        )
        require(
            not (outer["scenario"] == "deny-auth" and len(events) > 2), "cold-denied-auth-prefix"
        )
        tokens = worker["tokens"]
        require(
            type(tokens) is list
            and len(tokens) in ((0,), (0, 1), (1, 2), (2,), (2,), (2, 3))[len(events)],
            "cold-token-prefix",
        )
        for token in tokens:
            require(
                type(token) is dict
                and set(token)
                == {"dev", "ino", "bytes", "mode", "uid", "nlink", "mtime_ns", "ctime_ns"}
                and all(type(v) is int and v >= 0 for v in token.values())
                and token["mode"] == 0o600
                and token["nlink"] == 1,
                "cold-token",
            )
        require(
            type(worker["descriptor_closed"]) is bool
            and all(
                worker[name] is None or type(worker[name]) is str and 0 < len(worker[name]) <= 256
                for name in ("error", "cleanup_error", "output_error")
            ),
            "cold-worker-diagnostics",
        )
        generated = worker["input"]
        if generated is not None:
            require(
                type(generated) is dict
                and set(generated) == {"bytes", "sha256"}
                and type(generated["bytes"]) is int
                and 0 <= generated["bytes"] <= LIMITS["compressed_bytes"] + 1
                and _hex(generated["sha256"]),
                "cold-generated-input",
            )
        first, second = worker["pass1"], worker["pass2"]
        require(type(first) is dict and type(second) is dict, "cold-pass-types")
        if first:
            require(
                "generated" in events
                and set(first) == {"bytes", "sha256", "EOF_probes"}
                and type(first["bytes"]) is int
                and 0 <= first["bytes"] <= LIMITS["compressed_bytes"] + 1
                and _hex(first["sha256"])
                and type(first["EOF_probes"]) is int
                and first["EOF_probes"] in (0, 1),
                "cold-pass1-prefix",
            )
        if "pass1" in events:
            require(bool(first), "cold-missing-pass1")
            require(
                generated == {"bytes": first["bytes"], "sha256": first["sha256"]}
                and first["EOF_probes"] == 1
                and first["bytes"] <= LIMITS["compressed_bytes"],
                "cold-pass1-binding",
            )
        if second:
            require(
                "same-fd-rewind" in events
                and set(second)
                == {
                    "compressed_bytes",
                    "EOF_probes",
                    "decompressed_bytes",
                    "member_bytes_drained",
                    "completed_members",
                    "inventory_bytes",
                    "headers_prefix",
                    "max_decompressed_chunk",
                }
                and all(
                    type(second[name]) is int and 0 <= second[name] <= maximum
                    for name, maximum in (
                        ("compressed_bytes", LIMITS["compressed_bytes"] + 1),
                        ("EOF_probes", 1),
                        ("decompressed_bytes", LIMITS["decompressed_bytes"] + 1),
                        ("member_bytes_drained", LIMITS["decompressed_bytes"]),
                        ("completed_members", LIMITS["members"]),
                        ("inventory_bytes", LIMITS["inventory_bytes"]),
                        ("max_decompressed_chunk", 65536),
                    )
                ),
                "cold-pass2-prefix",
            )
        require("same-fd-rewind" not in events or bool(second), "cold-missing-pass2")
        inventory = worker["inventory"]
        if inventory is not None:
            require(
                "inventory" in events
                and type(inventory) is dict
                and set(inventory)
                == {
                    "headers",
                    "inventory_bytes",
                    "decompressed_bytes",
                    "member_bytes_opaquely_drained",
                },
                "cold-inventory-fields",
            )
            size, drained = _cold_rows(inventory["headers"])
            require(
                type(inventory["decompressed_bytes"]) is int
                and type(inventory["inventory_bytes"]) is int
                and type(inventory["member_bytes_opaquely_drained"]) is int
                and drained <= inventory["decompressed_bytes"] <= LIMITS["decompressed_bytes"]
                and size == inventory["inventory_bytes"] == second["inventory_bytes"]
                and drained
                == inventory["member_bytes_opaquely_drained"]
                == second["member_bytes_drained"]
                and len(inventory["headers"]) == second["completed_members"]
                and inventory["decompressed_bytes"] == second["decompressed_bytes"]
                and second["headers_prefix"] is None,
                "cold-inventory-counts",
            )
        else:
            require("inventory" not in events, "cold-missing-inventory")
            if second:
                size, drained = _cold_rows(second["headers_prefix"])
                require(
                    size == second["inventory_bytes"]
                    and len(second["headers_prefix"]) == second["completed_members"]
                    and drained <= second["member_bytes_drained"] <= second["decompressed_bytes"],
                    "cold-partial-inventory-prefix",
                )
        if worker["status"] == "invented-core-completed":
            require(
                events == stages
                and worker["error"] is None
                and worker["cleanup_error"] is None
                and worker["output_error"] is None
                and worker["descriptor_closed"] is True
                and inventory is not None
                and len(tokens) == 3
                and all(token == tokens[0] for token in tokens)
                and tokens[0]["bytes"] == generated["bytes"]
                and first["bytes"] == second["compressed_bytes"]
                and second["EOF_probes"] == 1,
                "cold-core-completion",
            )
        else:
            require(
                worker["status"] == "incomplete"
                and (
                    worker["error"] is not None
                    or worker["cleanup_error"] is not None
                    or worker["output_error"] is not None
                ),
                "cold-core-failure",
            )
    if outer["status"] == "invented-owned-route-completed":
        require(type(worker) is dict, "cold-complete-worker-required")
        require(
            outer["scenario"] != "finish-block"
            and _hex(held_completion_pin)
            and held_completion_pin == outer["issued_completion_pin"] == digest(encode(worker))
            and type(outer["returncode"]) is int
            and outer["returncode"] == 0
            and outer["cleanup_error"] is None
            and outer["reader_joined"] is True
            and outer["reader_eof"] is True
            and outer["reader_error"] is None
            and outer["reader_overflow"] is False
            and outer["error"] is None
            and outer["elapsed_ns"] <= outer["whole_budget_seconds"] * 1e9
            and worker["status"] == "invented-core-completed",
            "held-completion-lifecycle",
        )
    else:
        require(
            outer["status"] == "incomplete"
            and held_completion_pin is None
            and outer["issued_completion_pin"] is None,
            "cold-incomplete",
        )
    return {
        "status": "invented-metadata-consistent",
        "actual_inspection_authorized": False,
        "payload_reopened_or_rehashed": False,
        "physical_history_authenticated": False,
    }


def _fixture_audit(event, _args):
    if event in (
        "socket.connect",
        "socket.getaddrinfo",
        "subprocess.Popen",
        "os.system",
        "os.exec",
        "os.posix_spawn",
    ):
        raise PermissionError("invented reader worker forbids network/process activation")


def _entry():
    require(len(sys.argv) == 7 and sys.argv[1] == "--fixed-invented-worker", "fixed-worker-argv")
    scenario, fresh_root, source_pin, expires, deadline = sys.argv[2:]
    source = _identity()
    require(digest(encode(source)) == source_pin, "fixed-worker-source")
    sys.addaudithook(_fixture_audit)
    result = _worker(
        scenario,
        fresh_root,
        source,
        datetime.fromisoformat(expires.replace("Z", "+00:00")),
        float(deadline),
    )
    raw = encode(result)
    require(len(raw) <= MAX_REPORT_BYTES, "fixed-worker-report-cap")
    sys.stdout.buffer.write(raw)
    sys.stdout.buffer.flush()
    if scenario == "finish-block":
        time.sleep(60)


if __name__ == "__main__":
    _entry()
