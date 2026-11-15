"""Fixed invented source discovery: no actual HTTP, GH, Go or retained body."""

import base64
import hashlib
import io
import os
import tempfile
import time
import unittest
import uuid
from pathlib import Path
from unittest import mock

from experiments.simglucose_audit import verifier_preparation as p


class DiscoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        parent = os.environ.get("OT062_DISCOVERY_FIXTURE_PROOF_ROOT")
        cls.root = Path(
            parent
            if parent
            else tempfile.mkdtemp(prefix="ot062-discovery-invented-", dir="/private/tmp")
        )
        cls.root.mkdir(mode=0o700, parents=True, exist_ok=True)

    def output(self):
        parent = self.root / uuid.uuid4().hex
        parent.mkdir(mode=0o700)
        return parent / "invented-intake"

    def test_closed_public_entry_before_arguments(self):
        class Trap:
            def __fspath__(self):
                raise AssertionError("path touched")

        with self.assertRaises(PermissionError):
            p.run_preparation(Trap())

    def test_three_unknown_prehashed_locations_fixed(self):
        targets = p._targets()
        self.assertEqual([x["name"] for x in targets], list(p.NAMES))
        self.assertEqual([x["cap"] for x in targets], list(p.CAPS))
        self.assertTrue(
            all(
                x["expected_sha256"] is None and x["existence_content_verified"] is False
                for x in targets
            )
        )
        self.assertFalse(p.INERT_GH_PROBES["execution_authorized"])

    def test_invented_approval_cannot_actual_executor(self):
        inputs = p.fixture_inputs(self.output())
        with self.assertRaises(ValueError):
            p.collect_approved(*inputs)
        self.assertFalse(Path(inputs[3]["output_root"]).exists())

    def test_completed_three_files_single_readbacks_and_metadata_cold(self):
        output = self.output()
        result = p.run_fixture(output)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(len(result["rows"]), 3)
        for row, body in zip(result["rows"], p.FIXTURES, strict=True):
            self.assertEqual(row["stored_bytes"], len(body))
            self.assertEqual(row["stream_write_sha256"], p.digest(body))
            self.assertEqual(row["readback_attempts"], 1)
            self.assertEqual(row["readback"]["readback_passes"], 1)
            self.assertEqual(row["readback"]["readback_sha256"], p.digest(body))
            self.assertFalse(row["source_authenticated"])
        raw = (output / "intake-receipt.private.json").read_bytes()
        review = (output / "metadata-review.private.json").read_bytes()
        with mock.patch.object(p, "_readback", side_effect=AssertionError("body reread")):
            cold = p.inspect_receipt_metadata(
                raw,
                p.digest(raw),
                result["pins"],
                fixture=True,
                review_raw=review,
                held_review_sha256=p.digest(review),
            )
        self.assertFalse(cold["source_bodies_reopened_or_hashed"])
        self.assertFalse(cold["publisher_authenticated"])

    def test_overflow_consumes_sentinel_but_diskcap_no_readback(self):
        output = self.output()
        result = p.run_fixture(output, "extra")
        self.assertEqual(result["status"], "rejected")
        row = result["rows"][0]
        cap = p.FIXTURE_CAPS[0]
        self.assertEqual(row["controller_received_bytes"], cap + 1)
        self.assertEqual(row["stored_bytes"], cap)
        self.assertEqual((output / "objects/go.mod").stat().st_size, cap)
        self.assertEqual(row["stream_write_sha256"], p.digest(b"A" * cap))
        self.assertNotEqual(row["stream_write_sha256"], p.digest(b"A" * (cap + 1)))
        self.assertEqual(row["readback_attempts"], 0)
        self.assertIsNone(row["readback"])
        self.assertEqual(len(result["rows"]), 1)

    def test_invalid_empty_UTF8_NUL_rejected_without_readback(self):
        for case in ("empty", "utf8", "nul"):
            with self.subTest(case=case):
                result = p.run_fixture(self.output(), case)
                self.assertEqual(result["status"], "rejected")
                self.assertIsNone(result["rows"][0]["accepted_observed_sha256"])
                self.assertEqual(result["rows"][0]["readback_attempts"], 0)

    def test_actual_response_short_recv_utf8_and_unknown_hash(self):
        body = "INVENTED café\n".encode()
        frames = []

        class Connection:
            raw = (
                b"HTTP/1.1 200 OK\r\nContent-Length: "
                + str(len(body)).encode()
                + b"\r\n\r\n"
                + body
            )

            def sendall(self, _raw):
                pass

            def recv(self, _n):
                value, self.raw = self.raw[:1], self.raw[1:]
                return value

        with mock.patch.object(p, "_emit", side_effect=frames.append):
            p._response(Connection(), 0, 32)
        self.assertEqual(len(frames), 3)
        self.assertEqual(base64.b64decode(frames[1]["data"]), body)
        self.assertEqual(frames[2]["bytes"], len(body))

    def test_redirect_status_framing_and_headercaps(self):
        bad = [
            b"HTTP/1.1 200 OK\r\nContent-Length: 1\r\nContent-Length: 1\r\n\r\n",
            b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n",
            b"HTTP/1.1 200 OK\r\nContent-Range: bytes 0-1/2\r\n\r\n",
            b"HTTP/1.1 200 OK\r\nContent-Encoding: gzip\r\n\r\n",
            b"HTTP/1.1 200 OK\r\nX: " + b"x" * 8192 + b"\r\n\r\n",
        ]
        for raw in bad:
            with self.subTest(raw=raw[:30]), self.assertRaises(ValueError):
                p._headers(raw)

        class Connection:
            def __init__(self, raw):
                self.raw = raw

            def sendall(self, _raw):
                pass

            def recv(self, n):
                value, self.raw = self.raw[:n], self.raw[n:]
                return value

        for raw in [
            b"HTTP/1.1 302 Found\r\nLocation: https://evil.invalid\r\n\r\n",
            b"HTTP/1.1 404 Not Found\r\n\r\n",
            b"HTTP/1.1 200 OK\r\nContent-Length: +1\r\n\r\n",
            b"HTTP/1.1 200 OK\r\nContent-Length: 33\r\n\r\n",
        ]:
            with (
                mock.patch.object(p, "_emit"),
                self.subTest(raw=raw[:30]),
                self.assertRaises(ValueError),
            ):
                p._response(Connection(raw), 0, 32)

    def test_acknowledged_partial_zero_error_writes(self):
        expiry = p.core._now() + p.timedelta(minutes=5)
        wire = {"fixture": True, "case": "ok", "request_seconds": 1}
        saved = os.write
        for mode in ("partial", "zero", "error"):
            parent = self.output().parent
            fd = os.open(parent / "invented-prefix", os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o600)
            hasher = hashlib.sha256()
            calls = [0]
            observed = {}

            def write(number, raw):
                calls[0] += 1
                if mode == "zero":
                    return 0
                if mode == "error" and calls[0] > 1:
                    raise OSError("INVENTED")
                return saved(number, raw[:3])

            try:
                with mock.patch.object(p.os, "write", side_effect=write):
                    if mode == "partial":
                        count, _ = p._request(
                            wire, 0, fd, hasher, time.monotonic() + 2, expiry, observed
                        )
                        self.assertEqual(count, len(p.FIXTURES[0]))
                        self.assertEqual(hasher.hexdigest(), p.digest(p.FIXTURES[0]))
                    else:
                        with self.assertRaises((ValueError, OSError)):
                            p._request(wire, 0, fd, hasher, time.monotonic() + 2, expiry, observed)
                        count = 0 if mode == "zero" else 3
                        self.assertEqual(os.fstat(fd).st_size, count)
                        self.assertEqual(hasher.hexdigest(), p.digest(p.FIXTURES[0][:count]))
            finally:
                os.close(fd)

    def test_fixed_plan_mutations_before_path(self):
        inputs = p.fixture_inputs(self.output())
        original = p.decode(inputs[0])
        for key, value in (
            ("targets", []),
            ("limits", {}),
            ("source", {}),
            ("owner", {}),
            ("rights_basis_sha256", "0" * 64),
            ("qualification_sha256", None),
            ("output_root", "/private/tmp/not-the-held-path"),
        ):
            plan = dict(original, **{key: value})
            raw = p.encode(plan)
            held = dict(inputs[3], plan_sha256=p.digest(raw))
            approval = p.decode(inputs[1])
            approval["plan_sha256"] = held["plan_sha256"]
            approval_raw = p.encode(approval)
            held["approval_sha256"] = p.digest(approval_raw)
            with self.subTest(key=key), self.assertRaises(ValueError):
                p._gate(raw, approval_raw, inputs[2], held, True)

    def test_earlier_grant_and_origin_fences(self):
        inputs = p.fixture_inputs(self.output())
        approval = p.decode(inputs[1])
        approval["expires_utc"] = p.core._stamp(p.core._now() + p.timedelta(seconds=139))
        raw = p.encode(approval)
        held = dict(inputs[3], approval_sha256=p.digest(raw))
        with self.assertRaises(ValueError):
            p._gate(inputs[0], raw, inputs[2], held, True, True)
        for key, value in (
            ("unknown_referenced_origins_timely_claimed", True),
            ("does_not_reset_referenced_material_origins", False),
        ):
            origin = p.decode(inputs[2])
            origin[key] = value
            raw = p.encode(origin)
            held = dict(inputs[3], origin_sha256=p.digest(raw))
            with self.subTest(key=key), self.assertRaises(ValueError):
                p._gate(inputs[0], inputs[1], raw, held, True)

    def test_marker_prevents_replay_after_preserved_rename(self):
        output = self.output()
        inputs = p.fixture_inputs(output)
        first = p._execute(*inputs, fixture=True, case="ok", whole_seconds=3, request_seconds=1)
        self.assertEqual(first["status"], "completed")
        output.rename(output.parent / "preserved-invented")
        second = p._execute(*inputs, fixture=True, case="ok", whole_seconds=3, request_seconds=1)
        self.assertNotEqual(second["status"], "completed")
        self.assertFalse(output.exists())
        self.assertEqual(len(list(output.parent.glob(".discovery-consumed-*"))), 1)

    def test_source_fifo_symlink_and_chunk_expiry(self):
        parent = self.output().parent
        source = parent / "invented-source.py"
        source.write_bytes(b"# invented\n" * 7000)
        os.symlink(source, parent / "link")
        os.mkfifo(parent / "fifo", 0o600)
        expiry = p.core._now() + p.timedelta(minutes=1)
        for name in ("link", "fifo"):
            with self.subTest(name=name), self.assertRaises((OSError, ValueError)):
                p._source_hash(parent / name, expiry)
        now = p.core._now()
        with (
            mock.patch.object(p.core, "_now", side_effect=[now, now, now + p.timedelta(seconds=2)]),
            self.assertRaises(ValueError),
        ):
            p._source_hash(source, now + p.timedelta(seconds=1))

    def test_all_stalled_stages_stop_and_preserve_only_metadata(self):
        for case in (
            "stall-connect",
            "stall-header",
            "stall-body",
            "stall-storage",
            "stall-fsync",
            "stall-readback",
            "stall-finalize",
        ):
            with self.subTest(case=case):
                output = self.output()
                start = time.monotonic()
                result = p.run_fixture(output, case, whole_seconds=0.8, request_seconds=0.3)
                self.assertNotEqual(result["status"], "completed")
                self.assertLess(time.monotonic() - start, 2)
                if "rows" in result:
                    for row in result["rows"]:
                        self.assertIsNone(row["accepted_observed_sha256"])
                        self.assertIsNone(row["readback"])

    def test_protocol_error_after_receipt_and_nonzero_not_success(self):
        class Fake:
            def __init__(self, frames, code):
                self.stdin = io.BytesIO()
                self.stdout = io.BytesIO(b"".join(p.encode(x) + b"\n" for x in frames))
                self.returncode = code

            def poll(self):
                return self.returncode

            def wait(self, timeout):
                return self.returncode

        for frames, code in (
            ([{"receipt": {}}, {"error": "INVENTED"}], 0),
            ([{"receipt": {}}], 17),
        ):
            with (
                mock.patch.object(p.platform_process, "spawn", return_value=Fake(frames, code)),
                mock.patch.object(p.platform_process, "tree_exists", return_value=False),
                mock.patch.object(p.platform_process, "close_tree"),
            ):
                self.assertIsNone(
                    p._supervise({"deadline": time.monotonic() + 1}, time.monotonic() + 2)
                )

    def test_rehashed_metadata_cannot_promote_trust_readback(self):
        output = self.output()
        result = p.run_fixture(output)
        review = (output / "metadata-review.private.json").read_bytes()
        for key, value in (
            ("source_authenticated", True),
            ("GH_execution_authorized", True),
            ("trust_roots_admitted", True),
            ("installed_binary_verified", True),
        ):
            receipt = dict(result, **{key: value})
            raw = p.encode(receipt)
            with self.subTest(key=key), self.assertRaises(ValueError):
                p.inspect_receipt_metadata(
                    raw,
                    p.digest(raw),
                    result["pins"],
                    fixture=True,
                    review_raw=review,
                    held_review_sha256=p.digest(review),
                )
        receipt = p.decode(p.encode(result))
        receipt["rows"][0]["readback"]["readback_passes"] = 2
        raw = p.encode(receipt)
        with self.assertRaises(ValueError):
            p.inspect_receipt_metadata(
                raw,
                p.digest(raw),
                result["pins"],
                fixture=True,
                review_raw=review,
                held_review_sha256=p.digest(review),
            )

    def test_bounded_mod_lexical_summary_not_Go_evaluation(self):
        text = (
            "module invented.example/cli\ngo 1.99\ntoolchain go1.99.1\n"
            "require (\n invented.example/a v1.0.0 // indirect\n)\n"
            "replace invented.example/a => ../local\n"
        )
        summary = p._summarize_mod(text)
        self.assertEqual(summary["module"], "invented.example/cli")
        self.assertEqual(summary["toolchain"], "go1.99.1")
        self.assertEqual(
            summary["dependencies"], [{"module": "invented.example/a", "version": "v1.0.0"}]
        )
        self.assertIn("replace", summary["unknown_directives"])
        self.assertFalse(summary["semantic_or_dependency_closure_verified"])
        p._validate_static(summary, "go.mod")
        bounded = p._summarize_mod(
            "module a\nmodule b\n" + "require invented.example/a v1.0.0\n" * 70 + "x" * 4097
        )
        self.assertIsNone(bounded["module"])
        self.assertEqual(len(bounded["dependencies"]), 64)
        self.assertTrue(bounded["labels_truncated"])
        self.assertEqual(bounded["oversized_lines"], 1)
        p._validate_static(bounded, "go.mod")

    def test_receipt_order_stop_and_stat_only_incomplete(self):
        output = self.output()
        good = p.run_fixture(output)
        held = good["pins"]
        bad = p.decode(p.encode(good))
        bad["rows"].reverse()
        with self.assertRaises(ValueError):
            p._validate_receipt(bad, held, True)
        bad = p.decode(p.encode(good))
        bad["status"] = "rejected"
        bad["error"] = "capture-or-readback-rejected"
        with self.assertRaises(ValueError):
            p._validate_receipt(bad, held, True)
        partial = p.decode(p.encode(good))
        partial["status"] = "incomplete"
        partial["error"] = "owned-controller-failure"
        partial["metadata_review_sha256"] = None
        row = partial["rows"][0]
        partial["rows"] = [row]
        row.update(
            status="incomplete",
            stream_write_sha256=None,
            controller_received_bytes=None,
            readback=None,
            readback_attempts=None,
            readback_observed_bytes=None,
            accepted_observed_sha256=None,
        )
        p._validate_receipt(partial, held, True)
        for key, value in (
            ("stream_write_sha256", "0" * 64),
            ("controller_received_bytes", 0),
            ("readback_attempts", 0),
            ("readback_observed_bytes", 0),
        ):
            bad = p.decode(p.encode(partial))
            bad["rows"][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                p._validate_receipt(bad, held, True)

    def test_actual_caps_one_byte_fragments_and_sentinels_fit_IPC(self):
        import queue

        class Connection:
            def __init__(self, body, declared):
                self.raw = (
                    b"HTTP/1.1 200 OK\r\nContent-Length: "
                    + str(declared).encode()
                    + b"\r\n\r\n"
                    + body
                )
                self.cursor = 0

            def sendall(self, _raw):
                pass

            def recv(self, n):
                self.assert_bound = n
                value = self.raw[self.cursor : self.cursor + 1]
                self.cursor += len(value)
                return value

        for index, cap in enumerate(p.CAPS):
            for extra in (0, 1):
                frames = []
                connection = Connection(b"X" * (cap + extra), cap)
                with mock.patch.object(p, "_emit", side_effect=frames.append):
                    p._response(connection, index, cap)
                self.assertLess(len(frames), p.FRAME_LIMIT)
                self.assertEqual(frames[-1]["bytes"], cap + extra)
                self.assertEqual(
                    sum(len(base64.b64decode(f["data"])) for f in frames if f["phase"] == "body"),
                    cap + extra,
                )
                events = queue.Queue()
                p._frames(io.BytesIO(b"".join(p.encode(f) + b"\n" for f in frames)), events)
                items = []
                while not events.empty():
                    items.append(events.get_nowait())
                self.assertEqual(items[-1][0], "eof")
                self.assertNotIn("error", [x[0] for x in items])

    def test_raw_framing_and_truncated_UTF8_reach_same_controller(self):
        class Producer:
            def __init__(self, frames):
                self.stdin = io.BytesIO()
                self.stdout = io.BytesIO(b"".join(p.encode(f) + b"\n" for f in frames))
                self.returncode = 0

            def poll(self):
                return 0

            def wait(self, timeout):
                return 0

        for body, declared in ((b"AAA", 4), (b"A\xc3", 2)):
            frames = [
                {"phase": "headers", "declared": declared},
                {"phase": "body", "data": base64.b64encode(body).decode()},
                {"phase": "done", "bytes": len(body)},
            ]
            path = self.output().parent / "invented-rejected-prefix"
            fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o600)
            try:
                with (
                    mock.patch.object(p.subprocess, "Popen", return_value=Producer(frames)),
                    self.assertRaises(ValueError),
                ):
                    p._request(
                        {"fixture": True, "case": "ok", "request_seconds": 1},
                        0,
                        fd,
                        hashlib.sha256(),
                        time.monotonic() + 2,
                        p.core._now() + p.timedelta(minutes=1),
                    )
            finally:
                os.close(fd)

    def test_cold_metadata_rejects_current_source_and_owner_drift(self):
        output = self.output()
        result = p.run_fixture(output)
        raw = (output / "intake-receipt.private.json").read_bytes()
        review = (output / "metadata-review.private.json").read_bytes()
        for name in ("_identity", "_owner"):
            with (
                mock.patch.object(p, name, return_value={"changed": "0" * 64}),
                self.subTest(name=name),
                self.assertRaises(ValueError),
            ):
                p.inspect_receipt_metadata(
                    raw,
                    p.digest(raw),
                    result["pins"],
                    fixture=True,
                    review_raw=review,
                    held_review_sha256=p.digest(review),
                )
        actual = p._identity()
        with (
            mock.patch.object(p, "_identity", side_effect=[actual, {"changed": "0" * 64}]),
            self.assertRaises(ValueError),
        ):
            p.inspect_receipt_metadata(
                raw,
                p.digest(raw),
                result["pins"],
                fixture=True,
                review_raw=review,
                held_review_sha256=p.digest(review),
            )

    def test_namespace_rechecked_before_only_readback(self):
        output = self.output()
        inputs = p.fixture_inputs(output)
        wire = {
            name: base64.b64encode(raw).decode()
            for name, raw in zip(("plan", "approval", "origin"), inputs[:3], strict=True)
        }
        wire.update(
            held=inputs[3],
            fixture=True,
            case="ok",
            deadline=time.monotonic() + 3,
            request_seconds=1,
            recovery=False,
        )
        original = p._objects_binding
        calls = [0]

        def binding(directory, objects):
            calls[0] += 1
            if calls[0] > 1:
                raise ValueError("INVENTED objects namespace replaced before readback")
            original(directory, objects)

        with (
            mock.patch.object(p, "_objects_binding", side_effect=binding),
            mock.patch.object(p, "_readback", side_effect=AssertionError("unauthorized readback")),
            self.assertRaises(ValueError),
        ):
            p._controller(wire)
        self.assertGreaterEqual(calls[0], 2)

    def test_late_source_no_completed_receipt(self):
        result = p.run_fixture(self.output(), "late-source")
        self.assertNotEqual(result["status"], "completed")


if __name__ == "__main__":
    unittest.main()
