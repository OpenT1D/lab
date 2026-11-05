"""Fixed matched C19 I/O controls; never full host qualification or admission.

Only the source-owned pair can adopt its own canaries/base artifacts. There is
no caller inventory, target, executable, port, profile or listener selector.
"""

import base64
import copy
import hashlib
import json
import os
import socket
import stat
import threading
from pathlib import Path

PORT = 57321
SLOTS = ("base", "allow-twin")
OUTPUT = ("c19-allowed-read.txt", "c19-allowed-write.txt")
EVIDENCE = ("c19-denied-read.txt", "c19-denied-write.txt")
WITNESS = "c19-parent-witness.json"
OPS = ("output_read", "output_write", "evidence_read", "evidence_write", "loopback")
_TOKEN = object()


def _route():
    from experiments.lt1_diagnostic import native_route

    return native_route


def profile_delta(roots, slot):
    """SBPL constrains the loopback family; the socket uses fixed IPv4 127.0.0.1."""
    route = _route()
    route.need(slot in SLOTS, "fixed C19 profile slot")
    if slot == "base":
        return ""
    return (
        "(allow file-read* (literal " + json.dumps(roots["evidence"] + "/" + EVIDENCE[0]) + "))\n"
        "(allow file-write* (literal " + json.dumps(roots["evidence"] + "/" + EVIDENCE[1]) + "))\n"
        '(allow network-outbound (remote tcp "localhost:57321"))\n'
    )


def log_name(entry):
    return "c19-" + entry["slot"] + "-launch.log" if entry["case_id"] == "C19" else "launch.log"


def _write_bytes(entry):
    return ("opent1d-c19-write:" + entry["slot"] + ":" + entry["nonce_sha256"] + "\n").encode()


def _challenge(entry):
    return ("opent1d-c19:" + entry["slot"] + ":" + entry["nonce_sha256"] + "\n").encode()


def _digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _seed(entry, label):
    return ("opent1d-c19-seed:" + label + ":" + entry["nonce_sha256"] + "\n").encode()


def _snapshot(path):
    route = _route()
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    try:
        before = os.fstat(fd)
        route.need(
            stat.S_ISREG(before.st_mode)
            and before.st_nlink == 1
            and before.st_uid == os.getuid()
            and stat.S_IMODE(before.st_mode) == 0o600
            and before.st_size <= 16 * 1024 * 1024,
            "private bounded C19 object",
        )
        raw = bytearray()
        while part := os.read(fd, min(65536, before.st_size + 1 - len(raw))):
            raw.extend(part)
            route.need(len(raw) <= before.st_size, "C19 object grew")

        def signature(s):
            return [
                s.st_dev,
                s.st_ino,
                s.st_uid,
                stat.S_IMODE(s.st_mode),
                s.st_nlink,
                s.st_size,
                s.st_mtime_ns,
                s.st_ctime_ns,
            ]

        route.need(
            signature(before) == signature(os.fstat(fd)) == signature(Path(path).lstat())
            and len(raw) == before.st_size,
            "C19 object rebound",
        )
        return {"identity": signature(before), "sha256": _digest(raw)}
    finally:
        os.close(fd)


def _create(path, raw):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    parent = os.open(Path(path).parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(parent)
    finally:
        os.close(parent)


def validate_probe(report, entry):
    route = _route()
    route.storage.fields(
        report, "schema kind slot nonce_sha256 completed operations native_host_qualified"
    )
    route.need(
        report["schema"] == "opent1d.lt1-c19-operations/1"
        and all(report[k] == entry[k] for k in ("kind", "slot", "nonce_sha256"))
        and report["completed"] is True
        and report["native_host_qualified"] is False,
        "C19 operation context",
    )
    route.storage.fields(report["operations"], " ".join(OPS))
    for operation in report["operations"].values():
        route.storage.fields(operation, "status error_code sha256")
        route.need(
            (
                operation["status"] == "ok"
                and operation["error_code"] is None
                and route.prior.base.preflight.host_context.sha(operation["sha256"])
            )
            or (
                operation["status"] == "error"
                and operation["sha256"] is None
                and type(operation["error_code"]) is str
                and 0 < len(operation["error_code"]) <= 64
            ),
            "typed C19 operation result",
        )
    return report


class _Listener:
    def __init__(self, entries):
        self.entries = entries
        self.active = None
        self.listener_records = []
        self.listener_errors = []
        self.lock = threading.Lock()
        self.done = threading.Event()
        self.thread = self.listener = None
        self.listener_closed = False

    def start_listener(self):
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # One exclusive parent-owned listener; no reuse-port or fallback endpoint.
        self.listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.listener.bind(("127.0.0.1", PORT))
        self.listener.listen(4)
        self.listener.settimeout(0.1)

        def serve():
            while not self.done.is_set():
                try:
                    connection, address = self.listener.accept()
                except TimeoutError:
                    continue
                except OSError as error:
                    if not self.done.is_set():
                        self.listener_errors.append(type(error).__name__)
                    return
                with connection:
                    connection.settimeout(1)
                    raw = bytearray()
                    try:
                        while len(raw) <= 256:
                            part = connection.recv(min(257 - len(raw), 128))
                            if not part:
                                break
                            raw.extend(part)
                        with self.lock:
                            slot = self.active
                        entry = next((e for e in self.entries if e["slot"] == slot), None)
                        valid = entry is not None and bytes(raw) == _challenge(entry)
                        reply = ("ack:" + _digest(raw) + "\n").encode() if valid else b""
                        if reply:
                            connection.sendall(reply)
                        with self.lock:
                            if len(self.listener_records) >= 4:
                                self.listener_errors.append("connection-bound")
                                return
                            else:
                                self.listener_records.append(
                                    {
                                        "slot": slot,
                                        "peer_host": address[0],
                                        "received_b64": base64.b64encode(raw).decode(),
                                        "reply_b64": base64.b64encode(reply).decode(),
                                        "matched": valid,
                                    }
                                )
                    except OSError as error:
                        self.listener_errors.append(type(error).__name__)

        self.thread = threading.Thread(target=serve, daemon=True)
        self.thread.start()

    def close_listener(self):
        self.done.set()
        if self.thread is not None:
            self.thread.join(timeout=2)
            if self.thread.is_alive():
                self.listener_errors.append("listener-thread-unfinished")
        if self.listener is not None:
            try:
                self.listener.close()
            except OSError as error:
                self.listener_errors.append(type(error).__name__)
        self.listener_closed = not self.listener_errors and (
            self.thread is None or not self.thread.is_alive()
        )


class _PairContext(_Listener):
    """In-process capability, constructed only after both opaque grant checks."""

    def __init__(self, token, attempts, source, invented):
        route = _route()
        route.need(token is _TOKEN, "internal pair constructor")
        self.attempts = tuple((bytes(e), bytes(o)) for e, o in attempts)
        self.entries = [route.decode(e) for e, _ in self.attempts]
        self.source = copy.deepcopy(source)
        self.invented = invented
        self.phase = "preflight"
        super().__init__(self.entries)
        self.snapshots = {}
        self.seed_hashes = {}
        self.initial = {}
        self.base_artifacts = {}
        route.need([e["slot"] for e in self.entries] == list(SLOTS), "ordered C19 pair")
        a, b = self.entries
        route.need(
            all(e["case_id"] == "C19" for e in self.entries)
            and a["roots"]["staging"] == b["roots"]["staging"]
            and a["roots"]["evidence"] == b["roots"]["evidence"]
            and a["nonce_sha256"] != b["nonce_sha256"]
            and a["attempt"] != b["attempt"],
            "shared physical targets and fresh pair identities",
        )
        obs = [route.decode(o) for _, o in self.attempts]
        route.need(
            obs[0]["entry_executable"] == obs[1]["entry_executable"]
            and obs[0]["runtime"] == obs[1]["runtime"],
            "same pair runtime identity",
        )
        paths = [Path(a["roots"][k]) for k in ("staging", "evidence")]
        paths += [Path(e["roots"][k]) for e in self.entries for k in ("packet", "output")]
        route.need(
            all(
                p != q and p not in q.parents and q not in p.parents
                for i, p in enumerate(paths)
                for q in paths[i + 1 :]
            ),
            "separate pair roles",
        )
        self.paths = paths
        self.evidence = Path(a["roots"]["evidence"])

    def contains(self, raw):
        return any(type(raw) is bytes and raw == e for e, _ in self.attempts)

    def check(self, entry, roots, *, log=False):
        route = _route()
        route.need(
            entry in self.entries and self.phase in ("preflight", entry["slot"]), "pair phase"
        )
        if self.phase == "preflight":
            route.need(
                not os.listdir(roots["output"]) and not os.listdir(roots["evidence"]),
                "fresh pair contexts",
            )
            return
        output_names = set(OUTPUT)
        evidence_names = set(EVIDENCE) | set(self.base_artifacts)
        if log:
            evidence_names.add(log_name(entry))
        route.need(set(os.listdir(roots["output"])) == output_names, "C19 output adoption")
        route.need(set(os.listdir(roots["evidence"])) == evidence_names, "C19 evidence adoption")
        paths = [Path(roots["output"]) / n for n in OUTPUT] + [self.evidence / n for n in EVIDENCE]
        for path in paths:
            route.need(
                _snapshot(path) == self.snapshots[str(path)], "C19 canary changed before spawn"
            )
        for name, expected in self.base_artifacts.items():
            route.need(
                _snapshot(self.evidence / name) == expected, "base artifact changed before twin"
            )

    def seed(self):
        route = _route()
        route.need(self.phase == "preflight", "seed once")
        for entry in self.entries:
            for name in OUTPUT:
                path = Path(entry["roots"]["output"]) / name
                raw = _seed(entry, name)
                _create(path, raw)
                self.seed_hashes[str(path)] = _digest(raw)
                self.snapshots[str(path)] = _snapshot(path)
        for name in EVIDENCE:
            path = self.evidence / name
            raw = _seed(self.entries[0], name)
            _create(path, raw)
            self.seed_hashes[str(path)] = _digest(raw)
            self.snapshots[str(path)] = _snapshot(path)
        self.initial = copy.deepcopy(self.snapshots)
        self.phase = "base"

    def before_twin(self, base):
        route = _route()
        outer = base["receipt"]["transport"]["outer"] if base.get("receipt") else None
        route.need(
            base.get("readback")
            and base["readback"]["status"] == "completed"
            and outer
            and outer["status"] == "completed"
            and outer["error"] is None
            and outer.get("cleanup_error") is None
            and outer["exit_code"] == 0
            and outer["remaining_owned_processes"] == []
            and outer["received_signals"] == [],
            "base cleanup/scientific evidence incomplete",
        )
        names = {"c19-base-launch.log", "c19-base-live-entry.json"}
        route.need(
            set(self.evidence.iterdir()) == {self.evidence / n for n in (*EVIDENCE, *names)},
            "exact preserved base namespace",
        )
        self.base_artifacts = {n: _snapshot(self.evidence / n) for n in names}
        # A source-known successful base write is a failed confinement control,
        # but is not an unexplained mutation. Pin its actual bytes before twin.
        for path, original in self.initial.items():
            current = _snapshot(path)
            route.need(
                current["identity"][:5] == original["identity"][:5], "same physical canaries"
            )
            base_write = path in (
                str(self.evidence / EVIDENCE[1]),
                str(Path(self.entries[0]["roots"]["output"]) / OUTPUT[1]),
            )
            allowed_hashes = {original["sha256"]}
            if base_write:
                allowed_hashes.add(_digest(_write_bytes(self.entries[0])))
            route.need(current["sha256"] in allowed_hashes, "unexplained canary mutation")
            if not base_write:
                route.need(current == original, "read canary metadata changed")
            self.snapshots[path] = current
        route.legacy._roots(self.paths)
        self.phase = "allow-twin"


def _record(entry, status, *, receipt=None, result=None, error=None):
    return {
        "slot": entry["slot"],
        "status": status,
        "receipt": receipt,
        "readback": result,
        "error": error,
    }


def _operation_assessment(entries, reports, witness):
    result = {
        "state": "inconclusive",
        "checks": {},
        "native_host_qualified": False,
        "native_execution_authorized": False,
        "effective_erasure_verified": False,
    }
    if len(reports) != 2 or any(p is None for p in reports):
        return result
    for report, entry in zip(reports, entries):
        validate_probe(report, entry)
    base, twin = [p["operations"] for p in reports]
    seed = witness["initial_canaries"]
    checks = {}
    final = witness["final_canaries"]
    checks["same_physical_canaries"] = set(final) == set(seed) and all(
        final[name]["identity"][:5] == before["identity"][:5] for name, before in seed.items()
    )
    read_paths = [str(Path(e["roots"]["output"]) / OUTPUT[0]) for e in entries]
    read_paths.append(str(Path(entries[0]["roots"]["evidence"]) / EVIDENCE[0]))
    checks["read_canaries_unchanged"] = all(final.get(name) == seed[name] for name in read_paths)
    for i, entry in enumerate(entries):
        operations = reports[i]["operations"]
        checks[entry["slot"] + "_allowed_read"] = (
            operations["output_read"]["sha256"]
            == seed[str(Path(entry["roots"]["output"]) / OUTPUT[0])]["sha256"]
        )
        for name, path in (("output_write", Path(entry["roots"]["output"]) / OUTPUT[1]),):
            checks[entry["slot"] + "_allowed_write"] = (
                operations[name]["status"] == "ok"
                and operations[name]["sha256"] == _digest(_write_bytes(entry))
                and witness["final_canaries"].get(str(path), {}).get("sha256")
                == _digest(_write_bytes(entry))
            )
    for name in ("evidence_read", "evidence_write", "loopback"):
        checks["base_denied_" + name] = base[name]["status"] == "error" and base[name][
            "error_code"
        ] in ("EACCES", "EPERM")
        checks["twin_allowed_" + name] = twin[name]["status"] == "ok"
    epath = Path(entries[0]["roots"]["evidence"])
    checks["same_read_seed"] = (
        twin["evidence_read"]["sha256"] == seed[str(epath / EVIDENCE[0])]["sha256"]
    )
    checks["actual_twin_write"] = twin["evidence_write"]["sha256"] == _digest(
        _write_bytes(entries[1])
    ) and witness["final_canaries"].get(str(epath / EVIDENCE[1]), {}).get("sha256") == _digest(
        _write_bytes(entries[1])
    )
    expected_sent = _challenge(entries[1])
    expected_reply = ("ack:" + _digest(expected_sent) + "\n").encode()
    expected = {
        "slot": "allow-twin",
        "peer_host": "127.0.0.1",
        "received_b64": base64.b64encode(expected_sent).decode(),
        "reply_b64": base64.b64encode(expected_reply).decode(),
        "matched": True,
    }
    checks["actual_listener_exchange"] = witness["listener_records"] == [expected] and twin[
        "loopback"
    ]["sha256"] == _digest(expected_reply)
    checks["owned_listener_cleanup"] = (
        witness["listener_closed"] is True and witness["listener_errors"] == []
    )
    checks["pair_context_clean"] = witness["pair_error"] is None
    result["checks"] = checks
    result["state"] = "demonstrated" if all(checks.values()) else "inconclusive"
    if any(base[n]["status"] == "ok" for n in ("evidence_read", "evidence_write", "loopback")):
        result["state"] = "base-unconfined"
    return result


def _assessment(entries, records, witness):
    reports = [r["readback"].get("host_probe") if r.get("readback") else None for r in records]
    result = _operation_assessment(entries, reports, witness)
    if result["checks"]:
        complete = len(records) == 2 and all(
            r.get("readback") and r["readback"]["status"] == "completed" for r in records
        )
        result["checks"]["both_scientific_sessions_complete"] = complete
        if not complete and result["state"] == "demonstrated":
            result["state"] = "inconclusive"
    return result


def _run_pair(attempts, expected_identity, cancel, *, invented=False):
    route = _route()
    if not invented:
        registry = route.legacy._admissions()
        route.need(registry["setup"] and registry["execution"], "no reviewed C19 grants")
    route.need(type(attempts) in (list, tuple) and len(attempts) == 2, "two C19 slots")
    owned = copy.deepcopy(attempts)
    # Both exact opaque memberships precede any source, path or process intake.
    for e, o in owned:
        if invented:
            item = route.decode(e)
            registry = {
                "schema": "opent1d.lt1-native-admissions/1",
                "setup": [item["setup_sha256"]],
                "execution": [
                    route.storage.digest(e),
                    route.storage.digest(o),
                    item["engine_sha256"],
                    item["integration_sha256"],
                ],
            }
        route.admit(e, o, registry, invented)
    pair = _PairContext(_TOKEN, owned, expected_identity, invented)
    captures = []
    for e, o in owned:
        captures.append(
            route._launch(
                e, o, expected_identity, cancel, invented=invented, _pair=pair, _preflight_only=True
            )
        )
    if cancel is not None and cancel.is_set():
        return {
            "schema": "opent1d.lt1-native-case-observation/2",
            "case_id": "C19",
            "kind": pair.entries[0]["kind"],
            "planned_slots": list(SLOTS),
            "records": [_record(e, "not-started-cancelled") for e in pair.entries],
            "comparisons": {
                "state": "inconclusive",
                "checks": {},
                "native_host_qualified": False,
                "native_execution_authorized": False,
                "effective_erasure_verified": False,
            },
            "all_slots_accounted": True,
            "parent_witness_sha256": None,
            "unrelated_sentinel": None,
            "native_acceptance": False,
            "native_execution_authorized": False,
            "new_authority_granted": False,
        }
    route.need(route.source_identity() == expected_identity, "pair source before first write")
    if not invented:
        route.need(route.legacy._admissions() == registry, "pair authority before first write")
    route.legacy._roots(pair.paths)  # Cross-slot physical ancestry, including case aliases.
    pair.seed()
    records = []
    pair_error = None
    try:
        pair.start_listener()
        for ordinal, ((entry_raw, observation_raw), entry) in enumerate(zip(owned, pair.entries)):
            if cancel is not None and cancel.is_set():
                records.append(_record(entry, "not-started-cancelled"))
                continue
            if pair_error is not None:
                records.append(_record(entry, "not-run-pair-unsafe", error=pair_error))
                continue
            if ordinal:
                try:
                    pair.before_twin(records[0])
                except (ValueError, OSError) as error:
                    pair_error = str(error)
                    records.append(_record(entry, "not-run-pair-unsafe", error=pair_error))
                    continue
            with pair.lock:
                pair.active = entry["slot"]
            captured = {}
            receipt = None
            try:
                receipt = route._launch(
                    entry_raw,
                    observation_raw,
                    expected_identity,
                    cancel,
                    invented=invented,
                    _pair=pair,
                    _captured=captured,
                )
                from experiments.lt1_diagnostic.native_route_reader import inspect

                raw = route.encoded(receipt)
                result = inspect(
                    raw,
                    _digest(raw),
                    entry_raw,
                    observation_raw,
                    captured["packet"],
                    captured["output_files"],
                    expected_identity=expected_identity,
                )
                records.append(_record(entry, result["status"], receipt=receipt, result=result))
            except (ValueError, OSError) as error:
                pair_error = str(error)
                records.append(
                    _record(
                        entry,
                        "forensic-refusal" if receipt else "route-refused",
                        receipt=receipt,
                        error=pair_error,
                    )
                )
            with pair.lock:
                pair.active = None
    except (ValueError, OSError) as error:
        pair_error = type(error).__name__ + ": " + str(error)
    finally:
        pair.close_listener()
    for entry in pair.entries[len(records) :]:
        records.append(_record(entry, "not-run-pair-unsafe", error=pair_error))
    final = {}
    try:
        final = {path: _snapshot(path) for path in pair.initial}
        allowed_evidence = set(EVIDENCE) | {
            "c19-" + slot + suffix
            for slot in SLOTS
            for suffix in ("-launch.log", "-live-entry.json")
        }
        observed = set(os.listdir(pair.evidence))
        route.need(observed <= allowed_evidence, "unexpected final C19 evidence")
        if all(r.get("readback") and r["readback"]["status"] == "completed" for r in records):
            route.need(observed == allowed_evidence, "missing final C19 evidence")
        for name, expected in pair.base_artifacts.items():
            route.need(
                _snapshot(pair.evidence / name) == expected, "base artifact changed after twin"
            )
    except (ValueError, OSError) as error:
        pair_error = str(error)
    witness = {
        "schema": "opent1d.lt1-c19-parent-witness/1",
        "kind": pair.entries[0]["kind"],
        "entry_sha256": [_digest(e) for e, _ in owned],
        "receipt_sha256": [
            _digest(route.encoded(r["receipt"])) if r["receipt"] else None for r in records
        ],
        "source_identity": expected_identity,
        "initial_canaries": pair.initial,
        "final_canaries": final,
        "base_artifacts": pair.base_artifacts,
        "listener_records": pair.listener_records,
        "listener_errors": pair.listener_errors,
        "listener_closed": pair.listener_closed,
        "pair_error": pair_error,
        "native_host_qualified": False,
    }
    assessment = _assessment(pair.entries, records, witness)
    raw = route.encoded(witness)
    _create(pair.evidence / WITNESS, raw)
    return {
        "schema": "opent1d.lt1-native-case-observation/2",
        "case_id": "C19",
        "kind": pair.entries[0]["kind"],
        "planned_slots": list(SLOTS),
        "records": records,
        "comparisons": assessment,
        "all_slots_accounted": len(records) == 2,
        "parent_witness_sha256": _digest(raw),
        "unrelated_sentinel": None,
        "native_acceptance": False,
        "native_execution_authorized": False,
        "new_authority_granted": False,
    }


def inspect_pair(
    witness_raw, expected_witness_sha256, attempts, receipts, packets, outputs, *, expected_identity
):
    """Cold pair assessment from externally pinned parent and actual route bytes.

    A child report alone cannot establish an I/O denial. This consumer needs the
    separately retained parent witness, exact two receipts and all owned buffers.
    """
    route = _route()
    route.need(
        type(witness_raw) is bytes
        and 0 < len(witness_raw) <= 1024 * 1024
        and _digest(witness_raw) == expected_witness_sha256,
        "pinned parent witness",
    )
    witness = route.decode(witness_raw)
    route.storage.fields(
        witness,
        "schema kind entry_sha256 receipt_sha256 source_identity initial_canaries "
        "final_canaries base_artifacts listener_records listener_errors listener_closed "
        "pair_error native_host_qualified",
    )
    route.need(
        witness["schema"] == "opent1d.lt1-c19-parent-witness/1"
        and witness["source_identity"] == expected_identity == route.source_identity()
        and witness["native_host_qualified"] is False,
        "parent witness origin/source",
    )
    route.need(
        all(
            type(v) in (tuple, list) and len(v) == 2 for v in (attempts, receipts, packets, outputs)
        ),
        "complete pair data denominator",
    )
    entries = [route.decode(e) for e, _ in attempts]
    route.need(
        [e["slot"] for e in entries] == list(SLOTS)
        and all(e["case_id"] == "C19" and e["kind"] == witness["kind"] for e in entries)
        and entries[0]["nonce_sha256"] != entries[1]["nonce_sha256"]
        and all(entries[0]["roots"][k] == entries[1]["roots"][k] for k in ("staging", "evidence"))
        and entries[0]["roots"]["output"] != entries[1]["roots"]["output"]
        and entries[0]["roots"]["packet"] != entries[1]["roots"]["packet"]
        and witness["entry_sha256"] == [_digest(e) for e, _ in attempts],
        "pinned matched pair",
    )
    expected_seed = {
        str(Path(e["roots"]["output"]) / n): _digest(_seed(e, n)) for e in entries for n in OUTPUT
    }
    expected_seed.update(
        {
            str(Path(entries[0]["roots"]["evidence"]) / n): _digest(_seed(entries[0], n))
            for n in EVIDENCE
        }
    )
    route.need(
        type(witness["initial_canaries"]) is dict
        and set(witness["initial_canaries"]) == set(expected_seed),
        "exact six parent seeds",
    )
    for label in ("initial_canaries", "final_canaries"):
        values = witness[label]
        route.need(
            type(values) is dict and set(values) <= set(expected_seed), "fixed parent canary paths"
        )
        for name, value in values.items():
            route.storage.fields(value, "identity sha256")
            sig = value["identity"]
            route.need(
                type(sig) is list
                and len(sig) == 8
                and all(type(v) is int and v >= 0 for v in sig)
                and sig[3] == 0o600
                and sig[4] == 1
                and sig[5] <= 4096
                and route.prior.base.preflight.host_context.sha(value["sha256"]),
                "typed parent canary",
            )
            if label == "initial_canaries":
                route.need(value["sha256"] == expected_seed[name], "source-derived read seed")
            else:
                route.need(
                    sig[:5] == witness["initial_canaries"][name]["identity"][:5],
                    "same physical final canary",
                )
    route.need(
        type(witness["listener_closed"]) is bool
        and type(witness["listener_errors"]) is list
        and len(witness["listener_errors"]) <= 16
        and all(type(v) is str and 0 < len(v) <= 128 for v in witness["listener_errors"])
        and (
            witness["pair_error"] is None
            or type(witness["pair_error"]) is str
            and 0 < len(witness["pair_error"]) <= 16384
        ),
        "parent cleanup fields",
    )
    route.need(
        type(witness["listener_records"]) is list and len(witness["listener_records"]) <= 4,
        "bounded listener records",
    )
    for record in witness["listener_records"]:
        route.storage.fields(record, "slot peer_host received_b64 reply_b64 matched")
        route.need(
            record["slot"] in (*SLOTS, None)
            and type(record["matched"]) is bool
            and record["peer_host"] == "127.0.0.1",
            "parent listener context",
        )
        for key, maximum in (("received_b64", 344), ("reply_b64", 172)):
            value = record[key]
            route.need(type(value) is str and len(value) <= maximum, "bounded parent network bytes")
            raw = base64.b64decode(value, validate=True)
            route.need(base64.b64encode(raw).decode() == value, "canonical parent network bytes")
    route.need(
        type(witness["base_artifacts"]) is dict
        and set(witness["base_artifacts"])
        in (set(), {"c19-base-launch.log", "c19-base-live-entry.json"}),
        "fixed preserved base artifacts",
    )
    for snapshot in witness["base_artifacts"].values():
        route.storage.fields(snapshot, "identity sha256")
        sig = snapshot["identity"]
        route.need(
            type(sig) is list
            and len(sig) == 8
            and all(type(v) is int and v >= 0 for v in sig)
            and sig[3] == 0o600
            and sig[4] == 1
            and sig[5] <= 16 * 1024 * 1024
            and route.prior.base.preflight.host_context.sha(snapshot["sha256"]),
            "typed preserved base artifact",
        )
    records = []
    from experiments.lt1_diagnostic.native_route_reader import inspect

    route.need(
        witness["receipt_sha256"] == [_digest(r) if r is not None else None for r in receipts],
        "parent pinned actual receipts",
    )
    for entry, (entry_raw, observation_raw), receipt_raw, packet, output in zip(
        entries, attempts, receipts, packets, outputs
    ):
        if receipt_raw is None:
            records.append(_record(entry, "not-run", error="missing actual receipt"))
        else:
            result = inspect(
                receipt_raw,
                _digest(receipt_raw),
                entry_raw,
                observation_raw,
                packet,
                output,
                expected_identity=expected_identity,
            )
            records.append(
                _record(entry, result["status"], receipt=route.decode(receipt_raw), result=result)
            )
    if all(r.get("readback") and r["readback"]["status"] == "completed" for r in records):
        route.need(
            set(witness["base_artifacts"]) == {"c19-base-launch.log", "c19-base-live-entry.json"},
            "complete pair requires preserved base snapshots",
        )
    return _assessment(entries, records, witness)
