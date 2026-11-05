"""Actual fresh original-tree removal; no private data or native qualification."""

import ast
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import lt1_native_tree_fixture as fixture

from experiments.lt1_diagnostic import native_tree_reconciliation as reconciliation
from experiments.lt1_diagnostic import native_tree_removal as tree
from experiments.lt1_diagnostic import native_tree_removal_exec as runner

SUPPORTED = sys.platform == "darwin" or sys.platform.startswith("linux")


class TreeGateTests(unittest.TestCase):
    def test_canonical_gate_precedes_every_caller_getter_path_source_and_process(self):
        class Bomb:
            def __getattribute__(self, name):
                raise AssertionError("caller intake before gate")

        with (
            patch.object(tree, "source_identity", side_effect=AssertionError("source intake")),
            patch.object(tree, "_private_directory", side_effect=AssertionError("path intake")),
            patch.object(runner.owner, "supervise", side_effect=AssertionError("spawn intake")),
            self.assertRaisesRegex(ValueError, "no exact reviewed"),
        ):
            runner.remove(Bomb(), Bomb(), audit=Bomb(), cancel=Bomb(), timeout=Bomb())

    def test_code_projection_excludes_only_three_authority_files(self):
        audit = tree.source_identity()
        changed = copy.deepcopy(audit)
        for name in tree.AUTHORITY_FILES:
            changed["implementation"][name] = "f" * 64
        self.assertEqual(tree.code_source(audit), tree.code_source(changed))
        changed["implementation"]["experiments/lt1_diagnostic/native_tree_removal.py"] = "e" * 64
        self.assertNotEqual(tree.code_source(audit), tree.code_source(changed))
        self.assertEqual(len(tree.AUTHORITY_FILES), 3)
        self.assertFalse(any("native_route" in n for n in audit["implementation"]))
        self.assertLessEqual(
            reconciliation.source_identity()["implementation"].keys(),
            audit["implementation"].keys(),
        )

    def test_changed_recovery_assessor_invalidates_the_original_request_projection(self):
        with tempfile.TemporaryDirectory() as temporary:
            copied = Path(temporary).resolve() / "reader-code"
            sources = (
                tree.source_identity()["implementation"].keys()
                | reconciliation.source_identity()["implementation"].keys()
                | {"tests/lt1_native_tree_fixture.py"}
            )
            for name in sources:
                path = copied / name
                path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(tree.ROOT / name, path)
            script = copied / "exercise.py"
            script.write_text("""import importlib,pathlib,sys
from unittest.mock import patch
sys.path[:0]=[str(pathlib.Path(__file__).parent),str(pathlib.Path(__file__).parent/'tests')]
import lt1_native_tree_fixture as f
from experiments.lt1_diagnostic import native_tree_removal as t,native_tree_reconciliation as r
from experiments.lt1_diagnostic import recovery_evidence
work=t.ROOT/'fresh';work.mkdir(mode=0o700)
v=f.prepare(work,files={'route.json':b'fresh invented data'})
args=f.proposal(v,None)
assert r.propose(**args)['status']=='incomplete'
before=t.source_identity()
p=t.ROOT/'experiments/lt1_diagnostic/recovery_evidence.py'
p.write_text(p.read_text()+
    "\\ndef assess(*args, **kwargs):\\n    return {'changed_assessor': True}\\n")
importlib.reload(recovery_evidence)
assert t.source_identity()!=before, 'executing recovery dependency missing from audit'
with patch.object(t,'_private_directory',side_effect=AssertionError('private intake before gate')):
    try:r.propose(**args)
    except ValueError as error:assert 'context/current code/host identity' in str(error)
    else:raise AssertionError('changed recovery assessor accepted under original request')
assert (v['root']/'route.json').read_bytes()==b'fresh invented data'
""")
            result = subprocess.run(
                [sys.executable, "-B", str(script)],
                cwd=copied,
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


@unittest.skipUnless(SUPPORTED, "descriptor-relative exclusive rename requires macOS/Linux")
class OriginalTreeTests(unittest.TestCase):
    def prepare(self, **kwargs):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        parent = Path(temporary.name).resolve()
        sentinel = parent / "unrelated.txt"
        sentinel.write_bytes(b"unrelated original inode")
        before = sentinel.stat()
        self.addCleanup(
            lambda: self.assertEqual(
                (sentinel.read_bytes(), sentinel.stat().st_ino),
                (b"unrelated original inode", before.st_ino),
            )
        )
        return fixture.prepare(parent, **kwargs)

    def assert_complete(self, value, outer):
        self.assertEqual(outer["receipt"]["status"], "completed")
        self.assertEqual(outer["receipt"]["remaining_owned_processes"], [])
        self.assertFalse(value["root"].exists())
        self.assertFalse(fixture.target(value).exists())
        result = fixture.inspect(value, outer)
        self.assertEqual(result["status"], "completed")
        self.assertTrue(all(result[k] is False for k in tree.AUTHORITY))
        return result

    def prepare_packet(self, **kwargs):
        names = json.loads(tree.NAMESPACE.read_bytes())["roles"]["native-packet"]["files"]
        return self.prepare(
            role="native-packet",
            files={name: ("invented:" + name).encode() for name in names},
            **kwargs,
        )

    def test_original_native_packet_root_is_removed_with_a_recorded_fixed_mode_transition(self):
        names = json.loads(tree.NAMESPACE.read_bytes())["roles"]["native-packet"]["files"]
        entry = ast.parse((tree.ROOT / "experiments/lt1_diagnostic/native_entry.py").read_text())
        packet = next(
            node.value
            for node in entry.body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "PACKET" for target in node.targets
            )
        )
        self.assertEqual(set(names), set(ast.literal_eval(packet)))
        value = self.prepare_packet(hold=True)
        before = value["request"]["root"]
        self.assertEqual(before["mode"], 0o500)
        self.assertTrue(
            all(v["mode"] == 0o400 for v in value["request"]["inventory"]["files"].values())
        )
        outer = fixture.run(value)
        result = self.assert_complete(value, outer)
        events = [json.loads(line) for line in fixture.journal(value).splitlines()]
        self.assertEqual(
            [e["event"] for e in events[:3]], ["prepared", "quarantined", "packet-writable"]
        )
        self.assertEqual(events[2], {"event": "packet-writable"})
        self.assertEqual(result["packet_mode"], {"writable_recorded": True, "observed": None})
        self.assertEqual(result["removed"], sorted(names))
        proposal = reconciliation.propose(**fixture.proposal(value, outer))
        self.assertEqual(proposal["status"], "proposed")
        self.assertEqual(proposal["readback"]["role"], "native-packet")
        self.assertFalse(proposal["effective_erasure_verified"])
        before, after = (
            json.loads(raw)["subjects"]["subject-one"]
            for raw in (value["register_raw"], proposal["register_raw"])
        )
        for key in ("retained_since", "origin_evidence_sha256", "hold"):
            self.assertEqual(after[key], before[key])
        self.assertEqual(after["copies"]["other-copy"], before["copies"]["other-copy"])
        self.assertEqual(after["copies"]["original-copy"]["state"], "absence-observed")
        self.assertTrue(proposal["unregistered_records_block_effective_erasure"])
        self.assertFalse(proposal["new_records_registered"])
        self.assertEqual(fixture.inspect(value, None)["status"], "incomplete")
        for key, changed in (("role", "output"), ("copy", "other-copy")):
            args = fixture.proposal(value, outer)
            allocation = json.loads(args["allocation_raw"])
            allocation[key] = changed
            args["allocation_raw"] = tree.encoded(allocation)
            args["expected_allocation_sha256"] = tree.digest(args["allocation_raw"])
            with self.subTest(allocation_key=key), self.assertRaises(ValueError):
                reconciliation.propose(**args)

    def test_native_packet_requires_exact_members_and_fixed_original_modes_before_launch(self):
        value = self.prepare_packet()
        for change in ("missing", "extra", "directory", "root700", "parent500", "leaf600"):
            r = copy.deepcopy(value["request"])
            if change == "missing":
                r["inventory"]["files"].pop("grant.json")
            elif change == "extra":
                r["inventory"]["files"]["unknown.json"] = r["inventory"]["files"]["grant.json"]
            elif change == "directory":
                r["inventory"]["directories"]["session-0000"] = {
                    k: v for k, v in r["root"].items() if k != "path"
                }
            elif change == "root700":
                r["root"]["mode"] = 0o700
            elif change == "parent500":
                r["parent"]["mode"] = 0o500
            else:
                r["inventory"]["files"]["grant.json"]["mode"] = 0o600
            raw = tree.encoded(r)
            grants = {"schema": "opent1d.lt1-removal-admissions/1", "requests": [tree.digest(raw)]}
            with (
                self.subTest(change=change),
                patch.object(tree, "_private_directory", side_effect=AssertionError("path intake")),
                patch.object(runner.owner, "supervise", side_effect=AssertionError("spawn intake")),
                self.assertRaises(ValueError),
            ):
                runner._run_reviewed(raw, grants, value["context"], value["audit"], invented=True)
        self.assertEqual(fixture.pin(value["root"]), value["request"]["inventory"])
        self.assertEqual(fixture.signature(value["root"])["mode"], 0o500)
        with patch.object(tree.os, "fchmod", side_effect=AssertionError("original path chmod")):
            result = tree._remove_reviewed(
                value["raw"],
                value["grants"],
                value["context"],
                value["audit"],
                invented=True,
                stop=lambda: True,
            )
        self.assertEqual(result["status"], "interrupted")

    def test_native_packet_actual_unknown_entries_and_links_refuse_before_quarantine(self):
        for kind in ("unknown", "symlink", "hardlink", "fifo"):
            with self.subTest(kind=kind):
                value = self.prepare_packet()
                root = value["root"]
                root.chmod(0o700)
                if kind == "unknown":
                    (root / "unknown").write_bytes(b"preserve")
                elif kind == "hardlink":
                    os.link(root / "grant.json", root.parent / "copy")
                else:
                    (root / "grant.json").unlink()
                    if kind == "symlink":
                        (root / "grant.json").symlink_to(root.parent / "unrelated.txt")
                    else:
                        os.mkfifo(root / "grant.json", 0o400)
                root.chmod(0o500)
                value["request"]["root"] = {"path": str(root), **fixture.signature(root)}
                value["raw"] = tree.encoded(value["request"])
                value["grants"]["requests"] = [tree.digest(value["raw"])]
                outer = fixture.run(value)
                self.assertEqual(outer["receipt"]["status"], "failed")
                self.assertEqual(fixture.signature(root)["mode"], 0o500)
                self.assertFalse((value["cleanup"] / value["request"]["attempt"]).exists())

    def test_native_packet_chmod_and_sync_failures_preserve_truthful_mode_prefixes(self):
        for failure, mode in (("chmod", 0o500), ("sync", 0o700)):
            with self.subTest(failure=failure):
                value = self.prepare_packet()
                original_chmod, original_sync = os.fchmod, os.fsync
                root_identity = tuple(value["request"]["root"][k] for k in ("device", "inode"))
                calls = []

                def chmod(fd, requested):
                    info = os.fstat(fd)
                    self.assertEqual((info.st_dev, info.st_ino), root_identity)
                    target = fixture.target(value)
                    self.assertFalse(value["root"].exists())
                    self.assertEqual(fixture.signature(target)["mode"], 0o500)
                    self.assertEqual(requested, 0o700)
                    calls.append(requested)
                    if failure == "chmod":
                        raise OSError("invented fchmod failure")
                    return original_chmod(fd, requested)

                def sync(fd):
                    info = os.fstat(fd)
                    if (info.st_dev, info.st_ino) == root_identity:
                        raise OSError("invented root fsync failure")
                    return original_sync(fd)

                with (
                    patch.object(tree.os, "fchmod", side_effect=chmod),
                    patch.object(tree.os, "fsync", side_effect=sync),
                ):
                    result = tree._remove_reviewed(
                        value["raw"],
                        value["grants"],
                        value["context"],
                        value["audit"],
                        invented=True,
                    )
                self.assertEqual(result["status"], "failed")
                self.assertEqual(calls, [0o700])
                readback = fixture.inspect(value, None)
                self.assertEqual(readback["status"], "incomplete")
                self.assertEqual(
                    readback["packet_mode"], {"writable_recorded": False, "observed": mode}
                )
                self.assertEqual(
                    "packet-mode" in readback["unrecorded_mutations"], failure == "sync"
                )
                target = fixture.target(value)
                self.assertEqual(fixture.pin(target), value["request"]["inventory"])
                self.assertNotIn(b'"event":"packet-writable"', fixture.journal(value))

    def test_native_packet_actual_crash_prefixes_preserve_mode_and_unrecorded_mutations(self):
        for phase, mode, recorded, gap in (
            ("after-rename-before-journal", 0o500, False, "root-rename"),
            ("after-packet-chmod-before-journal", 0o700, False, "packet-mode"),
            ("packet-writable", 0o700, True, None),
            ("after-unlink-before-journal:grant.json", 0o700, True, "grant.json"),
            ("after-root-rmdir-before-journal", None, True, "root-rmdir"),
        ):
            with self.subTest(phase=phase):
                value = self.prepare_packet(
                    context={"kind": "invented", "fixture_phase": phase, "fixture_crash": True}
                )
                outer = fixture.run(value)
                self.assertEqual(outer["receipt"]["exit_code"], 61)
                self.assertEqual(outer["receipt"]["remaining_owned_processes"], [])
                result = fixture.inspect(value, outer)
                self.assertEqual(result["status"], "incomplete")
                self.assertEqual(
                    result["packet_mode"], {"writable_recorded": recorded, "observed": mode}
                )
                if gap:
                    self.assertIn(gap, result["unrecorded_mutations"])
                journal = fixture.journal(value)
                self.assertEqual(b'"event":"packet-writable"' in journal, recorded)
                args = fixture.proposal(value, outer)
                proposal = reconciliation.propose(**args)
                self.assertEqual(proposal["register_raw"], value["register_raw"])
                self.assertEqual(proposal["provenance_raw"], args["provenance_raw"])
                if mode is not None:
                    target = fixture.target(value)
                    actual = fixture.signature(target)
                    for key in ("device", "inode", "uid"):
                        self.assertEqual(actual[key], value["request"]["root"][key])
                    self.assertEqual(actual["mode"], mode)
                    if phase == "after-packet-chmod-before-journal":
                        self.assertEqual(fixture.pin(target), value["request"]["inventory"])

    def test_native_packet_cancel_and_deadline_preserve_actual_fixed_mode_prefix(self):
        for phase in (None, "quarantined", "packet-writable"):
            with self.subTest(phase=phase):
                value = self.prepare_packet(
                    context={
                        "kind": "invented",
                        "fixture_phase": phase,
                        "fixture_pause": 4,
                    }
                )
                cancel = threading.Event()
                if phase is None:
                    cancel.set()
                else:
                    wanted = tree.encoded({"event": phase})

                    def trigger():
                        end = time.monotonic() + 20
                        while time.monotonic() < end:
                            if wanted in fixture.journal(value):
                                cancel.set()
                                return
                            time.sleep(0.01)

                    thread = threading.Thread(target=trigger)
                    thread.start()
                outer = fixture.run(value, cancel=cancel)
                if phase is not None:
                    thread.join(20)
                    self.assertFalse(thread.is_alive())
                    self.assertTrue(cancel.is_set())
                self.assertEqual(outer["receipt"]["status"], "interrupted")
                self.assertEqual(outer["receipt"]["remaining_owned_processes"], [])
                result = fixture.inspect(value, outer)
                self.assertEqual(result["status"], "incomplete")
                self.assertEqual(
                    result["packet_mode"],
                    {
                        "writable_recorded": phase == "packet-writable",
                        "observed": 0o700 if phase == "packet-writable" else 0o500,
                    },
                )
                root = value["root"] if phase is None else fixture.target(value)
                self.assertEqual(fixture.pin(root), value["request"]["inventory"])
        value = self.prepare_packet(
            context={
                "kind": "invented",
                "fixture_phase": "packet-writable",
                "fixture_pause": 4,
            }
        )
        outer = fixture.run(value, timeout=1.5)
        self.assertEqual(outer["receipt"]["status"], "failed")
        self.assertEqual(outer["receipt"]["error"], "WorkerDeadline")
        self.assertEqual(outer["receipt"]["remaining_owned_processes"], [])
        result = fixture.inspect(value, outer)
        self.assertEqual(result["status"], "incomplete")
        roots = [p for p in (value["root"], fixture.target(value)) if p.exists()]
        self.assertEqual(len(roots), 1)
        self.assertEqual(fixture.pin(roots[0]), value["request"]["inventory"])
        self.assertIn(result["packet_mode"]["observed"], (0o500, 0o700))
        self.assertEqual(result["removed"], [])

    def test_native_packet_reader_refuses_mode_event_contradictions_even_when_rehashed(self):
        value = self.prepare_packet()
        outer = fixture.run(value)
        self.assert_complete(value, outer)
        path = value["cleanup"] / value["request"]["attempt"] / "events.jsonl"
        events = [json.loads(line) for line in path.read_bytes().splitlines()]
        for change in ("duplicate", "missing", "early", "late", "selector"):
            changed = copy.deepcopy(events)
            if change == "duplicate":
                changed.insert(3, {"event": "packet-writable"})
            elif change == "missing":
                changed.pop(2)
            elif change == "early":
                changed.insert(1, changed.pop(2))
            elif change == "late":
                changed.insert(3, changed.pop(2))
            else:
                changed[2]["mode"] = 0o777
            path.write_bytes(b"".join(tree.encoded(e) + b"\n" for e in changed))
            with self.subTest(change=change), self.assertRaises(ValueError):
                fixture.inspect(value, outer)
        value = self.prepare_packet(
            context={
                "kind": "invented",
                "fixture_phase": "packet-writable",
                "fixture_crash": True,
            }
        )
        outer = fixture.run(value)
        target = fixture.target(value)
        for mode in (0o500, 0o600, 0o750):
            target.chmod(mode)
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                fixture.inspect(value, outer)
        target.chmod(0o700)
        self.assertEqual(fixture.inspect(value, outer)["status"], "incomplete")
        value = self.prepare_packet()
        value["root"].chmod(0o700)
        with self.assertRaises(ValueError):
            fixture.inspect(value, None)
        value = self.prepare(files={"route.json": b"unchanged output behavior"})
        outer = fixture.run(value)
        path = value["cleanup"] / value["request"]["attempt"] / "events.jsonl"
        events = [json.loads(line) for line in path.read_bytes().splitlines()]
        events.insert(2, {"event": "packet-writable"})
        path.write_bytes(b"".join(tree.encoded(e) + b"\n" for e in events))
        with self.assertRaisesRegex(ValueError, "packet mode event order"):
            fixture.inspect(value, outer)

    def test_native_packet_sibling_quarantine_collision_and_name_changes_preserve_objects(self):
        value = self.prepare_packet()
        target = fixture.target(value)
        self.assertEqual(target.parent, value["root"].parent)
        self.assertEqual(target.name, "lt1-packet-" + tree.digest(value["raw"]))
        target.mkdir(mode=0o700)
        (target / "unrelated").write_bytes(b"preserve collision")
        identity = fixture.signature(target)
        outer = fixture.run(value)
        self.assertEqual(outer["receipt"]["status"], "failed")
        self.assertEqual(fixture.signature(target), identity)
        self.assertEqual((target / "unrelated").read_bytes(), b"preserve collision")
        self.assertEqual(fixture.signature(value["root"])["mode"], 0o500)
        self.assertFalse((value["cleanup"] / value["request"]["attempt"]).exists())
        with self.assertRaisesRegex(ValueError, "unstarted packet quarantine appeared"):
            fixture.inspect(value, outer)
        for change in ("exclusive-collision", "replaced-quarantine"):
            with self.subTest(change=change):
                value = self.prepare_packet()
                target = fixture.target(value)
                displaced = target.parent / "displaced-packet"
                original_rename = tree._rename

                def rename(*args):
                    target.mkdir(mode=0o500)
                    return original_rename(*args)

                def checkpoint(phase):
                    if change == "replaced-quarantine" and phase == "quarantined":
                        target.rename(displaced)
                        target.mkdir(mode=0o500)

                with patch.object(
                    tree,
                    "_rename",
                    side_effect=rename if change == "exclusive-collision" else original_rename,
                ):
                    result = tree._remove_reviewed(
                        value["raw"],
                        value["grants"],
                        value["context"],
                        value["audit"],
                        invented=True,
                        checkpoint=checkpoint,
                    )
                self.assertEqual(result["status"], "failed")
                preserved = value["root"] if change == "exclusive-collision" else displaced
                self.assertEqual(fixture.pin(preserved), value["request"]["inventory"])
                self.assertEqual(fixture.signature(preserved)["mode"], 0o500)
                self.assertEqual(list(target.iterdir()), [])
                self.assertNotIn(b'"event":"packet-writable"', fixture.journal(value))
                with self.assertRaises(ValueError):
                    fixture.inspect(value, None)

    def test_native_packet_reader_binds_both_sibling_names_and_rejects_wrong_parent_target(self):
        for change in (
            "original-replaced",
            "original-missing",
            "original-mode",
            "quarantine-appeared",
            "attempt-appeared",
            "cleanup-parent-replaced",
        ):
            with self.subTest(unstarted_change=change):
                value = self.prepare_packet()
                source_identity = tree.source_identity
                calls = 0

                def source():
                    nonlocal calls
                    calls += 1
                    if calls == 2:
                        if change in ("original-replaced", "original-missing"):
                            value["root"].rename(value["root"].parent / "displaced-original")
                            if change == "original-replaced":
                                value["root"].mkdir(mode=0o500)
                        elif change == "original-mode":
                            value["root"].chmod(0o700)
                        elif change == "quarantine-appeared":
                            fixture.target(value).mkdir(mode=0o500)
                        elif change == "attempt-appeared":
                            (value["cleanup"] / value["request"]["attempt"]).mkdir(mode=0o700)
                        else:
                            value["cleanup"].rename(value["cleanup"].parent / "displaced-cleanup")
                            value["cleanup"].mkdir(mode=0o700)
                    return source_identity()

                with patch.object(tree, "source_identity", side_effect=source):
                    with self.assertRaises((OSError, ValueError)):
                        fixture.inspect(value, None)
                self.assertEqual(calls, 2)
        for returned in ("original", "quarantine"):
            with self.subTest(returned=returned):
                value = self.prepare_packet()
                outer = fixture.run(value)
                self.assert_complete(value, outer)
                source_identity = tree.source_identity
                calls = 0

                def source():
                    nonlocal calls
                    calls += 1
                    if calls == 2:
                        (value["root"] if returned == "original" else fixture.target(value)).mkdir(
                            mode=0o500
                        )
                    return source_identity()

                with patch.object(tree, "source_identity", side_effect=source):
                    with self.assertRaisesRegex(ValueError, "late target namespace changed"):
                        fixture.inspect(value, outer)
                self.assertEqual(calls, 2)
        value = self.prepare_packet()
        outer = fixture.run(value)
        self.assert_complete(value, outer)
        wrong = value["cleanup"] / value["request"]["attempt"] / "target"
        wrong.mkdir(mode=0o700)
        (wrong / "unregistered").write_bytes(b"preserve wrong-parent record")
        with self.assertRaisesRegex(ValueError, "reader attempt namespace"):
            fixture.inspect(value, outer)
        self.assertEqual((wrong / "unregistered").read_bytes(), b"preserve wrong-parent record")

    def test_original_empty_partial_malformed_and_empty_session_trees(self):
        for files in (
            {},
            {"route.json": b"{malformed\x00"},
            {"session-0000/events.jsonl": b"{partial"},
        ):
            with self.subTest(files=list(files)):
                value = self.prepare(files=files)
                if not files:
                    (value["root"] / "session-0001").mkdir(mode=0o700)
                    # Re-pin only this fresh generated inventory before admission.
                    value = fixture.prepare(
                        value["root"].parent, root=value["root"], cleanup=value["cleanup"]
                    )
                self.assert_complete(value, fixture.run(value))

    def test_c19_two_outputs_and_one_shared_evidence_are_three_original_targets(self):
        parent = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, parent)
        namespace = json.loads(tree.NAMESPACE.read_bytes())["roles"]
        roots, values = [], []
        for index, role in enumerate(("output", "output", "evidence")):
            files = {name: (role + ":" + name).encode() for name in namespace[role]["files"]}
            if role == "output":
                files.update(
                    {"session-0000/events.jsonl": b"first", "session-0001/events.jsonl": b"second"}
                )
            value = fixture.prepare(
                parent,
                role=role,
                root=parent / ("original-" + str(index)),
                cleanup=parent / "cleanup",
                attempt="remove-" + str(index),
                copy_id="c19-copy-" + str(index),
                files=files,
            )
            roots.append((value["request"]["root"]["device"], value["request"]["root"]["inode"]))
            values.append(value)
        self.assertEqual(len(set(roots)), 3)
        self.assertEqual(len({v["request"]["copy"] for v in values}), 3)
        for value in values:
            self.assert_complete(value, fixture.run(value))
        self.assertEqual(len(list((parent / "cleanup").glob("remove-*"))), 9)

    @unittest.skipUnless(
        shutil.which("node"), "ordinary tooling Node required for original C15 output"
    )
    def test_original_actual_c15_two_session_output_and_evidence(self):
        import lt1_native_route_fixture as native_fixture

        from experiments.lt1_diagnostic import native_route, native_route_reader

        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        parent = Path(temporary.name).resolve()
        native = native_fixture.prepare(parent, case_id="C15", slot="direct-reset", mode="direct")
        captured = {}
        outer = native_route._launch(
            native["entry_raw"],
            native["observation_raw"],
            native["expected_identity"],
            None,
            invented=True,
            _captured=captured,
        )
        raw = native_route.encoded(outer)
        observed = native_route_reader.inspect(
            raw,
            native_route.storage.digest(raw),
            native["entry_raw"],
            native["observation_raw"],
            native["packet"],
            captured["output_files"],
            expected_identity=native["expected_identity"],
        )
        self.assertEqual(observed["status"], "completed")
        self.assertEqual(len(observed["sessions"]), 2)
        for index, role in enumerate(("output", "evidence")):
            value = fixture.prepare(
                parent,
                role=role,
                root=Path(native["roots"][role]),
                cleanup=parent / "cleanup",
                attempt="c15-clean-" + str(index),
                producer=native["expected_identity"],
            )
            self.assertEqual(value["request"]["producer"], native["expected_identity"])
            self.assert_complete(value, fixture.run(value))
        self.assertTrue(Path(native["roots"]["staging"]).is_dir())
        self.assertTrue(Path(native["roots"]["packet"]).is_dir())

    def test_real_cancellation_before_launch_and_at_three_mutation_phases(self):
        for phase in (None, "prepared", "quarantined", "removed:route.json"):
            with self.subTest(phase=phase):
                value = self.prepare(
                    files={"route.json": b"first", "session-0000/events.jsonl": b"second"},
                    context={"kind": "invented", "fixture_phase": phase, "fixture_pause": 3},
                )
                cancel = threading.Event()
                if phase is None:
                    cancel.set()
                else:
                    wanted = {
                        "prepared": b'"event":"prepared"',
                        "quarantined": b'"event":"quarantined"',
                        "removed:route.json": b'"event":"removed","name":"route.json"',
                    }[phase]

                    def trigger():
                        end = time.monotonic() + 10
                        while time.monotonic() < end:
                            if wanted in fixture.journal(value):
                                cancel.set()
                                return
                            time.sleep(0.01)

                    thread = threading.Thread(target=trigger)
                    thread.start()
                outer = fixture.run(value, cancel=cancel)
                if phase is not None:
                    thread.join(10)
                    self.assertFalse(thread.is_alive())
                self.assertEqual(outer["receipt"]["status"], "interrupted")
                self.assertEqual(outer["receipt"]["remaining_owned_processes"], [])
                self.assertEqual(fixture.inspect(value, outer)["status"], "incomplete")
                args = fixture.proposal(value, outer)
                result = reconciliation.propose(**args)
                self.assertEqual(result["register_raw"], value["register_raw"])
                self.assertEqual(result["provenance_raw"], args["provenance_raw"])

    def test_actual_worker_deadline_preserves_the_observed_incomplete_prefix(self):
        for phase in ("prepared", "quarantined"):
            with self.subTest(pause_at=phase):
                value = self.prepare(
                    files={"route.json": b"keep"},
                    context={"kind": "invented", "fixture_phase": phase, "fixture_pause": 4},
                )
                outer = fixture.run(value, timeout=1.5)
                self.assertEqual(outer["receipt"]["status"], "failed")
                self.assertEqual(outer["receipt"]["error"], "WorkerDeadline")
                self.assertEqual(outer["receipt"]["remaining_owned_processes"], [])
                result = fixture.inspect(value, outer)
                self.assertEqual(result["status"], "incomplete")
                self.assertFalse(result["outer_complete"])
                original = value["root"]
                quarantine = value["cleanup"] / value["request"]["attempt"] / "target"
                # The real owner deadline includes import/source verification.
                # A slower host can stop before the requested pause checkpoint.
                present = [path for path in (original, quarantine) if path.exists()]
                self.assertEqual(len(present), 1)
                self.assertEqual(result["original_present"], original.exists())
                self.assertEqual(result["quarantine_present"], quarantine.exists())
                root = present[0]
                actual_root = fixture.signature(root)
                for key in tree.STABLE_DIR:
                    self.assertEqual(actual_root[key], value["request"]["root"][key])
                leaf = root / "route.json"
                actual_leaf = {
                    **tree.removal.signature(leaf.stat(follow_symlinks=False)),
                    "sha256": tree.digest(leaf.read_bytes()),
                }
                self.assertEqual(actual_leaf, value["request"]["inventory"]["files"]["route.json"])
                self.assertEqual(leaf.stat(follow_symlinks=False).st_nlink, 1)
                self.assertEqual(leaf.read_bytes(), b"keep")
                self.assertEqual(result["removed"], [])
                self.assertEqual(result["directories_removed"], [])
                events = [
                    json.loads(line)
                    for line in fixture.journal(value).splitlines(keepends=True)
                    if line.endswith(b"\n")
                ]
                self.assertFalse(
                    any(
                        event["event"] in {"removed", "directory-removed", "root-removed"}
                        for event in events
                    )
                )

    def test_unstarted_missing_empty_and_partial_header_prefixes_remain_incomplete(self):
        for journal_raw in (None, b"", b'{"event":"prepared"'):
            with self.subTest(journal=journal_raw):
                value = self.prepare(files={"route.json": b"preserve"})
                attempt = value["cleanup"] / value["request"]["attempt"]
                attempt.mkdir(mode=0o700)
                if journal_raw is not None:
                    path = attempt / "events.jsonl"
                    path.write_bytes(journal_raw)
                    path.chmod(0o600)
                result = fixture.inspect(value, None)
                self.assertEqual(result["status"], "incomplete")
                self.assertFalse(result["prepared"])
                self.assertTrue(value["root"].is_dir())

    def test_whole_carrier_limit_refuses_before_private_directory_or_spawn(self):
        value = self.prepare()
        context = b"x" * tree.LIMIT
        r = copy.deepcopy(value["request"])
        r["context_sha256"] = tree.digest(context)
        producers = r["producer"]["implementation"]
        previous = None
        for index in range(4096):
            name = "tests/" + str(index) + "-" + "x" * 400 + ".py"
            producers[name] = "b" * 64
            raw = tree.encoded(r)
            if len(raw) > tree.LIMIT:
                del producers[name]
                raw = previous
                break
            previous = raw
        self.assertIsNotNone(raw)
        self.assertLessEqual(len(raw), tree.LIMIT)
        grants = {"schema": "opent1d.lt1-removal-admissions/1", "requests": [tree.digest(raw)]}
        with (
            patch.object(
                tree, "_private_directory", side_effect=AssertionError("private path intake")
            ),
            patch.object(runner.owner, "supervise", side_effect=AssertionError("spawn intake")),
            self.assertRaisesRegex(ValueError, "whole carrier"),
        ):
            runner._run_reviewed(raw, grants, context, value["audit"], invented=True)

    def test_actual_crash_gaps_after_rename_unlink_session_and_root_rmdir(self):
        phases = (
            "after-rename-before-journal",
            "after-unlink-before-journal:route.json",
            "after-rmdir-before-journal:session-0000",
            "after-root-rmdir-before-journal",
        )
        for phase in phases:
            with self.subTest(phase=phase):
                value = self.prepare(
                    files={"route.json": b"one", "session-0000/events.jsonl": b"two"},
                    context={"kind": "invented", "fixture_phase": phase, "fixture_crash": True},
                )
                outer = fixture.run(value)
                self.assertEqual(outer["receipt"]["exit_code"], 61)
                self.assertEqual(outer["receipt"]["remaining_owned_processes"], [])
                result = fixture.inspect(value, outer)
                self.assertEqual(result["status"], "incomplete")
                self.assertTrue(result["unrecorded_mutations"])

    def test_unknown_symlink_hardlink_and_special_entries_refuse_before_quarantine(self):
        for kind in ("unknown", "symlink", "hardlink", "fifo"):
            with self.subTest(kind=kind):
                value = self.prepare(files={"route.json": b"original"})
                root = value["root"]
                if kind == "unknown":
                    (root / "unexpected").write_bytes(b"preserve")
                elif kind == "symlink":
                    (root / "route.json").unlink()
                    (root / "route.json").symlink_to(root.parent / "unrelated.txt")
                elif kind == "hardlink":
                    os.link(root / "route.json", root.parent / "hardlink")
                else:
                    (root / "route.json").unlink()
                    os.mkfifo(root / "route.json", 0o600)
                value["request"]["root"] = {"path": str(root), **fixture.signature(root)}
                value["raw"] = tree.encoded(value["request"])
                value["grants"]["requests"] = [tree.digest(value["raw"])]
                outer = fixture.run(value)
                self.assertEqual(outer["receipt"]["status"], "failed")
                self.assertTrue(root.is_dir())
                self.assertFalse((value["cleanup"] / value["request"]["attempt"]).exists())

    def test_changed_inventory_and_source_refuse_before_owned_launch(self):
        value = self.prepare(files={"route.json": b"original"})
        for change in ("source", "unknown-role", "unknown-depth", "aggregate", "same-cleanup"):
            r = copy.deepcopy(value["request"])
            if change == "source":
                r["code_source"]["implementation"][
                    "experiments/lt1_diagnostic/native_tree_removal.py"
                ] = "e" * 64
            elif change == "unknown-role":
                r["role"] = "arbitrary-folder"
            elif change == "unknown-depth":
                r["inventory"]["files"]["session-0000/sub/events.jsonl"] = r["inventory"][
                    "files"
                ].pop("route.json")
            elif change == "aggregate":
                r["inventory"]["files"]["route.json"]["bytes"] = tree.removal.FILE_LIMIT + 1
            else:
                r["cleanup_parent"] = r["root"]
            raw = tree.encoded(r)
            grants = {"schema": "opent1d.lt1-removal-admissions/1", "requests": [tree.digest(raw)]}
            with (
                self.subTest(change=change),
                patch.object(
                    runner.owner, "supervise", side_effect=AssertionError("spawn reached")
                ),
                self.assertRaises(ValueError),
            ):
                runner._run_reviewed(raw, grants, value["context"], value["audit"], invented=True)
        self.assertEqual((value["root"] / "route.json").read_bytes(), b"original")

    def test_actual_late_namespace_change_preserves_unknown_object(self):
        value = self.prepare(
            files={"route.json": b"original"},
            context={"kind": "invented", "fixture_phase": "quarantined", "fixture_pause": 0.8},
        )

        def change():
            end = time.monotonic() + 10
            while time.monotonic() < end:
                target = value["cleanup"] / value["request"]["attempt"] / "target"
                if b'"event":"quarantined"' in fixture.journal(value):
                    (target / "unexpected").write_bytes(b"do not remove")
                    return
                time.sleep(0.01)

        thread = threading.Thread(target=change)
        thread.start()
        outer = fixture.run(value)
        thread.join(10)
        self.assertFalse(thread.is_alive())
        self.assertEqual(outer["receipt"]["status"], "failed")
        target = value["cleanup"] / value["request"]["attempt"] / "target"
        self.assertEqual((target / "unexpected").read_bytes(), b"do not remove")
        self.assertEqual((target / "route.json").read_bytes(), b"original")
        with self.assertRaises(ValueError):
            fixture.inspect(value, outer)

    def test_real_outer_record_mutations_and_missing_outer_never_complete(self):
        value = self.prepare(files={"route.json": b"erase"})
        outer = fixture.run(value)
        self.assert_complete(value, outer)
        variants = []
        for owned in (
            ["fake"],
            [{}],
            [],
            [copy.deepcopy(outer["receipt"]["owned_processes"][0])] * 2,
        ):
            changed = copy.deepcopy(outer)
            changed["receipt"]["owned_processes"] = owned
            variants.append(changed)
        for key, new in (
            ("pid", True),
            ("ppid", 0),
            ("start", ""),
            ("start", "x" * 257),
            ("alive", 1),
            ("pgid", 0),
        ):
            changed = copy.deepcopy(outer)
            changed["receipt"]["owned_processes"][0][key] = new
            variants.append(changed)
        for key, new in (
            ("status", "failed"),
            ("exit_code", None),
            ("remaining_owned_processes", [{}]),
            ("cleanup_error", "unknown"),
        ):
            changed = copy.deepcopy(outer)
            changed["receipt"][key] = new
            variants.append(changed)
        for key, new in (
            ("control_sha256", "e" * 64),
            ("log_sha256", "e" * 64),
            ("request_sha256", "e" * 64),
        ):
            changed = copy.deepcopy(outer)
            changed[key] = new
            variants.append(changed)
        variants.append(None)
        for changed in variants:
            with self.subTest(changed=changed):
                self.assertEqual(fixture.inspect(value, changed)["status"], "incomplete")
                result = reconciliation.propose(**fixture.proposal(value, changed))
                self.assertEqual(result["register_raw"], value["register_raw"])
                if changed is None:
                    self.assertIsNone(result["bindings"]["outer"])
                    self.assertIsNone(
                        result["new_record_copy_proposals"]["outer"]["evidence_sha256"]
                    )
                    self.assertEqual(
                        result["new_record_copy_proposals"]["outer"]["state"], "not-observed"
                    )

    def test_replaced_or_truncated_journal_never_completes_even_when_rehashed(self):
        for kind in ("replace", "truncate"):
            value = self.prepare(files={"route.json": b"erase"})
            outer = fixture.run(value)
            self.assert_complete(value, outer)
            path = value["cleanup"] / value["request"]["attempt"] / "events.jsonl"
            raw = path.read_bytes()
            if kind == "replace":
                replacement = value["cleanup"] / "replacement"
                replacement.write_bytes(raw)
                replacement.chmod(0o600)
                replacement.replace(path)
            else:
                path.write_bytes(raw[: raw.rfind(b"\n", 0, -1) + 1] + b"{partial")
            self.assertEqual(fixture.inspect(value, outer)["status"], "incomplete")

    def test_only_allocated_copy_changes_and_origin_hold_other_copies_survive(self):
        for origin, hold in ((None, False), ("2026-11-01T00:00:00Z", True)):
            value = self.prepare(files={"route.json": b"erase"}, retained_since=origin, hold=hold)
            outer = fixture.run(value)
            self.assert_complete(value, outer)
            args = fixture.proposal(value, outer)
            result = reconciliation.propose(**args)
            before, after = (
                json.loads(raw) for raw in (value["register_raw"], result["register_raw"])
            )
            b, a = (v["subjects"]["subject-one"] for v in (before, after))
            for name in ("retained_since", "origin_evidence_sha256", "hold"):
                self.assertEqual(a[name], b[name])
            self.assertEqual(a["copies"]["other-copy"], b["copies"]["other-copy"])
            self.assertEqual(a["copies"]["original-copy"]["state"], "absence-observed")
            self.assertEqual(
                result["assessment"]["deadlines"]["subject-one"],
                None if origin is None else "2026-12-01T00:00:00Z",
            )
            self.assertTrue(
                any(
                    "origin-unestablished" in b or "hold-" in b
                    for b in result["assessment"]["blockers"]
                )
            )
            self.assertEqual(
                set(result["new_record_copy_proposals"]), set(reconciliation.RECORD_ROLES)
            )
            self.assertFalse(result["new_records_registered"])
            self.assertFalse(result["effective_erasure_verified"])
            args["record_copy_ids"]["control"] = "other-copy"
            with self.assertRaises(ValueError):
                reconciliation.propose(**args)

    def test_authority_withdrawal_and_relocated_reader_without_old_checkout(self):
        parent = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, parent)
        original, relocated = parent / "producer-code", parent / "reader-code"
        source = tree.source_identity()
        for name in source["implementation"]:
            path = original / name
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(tree.ROOT / name, path)
        (original / "tests").mkdir(exist_ok=True)
        shutil.copyfile(Path(fixture.__file__), original / "tests/lt1_native_tree_fixture.py")
        work = parent / "fresh-fixture"
        work.mkdir(mode=0o700)
        bundle = parent / "private-bundle.json"
        script = original / "exercise.py"
        script.write_text("""import json,sys,pathlib
sys.path[:0]=[str(pathlib.Path(__file__).parent),str(pathlib.Path(__file__).parent/'tests')]
import lt1_native_tree_fixture as f
from experiments.lt1_diagnostic import native_tree_removal as t
v=f.prepare(sys.argv[1],files={'route.json':b'generated','session-0000/events.jsonl':b'partial'})
before={n:(t.ROOT/n).read_bytes() for n in t.AUTHORITY_FILES}
for n in sorted(t.AUTHORITY_FILES):
 p=t.ROOT/n;x=json.loads(p.read_bytes())
 for k in ('requests','setup','execution'):
  if k in x:x[k]=[t.digest(v['raw'])]
 p.write_bytes(t.encoded(x))
v['audit']=t.source_identity()
o=f.run(v)
assert f.inspect(v,o)['status']=='completed'
for n,raw in before.items():(t.ROOT/n).write_bytes(raw)
current=t.source_identity()
assert current!=v['audit'] and t.code_source(current)==t.code_source(v['audit'])
assert f.inspect(v,o,reader_audit=current)['status']=='completed'
def export(x):
 if isinstance(x,bytes):return x.hex()
 return str(x) if isinstance(x,pathlib.Path) else x
data={k:export(x) for k,x in v.items()}
pathlib.Path(sys.argv[2]).write_text(json.dumps({'value':data,'outer':o,'old_root':str(t.ROOT)}))
print('actual-complete-and-withdrawal-pass')
""")
        first = subprocess.run(
            [sys.executable, "-I", "-S", "-B", str(script), str(work), str(bundle)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertIn("actual-complete-and-withdrawal-pass", first.stdout)
        shutil.copytree(original, relocated)
        shutil.rmtree(original)
        script = relocated / "readback.py"
        script.write_text("""import json,sys,pathlib
sys.path[:0]=[str(pathlib.Path(__file__).parent),str(pathlib.Path(__file__).parent/'tests')]
import lt1_native_tree_fixture as f
from experiments.lt1_diagnostic import native_tree_removal as t
x=json.loads(pathlib.Path(sys.argv[1]).read_bytes());v=x['value']
for k in ('raw','context','allocation_raw','register_raw','policy_raw'):v[k]=bytes.fromhex(v[k])
for k in ('root','cleanup'):v[k]=pathlib.Path(v[k])
assert not pathlib.Path(x['old_root']).exists()
assert t.ROOT!=pathlib.Path(x['old_root'])
assert f.inspect(v,x['outer'],reader_audit=t.source_identity())['status']=='completed'
p=t.ROOT/'experiments/lt1_diagnostic/native_tree_removal.py'
p.write_bytes(p.read_bytes()+b'\\n# changed copied reader code\\n')
try:f.inspect(v,x['outer'],reader_audit=t.source_identity())
except ValueError:pass
else:raise AssertionError('changed code accepted')
print('relocated-withdrawn-reader-and-code-refusal-pass')
""")
        second = subprocess.run(
            [sys.executable, "-I", "-S", "-B", str(script), str(bundle)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertIn("relocated-withdrawn-reader-and-code-refusal-pass", second.stdout)
