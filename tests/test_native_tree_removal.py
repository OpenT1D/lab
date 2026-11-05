"""Actual fresh original-tree removal; no private data or native qualification."""

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
        self.assertFalse((value["cleanup"] / value["request"]["attempt"] / "target").exists())
        result = fixture.inspect(value, outer)
        self.assertEqual(result["status"], "completed")
        self.assertTrue(all(result[k] is False for k in tree.AUTHORITY))
        return result

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
