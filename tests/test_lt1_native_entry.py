"""Constructible new entry grants and actual FD3/4 continuation, gates closed."""

import base64
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.gui.ownership import ProcessTable
from experiments.lt1_diagnostic import entry_transport as transport
from experiments.lt1_diagnostic import native_entry as entry

ROOT = entry.ROOT
NODE = shutil.which("node")


def material(folder, mode, source, runtime, *, native=False):
    """Sources/argv, then old packet, then observation, then entry: no hash cycle."""
    roots = {key: "/invented/native-entry/" + key for key in entry.base.ROOTS}
    owner = ProcessTable().one(os.getpid())
    policy = entry.profile(roots, source)
    profile_sha = entry.base.preflight.digest(policy.encode())
    encoded, digest = entry.encoded, entry.base.preflight.digest
    argv = [runtime["exec_path"], str(ROOT / entry.FIXTURE), mode, str(folder)]
    if native:
        runtime = {
            **entry.base.preflight.RUNTIME,
            "exec_path": roots["staging"] + "/runtime/bin/node",
        }
        argv = [
            runtime["exec_path"],
            str(ROOT / entry.ENTRY),
            *(roots[k] for k in ("staging", "packet", "output")),
        ]
    packet = {name: encoded({"kind": "invented", "role": name}) for name in entry.PACKET}
    packet["integration_host_receipt.json"] = encoded(
        {
            "schema": "opent1d.lt1-native-entry-host/1",
            "kind": "observed" if native else "invented",
            "purpose": "qualification-only",
            "owner_context": {"observer": {"pid": os.getpid(), "start": owner["start"]}},
            "entry_sources": entry.grant_sources(source),
            "profile_sha256": profile_sha,
        }
    )
    packet["grant.json"] = encoded(
        {
            "schema": "opent1d.lt1-native-grant/1",
            "setup_receipt_sha256": digest(packet["setup_receipt.json"]),
            "staging_root": roots["staging"],
            "node": runtime["node"],
            "platform": runtime["platform"],
            "arch": runtime["arch"],
            "files": {"runtime/bin/node": runtime["executable_sha256"]},
        }
    )
    packet["integration-grant.json"] = encoded(
        {
            "schema": "opent1d.lt1-integration-grant/1",
            "engine_grant_sha256": digest(packet["grant.json"]),
            "host_receipt_sha256": digest(packet["integration_host_receipt.json"]),
            "owner_pid": os.getpid(),
            "attempt": "owned-invented-entry",
            "output_root": roots["output"],
            "reader_identity": {"invented": True},
        }
    )
    observation = {
        "schema": "opent1d.lt1-entry-observation-grant/1",
        "packet_sha256": {name: digest(raw) for name, raw in packet.items()},
        "runtime": {key: runtime[key] for key in ("node", "platform", "arch", "executable_sha256")},
        "entry_executable": runtime["exec_path"],
        "owner_pid": os.getpid(),
        "owner_start": owner["start"],
        "attempt": "owned-invented-entry",
        "nonce_sha256": "c" * 64,
        "profile_sha256": profile_sha,
        "producer_sha256": source["implementation"][
            "experiments/lt1_diagnostic/entry_observation.mjs"
        ],
        "reader_identity": {"invented": True},
        "process_argv": argv,
    }
    observation_raw = encoded(observation)
    grant = {
        "schema": "opent1d.lt1-native-entry-continuation-grant/1",
        "kind": "native-preparation" if native else "invented",
        "observation_sha256": digest(observation_raw),
        "engine_sha256": digest(packet["grant.json"]),
        "integration_sha256": digest(packet["integration-grant.json"]),
        "setup_sha256": digest(packet["setup_receipt.json"]),
        "entry_sources": entry.grant_sources(source),
        "roots": roots,
        "profile_sha256": profile_sha,
        "owner_pid": os.getpid(),
        "owner_start": owner["start"],
        "attempt": observation["attempt"],
        "nonce_sha256": observation["nonce_sha256"],
        "process_argv": argv,
        "new_host_qualification_required": True,
    }
    return encoded(grant), observation_raw, packet


@unittest.skipUnless(os.name == "posix" and NODE, "POSIX ordinary tooling Node required")
class NativeEntryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = entry.source_identity()
        cls.runtime = json.loads(
            subprocess.check_output(
                [
                    NODE,
                    "-p",
                    "JSON.stringify({exec_path:process.execPath,node:process.version,platform:process.platform,arch:process.arch})",
                ],
                text=True,
            )
        )
        cls.runtime["executable_sha256"] = hashlib.sha256(
            Path(cls.runtime["exec_path"]).read_bytes()
        ).hexdigest()

    def payload(self, folder, mode="complete", *, changes=None):
        native = mode in {
            "native-before-fd",
            "early-buffer-mutation",
            "declared-unreviewed",
            "actual-packet-unreviewed",
        }
        raw, observation, packet = material(folder, mode, self.source, self.runtime, native=native)
        if changes:
            value = json.loads(raw)
            value.update(changes)
            raw = entry.encoded(value)
        if native:
            declared = json.loads(raw)
            registry = {
                "execution": [
                    entry.base.preflight.digest(value)
                    for value in (
                        raw,
                        observation,
                        packet["grant.json"],
                        packet["integration-grant.json"],
                    )
                ],
                "setup": [declared["setup_sha256"]],
            }
            prepared = entry._validate(
                raw, observation, packet, self.source, registry, invented=False
            )
        else:
            prepared = entry._prepare_invented(
                raw, observation, packet, expected_identity=self.source
            )
        data = {
            "entry": base64.b64encode(raw).decode(),
            "observation": base64.b64encode(observation).decode(),
            "packet": {name: base64.b64encode(value).decode() for name, value in packet.items()},
            "args": prepared["fixed_args"],
            "expected": prepared["expected_context"],
        }
        (folder / "payload.json").write_bytes(entry.encoded(data))
        (folder / "payload.json").chmod(0o600)
        return data

    def invoke(self, folder, mode="complete", *, verify=None, stopped=None):
        self.payload(folder, mode)

        def acknowledge(raw):
            parts = raw.split(b"\n")
            self.assertEqual((parts[0], parts[-1], len(parts)), (b"OPENT1D-LT1-ENTRY-1", b"", 3))
            frame = json.loads(parts[1])
            self.assertEqual(frame["kind"], "invented")
            self.assertEqual(frame["nonce_sha256"], "c" * 64)
            row = ProcessTable().one(frame["facts"]["pid"])
            self.assertEqual(row["ppid"], os.getpid())
            self.assertEqual(row["pgid"], row["pid"])
            answer = {
                "schema": "opent1d.lt1-entry-ack/1",
                "kind": "invented",
                "frame_sha256": entry.base.preflight.digest(raw),
                "grant_sha256": frame["grant_sha256"],
                "attempt": frame["attempt"],
                "nonce_sha256": frame["nonce_sha256"],
            }
            if mode in {
                "cancel",
                "mutate-args",
                "mutate-buffer",
                "mutate-source-map",
                "switch-signal",
            }:
                time.sleep(0.15)
            if verify:
                return verify(raw, answer)
            return (
                b"OPENT1D-LT1-ACK-1\n" + json.dumps(answer, separators=(",", ":")).encode() + b"\n"
            )

        return transport.supervise_entry(
            [self.runtime["exec_path"], str(ROOT / entry.FIXTURE), mode, str(folder)],
            folder / "process.log",
            expected_identity=transport.source_identity(),
            verify_frame=acknowledge,
            timeout=4,
            handoff_timeout=1,
            grace=0.1,
            cancel=stopped,
        )

    def test_constructible_hash_order_full_source_closure_and_no_path_or_native_intake(self):
        with tempfile.TemporaryDirectory() as temp:
            raw, observation, packet = material(
                Path(temp).resolve(), "complete", self.source, self.runtime
            )
            with (
                patch.object(
                    entry.base.launcher,
                    "launch_native",
                    side_effect=AssertionError("native launch"),
                ),
                patch.object(
                    entry.base.launcher, "_roots", side_effect=AssertionError("private roots")
                ),
            ):
                result = entry._prepare_invented(
                    raw, observation, packet, expected_identity=self.source
                )
            self.assertFalse(result["native_cli_wired"])
            self.assertFalse(result["private_path_intake_performed"])
            self.assertTrue(all(result[k] is False for k in entry.base.AUTHORITY))
            self.assertEqual(
                result["native_cases"],
                {name: "not_run" for name in entry.base.preflight.NATIVE_CASES},
            )
            self.assertTrue(
                entry.base.source_identity()["implementation"].keys()
                <= self.source["implementation"].keys()
            )
            self.assertNotIn(result["entry_sha256"], " ".join(result["process_argv"]))
            self.assertNotIn(result["entry_sha256"].encode(), observation)

    def test_authority_publication_changes_only_external_audit_not_any_grant_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp).resolve()
            first = material(folder, "complete", self.source, self.runtime)
            raw, observation, packet = first
            registry = {
                "schema": "opent1d.lt1-native-admissions/1",
                "setup": [entry.base.preflight.digest(packet["setup_receipt.json"])],
                "execution": [
                    entry.base.preflight.digest(v)
                    for v in (
                        raw,
                        observation,
                        packet["grant.json"],
                        packet["integration-grant.json"],
                    )
                ],
            }
            admitted_source = json.loads(entry.encoded(self.source))
            name = "experiments/lt1_diagnostic/native-admissions.json"
            admitted_source["implementation"][name] = entry.base.preflight.digest(
                entry.encoded(registry)
            )
            self.assertNotEqual(
                admitted_source["implementation"][name], self.source["implementation"][name]
            )
            self.assertEqual(entry.grant_sources(admitted_source), entry.grant_sources(self.source))
            self.assertTrue(entry.AUTHORITY_SOURCES.isdisjoint(json.loads(raw)["entry_sources"]))
            self.assertEqual(material(folder, "complete", admitted_source, self.runtime), first)
            # Model a future published registry without changing any actual authority file.
            with patch.object(entry, "source_identity", return_value=admitted_source):
                result = entry._validate(
                    raw,
                    observation,
                    packet,
                    admitted_source,
                    registry,
                    invented=True,
                    authority_sha=admitted_source["implementation"][name],
                )
            self.assertEqual(result["entry_sha256"], entry.base.preflight.digest(raw))
            self.assertFalse(result["new_native_launcher"])

    def test_canonical_empty_gate_precedes_all_caller_intake_in_both_languages(self):
        class Trap:
            def __getattribute__(self, _name):
                raise AssertionError("caller touched")

        with patch.object(entry, "source_identity", side_effect=AssertionError("source intake")):
            with self.assertRaisesRegex(ValueError, "no reviewed entry continuation grant"):
                entry.prepare(Trap(), Trap(), Trap(), expected_identity=Trap())
        for mode in ("closed-gate", "nonempty-unreviewed", "declared-unreviewed"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temp:
                result = self.invoke(Path(temp).resolve(), mode)
                child = json.loads((Path(temp) / "entry.json").read_bytes())
                self.assertEqual(child["status"], "gate-refused", child)
                self.assertEqual(child["continuation_count"], 0)
                self.assertFalse(result["local_exchange_and_process_complete"])

    def test_nonempty_registry_and_mismatched_declared_grants_precede_packet_and_context(self):
        class Trap:
            def __getattribute__(self, _name):
                raise AssertionError("caller touched")

        with tempfile.TemporaryDirectory() as temp:
            raw, observation, _packet = material(
                Path(temp).resolve(), "complete", self.source, self.runtime
            )
            value = json.loads(raw)
            value["kind"] = "native-preparation"
            raw = entry.encoded(value)
            for registry, message in (
                (
                    {"setup": ["a" * 64], "execution": ["b" * 64]},
                    "exact entry/observation membership",
                ),
                (
                    {
                        "setup": ["a" * 64],
                        "execution": [
                            entry.base.preflight.digest(raw),
                            entry.base.preflight.digest(observation),
                        ],
                    },
                    "exact declared engine/integration/setup membership",
                ),
            ):
                with (
                    self.subTest(message=message),
                    patch.object(entry, "_registry", return_value=registry),
                    patch.object(
                        entry,
                        "source_identity",
                        side_effect=AssertionError("context source intake"),
                    ),
                ):
                    with self.assertRaisesRegex(ValueError, message):
                        entry.prepare(raw, observation, Trap(), expected_identity=Trap())

    def test_native_current_observation_refuses_before_descriptor_or_private_executable_intake(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp).resolve()
            result = self.invoke(folder, "native-before-fd")
            child = json.loads((folder / "entry.json").read_bytes())
            self.assertEqual(child["status"], "gate-refused", child)
            self.assertEqual(child["continuation_count"], 0)
            self.assertFalse(result["local_exchange_and_process_complete"])

    def test_options_getter_cannot_replace_admitted_grant_before_packet_intake(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp).resolve()
            result = self.invoke(folder, "early-buffer-mutation")
            child = json.loads((folder / "entry.json").read_bytes())
            self.assertEqual(child["status"], "gate-refused", child)
            self.assertEqual(child["continuation_count"], 0)
            self.assertFalse(result["local_exchange_and_process_complete"])

    def test_actual_packet_membership_precedes_argument_or_expected_context_getters(self):
        class Trap:
            def __eq__(self, _other):
                raise AssertionError("context touched before actual packet membership")

        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp).resolve()
            raw, observation, packet = material(folder, "complete", self.source, self.runtime)
            declared = json.loads(raw)
            registry = {
                "execution": [
                    entry.base.preflight.digest(v)
                    for v in (
                        raw,
                        observation,
                        packet["grant.json"],
                        packet["integration-grant.json"],
                    )
                ],
                "setup": [declared["setup_sha256"]],
            }
            altered = {**packet, "grant.json": b"unreviewed actual engine"}
            with self.assertRaisesRegex(ValueError, "exact engine/integration/setup memberships"):
                entry._validate(raw, observation, altered, Trap(), registry, invented=True)
            result = self.invoke(folder, "actual-packet-unreviewed")
            child = json.loads((folder / "entry.json").read_bytes())
            self.assertEqual(child["status"], "gate-refused", child)
            self.assertEqual(child["continuation_count"], 0)
            self.assertFalse(result["local_exchange_and_process_complete"])

    def test_consistently_rehashed_missing_transitive_source_is_refused_in_both_languages(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp).resolve()
            data = self.payload(folder)
            raw, observation, packet = (
                base64.b64decode(data["entry"]),
                base64.b64decode(data["observation"]),
                {k: base64.b64decode(v) for k, v in data["packet"].items()},
            )
            grant, observed = json.loads(raw), json.loads(observation)
            missing = "experiments/lt1_diagnostic/attempt_journal.mjs"
            grant["entry_sources"].pop(missing)
            host = json.loads(packet["integration_host_receipt.json"])
            host["entry_sources"].pop(missing)
            packet["integration_host_receipt.json"] = entry.encoded(host)
            integration = json.loads(packet["integration-grant.json"])
            integration["host_receipt_sha256"] = entry.base.preflight.digest(
                packet["integration_host_receipt.json"]
            )
            packet["integration-grant.json"] = entry.encoded(integration)
            observed["packet_sha256"] = {
                k: entry.base.preflight.digest(v) for k, v in packet.items()
            }
            observation = entry.encoded(observed)
            grant["observation_sha256"] = entry.base.preflight.digest(observation)
            grant["integration_sha256"] = entry.base.preflight.digest(
                packet["integration-grant.json"]
            )
            raw = entry.encoded(grant)
            with self.assertRaisesRegex(ValueError, "complete current entry/base code"):
                entry._prepare_invented(raw, observation, packet, expected_identity=self.source)
            data.update(
                entry=base64.b64encode(raw).decode(),
                observation=base64.b64encode(observation).decode(),
                packet={k: base64.b64encode(v).decode() for k, v in packet.items()},
            )
            data["expected"]["source_identity"]["implementation"].pop(missing)
            (folder / "payload.json").write_bytes(entry.encoded(data))
            # The ordinary tooling process must refuse before emitting a frame.
            result = transport.supervise_entry(
                [self.runtime["exec_path"], str(ROOT / entry.FIXTURE), "complete", str(folder)],
                folder / "process.log",
                expected_identity=transport.source_identity(),
                verify_frame=lambda _raw: (_ for _ in ()).throw(
                    AssertionError("frame before complete source closure")
                ),
                timeout=4,
                handoff_timeout=1,
                grace=0.1,
            )
            child = json.loads((folder / "entry.json").read_bytes())
            self.assertEqual(child["continuation_count"], 0)
            self.assertIn("versioned complete source-key manifest", child["reason"])
            self.assertFalse(result["local_exchange_and_process_complete"])

    def test_exact_ack_runs_fixed_benign_continuation_once_in_same_owned_pid(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp).resolve()
            folder.chmod(0o700)
            result = self.invoke(folder)
            self.assertTrue(result["local_exchange_and_process_complete"], result)
            child = json.loads((folder / "entry.json").read_bytes())
            startup = json.loads((folder / "startup.json").read_bytes())
            self.assertEqual(child["continuation_count"], 1)
            self.assertEqual(child["continuation_value"]["call_ordinal"], 1)
            self.assertEqual(child["continuation_value"]["pid"], startup["pid"])
            self.assertEqual(
                child["continuation_value"]["args"],
                ["/invented/native-entry/" + k for k in ("staging", "packet", "output")],
            )
            self.assertEqual(child["continuation_pid"], startup["pid"])
            self.assertEqual(
                [r["pid"] for r in result["outer"]["owned_processes"]], [startup["pid"]]
            )
            self.assertEqual(base64.b64decode(child["ack_raw"]), result["exchange"]["ack_sent_raw"])
            self.assertEqual(result["outer"]["remaining_owned_processes"], [])
            for key in transport.AUTHORITY:
                if key in child:
                    self.assertIs(child[key], False)

    def test_bad_ack_cancel_and_late_input_or_source_mutation_never_continue(self):
        for mode in (
            "bad-ack",
            "cancel",
            "mutate-args",
            "mutate-buffer",
            "mutate-source-map",
            "source-after-ack",
            "switch-signal",
        ):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temp:
                folder = Path(temp).resolve()
                result = self.invoke(
                    folder,
                    mode,
                    verify=(lambda _raw, _ack: b"wrong\n") if mode == "bad-ack" else None,
                )
                child = json.loads((folder / "entry.json").read_bytes())
                self.assertEqual(child["continuation_count"], 0, child)
                self.assertFalse(result["local_exchange_and_process_complete"])
                self.assertEqual(result["outer"]["remaining_owned_processes"], [])

    def test_abort_after_ack_settlement_but_before_continuation_does_not_invoke(self):
        unrelated = subprocess.Popen(
            [sys.executable, "-I", "-S", "-B", "-c", "import time;time.sleep(300)"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            with tempfile.TemporaryDirectory() as temp:
                folder = Path(temp).resolve()
                result = self.invoke(folder, "late-abort")
                child = json.loads((folder / "entry.json").read_bytes())
                self.assertEqual(child["exchange_status"], "acknowledged", child)
                self.assertTrue(child["cancelled_before_continuation"])
                self.assertEqual(child["continuation_count"], 0)
                self.assertEqual(child["status"], "cancelled")
                self.assertEqual(result["outer"]["remaining_owned_processes"], [])
                self.assertIsNone(unrelated.poll())
        finally:
            unrelated.kill()
            unrelated.wait(timeout=2)

    def test_node_source_nonce_owner_and_old_host_namespace_refuse_before_emitting(self):
        for mode in ("source", "nonce", "owner", "old-host"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temp:
                folder = Path(temp).resolve()
                data = self.payload(folder)
                grant = json.loads(base64.b64decode(data["entry"]))
                observation = json.loads(base64.b64decode(data["observation"]))
                packet = {k: base64.b64decode(v) for k, v in data["packet"].items()}
                if mode == "source":
                    grant["entry_sources"]["experiments/lt1_diagnostic/native_entry.mjs"] = "a" * 64
                elif mode == "nonce":
                    grant["nonce_sha256"] = "a" * 64
                elif mode == "owner":
                    grant["owner_pid"] += 1
                else:
                    host = json.loads(packet["integration_host_receipt.json"])
                    host["schema"] = "opent1d.lt1-prestart-host/1"
                    packet["integration_host_receipt.json"] = entry.encoded(host)
                    integration = json.loads(packet["integration-grant.json"])
                    integration["host_receipt_sha256"] = entry.base.preflight.digest(
                        packet["integration_host_receipt.json"]
                    )
                    packet["integration-grant.json"] = entry.encoded(integration)
                    observation["packet_sha256"] = {
                        k: entry.base.preflight.digest(v) for k, v in packet.items()
                    }
                    grant["integration_sha256"] = entry.base.preflight.digest(
                        packet["integration-grant.json"]
                    )
                    observed_raw = entry.encoded(observation)
                    grant["observation_sha256"] = entry.base.preflight.digest(observed_raw)
                    data["observation"] = base64.b64encode(observed_raw).decode()
                    data["packet"] = {k: base64.b64encode(v).decode() for k, v in packet.items()}
                    with self.assertRaisesRegex(ValueError, "new entry host namespace"):
                        entry._prepare_invented(
                            entry.encoded(grant),
                            observed_raw,
                            packet,
                            expected_identity=self.source,
                        )
                data["entry"] = base64.b64encode(entry.encoded(grant)).decode()
                (folder / "payload.json").write_bytes(entry.encoded(data))
                result = transport.supervise_entry(
                    [self.runtime["exec_path"], str(ROOT / entry.FIXTURE), "complete", str(folder)],
                    folder / "process.log",
                    expected_identity=transport.source_identity(),
                    verify_frame=lambda _raw: (_ for _ in ()).throw(
                        AssertionError("refusal must precede frame")
                    ),
                    timeout=4,
                    handoff_timeout=1,
                    grace=0.1,
                )
                child = json.loads((folder / "entry.json").read_bytes())
                self.assertEqual(child["continuation_count"], 0, child)
                self.assertEqual(child["status"], "refused")
                self.assertFalse(result["exchange"]["frame_raw"])
                self.assertEqual(result["outer"]["remaining_owned_processes"], [])

    def test_source_nonce_owner_host_and_exact_memberships_refuse_before_channels(self):
        with tempfile.TemporaryDirectory() as temp:
            raw, observation, packet = material(
                Path(temp).resolve(), "complete", self.source, self.runtime
            )
            for key, value in (
                ("nonce_sha256", "a" * 64),
                ("owner_pid", os.getpid() + 1),
                ("entry_sources", {}),
            ):
                altered = json.loads(raw)
                altered[key] = value
                with self.subTest(key=key), self.assertRaises(ValueError):
                    entry._prepare_invented(
                        entry.encoded(altered), observation, packet, expected_identity=self.source
                    )
            wrong = {
                **packet,
                "integration_host_receipt.json": entry.encoded(
                    {"schema": "opent1d.lt1-prestart-host/1"}
                ),
            }
            with self.assertRaises(ValueError):
                entry._prepare_invented(raw, observation, wrong, expected_identity=self.source)
            with self.assertRaisesRegex(ValueError, "exact entry/observation membership"):
                entry._validate(
                    raw,
                    observation,
                    packet,
                    self.source,
                    {"execution": [], "setup": []},
                    invented=True,
                )

    def test_missing_ack_eof_is_not_success(self):
        held = []
        original = transport.socket.socketpair
        calls = 0

        class HoldEOF:
            def __init__(self, sock):
                self.sock = sock

            def __getattr__(self, name):
                return getattr(self.sock, name)

            def shutdown(self, _how):
                pass

            def close(self):
                held.append(self.sock)

        def pair():
            nonlocal calls
            calls += 1
            left, right = original()
            return (HoldEOF(left), right) if calls == 2 else (left, right)

        try:
            with (
                tempfile.TemporaryDirectory() as temp,
                patch.object(transport.socket, "socketpair", side_effect=pair),
            ):
                folder = Path(temp).resolve()
                result = self.invoke(folder)
                child = json.loads((folder / "entry.json").read_bytes())
                self.assertEqual(child["continuation_count"], 0)
                self.assertEqual(child["exchange_status"], "timeout")
                self.assertFalse(result["local_exchange_and_process_complete"])
        finally:
            for sock in held:
                sock.close()

    def test_actual_descriptor_alias_stdio_and_regular_file_refuse_without_continuation(self):
        for mode in ("descriptor-alias", "stdio-alias", "regular-descriptor"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temp:
                folder = Path(temp).resolve()
                self.payload(folder, mode)
                (folder / "ordinary.txt").write_bytes(b"invented")
                ack_parent, ack_child = socket.socketpair()
                frame_parent, frame_child = socket.socketpair()
                original_spawn = transport.owner.canonical.spawn

                def spawn(argv, **kwargs):
                    kwargs.update(
                        pass_fds=(ack_child.fileno(), frame_child.fileno()),
                        close_fds=True,
                        stdin=subprocess.DEVNULL,
                    )
                    return original_spawn(argv, **kwargs)

                try:
                    result = transport.owner._supervisor_view(spawn)(
                        [
                            sys.executable,
                            "-I",
                            "-S",
                            "-B",
                            str(ROOT / "tests/lt1_native_entry_exec.py"),
                            self.runtime["exec_path"],
                            str(folder),
                            mode,
                            str(ack_child.fileno()),
                            str(frame_child.fileno()),
                        ],
                        folder / "process.log",
                        timeout=4,
                        grace=0.1,
                        environment=transport.owner.ENVIRONMENT,
                    )
                    child = json.loads((folder / "entry.json").read_bytes())
                    startup = json.loads((folder / "startup.json").read_bytes())
                    fds = startup["descriptors"]
                    self.assertTrue(fds["3"]["socket"], startup)
                    if mode == "descriptor-alias":
                        self.assertEqual(fds["3"]["key"], fds["4"]["key"])
                    elif mode == "stdio-alias":
                        self.assertTrue(fds["4"]["socket"])
                        self.assertEqual(fds["3"]["key"], fds["1"]["key"])
                    else:
                        self.assertTrue(fds["4"]["regular"])
                        self.assertFalse(fds["4"]["socket"])
                    self.assertEqual(child["continuation_count"], 0)
                    self.assertIn("separate socket identities", child["reason"])
                    self.assertEqual(result["remaining_owned_processes"], [])
                finally:
                    for sock in (ack_parent, ack_child, frame_parent, frame_child):
                        sock.close()
