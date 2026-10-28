"""Separate admission clocks, live ownership, cancellation and inert phase records."""

import errno
import json
import os
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from contextlib import contextmanager, nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

from experiments.desktop import admission, admission_worker
from experiments.workflows import checks, dispatch
from experiments.workflows.__main__ import parser
from experiments.workflows.registry import ROOT, TASKS


def options(**values):
    return SimpleNamespace(
        admission_prepare_seconds=30, operation_seconds=120, phase_state=None, **values
    )


def runtime(project, packages):
    return {
        "project": project,
        "python": str(checks.interpreter(project)),
        "expected_packages": packages,
        "expected_python": "3.12",
        "ready": True,
        "setup": "Verify bundled runtime; rerun this installer if repair is needed",
        "reason": None,
        "actual": {
            "python": "3.12.15",
            "implementation": "CPython",
            "packages": {"fixture": "1", **packages},
            "direct_urls": {name: None for name in {"fixture": "1", **packages}},
        },
    }


@contextmanager
def native_file_descriptors():
    """Observe real native handle transfers; never replace any file operation."""
    captured = []
    if os.name != "nt":
        yield captured
        return
    import msvcrt

    convert = msvcrt.open_osfhandle

    def observe(*args, **kwargs):
        descriptor = convert(*args, **kwargs)
        captured.append(descriptor)
        return descriptor

    with patch.object(msvcrt, "open_osfhandle", side_effect=observe):
        yield captured


class PackagedAdmissionTests(unittest.TestCase):
    def setUp(self):
        # Receipt fixtures select an explicit executable independently of the
        # surrounding checkout/installed/dirty diagnostic package layout.
        self.interpreters = patch.object(
            checks, "runtime_interpreter", return_value=Path(sys.executable)
        )
        self.interpreters.start()
        self.addCleanup(self.interpreters.stop)

        def descriptor(project, source_root=None):
            packages = checks.runtime_requirements(TASKS["m4-study-secure"]).get(project, {})
            return {
                "executable": checks.interpreter(project),
                "manifest": {"runtime": {"version": "3.12.15"}},
                "distributions": {"fixture": "1", **packages},
                "upstream_revisions": {},
            }

        self.descriptors = patch.object(admission, "packaged_runtime", side_effect=descriptor)
        self.descriptors.start()
        self.addCleanup(self.descriptors.stop)

    def test_canonical_roster_and_complete_outer_budget(self):
        with patch.object(admission, "packaged_manifest", return_value={}):
            self.assertEqual(admission.admission_allowance("m3-compare"), 960)
            self.assertEqual(admission.admission_allowance("m4-study-secure"), 2880)
            self.assertEqual(
                admission.admission_allowance("m4-study-secure", reconstruction=True), 960
            )
            self.assertEqual(admission.coordinator_budget("m3-compare", 120), 1140)
            self.assertEqual(admission.coordinator_budget("m4-study-secure", 30), 2970)
            self.assertEqual(
                admission.coordinator_budget("m4-study-secure", 30, 600, reconstruction=True), 1680
            )
        with patch.object(admission, "packaged_manifest", return_value=None):
            self.assertEqual(admission.admission_allowance("m4-study-secure"), 0)
            self.assertEqual(admission.coordinator_budget("m4-study-secure", 30, 600), 600)
            self.assertEqual(admission.coordinator_budget("m4-study-secure", 30), 30)

    def test_optional_flags_do_not_change_unflagged_checkout_path(self):
        args = parser().parse_args(["check", "m3-compare", "--config", "example.json"])
        with patch.object(admission, "packaged_manifest") as manifest:
            self.assertFalse(admission.requested(args, operation="check"))
            manifest.assert_not_called()
        for args, operation in ((options(), "check"), (options(operation="run"), "run")):
            with (
                patch.object(admission, "packaged_manifest", return_value=None),
                self.assertRaises(ValueError),
            ):
                admission.requested(args, operation=operation)
        for number in (0, -1, float("inf"), float("nan"), True):
            with self.subTest(number=number), self.assertRaises(ValueError):
                admission.coordinator_budget("m3-compare", number)

    def test_phase_records_are_fresh_atomic_and_never_accept_links_or_extra_fields(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary).resolve()
            path = base / "phase.json"
            state = admission.PhaseState(path)
            record = {
                "schema": admission.SCHEMA,
                "task": "m3-compare",
                "operation": "run",
                "phase": "auditing",
                "project": ".",
                "sequence": 1,
                "phase_limit_seconds": 930,
                "phase_started_monotonic": 1,
                "elapsed_seconds": 0,
                "error_type": None,
            }
            state.update(record)
            self.assertEqual(admission.read_phase(path), record)
            with self.assertRaises(ValueError):
                admission.PhaseState(path)
            record.update(phase="failed", sequence=2, error_type="PhaseDeadline")
            state.update(record)
            self.assertEqual(admission.read_phase(path)["error_type"], "PhaseDeadline")
            path.write_text(json.dumps(dict(record, authorized=True)))
            with self.assertRaises(ValueError):
                admission.read_phase(path)
            # A second pathname to the same telemetry file is not an ordinary
            # owned output, even on a standard account that cannot make symlinks.
            os.link(path, base / "hardlink.json")
            with self.assertRaises(ValueError):
                state.update(record)
            with self.assertRaises(ValueError):
                admission.read_phase(path)

    def test_phase_publication_preserves_held_reader_with_long_unicode_path(self):
        # Keep the temporary directory's own cleanup in the long-path namespace.
        temporary_root = admission.native_absolute(Path(tempfile.gettempdir()).resolve())
        with tempfile.TemporaryDirectory(dir=temporary_root) as temporary:
            base = admission.native_absolute(Path(temporary).resolve())
            for index in range(4):
                base /= f"phase-{index}-" + "x" * 60
            base.mkdir(parents=True)
            path = base / "phase-🧪.json"
            self.assertGreater(len(str(path)), 260)
            state = admission.PhaseState(path)
            record = {
                "schema": admission.SCHEMA,
                "task": "m3-forecast",
                "operation": "check",
                "phase": "preparing",
                "project": None,
                "sequence": 1,
                "phase_limit_seconds": 120,
                "phase_started_monotonic": 1,
                "elapsed_seconds": 0,
                "error_type": None,
            }
            state.update(record)
            descriptor = admission.open_regular(path)
            with os.fdopen(descriptor, "rb") as held:
                original = held.read()
                old_identity = admission.storage.signature(os.fstat(held.fileno()))[:2]
                changed = dict(record, sequence=2, phase="auditing", project=".")
                # This is the actual GUI reader's share mode. Native Windows
                # MoveFileEx replacement fails while this destination is open.
                with native_file_descriptors() as owned_descriptors:
                    state.update(changed)
                if os.name == "nt":
                    self.assertTrue(owned_descriptors)
                    for owned in owned_descriptors:
                        with self.assertRaises(OSError) as closed:
                            os.fstat(owned)
                        self.assertEqual(closed.exception.errno, errno.EBADF)
                held.seek(0)
                self.assertEqual(held.read(), original)
                self.assertEqual(admission.read_phase(path), changed)
                self.assertNotEqual(
                    admission.storage.signature(admission.storage.regular_info(path))[:2],
                    old_identity,
                )
            with self.assertRaises(OSError) as closed:
                os.fstat(descriptor)
            self.assertEqual(closed.exception.errno, errno.EBADF)
            self.assertFalse(path.with_name(path.name + ".pending").exists())
            state.update(dict(record, sequence=3, phase="complete"))
            self.assertEqual(admission.read_phase(path)["sequence"], 3)

    def test_phase_publication_during_real_public_reader_is_coherent(self):
        from experiments.gui.packaged_phases import public_phase

        with tempfile.TemporaryDirectory() as temporary:
            base = admission.native_absolute(Path(temporary).resolve())
            path = base / "m3-check-phase.json"
            state = admission.PhaseState(path)
            record = {
                "schema": admission.SCHEMA,
                "task": "m3-forecast",
                "operation": "check",
                "phase": "preparing",
                "project": None,
                "sequence": 1,
                "phase_limit_seconds": 120,
                "phase_started_monotonic": 1,
                "elapsed_seconds": 0,
                "error_type": None,
            }
            state.update(record)
            acquired, release = threading.Event(), threading.Event()
            observed, errors, descriptors = [], [], []
            real_open = admission.open_regular
            job = {"state": "running", "operation": "m3_check", "task": "m3-forecast"}

            def hold_open(name, *args, **kwargs):
                descriptor = real_open(name, *args, **kwargs)
                if threading.current_thread() is reader and Path(name) == path:
                    descriptors.append(descriptor)
                    acquired.set()
                    if not release.wait(10):
                        os.close(descriptor)
                        raise RuntimeError("Phase reader barrier was not released")
                return descriptor

            def observe():
                try:
                    observed.append(public_phase(job, base))
                except BaseException as error:
                    errors.append(error)

            reader = threading.Thread(target=observe)
            with patch.object(admission, "open_regular", side_effect=hold_open):
                reader.start()
                try:
                    self.assertTrue(acquired.wait(10), "Real phase reader did not open")
                    changed = dict(record, sequence=2, phase="auditing", project=".")
                    state.update(changed)
                    self.assertEqual(admission.read_phase(path), changed)
                finally:
                    release.set()
                    reader.join(10)
            self.assertFalse(reader.is_alive(), "Phase reader did not close")
            self.assertEqual(errors, [])
            self.assertEqual(len(observed), 1)
            # Replaced old descriptors can lose a link/change ChangeTime; the
            # existing reader may reject that snapshot and omit display data.
            self.assertIn(observed[0], (record, None))
            self.assertEqual(len(descriptors), 1)
            with self.assertRaises(OSError) as closed:
                os.fstat(descriptors[0])
            self.assertEqual(closed.exception.errno, errno.EBADF)
            self.assertFalse(path.with_name(path.name + ".pending").exists())

    @unittest.skipUnless(os.name == "nt", "Windows pending-handle publication contract")
    def test_windows_phase_publication_rejects_changed_pending_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = admission.native_absolute(Path(temporary).resolve())
            for kind in ("replacement", "hardlink"):
                with self.subTest(kind=kind):
                    path = base / (kind + ".json")
                    state = admission.PhaseState(path)
                    record = {"synthetic": 1}
                    state.update(record)
                    original = path.read_bytes()
                    real_write = state._write

                    def interfere(parent, name, raw):
                        signature = real_write(parent, name, raw)
                        pending = base / name
                        saved = pending.with_name(name + ".saved")
                        os.replace(pending, saved)
                        if kind == "hardlink":
                            os.link(saved, pending)
                        else:
                            pending.write_bytes(raw)
                        return signature

                    with native_file_descriptors() as owned_descriptors:
                        with (
                            patch.object(state, "_write", side_effect=interfere),
                            self.assertRaises(ValueError),
                        ):
                            state.update({"synthetic": 2})
                    self.assertTrue(owned_descriptors)
                    for owned in owned_descriptors:
                        with self.assertRaises(OSError) as closed:
                            os.fstat(owned)
                        self.assertEqual(closed.exception.errno, errno.EBADF)
                    self.assertEqual(path.read_bytes(), original)
                    pending = path.with_name(path.name + ".pending")
                    # A substituted or now-hardlinked pathname is no longer
                    # this writer's ordinary exclusive output; preserve it.
                    self.assertTrue(pending.is_file())
                    self.assertEqual(json.loads(pending.read_bytes()), {"synthetic": 2})
                    self.assertEqual(
                        json.loads(pending.with_name(pending.name + ".saved").read_bytes()),
                        {"synthetic": 2},
                    )
            path = base / "substituted.json"
            state = admission.PhaseState(path)
            saved = base / "original.json"
            os.replace(path, saved)
            path.write_bytes(saved.read_bytes())
            with self.assertRaisesRegex(ValueError, "was replaced"):
                state.update({"synthetic": 3})
            self.assertFalse(path.with_name(path.name + ".pending").exists())

    def test_ended_admission_and_malformed_telemetry_never_grant_authority(self):
        owner = admission.Admission("m3-compare", options())
        owner.admitted = True
        owner.__exit__(None, None, None)
        with self.assertRaises(admission.AdmissionFailure):
            owner.run(["must-not-launch"], {})
        record = {
            "schema": admission.SCHEMA,
            "task": "m3-compare",
            "operation": "run",
            "phase": "auditing",
            "project": ".",
            "sequence": 1,
            "phase_limit_seconds": 930,
            "phase_started_monotonic": 1,
            "elapsed_seconds": 0,
            "error_type": None,
        }
        for field in ("task", "operation", "phase", "project"):
            with (
                self.subTest(field=field),
                patch.object(admission, "_read_json", return_value=dict(record, **{field: {}})),
                self.assertRaises(ValueError),
            ):
                admission.read_phase("inert")

    def test_worker_cannot_audit_arbitrary_project_or_execute_a_model(self):
        identity = {
            "task": "m3-compare",
            "operation": "run",
            "mode": "audit",
            "project": ".",
            "source_root": str(admission_worker.ROOT),
            "manifest": "bound",
            "sequence": 1,
        }
        request = {"identity": identity, "payload": {"metadata": {}}}
        with (
            patch.object(admission_worker, "_manifest_identity", return_value="bound"),
            patch.object(admission_worker, "probe_runtime", side_effect=runtime) as probe,
        ):
            self.assertTrue(admission_worker.execute(request)["result"]["ready"])
            probe.assert_called_once_with(".", {})
            identity["project"] = "outside"
            with self.assertRaises(ValueError):
                admission_worker.execute(request)
            identity.update(project=None, mode="execute")
            with self.assertRaises(ValueError):
                admission_worker.execute(request)
            self.assertEqual(probe.call_count, 1)

    def test_worker_rejects_manifest_change_during_real_probe(self):
        request = {
            "identity": {
                "task": "m3-compare",
                "operation": "run",
                "mode": "audit",
                "project": ".",
                "source_root": str(admission_worker.ROOT),
                "manifest": "before",
                "sequence": 1,
            },
            "payload": {"metadata": {}},
        }
        with (
            patch.object(admission_worker, "_manifest_identity", side_effect=["before", "after"]),
            patch.object(admission_worker, "probe_runtime", side_effect=runtime) as probe,
            self.assertRaises(ValueError),
        ):
            admission_worker.execute(request)
        probe.assert_called_once_with(".", {})

    def test_each_current_audit_is_required_and_failure_stops_roster(self):
        owner = admission.Admission("m4-study-secure", options())
        requirements = checks.runtime_requirements(TASKS["m4-study-secure"])
        calls = []

        def worker(mode, payload, seconds, *, project=None):
            calls.append((mode, project, seconds))
            if mode == "prepare":
                return {"metadata": {}, "observation_path_issues": []}
            return runtime(project, requirements[project])

        with (
            patch.object(owner, "worker", side_effect=worker),
            patch.object(checks, "uv_ready", return_value={"ready": True}),
            patch.object(checks, "packaged_manifest", return_value={}),
        ):
            first = owner.check()
            second = owner.check()
        self.assertTrue(first["ready"])
        self.assertEqual(first, second)
        self.assertEqual(len(calls), 8)
        self.assertEqual([call[1] for call in calls[1:4]], list(requirements))
        owner.finish = Mock()
        failed = dict(runtime(".", {}), ready=False, reason="mutated")
        with (
            patch.object(
                owner,
                "worker",
                side_effect=[{"metadata": {}, "observation_path_issues": []}, failed],
            ) as call,
            patch.object(checks, "uv_ready", return_value={"ready": True}),
            patch.object(checks, "packaged_manifest", return_value={}),
        ):
            result = owner.check()
        self.assertFalse(result["runtimes_ready"])
        self.assertEqual(call.call_count, 2)
        owner.finish.assert_called_once_with("failed", "PackagedRuntimeUnavailable")

    def test_dispatch_uses_live_owner_without_a_second_public_check(self):
        args = options(output=Path("unused"))
        owner = Mock()
        owner.__enter__ = Mock(return_value=owner)
        owner.__exit__ = Mock(return_value=False)
        owner.check.return_value = {"runtimes_ready": True, "observation_path_issues": []}
        owner.run.return_value = (0, None)
        with (
            patch.object(admission, "requested", return_value=True),
            patch.object(admission, "Admission", return_value=owner),
            patch.object(dispatch, "check") as public,
            patch.object(dispatch, "command_for", return_value=["fixed"]),
            patch.object(dispatch, "report_status", return_value={}),
            patch.object(dispatch, "child_environment", return_value={}),
        ):
            result = dispatch.execute(TASKS["m3-compare"], args)
        self.assertEqual(result["child_exit_code"], 0)
        public.assert_not_called()
        owner.run.assert_called_once_with(["fixed"], {})
        self.assertLess(
            owner.mock_calls.index(call.run(["fixed"], {})),
            owner.mock_calls.index(call.__exit__(None, None, None)),
        )

    def test_failed_audit_never_dispatches(self):
        args = options(output=Path("unused"))
        owner = Mock()
        owner.__enter__ = Mock(return_value=owner)
        owner.__exit__ = Mock(return_value=False)
        owner.check.return_value = {"runtimes_ready": False}
        with (
            patch.object(admission, "requested", return_value=True),
            patch.object(admission, "Admission", return_value=owner),
            patch.object(dispatch, "command_for") as command,
        ):
            result = dispatch.execute(TASKS["m3-compare"], args)
        self.assertIsNone(result["child_exit_code"])
        command.assert_not_called()
        owner.run.assert_not_called()

    def test_cancel_between_audit_and_native_is_latched_with_no_spawn(self):
        owner = admission.Admission("m3-compare", options())
        owner._forward(signal.SIGTERM)
        with (
            patch.object(admission, "spawn") as spawn,
            self.assertRaises(admission.AdmissionFailure) as caught,
        ):
            owner.run(["fixed"], {})
        self.assertEqual(caught.exception.forwarded_signal, signal.SIGTERM)
        spawn.assert_not_called()

    def test_native_clock_begins_after_audit_and_unused_time_is_not_donated(self):
        owner = admission.Admission("m3-compare", options())
        owner.manifest = "same"
        owner.admitted = True
        owner.state = Mock()
        limits = []

        def supervise(argv, seconds, env):
            limits.append(seconds)
            return 0, None

        with (
            patch.object(admission, "_manifest_identity", return_value="same"),
            patch.object(owner, "supervise", side_effect=supervise),
        ):
            owner.run(["fixed"], {})
        self.assertEqual(limits, [120])
        self.assertEqual(owner.record["phase_limit_seconds"], 120)
        self.assertEqual(owner.record["phase"], "complete")

    def test_truthy_or_incomplete_runtime_receipts_cannot_grant_admission(self):
        owner = admission.Admission("m3-compare", options())
        prepared = {"metadata": {}, "observation_path_issues": []}
        truthy = dict(runtime(".", {}), ready="yes")
        missing = runtime(".", {})
        missing.pop("actual")
        wrong_packages = runtime(".", {})
        wrong_packages["actual"]["packages"] = []
        for invalid in (truthy, missing, wrong_packages):
            with (
                self.subTest(value=invalid),
                patch.object(owner, "worker", side_effect=[prepared, invalid]),
                self.assertRaises(admission.AdmissionFailure) as caught,
            ):
                owner.check()
            self.assertEqual(caught.exception.error_type, "AdmissionRuntimeMismatch")

    def test_native_dispatch_requires_unconsumed_live_admission(self):
        owner = admission.Admission("m3-compare", options())
        owner.state = Mock()
        owner.manifest = "same"
        with (
            patch.object(admission, "_manifest_identity", return_value="same"),
            patch.object(owner, "supervise", return_value=(0, None)) as native,
        ):
            with self.assertRaises(admission.AdmissionFailure):
                owner.run(["fixed"], {})
            owner.admitted = True
            owner.run(["fixed"], {})
            with self.assertRaises(admission.AdmissionFailure):
                owner.run(["fixed"], {})
        native.assert_called_once()

    def test_wrong_current_worker_receipt_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            owner = admission.Admission("m3-compare", options())
            owner.temporary = SimpleNamespace(name=str(Path(temporary).resolve()))
            owner.manifest = "same"
            owner.state = Mock()
            with (
                patch.object(owner, "supervise", return_value=(0, None)),
                patch.object(admission, "_read_json", return_value={"identity": {}, "result": {}}),
                self.assertRaises(admission.AdmissionFailure) as caught,
            ):
                owner.worker("prepare", {}, 30)
            self.assertEqual(caught.exception.error_type, "AdmissionResultMismatch")

    def test_owned_phase_deadline_reaps_actual_process(self):
        # The clock test does not depend on reaching a nested-child marker. Its
        # contract is deadline enforcement and reaping the retained root handle.
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary).resolve()
            package = base / "experiments"
            (package / "gui").mkdir(parents=True)
            (package / "__init__.py").write_text("")
            (package / "gui/__init__.py").write_text("")
            (package / "gui/windows_worker.py").write_bytes(
                (ROOT / "experiments/gui/windows_worker.py").read_bytes()
            )
            (package / "admission_fixture.py").write_text("import time\ntime.sleep(120)\n")
            owner = admission.Admission("m3-compare", options())
            owner.root = base
            retained = []
            actual_spawn = admission.spawn

            def start(*args, **kwargs):
                process = actual_spawn(*args, **kwargs)
                retained.append(process)
                return process

            with (
                patch.object(admission, "spawn", side_effect=start),
                self.assertRaises(admission.AdmissionFailure) as caught,
            ):
                owner.supervise(
                    [sys.executable, "-B", "-E", "-s", "-m", "experiments.admission_fixture"],
                    0.2,
                    dict(os.environ),
                )
            self.assertEqual(caught.exception.error_type, "PhaseDeadline")
            self.assertIsNotNone(retained[0].poll())
            self.assertIsNone(owner.active)
            if os.name == "nt":
                self.assertTrue(retained[0]._opent1d_ownership.closed)

    def test_soft_cancellation_is_delivered_once_while_native_seals(self):
        self.check_soft_cancellation()

    @unittest.skipUnless(sys.platform == "darwin", "Actual Darwin unreaped group contract")
    def test_soft_cancellation_at_unreaped_exit_preserves_the_native_seal(self):
        self.check_soft_cancellation(pause_at_exit=True)

    def check_soft_cancellation(self, *, pause_at_exit=False):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary).resolve()
            package = base / "experiments"
            (package / "gui").mkdir(parents=True)
            (package / "__init__.py").write_text("")
            (package / "gui/__init__.py").write_text("")
            (package / "gui/windows_worker.py").write_bytes(
                (ROOT / "experiments/gui/windows_worker.py").read_bytes()
            )
            marker, sealed = base / "ready", base / "sealed"
            (package / "admission_fixture.py").write_text(
                "import signal,time\nfrom pathlib import Path\n"
                "count=0\n"
                "def stop(*args):\n"
                " global count\n count+=1\n"
                " if count>1: raise SystemExit(3)\n"
                " time.sleep(0.25)\n" + f" Path({str(sealed)!r}).write_text(str(count))\n"
                " raise SystemExit(0)\n"
                "signal.signal(signal.SIGTERM,stop)\n"
                "signal.signal(signal.SIGINT,stop)\n" + f"Path({str(marker)!r}).touch()\n"
                "while True: time.sleep(0.01)\n"
            )
            owner = admission.Admission("m3-compare", options())
            owner.root = base
            stopped = threading.Event()

            def cancel():
                while not stopped.wait(0.02):
                    if marker.is_file() and owner.active is not None:
                        owner._forward(signal.SIGTERM)
                        return

            observer = threading.Thread(target=cancel)
            observer.start()
            actual_exists, paused = admission.tree_exists, []

            def observe(process):
                if owner.received is not None and process.returncode is None and not paused:
                    paused.append(process)
                    deadline = time.monotonic() + 3
                    while time.monotonic() < deadline:
                        # Only our retained fixture's PID. Do not reap it before
                        # exercising the actual kernel group-observation race.
                        state = subprocess.check_output(
                            ["ps", "-p", str(process.pid), "-o", "stat="], text=True
                        ).strip()
                        if state.startswith("Z"):
                            break
                        time.sleep(0.005)
                    else:
                        self.fail("Owned sealing worker did not reach unreaped exit")
                return actual_exists(process)

            try:
                with (
                    patch.object(admission, "tree_exists", side_effect=observe)
                    if pause_at_exit
                    else nullcontext(),
                    self.assertRaises(admission.AdmissionFailure) as caught,
                ):
                    owner.supervise(
                        [sys.executable, "-B", "-E", "-s", "-m", "experiments.admission_fixture"],
                        120,
                        dict(os.environ),
                    )
                self.assertEqual(caught.exception.error_type, "GlobalInterruption")
                self.assertEqual(sealed.read_text(), "1")
                if pause_at_exit:
                    self.assertEqual(len(paused), 1)
                    self.assertEqual(paused[0].poll(), 0)
                    self.assertFalse(actual_exists(paused[0]))
            finally:
                stopped.set()
                observer.join(timeout=2)
            self.assertFalse(observer.is_alive())

    def test_cancellation_transition_retains_failure_and_restores_signal_handler(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary).resolve() / "phase.json"
            args = options()
            args.phase_state = path
            previous = signal.getsignal(signal.SIGTERM)
            with patch.object(admission, "_manifest_identity", return_value="bound"):
                with self.assertRaises(admission.AdmissionFailure):
                    with admission.Admission("m3-compare", args, operation="run") as owner:
                        owner.phase("auditing", 930, ".")
                        owner._forward(signal.SIGTERM)
                        owner.run(["must-not-launch"], {})
            record = admission.read_phase(path)
            self.assertEqual(record["phase"], "cancelled")
            self.assertEqual(record["project"], ".")
            self.assertEqual(record["error_type"], "GlobalInterruption")
            self.assertIs(signal.getsignal(signal.SIGTERM), previous)

    def test_cancellation_reaps_an_admitted_live_descendant(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary).resolve()
            package = base / "experiments"
            (package / "gui").mkdir(parents=True)
            (package / "__init__.py").write_text("")
            (package / "gui/__init__.py").write_text("")
            (package / "gui/windows_worker.py").write_bytes(
                (ROOT / "experiments/gui/windows_worker.py").read_bytes()
            )
            marker = base / "descendant-ready"
            (package / "admission_fixture.py").write_text(
                "import os,signal,subprocess,sys,threading\nfrom pathlib import Path\n"
                "if len(sys.argv)>1:\n"
                " p=Path(sys.argv[1]); t=p.with_suffix('.pending')\n"
                " t.write_text(str(os.getpid())); t.replace(p)\n"
                " threading.Event().wait()\n"
                "else:\n"
                " def stop(*args): raise KeyboardInterrupt\n"
                " signal.signal(signal.SIGTERM,stop)\n"
                " child=subprocess.Popen([sys.executable,'-B','-E','-s',"
                "'-m','experiments.admission_fixture'," + repr(str(marker)) + "],"
                "stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,"
                "stderr=subprocess.DEVNULL,creationflags=8 if sys.platform=='win32' else 0)\n"
                " try: child.wait()\n"
                " finally:\n"
                "  if child.poll() is None: child.terminate()\n"
                "  child.wait()\n"
            )
            owner = admission.Admission("m3-compare", options())
            owner.root = base
            witnessed, handles, errors = [], [], []
            stop = threading.Event()
            if os.name == "nt":
                import ctypes
                from ctypes import wintypes

                kernel = ctypes.WinDLL("kernel32", use_last_error=True)
                for name, arguments, result in (
                    (
                        "OpenProcess",
                        (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD),
                        wintypes.HANDLE,
                    ),
                    ("WaitForSingleObject", (wintypes.HANDLE, wintypes.DWORD), wintypes.DWORD),
                    (
                        "IsProcessInJob",
                        (wintypes.HANDLE, wintypes.HANDLE, ctypes.POINTER(wintypes.BOOL)),
                        wintypes.BOOL,
                    ),
                    ("CloseHandle", (wintypes.HANDLE,), wintypes.BOOL),
                ):
                    function = getattr(kernel, name)
                    function.argtypes, function.restype = arguments, result

            def observe():
                try:
                    deadline = None
                    while not stop.wait(0.02):
                        process = owner.active
                        if process is None:
                            continue
                        if deadline is None:
                            deadline = time.monotonic() + 120
                        if time.monotonic() >= deadline:
                            raise AssertionError("Owned child did not reach live admission")
                        if not marker.is_file() or process.poll() is not None:
                            continue
                        pid = int(marker.read_text())
                        if os.name == "nt":
                            handle = kernel.OpenProcess(0x00100000 | 0x1000, False, pid)
                            if not handle:
                                raise ctypes.WinError(ctypes.get_last_error())
                            handles.append(handle)
                            member = wintypes.BOOL()
                            if not kernel.IsProcessInJob(
                                handle, process.job.handle, ctypes.byref(member)
                            ):
                                raise ctypes.WinError(ctypes.get_last_error())
                            if not member.value or kernel.WaitForSingleObject(handle, 0) != 258:
                                raise AssertionError("Descendant was not alive inside owned Job")
                        else:
                            if os.getpgid(pid) != process.pid:
                                raise AssertionError("Descendant left the owned process group")
                            os.kill(pid, 0)  # Observation only; control uses the live owner.
                        witnessed.append(process)
                        owner._forward(signal.SIGTERM)
                        return
                except BaseException as error:
                    errors.append(error)
                    owner._forward(signal.SIGTERM)

            thread = threading.Thread(target=observe)
            thread.start()
            try:
                with self.assertRaises(admission.AdmissionFailure) as caught:
                    owner.supervise(
                        [sys.executable, "-B", "-E", "-s", "-m", "experiments.admission_fixture"],
                        120,
                        dict(os.environ),
                    )
                self.assertEqual(errors, [])
                self.assertTrue(witnessed)
                self.assertEqual(caught.exception.error_type, "GlobalInterruption")
                self.assertIsNotNone(witnessed[0].poll())
                if os.name == "nt":
                    self.assertTrue(witnessed[0]._opent1d_ownership.closed)
                    self.assertEqual(kernel.WaitForSingleObject(handles[0], 0), 0)
                else:
                    self.assertFalse(admission.tree_exists(witnessed[0]))
            finally:
                stop.set()
                thread.join(timeout=2)
                if os.name == "nt":
                    for handle in handles:
                        kernel.CloseHandle(handle)
            self.assertFalse(thread.is_alive())


if __name__ == "__main__":
    unittest.main()
