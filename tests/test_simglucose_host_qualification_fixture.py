"""Pure invented host-control fixtures; no host/runtime/process qualification."""

import builtins
import copy
import unittest
from unittest.mock import patch

from experiments.simglucose_audit import host_qualification_fixture as host
from experiments.simglucose_audit.contract import decode, digest, encode


class SimglucoseHostQualificationFixtureTests(unittest.TestCase):
    def setUp(self):
        self.candidate = encode(host.invented_candidate())
        self.candidate_pin = digest(self.candidate)
        self.profile = encode(
            host.propose_profile(
                self.candidate,
                self.candidate_pin,
                "/__ot062_invented__/stage",
                "/__ot062_invented__/evidence",
            )
        )
        self.profile_pin = digest(self.profile)

    def request(self, case="complete"):
        return encode(
            host.fixture_request(
                self.profile, self.profile_pin, self.candidate, self.candidate_pin, case
            )
        )

    def inspect(self, frames, request):
        return host.inspect_fixture(
            frames,
            digest(frames),
            request,
            digest(request),
            self.profile,
            self.profile_pin,
            self.candidate,
            self.candidate_pin,
        )

    def run_case(self, case="complete"):
        request = self.request(case)
        frames = host.run_fixture(
            request, self.profile, self.profile_pin, self.candidate, self.candidate_pin
        )
        return request, frames, self.inspect(frames, request)

    def rechain(self, rows):
        previous, lines = None, []
        for index, row in enumerate(rows):
            raw = encode(row | {"sequence": index, "previous_sha256": previous}) + b"\n"
            lines.append(raw)
            previous = digest(raw)
        return b"".join(lines)

    def rows(self, frames):
        return [decode(raw) for raw in frames.splitlines()]

    def test_pure_profile_has_concrete_proposed_argv_ENV_filemap_and_matched_roster(self):
        with patch("builtins.open", side_effect=AssertionError("profile opened a path")):
            profile = host.propose_profile(
                self.candidate, self.candidate_pin, "/proposed/runtime", "/proposed/evidence"
            )
        self.assertEqual(
            profile["argv"],
            [
                "/proposed/runtime/bin/python3",
                "-I",
                "-S",
                "-B",
                "/proposed/runtime/opent1d/host_qualification_probe.py",
                "--request",
                "/proposed/evidence/request.json",
                "--events",
                "/proposed/evidence/worker-events.ndjson",
            ],
        )
        self.assertEqual(
            set(profile["env"]),
            {
                "LANG",
                "LC_ALL",
                "PATH",
                "HOME",
                "TMPDIR",
                "MPLCONFIGDIR",
                "MPLBACKEND",
                "PYTHONDONTWRITEBYTECODE",
            },
        )
        self.assertEqual(len(profile["output_file_map"]), 8)
        self.assertEqual(len(profile["controls"]), 12)
        self.assertEqual(
            [row["expected"] for row in profile["controls"]], ["allowed", "denied"] * 6
        )
        self.assertTrue(
            all(value is None for value in profile["missing_actual_prerequisites"].values())
        )
        self.assertFalse(profile["host_qualified"])
        self.assertFalse(profile["qualification_ready"])
        self.assertIsNone(profile["actual_executable_sha256"])
        self.assertIsNone(profile["actual_probe_source_sha256"])
        self.assertFalse(profile["rules"]["MPLCONFIGDIR_or_Agg_is_confinement"])

    def test_opaque_candidate_metadata_never_supplies_runtime_admission(self):
        candidate = encode(
            {"schema": "invented-opaque-candidate/1", "native_execution_authorized": True}
        )
        profile = host.propose_profile(candidate, digest(candidate), "/stage", "/evidence")
        self.assertEqual(
            profile["candidate_admission"], "none; opaque metadata identity binding only"
        )
        self.assertFalse(profile["authority"]["native_execution_authorized"])
        self.assertFalse(profile["qualification_ready"])

    def test_proposal_schema_is_blocked_and_cannot_be_used_as_fixture_or_actual_runner(self):
        request = encode(
            host.propose_request(self.profile, self.profile_pin, self.candidate, self.candidate_pin)
        )
        decoded, _profile = host.validate_request(
            request,
            digest(request),
            self.profile,
            self.profile_pin,
            self.candidate,
            self.candidate_pin,
        )
        self.assertIsNone(decoded["ownership"])
        self.assertFalse(decoded["actual_qualification_requested"])
        self.assertFalse(decoded["model_execution_requested"])
        with self.assertRaisesRegex(ValueError, "invented-fixture-only"):
            host.run_fixture(
                request, self.profile, self.profile_pin, self.candidate, self.candidate_pin
            )

    def test_completed_fixture_is_invented_only_and_repeats_with_fresh_state(self):
        request, frames, summary = self.run_case()
        self.assertEqual(summary["status"], "completed")
        self.assertEqual((summary["observed_controls"], summary["planned_controls"]), (12, 12))
        self.assertIsNone(summary["pending_control"])
        self.assertFalse(summary["host_qualified"])
        self.assertFalse(summary["native_acceptance"])
        self.assertFalse(summary["actual_OS_observation"])
        repeated = host.run_fixture(
            request, self.profile, self.profile_pin, self.candidate, self.candidate_pin
        )
        self.assertEqual(repeated, frames)
        self.assertNotIn(b'"pid"', frames)

    def test_cancel_deadline_error_and_crash_preserve_two_controls_and_pending(self):
        statuses = {
            "cancel-after-two": "interrupted",
            "deadline-after-two": "incomplete",
            "error-after-two": "failed",
            "crash-after-two": "incomplete",
        }
        for case, status in statuses.items():
            with self.subTest(case=case):
                _request, _frames, summary = self.run_case(case)
                self.assertEqual(summary["status"], status)
                self.assertEqual(summary["observed_controls"], 2)
                self.assertEqual(summary["planned_controls"], 12)
                self.assertEqual(summary["pending_control"], "network:reference-positive")
        _request, frames, summary = self.run_case("cancel-before-start")
        self.assertEqual((summary["status"], summary["observed_controls"]), ("interrupted", 0))
        self.assertNotIn(b'"constructed"', frames)
        self.assertNotIn(b'"cleanup"', frames)

    def test_cleanup_error_and_unmatched_deny_cannot_remain_completed(self):
        for case, count in (("cleanup-error", 12), ("denial-mismatch", 2)):
            request, frames, summary = self.run_case(case)
            self.assertEqual((summary["status"], summary["observed_controls"]), ("failed", count))
            rows = self.rows(frames)
            rows[-1]["data"].update(status="completed", primary_error=None, cleanup_error=None)
            with self.assertRaises(ValueError):
                self.inspect(self.rechain(rows), request)

    def test_primary_error_survives_cleanup_error_and_pending_prefix(self):
        request, frames, summary = self.run_case("error-and-cleanup")
        terminal = self.rows(frames)[-1]["data"]
        self.assertEqual(summary["status"], "failed")
        self.assertEqual(summary["observed_controls"], 2)
        self.assertIsNotNone(summary["pending_control"])
        self.assertEqual(terminal["primary_error"], "invented-control-error")
        self.assertEqual(terminal["cleanup_error"], "invented-cleanup-error")
        rows = self.rows(frames)
        rows[-1]["data"]["primary_error"] = None
        with self.assertRaises(ValueError):
            self.inspect(self.rechain(rows), request)

    def test_every_complete_prefix_and_torn_prefix_remains_incomplete(self):
        request, frames, _summary = self.run_case()
        lines = frames.splitlines(keepends=True)
        for count in range(1, len(lines)):
            prefix = b"".join(lines[:count])
            self.assertEqual(self.inspect(prefix, request)["status"], "incomplete")
        prefix = b"".join(lines[:-1]) + b'{"partial":'
        summary = self.inspect(prefix, request)
        self.assertEqual(summary["status"], "incomplete")
        self.assertTrue(summary["torn_tail"])
        with self.assertRaisesRegex(ValueError, "trailing-bytes"):
            self.inspect(frames + b'{"diagnostic":', request)

    def test_rehashed_owner_source_input_deny_cleanup_and_host_promotions_rejected(self):
        request, frames, _summary = self.run_case()
        original = self.rows(frames)
        changes = []
        for field, value in (
            ("ownership", {}),
            ("source_identity", {}),
            ("input_sha256", "0" * 64),
            ("process_owner_source_identity", {}),
            ("actual_OS_observation", True),
        ):
            rows = copy.deepcopy(original)
            rows[0]["data"][field] = value
            changes.append(rows)
        rows = copy.deepcopy(original)
        rows[5]["data"]["result"] = "allowed"
        changes.append(rows)
        rows = copy.deepcopy(original)
        rows[-2]["data"]["reader_joined"] = False
        changes.append(rows)
        rows = copy.deepcopy(original)
        rows[-1]["data"]["host_result"]["host_qualified"] = True
        changes.append(rows)
        rows = copy.deepcopy(original)
        rows[-1]["data"]["authority"]["native_execution_authorized"] = True
        changes.append(rows)
        for rows in changes:
            with self.assertRaises(ValueError):
                self.inspect(self.rechain(rows), request)

    def test_reordered_duplicate_early_terminal_unknown_and_bad_chain_rejected(self):
        request, frames, _summary = self.run_case()
        original = self.rows(frames)
        for rows in (
            original[:2] + [original[-1]],
            original[:3] + [original[2]] + original[3:],
            original[:2] + [original[3], original[2]] + original[4:],
            original + [original[-1]],
        ):
            with self.assertRaises(ValueError):
                self.inspect(self.rechain(rows), request)
        rows = copy.deepcopy(original)
        rows[2]["event"] = "selected-runtime-started"
        with self.assertRaises(ValueError):
            self.inspect(self.rechain(rows), request)
        rows = copy.deepcopy(original)
        rows[2]["previous_sha256"] = "0" * 64
        bad = b"\n".join(map(encode, rows)) + b"\n"
        with self.assertRaisesRegex(ValueError, "chain"):
            self.inspect(bad, request)

    def test_deadline_cancel_and_error_observations_are_required_and_clock_bound(self):
        for case, event in (
            ("deadline-after-two", "deadline"),
            ("cancel-after-two", "cancel"),
            ("error-after-two", "control-error"),
        ):
            request, frames, _summary = self.run_case(case)
            rows = self.rows(frames)
            without = [row for row in rows if row["event"] != event]
            with self.assertRaises(ValueError):
                self.inspect(self.rechain(without), request)
        request, frames, _summary = self.run_case("deadline-after-two")
        rows = self.rows(frames)
        next(row for row in rows if row["event"] == "deadline")["data"]["deadline_ms"] = 999999
        with self.assertRaisesRegex(ValueError, "deadline-clock"):
            self.inspect(self.rechain(rows), request)

    def test_request_profile_and_ANYEXEC_field_promotions_refused_after_rehash(self):
        request = decode(self.request())
        for field, value in (
            ("actual_qualification_requested", True),
            ("model_execution_requested", True),
            ("ownership", {"pid": 1}),
            ("factory", "native"),
            ("input_sha256", "0" * 64),
        ):
            changed = encode(request | {field: value})
            with self.assertRaises(ValueError):
                host.validate_request(
                    changed,
                    digest(changed),
                    self.profile,
                    self.profile_pin,
                    self.candidate,
                    self.candidate_pin,
                )
        changed = copy.deepcopy(request)
        changed["actual_prerequisites"]["explicit_scoped_postponement_lift_sha256"] = "0" * 64
        changed_raw = encode(changed)
        with self.assertRaises(ValueError):
            host.validate_request(
                changed_raw,
                digest(changed_raw),
                self.profile,
                self.profile_pin,
                self.candidate,
                self.candidate_pin,
            )
        for field, value in (
            ("argv", ["native", "--version"]),
            ("env", {"HTTP_PROXY": "invented"}),
            ("host_qualified", True),
            ("actual_OS_policy_sha256", "0" * 64),
        ):
            profile = encode(decode(self.profile) | {field: value})
            with self.assertRaisesRegex(ValueError, "profile-reconstruction"):
                host.propose_request(profile, digest(profile), self.candidate, self.candidate_pin)

    def test_virtual_posix_root_controls_parent_overlap_and_nonfinite_JSON_refused(self):
        for stage in (
            "/bad\0root",
            "/bad\nroot",
            "/bad\troot",
            "//bad/root",
            "/bad/../root",
            "/bad//root",
            "relative",
            "/stage/",
        ):
            with self.subTest(stage=stage), self.assertRaises(ValueError):
                host.propose_profile(self.candidate, self.candidate_pin, stage, "/evidence")
        with self.assertRaises(ValueError):
            host.propose_profile(self.candidate, self.candidate_pin, "/stage", "/stage/evidence")
        for raw in (
            b'{"schema":"x","schema":"y"}',
            b'{"schema":"x","n":NaN}',
            b'{"schema":"x","n":1e309}',
        ):
            with self.assertRaises(ValueError):
                host.propose_profile(raw, digest(raw), "/stage", "/evidence")

    def test_external_pins_input_bytes_and_source_drift_are_not_self_authorized(self):
        request, frames, _summary = self.run_case()
        with self.assertRaisesRegex(ValueError, "held-frame"):
            host.inspect_fixture(
                frames,
                "0" * 64,
                request,
                digest(request),
                self.profile,
                self.profile_pin,
                self.candidate,
                self.candidate_pin,
            )
        with self.assertRaisesRegex(ValueError, "input"):
            host.run_fixture(
                request,
                self.profile,
                self.profile_pin,
                self.candidate,
                self.candidate_pin,
                input_raw=b"changed-invented-canary",
            )
        identity = host._identity()
        with (
            patch.object(host, "_identity", return_value=identity | {"drift": "invented"}),
            self.assertRaises(ValueError),
        ):
            self.inspect(frames, request)

    def test_closed_actual_entry_refuses_before_any_argument_or_source_use(self):
        class Poison:
            def __fspath__(self):
                raise AssertionError("path used")

            def __bytes__(self):
                raise AssertionError("input used")

        with (
            patch.object(host, "_identity", side_effect=AssertionError("source read")),
            self.assertRaises(PermissionError),
        ):
            host.run_host_qualification(Poison(), request=Poison(), grant=Poison())

    def test_fixture_producer_never_probes_a_host_or_process(self):
        request = self.request()
        with (
            patch("subprocess.Popen", side_effect=AssertionError("process probe")),
            patch("socket.socket", side_effect=AssertionError("network probe")),
            patch("os.kill", side_effect=AssertionError("PID probe")),
            patch("os.killpg", side_effect=AssertionError("process group probe"), create=True),
        ):
            frames = host.run_fixture(
                request, self.profile, self.profile_pin, self.candidate, self.candidate_pin
            )
        self.assertEqual(self.inspect(frames, request)["status"], "completed")

    def test_cold_reader_never_calls_producer_process_network_or_selected_dependency(self):
        request, frames, _summary = self.run_case()
        real_import = builtins.__import__

        def guard(name, *args, **kwargs):
            if name.split(".")[0] in {"simglucose", "gym", "numpy", "matplotlib", "pkg_resources"}:
                raise AssertionError("selected dependency")
            return real_import(name, *args, **kwargs)

        with (
            patch.object(host, "run_fixture", side_effect=AssertionError("producer")),
            patch.object(host, "_event_sequence", side_effect=AssertionError("producer oracle")),
            patch("subprocess.Popen", side_effect=AssertionError("process")),
            patch("socket.socket", side_effect=AssertionError("socket")),
            patch("os.kill", side_effect=AssertionError("PID action")),
            patch("builtins.__import__", side_effect=guard),
        ):
            self.assertEqual(self.inspect(frames, request)["status"], "completed")


if __name__ == "__main__":
    unittest.main()
