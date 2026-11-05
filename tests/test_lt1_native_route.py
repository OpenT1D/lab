"""Actual owned v2 wiring with fixed invented code; no native candidate or setup."""

import base64
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import lt1_native_route_fixture as fixture

from experiments.lt1_diagnostic import native_route as route
from experiments.lt1_diagnostic import native_route_cases as cases
from experiments.lt1_diagnostic import native_route_observer as observer
from experiments.lt1_diagnostic import native_route_reader as reader

NODE = shutil.which("node")


class RouteClosedGateTests(unittest.TestCase):
    def test_all_native_apis_refuse_before_input_source_process_path_or_spawn(self):
        class Bomb:
            def __getattribute__(self, name):
                raise AssertionError("caller input touched")

        with (
            patch.object(
                route, "source_identity", side_effect=AssertionError("source before gate")
            ),
            patch.object(route, "ProcessTable", side_effect=AssertionError("process before gate")),
            patch.object(
                route.transport.socket, "socketpair", side_effect=AssertionError("FD before gate")
            ),
        ):
            for action in (
                lambda: route.launch(Bomb(), Bomb(), expected_identity=Bomb()),
                lambda: cases.run("C15", Bomb(), expected_identity=Bomb()),
                lambda: observer.start(Bomb(), expected_identity=Bomb()),
                lambda: observer.observe(
                    Bomb(), b"unreviewed", Bomb(), Bomb(), expected_identity=Bomb()
                ),
            ):
                with self.subTest(action=action), self.assertRaises(ValueError):
                    action()
        self.assertTrue(
            all(
                v["state"] == "not_run" and v["origin"] == "none"
                for v in cases.planned_native_cases().values()
            )
        )

    def test_exact_bytes_and_staged_authority_context_are_distinct(self):
        class Malicious(bytes):
            def decode(self, *args):
                raise AssertionError("overridden decoder reached")

        with self.assertRaises(ValueError):
            route.decode(Malicious(b"{}"))
        source = route.source_identity()
        newer = copy.deepcopy(source)
        for name in route.prior.AUTHORITY_SOURCES:
            newer["implementation"][name] = "f" * 64
        self.assertEqual(observer._code_context(source), observer._code_context(newer))
        newer["implementation"]["experiments/lt1_diagnostic/native_route.py"] = "e" * 64
        self.assertNotEqual(observer._code_context(source), observer._code_context(newer))
        # A route exception carries no independently observed phase boundary.
        attempts = []
        for slot in cases.SLOTS["C17"]:
            entry = {k: None for k in route.FIELDS.split()}
            entry.update(
                schema="opent1d.lt1-native-route-grant/2",
                kind="invented",
                observation_sha256=route.storage.digest(b"{}"),
                engine_sha256="a" * 64,
                integration_sha256="b" * 64,
                setup_sha256="c" * 64,
                entry_sources=route.prior.grant_sources(source),
                owner_pid=os.getpid(),
                owner_start="fixed owner",
                case_id="C17",
                slot=slot,
            )
            attempts.append((route.encoded(entry), b"{}"))
        with (
            patch.object(cases, "ProcessTable") as table,
            patch.object(route, "_launch", side_effect=OSError("phase not observed")),
        ):
            table.return_value.one.return_value = {"start": "fixed owner"}
            result = cases._run("C17", attempts, source, None, invented=True)
        self.assertTrue(result["all_slots_accounted"])
        self.assertTrue(
            all(
                record["status"] == "route-refused" and record["receipt"] is None
                for record in result["records"]
            )
        )

    @unittest.skipUnless(NODE, "ordinary Node required")
    def test_js_native_entries_gate_before_caller_prototype_and_environment(self):
        code = """
        const root='./experiments/lt1_diagnostic/';
        const {mainNative}=await import(root+'native_route_cli.mjs');
        const {runNative}=await import(root+'native_route_worker.mjs');
        const {collectCurrent}=await import(root+'native_route_observation.mjs');
        const {handoffCurrent}=await import(root+'native_route_handoff.mjs');
        const bomb=new Proxy({}, {
          get(){throw Error('CALLER_INTAKE')},
          getPrototypeOf(){throw Error('CALLER_PROTO')}
        });
        const calls=[()=>mainNative(),()=>runNative(bomb),
          ()=>collectCurrent(bomb,bomb,bomb),
          ()=>handoffCurrent(bomb,bomb,bomb,bomb,bomb,bomb)];
        for(const call of calls){
          try{await call();throw Error('UNEXPECTED_SUCCESS')}
          catch(e){if(!String(e).includes('no reviewed'))throw e;}
        }
        """
        subprocess.run(
            [NODE, "--input-type=module", "-e", code],
            cwd=route.ROOT,
            check=True,
            capture_output=True,
            timeout=10,
        )

    def test_c16_comparison_rejects_empty_failed_and_short_prefixes(self):
        for status, rows in [("failed", []), ("completed", []), ("completed", [{"time_ms": 0}])]:
            records = [
                {
                    "slot": slot,
                    "status": status,
                    "readback": {"status": status, "sessions": [{"status": status, "rows": rows}]},
                }
                for slot in cases.SLOTS["C16"]
            ]
            result = cases.compare_C16(records)
            self.assertFalse(result["exact_direct_wrapped_pairs"])
            self.assertFalse(result["future_meal_prefix_unchanged"])
            self.assertTrue(result["not_demonstrated_slots"])


@unittest.skipUnless(os.name == "posix" and NODE, "POSIX ordinary tooling Node required")
class NativeRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.storage = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.storage.cleanup)
        cls.parent = Path(cls.storage.name).resolve()
        cls.parent.chmod(0o700)
        cls.value = fixture.prepare(cls.parent)
        cls.captured = {}
        cls.receipt = route._launch(
            cls.value["entry_raw"],
            cls.value["observation_raw"],
            cls.value["expected_identity"],
            None,
            invented=True,
            _captured=cls.captured,
        )
        cls.source = route.source_identity()

    def inspect(self, receipt=None, value=None, files=None, identity=None):
        receipt = copy.deepcopy(self.receipt) if receipt is None else receipt
        value = self.value if value is None else value
        raw = route.encoded(receipt)
        return reader.inspect(
            raw,
            route.storage.digest(raw),
            value["entry_raw"],
            value["observation_raw"],
            value["packet"],
            self.captured["output_files"] if files is None else files,
            expected_identity=self.source if identity is None else identity,
        )

    def test_complete_actual_same_pid_exact_science_and_private_carrier(self):
        data = self.inspect()
        self.assertEqual(data["status"], "completed")
        session = data["sessions"][0]
        self.assertEqual(session["native_callbacks"], 32)
        self.assertEqual(session["modeled_delivered_u"], {"numerator": 25, "denominator": 48})
        outer = self.receipt["transport"]["outer"]
        child = json.loads(self.captured["output_files"]["route.json"])
        self.assertEqual(outer["status"], "completed")
        self.assertEqual(outer["remaining_owned_processes"], [])
        self.assertEqual(len(outer["owned_processes"]), 1)
        self.assertEqual(child["pid"], outer["owned_processes"][0]["pid"])
        self.assertNotIn(self.value["entry_raw"].decode(), json.dumps(outer["argv"]))
        self.assertNotIn(self.value["observation_raw"].decode(), json.dumps(outer["argv"]))
        self.assertEqual(
            child["startup_environment_keys"],
            sorted(
                [*json.loads(self.value["observation_raw"])["runtime_environment"], route.CARRIER]
            ),
        )
        self.assertEqual(
            child["post_clear_environment_keys"],
            sorted(json.loads(self.value["observation_raw"])["runtime_environment"]),
        )
        self.assertFalse(child["startup_confinement_qualified"])
        self.assertTrue(all(data[k] is False for k in route.AUTHORITY))

    def test_current_authority_revocation_does_not_block_readonly_historical_bytes(self):
        current = copy.deepcopy(self.source)
        for key in route.prior.AUTHORITY_SOURCES:
            current["implementation"][key] = "f" * 64
        with patch.object(route, "source_identity", return_value=current):
            self.assertEqual(self.inspect(identity=current)["status"], "completed")
        changed = copy.deepcopy(current)
        changed["implementation"]["experiments/lt1_diagnostic/native_route_worker.mjs"] = "e" * 64
        with (
            patch.object(route, "source_identity", return_value=changed),
            self.assertRaises(ValueError),
        ):
            self.inspect(identity=changed)

    def test_reader_owns_inputs_and_rejects_late_mutation_and_mutable_members(self):
        for changed in ("packet", "outputs", "expected"):
            value = copy.deepcopy(self.value)
            outputs = dict(self.captured["output_files"])
            expected = copy.deepcopy(self.source)
            calls = 0

            def source():
                nonlocal calls
                calls += 1
                if calls == 2:
                    if changed == "packet":
                        value["packet"]["grant.json"] = b"{}"
                    elif changed == "outputs":
                        outputs.pop("route.json")
                    else:
                        expected["python"] = "caller changed"
                return self.source

            with (
                self.subTest(changed=changed),
                patch.object(route, "source_identity", side_effect=source),
                self.assertRaisesRegex(ValueError, "caller .* changed"),
            ):
                self.inspect(value=value, files=outputs, identity=expected)
        value = copy.deepcopy(self.value)
        value["packet"]["grant.json"] = bytearray(value["packet"]["grant.json"])
        with (
            patch.object(
                route, "source_identity", side_effect=AssertionError("source before bounds")
            ),
            self.assertRaisesRegex(ValueError, "immutable exact packet"),
        ):
            self.inspect(value=value)
        outputs = dict(self.captured["output_files"])
        outputs["route.json"] = bytearray(outputs["route.json"])
        with self.assertRaisesRegex(ValueError, "immutable bounded output"):
            self.inspect(files=outputs)

    def test_historical_interpreter_shim_fd_and_extra_argument_abi_refuse(self):
        for change in ("interpreter", "shim", "alias", "extra", "rawgrant"):
            receipt = copy.deepcopy(self.receipt)
            argv = receipt["transport"]["outer"]["argv"]
            if change == "interpreter":
                argv[0] = "/bin/sh"
            elif change == "shim":
                argv[4] = "/invented/foreign.py"
            elif change == "alias":
                argv[5] = argv[6]
            elif change == "extra":
                argv.insert(7, "extra")
            else:
                argv.insert(7, self.value["entry_raw"].decode())
            with (
                self.subTest(change=change),
                self.assertRaisesRegex(ValueError, "actual grant-free outer argv"),
            ):
                self.inspect(receipt)

    def test_nonce_and_session_mode_crossbindings_refuse_even_rehashed(self):
        receipt = copy.deepcopy(self.receipt)
        value = copy.deepcopy(self.value)
        entry = json.loads(value["entry_raw"])
        entry["nonce_sha256"] = "b" * 64
        value["entry_raw"] = route.encoded(entry)
        receipt["entry_sha256"] = route.storage.digest(value["entry_raw"])
        with self.assertRaisesRegex(ValueError, "observation/entry"):
            self.inspect(receipt, value)
        receipt = copy.deepcopy(self.receipt)
        files = dict(self.captured["output_files"])
        name = "session-0000/events.jsonl"
        events = [json.loads(line) for line in files[name].splitlines()]
        events[0]["mode"] = "direct"
        files[name] = b"".join(route.encoded(e) + b"\n" for e in events)
        receipt["output_sha256"][name] = route.storage.digest(files[name])
        with self.assertRaisesRegex(ValueError, "journal source/origin"):
            self.inspect(receipt, files=files)

    def test_origin_promotion_cannot_relabel_ordinary_tooling_entry_as_native(self):
        value = copy.deepcopy(self.value)
        receipt = copy.deepcopy(self.receipt)
        entry = json.loads(value["entry_raw"])
        entry["kind"] = "native-unadmitted"
        value["entry_raw"] = route.encoded(entry)
        receipt["kind"] = "native-unadmitted"
        receipt["entry_sha256"] = route.storage.digest(value["entry_raw"])
        with self.assertRaisesRegex(ValueError, "fixed historical Node ABI"):
            self.inspect(receipt, value)

    def test_cold_reader_from_genuinely_separate_trusted_source_copy(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            copyroot = root / "trusted"
            copyroot.mkdir(mode=0o700)
            for name in self.source["implementation"]:
                target = copyroot / name
                target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                target.write_bytes((route.ROOT / name).read_bytes())
                target.chmod(0o600)

            def b64(raw):
                return base64.b64encode(raw).decode()

            raw = route.encoded(self.receipt)
            payload = {
                "receipt": b64(raw),
                "pin": route.storage.digest(raw),
                "entry": b64(self.value["entry_raw"]),
                "observation": b64(self.value["observation_raw"]),
                "packet": {n: b64(v) for n, v in self.value["packet"].items()},
                "outputs": {n: b64(v) for n, v in self.captured["output_files"].items()},
            }
            data = root / "input.json"
            data.write_bytes(route.encoded(payload))
            data.chmod(0o600)
            program = """
import sys,json,base64,builtins
sys.path.insert(0,sys.argv[1])
from experiments.lt1_diagnostic import native_route as r,native_route_reader as reader
raw=json.loads(open(sys.argv[2]).read());decode=base64.b64decode
original=builtins.open
def opened(path,*args,**kwargs):
    if str(path).startswith(sys.argv[3]+'/experiments/'):
        raise AssertionError('historical source intake')
    return original(path,*args,**kwargs)
builtins.open=opened
result=reader.inspect(decode(raw['receipt']),raw['pin'],decode(raw['entry']),decode(raw['observation']),
    {n:decode(v)for n,v in raw['packet'].items()},
    {n:decode(v)for n,v in raw['outputs'].items()},expected_identity=r.source_identity())
assert result['status']=='completed';print('completed')
"""
            result = subprocess.run(
                [
                    sys.executable,
                    "-I",
                    "-S",
                    "-B",
                    "-c",
                    program,
                    str(copyroot),
                    str(data),
                    str(route.ROOT),
                ],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), "completed")

    def test_after_exact_ack_fixed_late_cancellation_never_invokes_worker(self):
        value, receipt, captured = self.invoke("C17", "after-ack-cancel")
        self.assertTrue(receipt["transport"]["exchange"]["ack_sent"])
        child = json.loads(captured["output_files"]["route.json"])
        self.assertEqual(child["exchange_status"], "acknowledged")
        self.assertIsNone(child["worker"])
        self.assertFalse(any(n.endswith("events.jsonl") for n in captured["output_files"]))
        raw = route.encoded(receipt)
        self.assertEqual(
            reader.inspect(
                raw,
                route.storage.digest(raw),
                value["entry_raw"],
                value["observation_raw"],
                value["packet"],
                captured["output_files"],
                expected_identity=self.source,
            )["status"],
            "incomplete",
        )

    def test_actual_inherited_alias_and_regular_channels_refuse_before_worker(self):
        real = route.transport.socket.socketpair
        for kind in ("alias", "regular"):
            first = []

            def pair():
                left, right = real()
                if not first:
                    first.extend((left, right))
                    return left, right
                right.close()
                replacement = (
                    route.transport.socket.socket(fileno=os.dup(first[1].fileno()))
                    if kind == "alias"
                    else tempfile.TemporaryFile()
                )
                return left, replacement

            with patch.object(route.transport.socket, "socketpair", side_effect=pair):
                value, receipt, captured = self.invoke("attempt", "complete")
            self.assertNotEqual(receipt["transport"]["outer"]["exit_code"], 0)
            self.assertEqual(receipt["transport"]["outer"]["remaining_owned_processes"], [])
            self.assertIn(
                "separate inherited sockets",
                (Path(value["roots"]["evidence"]) / "launch.log").read_text(),
            )
            self.assertFalse(any(n.endswith("events.jsonl") for n in captured["output_files"]))

    def test_transport_negative_facts_survive_later_source_restoration(self):
        for field in ("source_stable", "local_exchange_and_process_complete"):
            for false in (False, None, 1):
                receipt = copy.deepcopy(self.receipt)
                receipt["transport"][field] = false
                raw = route.encoded(receipt)
                report = reader.inspect(
                    raw,
                    route.storage.digest(raw),
                    self.value["entry_raw"],
                    self.value["observation_raw"],
                    self.value["packet"],
                    self.captured["output_files"],
                    expected_identity=self.source,
                )
                self.assertEqual(report["status"], "incomplete")

        for sent in ("", base64.b64encode(b"OPENT").decode()):
            receipt = copy.deepcopy(self.receipt)
            receipt["transport"]["exchange"]["ack_sent_raw_b64"] = sent
            with self.assertRaisesRegex(ValueError, "journal without acknowledged"):
                self.inspect(receipt)
        for sent in ("a" * 1369, "!!!!", base64.b64encode(b"a").decode() + "="):
            receipt = copy.deepcopy(self.receipt)
            receipt["transport"]["exchange"]["ack_sent_raw_b64"] = sent
            with self.assertRaises(ValueError):
                self.inspect(receipt)

    def test_complete_footer_never_promotes_failed_or_signalled_outer(self):
        for change in (
            {"status": "failed", "exit_code": -15, "error": "WorkerDeadline"},
            {"received_signals": [15]},
            {"exit_code": False},
        ):
            receipt = copy.deepcopy(self.receipt)
            receipt["transport"]["outer"].update(change)
            self.assertEqual(self.inspect(receipt)["status"], "incomplete")

    def test_recorded_producer_errors_cannot_be_hidden_by_positive_flags(self):
        for field in ("postcheck_error", "output_snapshot_error"):
            receipt = copy.deepcopy(self.receipt)
            receipt[field] = "Recorded producer intake failure"
            self.assertEqual(self.inspect(receipt)["status"], "incomplete")
            for invalid in (False, 1, "", "x" * 16385):
                receipt[field] = invalid
                with self.subTest(field=field, invalid=type(invalid).__name__):
                    with self.assertRaisesRegex(ValueError, "producer error"):
                        self.inspect(receipt)
            del receipt[field]
            with self.assertRaisesRegex(ValueError, "producer error"):
                self.inspect(receipt)

    def test_child_and_worker_context_and_durable_session_reports_must_agree(self):
        changes = [
            (("schema",), "foreign"),
            (("case_id",), "C99"),
            (("slot",), "foreign"),
            (("exchange_status",), "failed"),
            (("worker", "schema"), "foreign"),
            (("worker", "kind"), "native-unadmitted"),
            (("worker", "case_id"), "C99"),
            (("worker", "slot"), "foreign"),
            (("worker", "verification_context_origin"), "current-runtime"),
            (("worker", "completed"), False),
            (("worker", "sessions", 0, "name"), "session-0001"),
            (("worker", "sessions", 0, "status"), "failed"),
            (("worker", "sessions", 0, "rows"), 0),
            (("worker", "sessions", 0, "journal_sha256"), "f" * 64),
        ]
        for path, value in changes:
            receipt = copy.deepcopy(self.receipt)
            files = dict(self.captured["output_files"])
            child = json.loads(files["route.json"])
            target = child
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
            files["route.json"] = route.encoded(child)
            receipt["output_sha256"]["route.json"] = route.storage.digest(files["route.json"])
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.inspect(receipt, files=files)

        # Missing worker evidence remains incomplete; a complete footer is not
        # overwritten to make it match a downgraded failed/signalled outer.
        receipt = copy.deepcopy(self.receipt)
        files = dict(self.captured["output_files"])
        child = json.loads(files["route.json"])
        child["worker"] = None
        files["route.json"] = route.encoded(child)
        receipt["output_sha256"]["route.json"] = route.storage.digest(files["route.json"])
        self.assertEqual(self.inspect(receipt, files=files)["status"], "incomplete")

    def test_carrier_complete_bootstrap_bound_and_exec_budget_precede_resources(self):
        with (
            patch.object(route.os, "sysconf", return_value=16),
            patch.object(
                route.storage,
                "_private_directory",
                side_effect=AssertionError("private intake before exec budget"),
            ),
        ):
            with self.assertRaisesRegex(ValueError, "exec argument/environment budget"):
                route._launch_invented(
                    self.value["entry_raw"],
                    self.value["observation_raw"],
                    expected_identity=self.source,
                )
        base = {
            "schema": "opent1d.lt1-route-carrier/2",
            "entry": self.value["entry_raw"].decode(),
            "observation": self.value["observation_raw"].decode(),
            "audit": self.source,
            "bootstrap": None,
        }
        length = len(route.encoded(base))
        extra = (65490 - length) // 10
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            root.chmod(0o700)
            wanted = len(str(self.parent)) + extra
            parent = root
            while len(str(parent)) + 100 < wanted:
                parent = parent / ("x" * min(100, wanted - len(str(parent)) - 1))
                parent.mkdir(mode=0o700)
            left = wanted - len(str(parent)) - 1
            if left > 0:
                parent = parent / ("y" * left)
                parent.mkdir(mode=0o700)
            value = fixture.prepare(parent)
            raw = route.encoded(
                {
                    "schema": "opent1d.lt1-route-carrier/2",
                    "entry": value["entry_raw"].decode(),
                    "observation": value["observation_raw"].decode(),
                    "audit": value["expected_identity"],
                    "bootstrap": None,
                }
            )
            self.assertLessEqual(len(raw), 65536)
            self.assertGreater(len(raw), 65300)
            with (
                patch.object(
                    route.transport, "_supervise", side_effect=AssertionError("spawn reached")
                ),
                self.assertRaisesRegex(ValueError, "complete bootstrap carrier ceiling"),
            ):
                route._launch_invented(
                    value["entry_raw"],
                    value["observation_raw"],
                    expected_identity=value["expected_identity"],
                )

    def invoke(self, case, slot, *, mode="wrapped", timeout=10, cancel=None, hook=None):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        parent = Path(temporary.name).resolve()
        parent.chmod(0o700)
        value = fixture.prepare(parent, case_id=case, slot=slot, mode=mode, timeout=timeout)
        captured = {}
        if hook:
            original = reader.acknowledge

            def acknowledge(*args, **kwargs):
                result = original(*args, **kwargs)
                hook(value)
                return result

            context = patch.object(reader, "acknowledge", side_effect=acknowledge)
        else:
            from contextlib import nullcontext

            context = nullcontext()
        with context:
            receipt = route._launch(
                value["entry_raw"],
                value["observation_raw"],
                value["expected_identity"],
                cancel,
                invented=True,
                _captured=captured,
            )
        return value, receipt, captured

    def test_c15_same_instance_twice_and_four_fresh_direct_wrapped_invocations(self):
        prepared = []
        for slot in cases.SLOTS["C15"]:
            t = tempfile.TemporaryDirectory()
            self.addCleanup(t.cleanup)
            p = Path(t.name).resolve()
            p.chmod(0o700)
            v = fixture.prepare(p, case_id="C15", slot=slot, mode=slot.split("-")[0])
            prepared.append((v["entry_raw"], v["observation_raw"]))
        result = cases._run("C15", prepared, self.source, None, invented=True)
        self.assertTrue(result["all_slots_accounted"])
        self.assertTrue(all(result["comparisons"].values()))
        for record in result["records"]:
            self.assertEqual(len(record["readback"]["sessions"]), 2)
            child = json.loads(
                route.snapshot_output(record["receipt"]["roots"]["output"])["route.json"]
            )
            self.assertEqual(child["worker"]["construction_count"], 1)
            self.assertEqual(child["worker"]["patient_reset_calls"], 2)
            self.assertEqual(child["worker"]["native_basal"]["calls"], 1)

    def test_c16_all_eight_actual_owned_direct_wrapped_meal_cases(self):
        prepared = []
        for slot in cases.SLOTS["C16"]:
            temporary = tempfile.TemporaryDirectory()
            self.addCleanup(temporary.cleanup)
            parent = Path(temporary.name).resolve()
            parent.chmod(0o700)
            value = fixture.prepare(parent, case_id="C16", slot=slot, mode=slot.split("-")[0])
            prepared.append((value["entry_raw"], value["observation_raw"]))
        result = cases._run("C16", prepared, self.source, None, invented=True)
        self.assertTrue(result["all_slots_accounted"])
        self.assertTrue(result["comparisons"]["exact_direct_wrapped_pairs"])
        self.assertTrue(result["comparisons"]["future_meal_prefix_unchanged"])
        self.assertEqual(result["comparisons"]["not_demonstrated_slots"], [])
        self.assertTrue(all(record["status"] == "completed" for record in result["records"]))

    def test_c18_fixed_case_consumer_cancels_before_init_and_keeps_unrelated_sentinel(self):
        prepared = []
        for slot in cases.SLOTS["C18"]:
            temporary = tempfile.TemporaryDirectory()
            self.addCleanup(temporary.cleanup)
            parent = Path(temporary.name).resolve()
            parent.chmod(0o700)
            value = fixture.prepare(parent, case_id="C18", slot=slot, timeout=6)
            prepared.append((value["entry_raw"], value["observation_raw"]))
        result = cases._run("C18", prepared, self.source, None, invented=True)
        self.assertTrue(result["comparisons"]["owned_cleanup_resolved"])
        self.assertTrue(result["unrelated_sentinel"]["alive_after_cases"])
        self.assertTrue(result["unrelated_sentinel"]["cleanup_confirmed"])
        byslot = {v["slot"]: v for v in result["records"]}
        self.assertEqual(byslot["complete"]["status"], "completed")
        self.assertEqual(
            byslot["before-init-block"]["receipt"]["transport"]["outer"]["error"], "Cancelled"
        )
        self.assertEqual(
            byslot["blocked"]["receipt"]["transport"]["outer"]["error"], "WorkerDeadline"
        )
        self.assertEqual(byslot["blocked"]["readback"]["sessions"][0]["completed_intervals"], 2)

    def test_wrong_ack_nonce_frame_and_eof_never_import_fixed_worker(self):
        original = reader.acknowledge
        for field in ("nonce_sha256", "frame_sha256", "EOF"):
            temporary = tempfile.TemporaryDirectory()
            self.addCleanup(temporary.cleanup)
            parent = Path(temporary.name).resolve()
            parent.chmod(0o700)
            value = fixture.prepare(parent)
            captured = {}

            def wrong_ack(*args, **kwargs):
                ack, child = original(*args, **kwargs)
                if field == "EOF":
                    return b"", child
                parts = ack.split(b"\n")
                decoded = json.loads(parts[1])
                decoded[field] = "0" * 64
                return parts[0] + b"\n" + route.encoded(decoded) + b"\n", child

            with patch.object(reader, "acknowledge", side_effect=wrong_ack):
                receipt = route._launch(
                    value["entry_raw"],
                    value["observation_raw"],
                    value["expected_identity"],
                    None,
                    invented=True,
                    _captured=captured,
                )
            self.assertNotEqual(receipt["transport"]["outer"]["exit_code"], 0)
            self.assertEqual(receipt["transport"]["outer"]["remaining_owned_processes"], [])
            self.assertFalse(any(key.endswith("events.jsonl") for key in captured["output_files"]))

    def test_failure_prefix_primary_export_and_real_initial_state_injection(self):
        for slot in (
            "loader-error",
            "invalid-init",
            "after-two",
            "diagnostic-error",
            "terminal-tail",
        ):
            value, receipt, captured = self.invoke("C17", slot)
            raw = route.encoded(receipt)
            report = reader.inspect(
                raw,
                route.storage.digest(raw),
                value["entry_raw"],
                value["observation_raw"],
                value["packet"],
                captured["output_files"],
                expected_identity=self.source,
            )
            self.assertEqual(report["status"], "incomplete")
            session = report["sessions"][0]
            self.assertEqual(session["status"], "failed")
            if slot == "invalid-init":
                self.assertEqual(session["native_callbacks"], 0)
                self.assertTrue(
                    json.loads(captured["output_files"]["route.json"])["worker"][
                        "nonfinite_initial_state_probe"
                    ]
                )
                self.assertTrue(
                    json.loads(captured["output_files"]["route.json"])["worker"][
                        "initial_state_consumed_observation"
                    ]
                )
            if slot in ("after-two", "diagnostic-error"):
                self.assertEqual(session["completed_intervals"], 2)
            if slot == "diagnostic-error":
                self.assertTrue(session["primary_error"])
                self.assertTrue(session["diagnostic_error"])
            if slot == "terminal-tail":
                self.assertEqual(session["diagnostic_tail_records"], 1)
                self.assertLess(session["observed_duration_ms"], 1800000)

    def test_packet_replacement_after_entry_capture_never_changes_buffer_worker(self):
        def replace(value):
            path = Path(value["roots"]["packet"]) / "plan.json"
            path.chmod(0o600)
            path.write_bytes(b'{"not":"the admitted plan"}')

        value, receipt, captured = self.invoke("attempt", "complete", hook=replace)
        self.assertEqual(receipt["transport"]["outer"]["status"], "completed")
        self.assertFalse(receipt["source_and_packet_stable"])
        worker = json.loads(captured["output_files"]["route.json"])["worker"]
        self.assertTrue(worker["completed"])
        self.assertEqual(
            worker["packet_sha256"]["plan.json"], route.storage.digest(value["packet"]["plan.json"])
        )
        raw = route.encoded(receipt)
        self.assertEqual(
            reader.inspect(
                raw,
                route.storage.digest(raw),
                value["entry_raw"],
                value["observation_raw"],
                value["packet"],
                captured["output_files"],
                expected_identity=self.source,
            )["status"],
            "incomplete",
        )

    def test_cancel_and_deadline_prefix_keep_unrelated_process_and_no_false_completion(self):
        sentinel = subprocess.Popen(
            [sys.executable, "-I", "-S", "-B", "-c", "import time;time.sleep(120)"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            for slot, cancellation in [
                ("before-init-block", True),
                ("blocked", False),
                ("after-finish-block", False),
            ]:
                stopped = threading.Event()
                done = threading.Event()
                temporary = tempfile.TemporaryDirectory()
                self.addCleanup(temporary.cleanup)
                parent = Path(temporary.name).resolve()
                parent.chmod(0o700)
                value = fixture.prepare(parent, case_id="C17", slot=slot, timeout=6)

                def watch():
                    while not done.wait(0.01):
                        if (parent / "output/session-0000/events.jsonl").exists():
                            stopped.set()
                            return

                watcher = threading.Thread(target=watch) if cancellation else None
                if watcher:
                    watcher.start()
                try:
                    receipt = route._launch(
                        value["entry_raw"],
                        value["observation_raw"],
                        value["expected_identity"],
                        stopped,
                        invented=True,
                    )
                finally:
                    done.set()
                    if watcher:
                        watcher.join(timeout=1)
                self.assertEqual(receipt["transport"]["outer"]["remaining_owned_processes"], [])
                self.assertEqual(
                    receipt["transport"]["outer"]["error"],
                    "Cancelled" if cancellation else "WorkerDeadline",
                )
                raw = route.encoded(receipt)
                data = reader.inspect(
                    raw,
                    route.storage.digest(raw),
                    value["entry_raw"],
                    value["observation_raw"],
                    value["packet"],
                    route.snapshot_output(value["roots"]["output"]),
                    expected_identity=self.source,
                )
                self.assertEqual(data["status"], "incomplete")
                self.assertIsNone(sentinel.poll())
                if slot == "blocked":
                    self.assertEqual(data["sessions"][0]["completed_intervals"], 2)
                if slot == "after-finish-block":
                    self.assertTrue(data["sessions"][0]["worker_finish_present"])
        finally:
            sentinel.terminate()
            sentinel.wait(timeout=3)

    def test_c18_self_created_coordinator_loss_keeps_real_outer_missing(self):
        sentinel = subprocess.Popen(
            [sys.executable, "-I", "-S", "-B", "-c", "import time;time.sleep(120)"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            result = observer.invented_coordinator_loss()
            self.assertTrue(result["actual_route_outer_missing"])
            self.assertIsNone(result["actual_route_outer_receipt"])
            self.assertEqual(result["completion"], "incomplete")
            self.assertEqual(result["remaining_owned_processes"], [])
            self.assertGreaterEqual(len(result["before_stop_owned"]), 4)
            self.assertIsNone(sentinel.poll())
        finally:
            sentinel.terminate()
            sentinel.wait(timeout=3)
