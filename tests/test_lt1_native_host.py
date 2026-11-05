"""C19 matched controls with actual owned ordinary tooling, never native setup."""

import base64
import copy
import json
import os
import shutil
import socket
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import lt1_native_route_fixture as fixture

from experiments.lt1_diagnostic import native_route as route
from experiments.lt1_diagnostic import native_route_cases as cases
from experiments.lt1_diagnostic import native_route_host as host


class HostClosedTests(unittest.TestCase):
    def test_native_pair_gate_precedes_every_caller_source_path_and_process(self):
        class Bomb:
            def __getattribute__(self, name):
                raise AssertionError("caller touched before gate")

        with (
            patch.object(route, "source_identity", side_effect=AssertionError("source")),
            patch.object(host, "_create", side_effect=AssertionError("write")),
            patch.object(host.socket, "socket", side_effect=AssertionError("listener")),
        ):
            with self.assertRaisesRegex(ValueError, "no reviewed"):
                cases.run("C19", Bomb(), expected_identity=Bomb())
            with self.assertRaisesRegex(ValueError, "no reviewed"):
                host._run_pair(Bomb(), Bomb(), Bomb())
        self.assertEqual(cases.planned_native_cases()["C19"]["slots"], ["base", "allow-twin"])

    def test_fixed_profile_delta_has_same_literal_targets_and_one_endpoint(self):
        roots = {k: "/private/tmp/fixed-" + k for k in route.prior.base.ROOTS}
        self.assertEqual(host.profile_delta(roots, "base"), "")
        twin = host.profile_delta(roots, "allow-twin")
        self.assertEqual(twin.count("(allow "), 3)
        self.assertIn('(literal "/private/tmp/fixed-evidence/c19-denied-read.txt")', twin)
        self.assertIn('(literal "/private/tmp/fixed-evidence/c19-denied-write.txt")', twin)
        self.assertIn('(remote tcp "localhost:57321")', twin)
        self.assertNotIn("subpath", twin)
        self.assertNotIn("process-exec", twin)
        with self.assertRaises(ValueError):
            host.profile_delta(roots, "foreign")

    def test_shared_namespace_and_tooling_profile_remain_fixed(self):
        from experiments.lt1_diagnostic import native_route_host_tooling as tooling

        namespace = json.loads((route.HERE / "native_attempt_namespace.json").read_bytes())
        self.assertTrue(set(host.OUTPUT) <= set(namespace["roles"]["output"]["files"]))
        self.assertTrue(
            set((*host.EVIDENCE, host.WITNESS)) <= set(namespace["roles"]["evidence"]["files"])
        )
        roots = {"output": "/private/tmp/c19-output", "evidence": "/private/tmp/c19-evidence"}
        node, log = Path("/fixed/ordinary/bin/node"), Path("/private/tmp/c19.log")
        base = tooling.profile(node, roots, "base", log)
        twin = tooling.profile(node, roots, "allow-twin", log)
        self.assertEqual(twin, base + host.profile_delta(roots, "allow-twin"))
        self.assertIn('(allow process-exec (literal "/fixed/ordinary/bin/node"))', base)
        self.assertNotIn("runtime/bin/node", base)
        self.assertNotIn("native_route_cli.mjs", base)

    def test_matched_positive_needs_real_parent_seed_write_and_listener_controls(self):
        entries = [
            {
                "kind": "invented",
                "slot": slot,
                "nonce_sha256": str(i + 1) * 64,
                "roots": {"output": "/private/tmp/" + slot, "evidence": "/private/tmp/shared"},
            }
            for i, slot in enumerate(host.SLOTS)
        ]
        initial = {
            str(Path(e["roots"]["output"]) / n): {"sha256": host._digest(host._seed(e, n))}
            for e in entries
            for n in host.OUTPUT
        }
        initial.update(
            {
                "/private/tmp/shared/" + n: {"sha256": host._digest(host._seed(entries[0], n))}
                for n in host.EVIDENCE
            }
        )
        for index, value in enumerate(initial.values()):
            value["identity"] = [1, index + 1, os.getuid(), 0o600, 1, 123, 1, 1]
        final = copy.deepcopy(initial)
        reports = []
        for entry in entries:
            operations = {
                n: {"status": "ok", "error_code": None, "sha256": "a" * 64} for n in host.OPS
            }
            operations["output_read"]["sha256"] = initial[
                entry["roots"]["output"] + "/" + host.OUTPUT[0]
            ]["sha256"]
            operations["output_write"]["sha256"] = host._digest(host._write_bytes(entry))
            final[entry["roots"]["output"] + "/" + host.OUTPUT[1]]["sha256"] = host._digest(
                host._write_bytes(entry)
            )
            if entry["slot"] == "base":
                for n in ("evidence_read", "evidence_write", "loopback"):
                    operations[n] = {"status": "error", "error_code": "EPERM", "sha256": None}
            else:
                operations["evidence_read"]["sha256"] = initial[
                    "/private/tmp/shared/" + host.EVIDENCE[0]
                ]["sha256"]
                operations["evidence_write"]["sha256"] = host._digest(host._write_bytes(entry))
                final["/private/tmp/shared/" + host.EVIDENCE[1]]["sha256"] = host._digest(
                    host._write_bytes(entry)
                )
                operations["loopback"]["sha256"] = host._digest(
                    ("ack:" + host._digest(host._challenge(entry)) + "\n").encode()
                )
            reports.append(
                {
                    "schema": "opent1d.lt1-c19-operations/1",
                    "kind": "invented",
                    "slot": entry["slot"],
                    "nonce_sha256": entry["nonce_sha256"],
                    "operations": operations,
                    "completed": True,
                    "native_host_qualified": False,
                }
            )
        sent = host._challenge(entries[1])
        reply = ("ack:" + host._digest(sent) + "\n").encode()
        witness = {
            "initial_canaries": initial,
            "final_canaries": final,
            "pair_error": None,
            "listener_closed": True,
            "listener_errors": [],
            "listener_records": [
                {
                    "slot": "allow-twin",
                    "peer_host": "127.0.0.1",
                    "received_b64": base64.b64encode(sent).decode(),
                    "reply_b64": base64.b64encode(reply).decode(),
                    "matched": True,
                }
            ],
        }
        positive = host._operation_assessment(entries, reports, witness)
        self.assertEqual(positive["state"], "demonstrated")
        self.assertFalse(positive["native_host_qualified"])
        for error in ("ENOENT", "ECONNREFUSED", "ETIMEDOUT", "UNKNOWN"):
            altered = copy.deepcopy(reports)
            altered[0]["operations"]["loopback"]["error_code"] = error
            self.assertEqual(
                host._operation_assessment(entries, altered, witness)["state"], "inconclusive"
            )
        for change in (
            lambda w: w.update(listener_closed=False),
            lambda w: w.update(listener_records=[]),
            lambda w: w["initial_canaries"]["/private/tmp/shared/" + host.EVIDENCE[0]].update(
                sha256="f" * 64
            ),
            lambda w: w["final_canaries"]["/private/tmp/shared/" + host.EVIDENCE[1]].update(
                sha256="e" * 64
            ),
            lambda w: w["final_canaries"]["/private/tmp/shared/" + host.EVIDENCE[0]].update(
                sha256="d" * 64
            ),
            lambda w: w["final_canaries"]["/private/tmp/shared/" + host.EVIDENCE[1]][
                "identity"
            ].__setitem__(1, 999),
        ):
            altered = copy.deepcopy(witness)
            change(altered)
            self.assertEqual(
                host._operation_assessment(entries, reports, altered)["state"], "inconclusive"
            )

    def test_typed_operation_errors_are_not_permission_success(self):
        entry = {"kind": "invented", "slot": "base", "nonce_sha256": "a" * 64}
        report = {
            "schema": "opent1d.lt1-c19-operations/1",
            **entry,
            "completed": True,
            "operations": {
                n: {"status": "error", "error_code": "ENOENT", "sha256": None} for n in host.OPS
            },
            "native_host_qualified": False,
        }
        host.validate_probe(report, entry)
        for change in (
            lambda p: p.update(completed=1),
            lambda p: p.update(native_host_qualified=True),
            lambda p: p["operations"]["loopback"].update(error_code=""),
            lambda p: p["operations"].update(extra={}),
            lambda p: p.update(nonce_sha256="b" * 64),
        ):
            altered = copy.deepcopy(report)
            change(altered)
            with self.assertRaises(ValueError):
                host.validate_probe(altered, entry)


@unittest.skipUnless(
    os.name == "posix" and shutil.which("node"), "POSIX ordinary Node fixture required"
)
class HostPairTests(unittest.TestCase):
    def pair(self, parent):
        fixtures = []
        for slot in host.SLOTS:
            directory = parent / slot
            directory.mkdir(mode=0o700)
            shared = (
                None
                if not fixtures
                else {k: fixtures[0]["roots"][k] for k in ("staging", "evidence")}
            )
            fixtures.append(fixture.prepare(directory, case_id="C19", slot=slot, _shared=shared))
        return fixtures

    def test_second_actual_packet_refusal_precedes_first_canary_listener_and_spawn(self):
        with tempfile.TemporaryDirectory() as directory:
            items = self.pair(Path(directory).resolve())
            packet = Path(items[1]["roots"]["packet"])
            packet.chmod(0o700)
            member = packet / "rights_receipt.json"
            member.chmod(0o600)
            member.write_bytes(b"changed actual bytes")
            packet.chmod(0o500)
            with (
                patch.object(
                    host, "_create", side_effect=AssertionError("canary before second packet")
                ),
                patch.object(
                    host.socket,
                    "socket",
                    side_effect=AssertionError("listener before second packet"),
                ),
                patch.object(
                    route.transport,
                    "_supervise",
                    side_effect=AssertionError("spawn before second packet"),
                ),
            ):
                with self.assertRaisesRegex(ValueError, "packet bytes"):
                    cases._run(
                        "C19",
                        [(v["entry_raw"], v["observation_raw"]) for v in items],
                        items[0]["expected_identity"],
                        None,
                        invented=True,
                    )
            for item in items:
                self.assertEqual(list(Path(item["roots"]["output"]).iterdir()), [])
            self.assertEqual(list(Path(items[0]["roots"]["evidence"]).iterdir()), [])

    def test_cross_slot_physical_alias_refuses_before_pair_resources(self):
        with tempfile.TemporaryDirectory() as directory:
            items = self.pair(Path(directory).resolve())
            original = route.legacy._overlap
            left, right = (Path(items[0]["roots"]["output"]), Path(items[1]["roots"]["output"]))

            def physical_alias(a, b):
                return {a, b} == {left, right} or original(a, b)

            with (
                patch.object(route.legacy, "_overlap", side_effect=physical_alias),
                patch.object(
                    host, "_create", side_effect=AssertionError("canary before cross-slot alias")
                ),
                patch.object(
                    host.socket,
                    "socket",
                    side_effect=AssertionError("listener before cross-slot alias"),
                ),
            ):
                with self.assertRaisesRegex(ValueError, "separate roots"):
                    cases._run(
                        "C19",
                        [(v["entry_raw"], v["observation_raw"]) for v in items],
                        items[0]["expected_identity"],
                        None,
                        invented=True,
                    )

    def test_second_physical_context_refusal_precedes_pair_resources(self):
        with tempfile.TemporaryDirectory() as directory:
            items = self.pair(Path(directory).resolve())
            Path(items[1]["roots"]["output"]).chmod(0o500)
            with (
                patch.object(
                    host, "_create", side_effect=AssertionError("canary before second context")
                ),
                patch.object(
                    host.socket,
                    "socket",
                    side_effect=AssertionError("listener before second context"),
                ),
            ):
                with self.assertRaises(ValueError):
                    cases._run(
                        "C19",
                        [(v["entry_raw"], v["observation_raw"]) for v in items],
                        items[0]["expected_identity"],
                        None,
                        invented=True,
                    )

    def test_cancellation_after_preflight_creates_no_canary_or_listener(self):
        with tempfile.TemporaryDirectory() as directory:
            items = self.pair(Path(directory).resolve())
            cancel = threading.Event()
            cancel.set()
            with (
                patch.object(host, "_create", side_effect=AssertionError("cancelled write")),
                patch.object(
                    host.socket, "socket", side_effect=AssertionError("cancelled listener")
                ),
            ):
                result = cases._run(
                    "C19",
                    [(v["entry_raw"], v["observation_raw"]) for v in items],
                    items[0]["expected_identity"],
                    cancel,
                    invented=True,
                )
            self.assertEqual(
                [r["status"] for r in result["records"]], ["not-started-cancelled"] * 2
            )
            self.assertIsNone(result["parent_witness_sha256"])

    def test_seed_storage_failure_retains_both_slots_and_partial_canaries(self):
        with tempfile.TemporaryDirectory() as directory:
            items = self.pair(Path(directory).resolve())
            original_create = host._create
            created = []

            def fail_third_canary(path, raw):
                if len(created) == 2:
                    raise OSError(28, "invented canary ENOSPC")
                original_create(path, raw)
                created.append(path)

            with (
                patch.object(host, "_create", side_effect=fail_third_canary),
                patch.object(host.socket, "socket", side_effect=AssertionError("seed listener")),
                patch.object(
                    route.transport, "_supervise", side_effect=AssertionError("seed spawn")
                ),
            ):
                result = cases._run(
                    "C19",
                    [(v["entry_raw"], v["observation_raw"]) for v in items],
                    items[0]["expected_identity"],
                    None,
                    invented=True,
                )
            self.assertEqual([r["slot"] for r in result["records"]], list(host.SLOTS))
            self.assertTrue(result["all_slots_accounted"])
            self.assertTrue(all(r["status"] == "not-run-pair-unsafe" for r in result["records"]))
            self.assertTrue(all("ENOSPC" in r["error"] for r in result["records"]))
            self.assertEqual(result["comparisons"]["state"], "inconclusive")
            self.assertIsNone(result["parent_witness_sha256"])
            self.assertIn("incomplete canary seeding", result["parent_witness_error"])
            self.assertTrue(result["private_evidence_may_remain"])
            self.assertEqual(set(Path(items[0]["roots"]["output"]).iterdir()), set(created))
            self.assertEqual(list(Path(items[1]["roots"]["output"]).iterdir()), [])
            self.assertEqual(list(Path(items[0]["roots"]["evidence"]).iterdir()), [])

    def test_witness_storage_failure_never_returns_a_pin_for_partial_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            items = self.pair(Path(directory).resolve())
            original_create = host._create

            def fail_witness(path, raw):
                if Path(path).name == host.WITNESS:
                    original_create(path, b"{")
                    raise OSError(28, "invented witness ENOSPC")
                original_create(path, raw)

            with (
                patch.object(host, "_create", side_effect=fail_witness),
                patch.object(
                    host._PairContext, "start_listener", side_effect=OSError("busy control")
                ),
            ):
                result = cases._run(
                    "C19",
                    [(v["entry_raw"], v["observation_raw"]) for v in items],
                    items[0]["expected_identity"],
                    None,
                    invented=True,
                )
            self.assertTrue(result["all_slots_accounted"])
            self.assertTrue(all(r["receipt"] is None for r in result["records"]))
            self.assertEqual(result["comparisons"]["state"], "inconclusive")
            self.assertFalse(result["comparisons"]["checks"]["parent_witness_persisted"])
            self.assertIsNone(result["parent_witness_sha256"])
            self.assertIn("witness ENOSPC", result["parent_witness_error"])
            self.assertTrue(result["private_evidence_may_remain"])
            witness = Path(items[0]["roots"]["evidence"]) / host.WITNESS
            self.assertEqual(witness.read_bytes(), b"{")

    def test_cold_parent_witness_preserves_authority_history_without_restoring_it(self):
        with tempfile.TemporaryDirectory() as directory:
            items = self.pair(Path(directory).resolve())
            attempts = [(v["entry_raw"], v["observation_raw"]) for v in items]
            with patch.object(
                host._PairContext, "start_listener", side_effect=OSError("unavailable control")
            ):
                result = cases._run(
                    "C19", attempts, items[0]["expected_identity"], None, invented=True
                )
            witness_raw = (Path(items[0]["roots"]["evidence"]) / host.WITNESS).read_bytes()
            args = (
                witness_raw,
                result["parent_witness_sha256"],
                attempts,
                [None, None],
                [v["packet"] for v in items],
                [{}, {}],
            )
            source = items[0]["expected_identity"]
            control = host.inspect_pair(*args, expected_identity=source)
            self.assertEqual(control["state"], "inconclusive")
            for authority in route.prior.AUTHORITY_SOURCES:
                with self.subTest(authority=authority):
                    current = copy.deepcopy(source)
                    current["implementation"][authority] = "f" * 64
                    with patch.object(route, "source_identity", return_value=current):
                        self.assertEqual(
                            host.inspect_pair(*args, expected_identity=current), control
                        )
            current = copy.deepcopy(source)
            current["implementation"]["experiments/lt1_diagnostic/native_route_host.py"] = "f" * 64
            with patch.object(route, "source_identity", return_value=current):
                with self.assertRaisesRegex(ValueError, "parent witness origin/source"):
                    host.inspect_pair(*args, expected_identity=current)
            witness = route.decode(witness_raw)
            for change in (
                lambda s: s["implementation"].pop(next(iter(route.prior.AUTHORITY_SOURCES))),
                lambda s: s["implementation"].update(
                    {next(iter(route.prior.AUTHORITY_SOURCES)): "not-a-digest"}
                ),
                lambda s: s.update(extra="unreviewed producer field"),
            ):
                altered = copy.deepcopy(witness)
                change(altered["source_identity"])
                raw = route.encoded(altered)
                with self.assertRaises(ValueError):
                    host.inspect_pair(raw, host._digest(raw), *args[2:], expected_identity=source)

    def test_busy_endpoint_accounts_both_slots_without_a_denial_claim(self):
        with tempfile.TemporaryDirectory() as directory, socket.socket() as foreign:
            foreign.bind(("127.0.0.1", host.PORT))
            foreign.listen(1)
            items = self.pair(Path(directory).resolve())
            result = cases._run(
                "C19",
                [(v["entry_raw"], v["observation_raw"]) for v in items],
                items[0]["expected_identity"],
                None,
                invented=True,
            )
            self.assertTrue(result["all_slots_accounted"])
            self.assertTrue(all(r["receipt"] is None for r in result["records"]))
            self.assertEqual(result["comparisons"]["state"], "inconclusive")
            self.assertFalse(result["comparisons"]["native_host_qualified"])
            self.assertGreater(foreign.fileno(), 0)

    def test_actual_unconfined_pair_preserves_science_and_cold_parent_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            items = self.pair(Path(directory).resolve())
            attempts = [(v["entry_raw"], v["observation_raw"]) for v in items]
            result = cases._run("C19", attempts, items[0]["expected_identity"], None, invented=True)
            self.assertEqual(
                [r["status"] for r in result["records"]], ["completed", "completed"], result
            )
            self.assertEqual(result["comparisons"]["state"], "base-unconfined")
            self.assertFalse(result["comparisons"]["native_host_qualified"])
            packets, outputs, receipts = [], [], []
            for item, record in zip(items, result["records"]):
                receipts.append(route.encoded(record["receipt"]))
                packets.append(item["packet"])
                outputs.append(route.snapshot_output(item["roots"]["output"]))
                self.assertEqual(
                    record["receipt"]["transport"]["outer"]["remaining_owned_processes"], []
                )
                session = record["readback"]["sessions"][0]
                self.assertEqual(session["status"], "completed")
                self.assertEqual(len(session["rows"]), 32)
                self.assertEqual({n for n in outputs[-1] if n.startswith("c19-")}, set(host.OUTPUT))
            evidence = Path(items[0]["roots"]["evidence"])
            witness_raw = (evidence / host.WITNESS).read_bytes()
            args = (attempts, receipts, packets, outputs)
            assessment = host.inspect_pair(
                witness_raw,
                result["parent_witness_sha256"],
                *args,
                expected_identity=items[0]["expected_identity"],
            )
            self.assertEqual(assessment, result["comparisons"])
            original_source = items[0]["expected_identity"]
            for authority in route.prior.AUTHORITY_SOURCES:
                with self.subTest(retained_receipts_after_authority_change=authority):
                    current = copy.deepcopy(original_source)
                    current["implementation"][authority] = "f" * 64
                    with patch.object(route, "source_identity", return_value=current):
                        self.assertEqual(
                            host.inspect_pair(
                                witness_raw,
                                result["parent_witness_sha256"],
                                *args,
                                expected_identity=current,
                            ),
                            assessment,
                        )
            self.assertEqual(route.decode(witness_raw)["source_identity"], original_source)
            self.assertTrue(assessment["checks"]["actual_twin_write"])
            self.assertTrue(assessment["checks"]["same_read_seed"])
            self.assertTrue(assessment["checks"]["owned_listener_cleanup"])
            self.assertFalse(assessment["checks"]["actual_listener_exchange"])
            expected_leaves = {
                *host.EVIDENCE,
                host.WITNESS,
                "c19-base-launch.log",
                "c19-base-live-entry.json",
                "c19-allow-twin-launch.log",
                "c19-allow-twin-live-entry.json",
            }
            self.assertEqual({p.name for p in evidence.iterdir()}, expected_leaves)
            witness = route.decode(witness_raw)
            variants = []
            for change in (
                lambda w: w["initial_canaries"][str(evidence / host.EVIDENCE[0])].update(
                    sha256="f" * 64
                ),
                lambda w: w["entry_sha256"].reverse(),
                lambda w: w.update(native_host_qualified=True),
                lambda w: w.update(base_artifacts={}),
                lambda w: w.update(
                    base_artifacts={
                        "c19-base-launch.log": "garbage",
                        "c19-base-live-entry.json": "garbage",
                    }
                ),
                lambda w: w["final_canaries"][str(evidence / host.EVIDENCE[1])][
                    "identity"
                ].__setitem__(1, 0),
            ):
                altered = copy.deepcopy(witness)
                change(altered)
                variants.append(route.encoded(altered))
            for altered in variants:
                with self.assertRaises(ValueError):
                    host.inspect_pair(
                        altered,
                        route.storage.digest(altered),
                        *args,
                        expected_identity=items[0]["expected_identity"],
                    )
            with self.assertRaisesRegex(ValueError, "pinned parent"):
                host.inspect_pair(
                    witness_raw, "0" * 64, *args, expected_identity=items[0]["expected_identity"]
                )
            missing = copy.deepcopy(witness)
            missing["receipt_sha256"][1] = None
            missing_raw = route.encoded(missing)
            incomplete = host.inspect_pair(
                missing_raw,
                route.storage.digest(missing_raw),
                attempts,
                [receipts[0], None],
                packets,
                outputs,
                expected_identity=items[0]["expected_identity"],
            )
            self.assertEqual(incomplete["state"], "inconclusive")
