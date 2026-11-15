"""Bounded gzip/ustar INVENTED fixtures, not a real PBS inspection admission.

Only caller-owned invented buffers belong at the fixture API. Its marker cannot
prove provenance against a malicious caller copying it into other material.
There is no extraction, path open, native parsing, authentication or use grant.
Actual archive inspection stays unconditionally closed before input/path use.
"""

import hashlib
import unicodedata
import zlib
from pathlib import Path

from .contract import AUTHORITY, decode, digest, encode, require, source_identity

SCHEMA = "opent1d.pbs-invented-archive-inspection/1"
MARKER_NAME = "__OPENT1D_INVENTED_FIXTURE__"
MARKER = b"OpenT1D invented gzip/tar grammar fixture; no real archive material.\n"
LIMITS = {
    "compressed_bytes": 256 * 1024,
    "decompressed_bytes": 8 * 1024 * 1024,
    "members": 256,
    "member_bytes": 2 * 1024 * 1024,
    "path_utf8_bytes": 4096,
    "path_depth": 32,
    "notice_bytes": 64 * 1024,
    "notice_total_bytes": 128 * 1024,
    "inventory_bytes": 128 * 1024,
}
INHERITED_UNQUALIFIED_LIMITS = {
    "decompressed_bytes": 512 * 1024 * 1024,
    "members": 20000,
    "member_bytes": 256 * 1024 * 1024,
    "path_utf8_bytes": 4096,
    "path_depth": 32,
    "notice_bytes": 1024 * 1024,
    "notice_total_bytes": 8 * 1024 * 1024,
    "inventory_bytes": 8 * 1024 * 1024,
}
NOTICE_ALLOWLIST = frozenset(
    (
        "python/LICENSE.fixture.txt",
        "python/licenses/NOTICE.fixture.txt",
        "python/licenses/COPYING.fixture.txt",
    )
)


def inspect_archive(*_args, **_kwargs):
    """No actual inspection until separate authenticated admission is reviewed."""
    raise PermissionError("actual PBS archive inspection closed; opaque intake grants no members")


def _identity():
    return source_identity() | {"pbs_archive.py": digest(Path(__file__).read_bytes())}


def _pin(raw, expected):
    require(
        type(raw) is bytes and 18 <= len(raw) <= LIMITS["compressed_bytes"],
        "bounded-invented-compressed-bytes",
    )
    require(
        type(expected) is str and len(expected) == 64 and digest(raw) == expected,
        "held-invented-archive-pin",
    )


class _Inflated:
    """One gzip member; bounded output chunks and at most one sentinel byte."""

    def __init__(self, raw):
        require(raw[:3] == b"\x1f\x8b\x08" and raw[3] == 0, "gzip-deflate-without-extensions-only")
        self.raw, self.cursor, self.pending = raw, 0, b""
        self.decoder = zlib.decompressobj(31)
        self.buffer, self.finished, self.expanded = b"", False, 0
        self.hasher = hashlib.sha256()

    def _pump(self):
        require(not self.finished, "gzip-already-finished")
        if self.pending:
            supplied, self.pending = self.pending, b""
        else:
            supplied = self.raw[self.cursor : self.cursor + 4096]
            self.cursor += len(supplied)
        bound = min(65536, LIMITS["decompressed_bytes"] - self.expanded + 1)
        try:
            output = self.decoder.decompress(supplied, bound)
        except zlib.error as error:
            raise ValueError("gzip-checksum-or-format") from error
        self.pending = self.decoder.unconsumed_tail
        self.expanded += len(output)
        require(self.expanded <= LIMITS["decompressed_bytes"], "decompressed-byte-cap")
        self.hasher.update(output)
        self.buffer += output
        if self.decoder.eof:
            require(
                not self.decoder.unused_data and not self.pending and self.cursor == len(self.raw),
                "single-gzip-stream-without-tail",
            )
            self.finished = True
        else:
            require(output or self.pending or self.cursor < len(self.raw), "truncated-gzip-stream")

    def read(self, count):
        require(type(count) is int and 0 < count <= 65536, "bounded-drain-size")
        while not self.buffer and not self.finished:
            self._pump()
        result, self.buffer = self.buffer[:count], self.buffer[count:]
        return result

    def exact(self, count):
        require(type(count) is int and 0 <= count <= 65536, "bounded-exact-size")
        chunks, remaining = [], count
        while remaining:
            raw = self.read(remaining)
            require(raw, "truncated-tar-data")
            chunks.append(raw)
            remaining -= len(raw)
        return b"".join(chunks)


def _octal(raw, blank=False):
    require(not raw or raw[0] < 128, "base256-unsupported")
    digits = raw.strip(b"\x00 ")
    if not digits:
        require(blank, "required-octal-field")
        return 0
    require(all(48 <= value <= 55 for value in digits), "strict-octal-field")
    return int(digits, 8)


def _text(raw):
    head, separator, tail = raw.partition(b"\0")
    require(not separator or not tail.strip(b"\0"), "NUL-field-padding")
    try:
        value = head.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise ValueError("UTF8-tar-metadata") from error
    require(
        all(unicodedata.category(char) not in ("Cc", "Cf", "Cs", "Zl", "Zp") for char in value),
        "metadata-control-char",
    )
    return value


def _path(value, directory=False):
    require(
        type(value) is str
        and value
        and not value.startswith("/")
        and "\\" not in value
        and ":" not in value
        and "//" not in value,
        "relative-canonical-POSIX-path",
    )
    if directory and value.endswith("/"):
        value = value[:-1]
    require(
        value and not value.endswith("/") and unicodedata.normalize("NFC", value) == value,
        "canonical-NFC-path",
    )
    parts = value.split("/")
    require(
        len(value.encode("utf-8")) <= LIMITS["path_utf8_bytes"]
        and len(parts) <= LIMITS["path_depth"]
        and all(part not in ("", ".", "..") for part in parts),
        "path-size-depth-parent",
    )
    require(
        all(unicodedata.category(char) not in ("Cc", "Cf", "Cs", "Zl", "Zp") for char in value),
        "path-control-char",
    )
    return value


def _header(raw):
    require(
        len(raw) == 512 and raw[257:265] == b"ustar\x0000" and raw[500:] == b"\0" * 12,
        "POSIX-ustar-subset-only",
    )
    checksum = _octal(raw[148:156])
    require(sum(raw[:148]) + 8 * 32 + sum(raw[156:]) == checksum, "tar-header-checksum")
    flag = raw[156:157]
    kinds = {b"0": "file", b"\0": "file", b"5": "directory", b"2": "symlink", b"1": "hardlink"}
    require(flag in kinds, "unsupported-tar-type-extension-or-sparse")
    kind = kinds[flag]
    name, prefix = _text(raw[:100]), _text(raw[345:500])
    path = _path(prefix + "/" + name if prefix else name, kind == "directory")
    mode, size = _octal(raw[100:108]), _octal(raw[124:136])
    for start, end in ((108, 116), (116, 124), (136, 148)):
        _octal(raw[start:end])
    require(mode <= 0o777 and size <= LIMITS["member_bytes"], "member-mode-or-size-cap")
    require(
        _octal(raw[329:337], blank=True) == _octal(raw[337:345], blank=True) == 0,
        "device-metadata-unsupported",
    )
    _text(raw[265:297])
    _text(raw[297:329])
    link = _text(raw[157:257])
    if kind == "file":
        require(not link, "regular-file-link-field")
    elif kind == "directory":
        require(not link and size == 0, "directory-has-no-payload-or-link")
    else:
        require(link and size == 0, "link-has-target-and-no-payload")
        link = _path(link)
    return path, kind, size, mode, link


class _Namespace:
    def __init__(self):
        self.nodes, self.aliases = {}, {}

    def add(self, path, kind):
        parts = path.split("/")
        for index in range(1, len(parts) + 1):
            current = "/".join(parts[:index])
            folded = unicodedata.normalize("NFC", current.casefold())
            require(
                folded not in self.aliases or self.aliases[folded] == current,
                "case-or-Unicode-namespace-collision",
            )
            self.aliases[folded] = current
            old = self.nodes.get(current)
            if index < len(parts):
                require(old in (None, "implicit-directory", "directory"), "linked-or-file-prefix")
                self.nodes.setdefault(current, "implicit-directory")
            else:
                require(
                    old is None or old == "implicit-directory" and kind == "directory",
                    "duplicate-member-or-prefix-ambiguity",
                )
                self.nodes[current] = kind

    def target(self, path, kind, link):
        resolved = _path(
            (path.rsplit("/", 1)[0] + "/" + link) if kind == "symlink" and "/" in path else link
        )
        allowed = ("file", "directory") if kind == "symlink" else ("file",)
        require(
            resolved != path and self.nodes.get(resolved) in allowed,
            "links-require-earlier-direct-target-without-chains",
        )
        for index in range(1, len(resolved.split("/"))):
            prefix = "/".join(resolved.split("/")[:index])
            require(
                self.nodes.get(prefix) in ("implicit-directory", "directory"), "link-target-prefix"
            )
        return resolved


def _drain(stream, size, capture=False):
    hasher, chunks, remaining = hashlib.sha256(), [], size
    while remaining:
        chunk = stream.exact(min(65536, remaining))
        hasher.update(chunk)
        if capture:
            chunks.append(chunk)
        remaining -= len(chunk)
    padding = (-size) % 512
    require(stream.exact(padding) == b"\0" * padding, "tar-payload-padding")
    return hasher.hexdigest(), b"".join(chunks)


def _parse(raw):
    stream, namespace = _Inflated(raw), _Namespace()
    members, notice_rows, unknown_notice_names = [], [], []
    inventory_bytes, notice_total = 2, 0
    while True:
        block = stream.exact(512)
        if block == b"\0" * 512:
            require(stream.exact(512) == b"\0" * 512, "two-tar-end-blocks")
            while tail := stream.read(65536):
                require(not tail.strip(b"\0"), "nonzero-after-tar-end")
            require(stream.expanded % 512 == 0 and members, "aligned-complete-tar")
            break
        require(len(members) < LIMITS["members"], "member-count-cap")
        path, kind, size, mode, link = _header(block)
        if not members:
            require(
                path == MARKER_NAME and kind == "file" and size == len(MARKER),
                "mandatory-invented-first-member",
            )
        resolved = namespace.target(path, kind, link) if kind in ("symlink", "hardlink") else None
        namespace.add(path, kind)
        notice_candidate = kind == "file" and path.rsplit("/", 1)[-1].upper().startswith(
            ("LICENSE", "NOTICE", "COPYING")
        )
        if notice_candidate:
            require(size <= LIMITS["notice_bytes"], "notice-byte-cap")
            notice_total += size
            require(notice_total <= LIMITS["notice_total_bytes"], "notice-aggregate-cap")
        payload_sha, captured = _drain(stream, size, capture=not members)
        if not members:
            require(captured == MARKER, "invented-marker-content")
        row = {
            "path": path,
            "kind": kind,
            "bytes": size,
            "mode": mode,
            "payload_sha256": payload_sha if kind == "file" else None,
            "link_target": resolved,
        }
        inventory_bytes += len(encode(row)) + (1 if members else 0)
        require(inventory_bytes <= LIMITS["inventory_bytes"], "inventory-byte-cap")
        members.append(row)
        if notice_candidate:
            if path in NOTICE_ALLOWLIST:
                notice_rows.append({"path": path, "bytes": size, "sha256": payload_sha})
            else:
                unknown_notice_names.append(path)
    return {
        "members": members,
        "expanded_bytes": stream.expanded,
        "expanded_sha256": stream.hasher.hexdigest(),
        "inventory_bytes": inventory_bytes,
        "invented_notice_allowlist_metadata": notice_rows,
        "unreviewed_notice_names": unknown_notice_names,
        "notice_candidate_bytes": notice_total,
    }


def _report(raw, held_archive_sha256):
    _pin(raw, held_archive_sha256)
    inventory = _parse(raw)
    identity = _identity()
    return {
        "schema": SCHEMA,
        "kind": "invented",
        "status": "fixture-inventory-complete",
        "source_identity": identity,
        "archive_sha256": held_archive_sha256,
        "compressed_bytes": len(raw),
        "fixture_limits": dict(LIMITS),
        "inherited_limits_not_qualified_for_real_material": dict(INHERITED_UNQUALIFIED_LIMITS),
        "grammar": "one-gzip-flags0-POSIX-ustar-no-extensions-earlier-direct-links-only",
        "notice_coverage": "fixed-invented-allowlist-only-not-complete-notice-clearance",
        "notice_or_member_text_returned": False,
        "payload_provenance_proved_by_marker": False,
        "actual_PBS_grammar_qualified": False,
        "actual_archive_authenticated": False,
        "actual_archive_inspection_authorized": False,
        "runtime_use_authorized": False,
        "native_payload_selectors": None,
        "native_payload_parsed_or_loaded": False,
        "extraction_performed": False,
        "authority": dict(AUTHORITY),
        "retention": {
            "not_after_utc": "2026-11-28T18:32:01Z",
            "max_days_new_facts": 30,
            "earlier_limits_win": True,
            "old_origins_reset": False,
            "unknown_old_origins_timely": False,
            "automatic_cleanup_or_extension": False,
        },
        **inventory,
    }


def inspect_invented_archive(raw, held_archive_sha256):
    """Owned literal invented fixture bytes only; never actual phaseA material."""
    result = _report(raw, held_archive_sha256)
    require(_identity() == result["source_identity"], "fixture-source-changed")
    return result


def inspect_fixture_report(report_raw, held_report_sha256, archive_raw, held_archive_sha256):
    """Cold reconstruction; never call the public producer or follow a path."""
    require(
        type(report_raw) is bytes and 0 < len(report_raw) <= 1024 * 1024, "bounded-fixture-report"
    )
    require(
        type(held_report_sha256) is str and digest(report_raw) == held_report_sha256,
        "held-report-pin",
    )
    report = decode(report_raw)
    expected = _report(archive_raw, held_archive_sha256)
    require(encode(report) == encode(expected), "cold-fixture-reconstruction")
    require(_identity() == expected["source_identity"], "cold-source-changed")
    return {
        "kind": "invented",
        "status": "fixture-metadata-reconstructed",
        "members": len(expected["members"]),
        "actual_archive_authenticated": False,
        "actual_archive_inspection_authorized": False,
        "runtime_use_authorized": False,
        "native_payload_parsed_or_loaded": False,
        "extraction_performed": False,
        "authority": dict(AUTHORITY),
    }
