"""Live phase hints can be incomplete; cancellation still requires actual analysis."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from tests import test_gui_sampling as sampling


class AnalysisPhaseWaitTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.phase = self.root / "archive/studies/full/execution.json"
        self.phase.parent.mkdir(parents=True)
        self.now = 0

    def clock(self):
        return self.now

    def fixture(self):
        case = sampling.SamplingGUITests("test_cancel_preserves_all_denominators_and_reconstructs")
        case.configure = Mock(return_value={"id": "configuration"})
        case.request = Mock(
            side_effect=[(202, {"id": "job", "sampling_entry_id": "entry"}), (400, {}), (202, {})]
        )
        case.service = Mock()
        case.service.get_job.return_value = {"state": "running"}
        case.service.sampling.get.return_value = {"id": "entry"}
        case.service.sampling.folder.return_value = self.root
        case.service.sampling.report.return_value = {
            "native_report": {
                "execution_status": "interrupted",
                "coverage": {"planned_variant_pairs": 60, "not_attempted_draw_pairs": 1},
            }
        }
        case.wait = Mock(
            return_value={"state": "cancelled", "verification": "native_reader_verified"}
        )
        return case

    def test_cancellation_fixture_retries_transient_json_until_actual_analysis(self):
        case = self.fixture()
        self.phase.write_bytes(b"")
        pending = [
            None,
            b'{"phase":',
            b'{"status":"started","phase":"preflight"}',
            b'{"status":"started","phase":"snapshot"}',
            b'{"status":"started","phase":"analysis"}',
        ]
        observed = []

        def advance(_seconds):
            case.service.cancel.assert_not_called()
            raw = pending.pop(0)
            observed.append(raw)
            self.now += 0.01
            if raw is None:
                self.phase.unlink()
            else:
                self.phase.write_bytes(raw)

        def cancel(_identity):
            self.assertFalse(pending, "Cancellation happened before all non-analysis hints")
            self.assertEqual(json.loads(self.phase.read_bytes())["phase"], "analysis")

        case.service.cancel.side_effect = cancel
        with (
            patch.object(sampling.time, "monotonic", side_effect=self.clock),
            patch.object(sampling.time, "sleep", side_effect=advance),
        ):
            case.test_cancel_preserves_all_denominators_and_reconstructs()
        self.assertEqual(len(observed), 5)
        case.service.cancel.assert_called_once_with("job")

    def test_permanently_incomplete_or_non_analysis_hints_never_cancel(self):
        for raw in (b"", b'{"phase":', b'{"status":"started","phase":"snapshot"}'):
            with self.subTest(raw=raw):
                case = self.fixture()
                self.phase.write_bytes(raw)
                self.now = 0

                def advance(_seconds):
                    self.now += 4

                with (
                    patch.object(sampling.time, "monotonic", side_effect=self.clock),
                    patch.object(sampling.time, "sleep", side_effect=advance),
                    self.assertRaisesRegex(AssertionError, "analysis phase not observed"),
                ):
                    case.test_cancel_preserves_all_denominators_and_reconstructs()
                case.service.cancel.assert_not_called()
                case.wait.assert_not_called()
                self.assertGreaterEqual(self.now, 10)

    def test_analysis_hint_while_queued_is_not_permission_for_early_cancellation(self):
        self.phase.write_bytes(b'{"status":"started","phase":"analysis"}')
        states = iter(("queued", "running"))
        with patch.object(sampling.time, "sleep") as sleep:
            sampling.wait_for_analysis(self.phase, lambda: next(states))
        sleep.assert_called_once_with(0.01)

    def test_terminal_job_or_execution_error_cannot_be_an_analysis_observation(self):
        for state in ("completed", "failed", "cancelled"):
            with self.subTest(job=state):
                case = self.fixture()
                self.phase.write_bytes(b'{"status":"started","phase":"analysis"}')
                case.service.get_job.return_value = {"state": state}
                with self.assertRaisesRegex(AssertionError, "ended before analysis"):
                    case.test_cancel_preserves_all_denominators_and_reconstructs()
                case.service.cancel.assert_not_called()
        for status in ("completed", "failed", "interrupted"):
            with self.subTest(execution=status):
                case = self.fixture()
                self.phase.write_text(json.dumps({"status": status, "phase": "analysis"}))
                with self.assertRaisesRegex(AssertionError, "Execution ended before analysis"):
                    case.test_cancel_preserves_all_denominators_and_reconstructs()
                case.service.cancel.assert_not_called()

    def test_permanent_filesystem_error_is_not_retried_or_converted_to_success(self):
        case = self.fixture()
        with (
            patch.object(Path, "read_text", side_effect=PermissionError("synthetic denial")),
            patch.object(sampling.time, "sleep") as sleep,
            self.assertRaises(PermissionError),
        ):
            case.test_cancel_preserves_all_denominators_and_reconstructs()
        sleep.assert_not_called()
        case.service.cancel.assert_not_called()


if __name__ == "__main__":
    unittest.main()
