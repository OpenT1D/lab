"""Invented-only PBS transport, authority and owned-watchdog checks."""

import io
import os
import tempfile
import time
import unittest
import uuid
from pathlib import Path
from unittest import mock

from experiments.simglucose_audit import pbs_intake as p


class CollectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw = os.environ.get("OT062_PBS_INTAKE_FIXTURE_PROOF_ROOT")
        if not raw:
            raw = tempfile.mkdtemp(prefix="ot062-pbs-fixture-")  # Retained, no cleanup.
        cls.root = Path(raw)
        cls.root.mkdir(mode=0o700, parents=True, exist_ok=True)

    def output(self):
        parent = self.root / uuid.uuid4().hex
        parent.mkdir(mode=0o700)
        return parent / "invented-intake"

    def rebind(self, inputs, plan=None, approval=None, origin=None):
        plan = p.decode(inputs[0]) if plan is None else plan
        approval = p.decode(inputs[1]) if approval is None else approval
        origin_raw = inputs[2] if origin is None else p.encode(origin)
        held = dict(inputs[3], origin_sha256=p.digest(origin_raw))
        plan["origin_sha256"] = held["origin_sha256"]
        plan_raw = p.encode(plan)
        held["plan_sha256"] = p.digest(plan_raw)
        approval["plan_sha256"] = held["plan_sha256"]
        approval["origin_sha256"] = held["origin_sha256"]
        approval_raw = p.encode(approval)
        held["approval_sha256"] = p.digest(approval_raw)
        return plan_raw, approval_raw, origin_raw, held

    def test_public_refuses_without_inspecting_arguments(self):
        class Trap:
            def __fspath__(self):
                raise AssertionError("touched")

        with self.assertRaises(PermissionError):
            p.run_intake(Trap(), invented=Trap())

    def test_invented_cannot_enter_actual_executor(self):
        inputs = p.fixture_inputs(self.output())
        with self.assertRaises(ValueError):
            p.collect_approved(*inputs)
        self.assertFalse(Path(inputs[3]["output_root"]).exists())

    def test_fixed_metadata_mutations(self):
        inputs = p.fixture_inputs(self.output())
        p._gate(*inputs, fixture=True, headroom=True)
        for key, value in (
            ("kind", "opaque-pbs-plan"),
            ("limits", {}),
            ("target", p._target()),
            ("rights_basis_sha256", "0" * 64),
            ("qualification_sha256", None),
            ("source", {}),
            ("owner", {}),
            ("parent_identity", {}),
            ("retention", {}),
        ):
            plan = p.decode(inputs[0])
            plan[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                p._gate(*self.rebind(inputs, plan=plan), fixture=True)

    def test_approval_and_origin_negative_cases(self):
        inputs = p.fixture_inputs(self.output())
        for key, value in (
            ("authority", {}),
            ("scope", "execute"),
            ("nonce", "x"),
            ("expires_utc", "2026-01-01T00:00:00Z"),
            ("source_sha256", "0" * 64),
            ("kind", "private-one-shot-approval"),
        ):
            approval = p.decode(inputs[1])
            approval[key] = value
            raw = p.encode(approval)
            held = dict(inputs[3], approval_sha256=p.digest(raw))
            with self.subTest(key=key), self.assertRaises(ValueError):
                p._gate(inputs[0], raw, inputs[2], held, fixture=True)
        for key, value in (
            ("origins_verified", False),
            ("unknown_required_origins", ["unknown"]),
            ("records", []),
            ("kind", "private-origin-context"),
        ):
            origin = p.decode(inputs[2])
            origin[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                p._gate(*self.rebind(inputs, origin=origin), fixture=True)

    def test_redirect_exact_scope(self):
        good = f"https://{p.CDN}{p.PREFIX}abc/file?SECRET=ephemeral"
        self.assertEqual(p._redirect(good), good)
        for url in (
            good.replace("https:", "http:"),
            good.replace(p.CDN, "evil.test"),
            good.replace(p.CDN, "user@" + p.CDN),
            good.replace(p.CDN, p.CDN + ":443"),
            good + "#frag",
            good.replace("abc/file", "../file"),
            good.replace("abc/file", "%2e%2e/file"),
            good.replace("abc/file", "abc//file"),
            good + "\r\n",
            good.replace(p.PREFIX, "/other/"),
        ):
            with self.subTest(url=url), self.assertRaises(ValueError):
                p._redirect(url)

    def test_raw_headers(self):
        p._headers(b"HTTP/1.1 200 OK\r\nContent-Length: 12\r\n\r\n")
        cases = [
            b"Content-Range: bytes 0-4/5",
            b"Transfer-Encoding: chunked",
            b"Content-Encoding: gzip",
            b"Content-Length: 1\r\nContent-Length: 1",
            b"X: a\r\nX: b",
            b" malformed",
            b"X: \x00",
            b"X: " + b"a" * 8192,
            b"\r\n".join(f"X{i}: a".encode() for i in range(65)),
        ]
        for raw in cases:
            with self.subTest(raw=raw[:40]), self.assertRaises(ValueError):
                p._headers(b"HTTP/1.1 200 OK\r\n" + raw + b"\r\n\r\n")

    def test_response_sentinel_and_query_redaction(self):
        class Connection:
            def __init__(self, raw):
                self.raw, self.sent = io.BytesIO(raw), None

            def recv(self, maximum):
                return self.raw.read(maximum)

            def sendall(self, raw):
                self.sent = raw

        events = []
        conn = Connection(b"HTTP/1.1 200 OK\r\nContent-Length: 3\r\n\r\nabcdef")
        with mock.patch.object(p, "_emit", events.append):
            self.assertIsNone(p._response(conn, p.URL, 3, False))
        bodies = [p.base64.b64decode(event["data"]) for event in events if event["phase"] == "body"]
        self.assertEqual(b"".join(bodies), b"abcd")
        self.assertEqual(events[-1], {"phase": "done", "bytes": 4})
        self.assertNotIn(b"Cookie", conn.sent)
        url = f"https://{p.CDN}{p.PREFIX}abc?SECRET=abc"
        conn = Connection(b"HTTP/1.1 200 OK\r\n\r\nabc")
        events.clear()
        with mock.patch.object(p, "_emit", events.append):
            p._response(conn, url, 3, True)
        self.assertNotIn("SECRET", repr(events))
        self.assertIn(b"SECRET=abc", conn.sent)

    def test_fragmented_invented_response_is_coalesced_and_sentinel_bounded(self):
        class Connection:
            def __init__(self, body, fragment):
                self.raw = io.BytesIO(b"HTTP/1.1 200 OK\r\n\r\n" + body)
                self.fragment = fragment
                self.requested = []

            def recv(self, maximum):
                self.requested.append(maximum)
                return self.raw.read(min(maximum, self.fragment))

            def sendall(self, _raw):
                pass

        for expected, fragment, extra in (
            (600, 1, 0),
            (600, 1, 5),
            (2 * p.CHUNK_BYTES + 3, 16384, 0),
            (2 * p.CHUNK_BYTES, 16384, 5),
        ):
            body = b"I" * (expected + extra)  # Invented only, at most128KiB+5.
            connection, events = Connection(body, fragment), []
            with (
                self.subTest(expected=expected, fragment=fragment, extra=extra),
                mock.patch.object(p, "_emit", events.append),
            ):
                p._response(connection, p.URL, expected, False)
                chunks = [
                    p.base64.b64decode(row["data"]) for row in events if row["phase"] == "body"
                ]
                consumed = min(len(body), expected + 1)
                self.assertEqual(b"".join(chunks), body[:consumed])
                self.assertEqual(events[-1], {"phase": "done", "bytes": consumed})
                self.assertEqual(len(chunks), (consumed + p.CHUNK_BYTES - 1) // p.CHUNK_BYTES)
                self.assertTrue(all(0 < len(chunk) <= p.CHUNK_BYTES for chunk in chunks))
                self.assertTrue(all(0 < n <= p.CHUNK_BYTES for n in connection.requested))
                self.assertEqual(connection.raw.read(), body[consumed:])
                self.assertLess(len(events), p.FRAME_LIMIT)

    def test_production_size_derived_ipc_capacity_without_archive_allocation(self):
        maximum_body_frames = (p.SIZE + 1 + p.CHUNK_BYTES - 1) // p.CHUNK_BYTES
        self.assertEqual(maximum_body_frames, 385)
        self.assertLess(maximum_body_frames + 2, p.FRAME_LIMIT)  # Headers + done + EOF slot.
        largest_invented_frame = (
            p.encode(
                {"phase": "body", "data": p.base64.b64encode(b"I" * p.CHUNK_BYTES).decode("ascii")}
            )
            + b"\n"
        )
        self.assertLess(len(largest_invented_frame), 90000)
        events = p.queue.Queue(maxsize=p.FRAME_LIMIT + 1)
        # Only small synthetic JSON frames: capacity math requires no25MB body.
        raw = b"".join(
            p.encode({"phase": "body", "data": "SQ=="}) + b"\n"
            for _ in range(maximum_body_frames + 2)
        )
        p._frames(io.BytesIO(raw), events)
        observed = [events.get_nowait() for _ in range(events.qsize())]
        self.assertEqual(len(observed), maximum_body_frames + 3)
        self.assertEqual(observed[-1], ("eof", None))
        self.assertNotIn("error", [row[0] for row in observed])

    def test_tls_defaults_with_invented_context_and_socket_only(self):
        context = mock.Mock(check_hostname=True, verify_mode=p.ssl.CERT_REQUIRED)
        sock = mock.Mock()
        with (
            mock.patch.object(p.ssl, "create_default_context", return_value=context),
            mock.patch.object(p.socket, "create_connection", return_value=sock) as connect,
        ):
            self.assertIs(p._connect(p.URL), context.wrap_socket.return_value)
        connect.assert_called_once_with(("github.com", 443), timeout=60)
        context.wrap_socket.assert_called_once_with(sock, server_hostname="github.com")
        self.assertIsNone(context.keylog_filename)
        context.check_hostname = False
        with (
            mock.patch.object(p.ssl, "create_default_context", return_value=context),
            mock.patch.object(p.socket, "create_connection") as connect,
            self.assertRaises(ValueError),
        ):
            p._connect(p.URL)
        connect.assert_not_called()
        context.check_hostname = True
        context.wrap_socket.side_effect = OSError("INVENTED TLS refusal")
        with (
            mock.patch.object(p.ssl, "create_default_context", return_value=context),
            mock.patch.object(p.socket, "create_connection", return_value=sock),
            self.assertRaises(OSError),
        ):
            p._connect(p.URL)
        sock.close.assert_called_once()

    def test_raw_response_rejections(self):
        class Connection:
            def __init__(self, raw):
                self.raw = io.BytesIO(raw)

            def recv(self, maximum):
                return self.raw.read(maximum)

            def sendall(self, _raw):
                pass

        for raw in (
            b"HTTP/1.1 201 OK\r\n\r\n",
            b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\n",
            b"HTTP/1.1 302 Found\r\nLocation: https://evil.test/a\r\n\r\n",
            b"HTTP/1.1 200 OK\r\nX: " + b"a" * 8192,
        ):
            with self.subTest(raw=raw[:30]), self.assertRaises(ValueError):
                p._response(Connection(raw), p.URL, 3, False)

    def test_owned_success_and_body_identity(self):
        output = self.output()
        receipt = p.run_fixture(output)
        self.assertEqual(receipt["status"], "completed")
        self.assertEqual(receipt["accepted_sha256"], p.digest(p.FIXTURE))
        self.assertFalse(receipt["authentication_verified"])
        self.assertFalse(receipt["members_inspected"])
        self.assertEqual(receipt["authority"], p.AUTHORITY)
        self.assertEqual(receipt["body_readback_passes"], 0)
        self.assertEqual((output / "archive.opaque").stat().st_size, len(p.FIXTURE))
        self.assertEqual(
            sorted(path.name for path in output.iterdir()),
            ["archive.opaque", "intake-receipt.private.json"],
        )
        with self.assertRaises(ValueError):
            p.run_fixture(output)

    def test_owned_wrong_short_extra_rejected(self):
        for case in ("extra", "short", "wrong", "late-source"):
            output = self.output()
            receipt = p.run_fixture(output, case)
            with self.subTest(case=case):
                self.assertNotEqual(receipt["status"], "completed")
                self.assertIsNone(receipt["accepted_sha256"])
                self.assertTrue((output / "archive.opaque").exists())

    def test_actual_owned_watchdogs_and_prefix_preservation(self):
        for case in (
            "stall-connect",
            "stall-header",
            "stall-body",
            "stall-storage",
            "stall-fsync",
            "stall-finalize",
        ):
            output = self.output()
            started = time.monotonic()
            with self.subTest(case=case):
                receipt = p.run_fixture(output, case, whole_seconds=1.6, request_seconds=0.6)
                self.assertLess(time.monotonic() - started, 2.5)
                self.assertNotEqual(receipt["status"], "completed")
                self.assertIsNone(receipt["accepted_sha256"])
                self.assertTrue((output / "archive.opaque").exists())
                if case in ("stall-body", "stall-fsync", "stall-finalize"):
                    self.assertEqual((output / "archive.opaque").stat().st_size, len(p.FIXTURE))

    def test_cleanup_wait_failure_still_joins_and_closes(self):
        class Process:
            stdout = io.BytesIO()

            def poll(self):
                return None

            def kill(self):
                pass

            def wait(self, timeout):
                raise p.subprocess.TimeoutExpired("INVENTED", timeout)

        reader = mock.Mock(ident=1)
        reader.is_alive.return_value = False
        process = Process()
        with self.assertRaises(ValueError):
            p._stop(process, reader, None, False, time.monotonic() + 1)
        reader.join.assert_called_once()
        self.assertTrue(process.stdout.closed)

    def test_receipt_followed_by_error_or_nonzero_exit_is_incomplete(self):
        class Process:
            def __init__(self, frames, code):
                self.stdin = io.BytesIO()
                self.stdout = io.BytesIO(b"".join(p.encode(row) + b"\n" for row in frames))
                self.returncode = code

            def wait(self, timeout):
                return self.returncode

        held = {"output_root": str(self.output())}
        wire = {"deadline": time.monotonic() + 1}
        for frames, code in (
            ([{"receipt": {"status": "completed"}}, {"error": "late"}], 0),
            ([{"receipt": {"status": "completed"}}], 17),
        ):
            process = Process(frames, code)
            with (
                mock.patch.object(p.platform_process, "spawn", return_value=process),
                mock.patch.object(p, "_stop", return_value=False),
            ):
                self.assertIsNone(p._supervise(wire, time.monotonic() + 1))
        self.assertFalse(Path(held["output_root"]).exists())

    def test_clean_leader_with_descendant_cannot_promote_success(self):
        process = mock.Mock()
        process.poll.return_value = 0
        process.stdout = io.BytesIO()
        process.stdin = io.BytesIO()
        reader = mock.Mock(ident=1)
        reader.is_alive.return_value = False
        with (
            mock.patch.object(p.platform_process, "tree_exists", side_effect=[True, False]),
            mock.patch.object(p.platform_process, "force_tree") as force,
            mock.patch.object(p.platform_process, "close_tree") as close,
        ):
            self.assertTrue(p._stop(process, reader, None, True, time.monotonic() + 1))
        force.assert_called_once_with(process)
        close.assert_called_once_with(process)

    def test_partial_and_zero_writes_never_hash_unwritten_suffix(self):
        class Process:
            def __init__(self):
                self.stdin = io.BytesIO()
                self.stdout = io.BytesIO(
                    b"".join(
                        p.encode(row) + b"\n"
                        for row in (
                            {"phase": "headers", "redirected": False},
                            {"phase": "body", "data": p.base64.b64encode(p.FIXTURE).decode()},
                            {"phase": "done", "bytes": len(p.FIXTURE)},
                        )
                    )
                )

        for writes, expected in (([3, OSError("INVENTED")], p.FIXTURE[:3]), ([0], b"")):
            hasher = p.hashlib.sha256()
            wire = {"fixture": True, "case": "ok", "request_seconds": 1}
            with (
                mock.patch.object(p.subprocess, "Popen", return_value=Process()),
                mock.patch.object(p, "_stop", return_value=False),
                mock.patch.object(p.os, "write", side_effect=writes),
                self.assertRaises((OSError, ValueError)),
            ):
                p._request(wire, -1, hasher, 0, time.monotonic() + 1, p.core._utc(p.DEADLINE))
            self.assertEqual(hasher.hexdigest(), p.digest(expected))

    def test_expired_approval_refuses_before_source_read(self):
        inputs = p.fixture_inputs(self.output())
        approval = p.decode(inputs[1])
        approval["expires_utc"] = "2026-01-01T00:00:00Z"
        with (
            mock.patch.object(p, "_identity", side_effect=AssertionError("source read")),
            self.assertRaises(ValueError),
        ):
            p._gate(*self.rebind(inputs, approval=approval), fixture=True)

    def test_source_fifo_and_symlink_refuse_without_body_read(self):
        parent = self.output().parent
        fifo = parent / "invented-fifo"
        os.mkfifo(fifo, 0o600)
        link = parent / "invented-link"
        link.symlink_to(fifo)
        for path in (fifo, link):
            with self.subTest(path=path), self.assertRaises((OSError, ValueError)):
                p._source_hash(path)

    def test_receipt_semantic_counterexamples(self):
        held = {"output_root": str(self.output())}
        wire = {"fixture": True, "held": held}
        good = p._receipt(wire, "completed", len(p.FIXTURE), p.digest(p.FIXTURE), None)
        p._validate_receipt(good, held, True)
        for key, value in (
            ("kind", "opaque-pbs-receipt"),
            ("accepted_sha256", "0" * 64),
            ("bytes", len(p.FIXTURE) + 1),
            ("authentication_verified", True),
            ("members_inspected", True),
            ("runtime_use_authorized", True),
            ("actual_tls_observed", True),
            ("body_readback_passes", False),
            ("retention", {}),
            ("body_path", "../escape"),
            ("authority", {}),
            ("ended_utc", "2030-01-01T00:00:00Z"),
            ("error", "https://secret.example/query"),
        ):
            with self.subTest(key=key), self.assertRaises(ValueError):
                p._validate_receipt(dict(good, **{key: value}), held, True)

    def test_symlink_existing_output_refuses_without_repair(self):
        output = self.output()
        output.symlink_to(output.parent)
        inputs = p.fixture_inputs(output)
        with self.assertRaises(ValueError):
            p._execute(*inputs, fixture=True, whole_seconds=2, request_seconds=0.5)
        self.assertTrue(output.is_symlink())


if __name__ == "__main__":
    unittest.main()
