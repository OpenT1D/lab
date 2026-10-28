"""C1 development config and audit checks need no simulator dependency."""

import json
import unittest
from pathlib import Path

from experiments.c1.report import replay_commands, validate_command
from experiments.c1.simglucose_dev import Config
from experiments.m1.contracts import Row

ROOT = Path(__file__).resolve().parents[1]


def example(method="trend_overlay"):
    path = (
        ROOT
        / "experiments/c1"
        / f"simglucose-{'overlay' if method == 'trend_overlay' else 'pid'}.example.json"
    )
    return json.loads(path.read_text())


class C1DevelopmentTest(unittest.TestCase):
    def test_examples_are_known_development_cases(self):
        overlay = Config.parse(example())
        pid = Config.parse(example("bounded_pid"))
        self.assertEqual(
            (overlay.profile, overlay.condition, overlay.method),
            ("adult#001", "B", "trend_overlay"),
        )
        self.assertEqual(pid.method, "bounded_pid")
        self.assertEqual(overlay.settings, pid.settings)

    def test_evaluation_profile_and_incomplete_settings_rejected(self):
        value = example()
        value["profile"] = "adult#003"
        with self.assertRaises(ValueError):
            Config.parse(value)
        value = example()
        del value["settings"]["max_total_u_h"]
        with self.assertRaises(ValueError):
            Config.parse(value)

    def test_command_audit_cannot_hide_masked_correction_or_bolus_change(self):
        cfg = Config.parse(example())
        row = Row(0, 3, 140, 140, True, 140, 0, 0, 0, 1 / 60, 0, 1 / 60, False)
        command = {
            "time_min": 0,
            "controller_source_min": 0,
            "controller_cgm_mg_dl": 140,
            "sensor_available": True,
            "announced_g": 0,
            "base_basal_u_h": 1,
            "base_bolus_u_min": 0,
            "final_basal_u_h": 1,
            "final_bolus_u_min": 0,
            "reason": "no_recent_rise",
            "extra_u_h": 0,
            "inventory_u": 0,
            "rise_mg_dl_min": 0,
        }
        validate_command(command, row, cfg)
        changed = dict(command, final_bolus_u_min=0.01)
        with self.assertRaises(ValueError):
            validate_command(changed, row, cfg)
        held_row = Row(3, 6, 140, 140, True, 140, 0, 0, 0, 1.1 / 60, 0, 1.1 / 60, False)
        held = dict(
            command,
            time_min=3,
            controller_source_min=0,
            sensor_available=False,
            final_basal_u_h=1.1,
            extra_u_h=0.1,
        )
        with self.assertRaises(ValueError):
            validate_command(held, held_row, cfg)

    def test_offline_state_replay_detects_a_rewritten_command(self):
        cfg = Config.parse(example())
        row = Row(0, 3, 140, 140, True, 140, 0, 0, 0, 1 / 60, 0, 1 / 60, False)
        command = {
            "time_min": 0,
            "controller_source_min": 0,
            "controller_cgm_mg_dl": 140,
            "sensor_available": True,
            "announced_g": 0,
            "base_basal_u_h": 1,
            "base_bolus_u_min": 0,
            "final_basal_u_h": 1,
            "final_bolus_u_min": 0,
            "reason": "no_recent_rise",
            "extra_u_h": 0,
            "inventory_u": 0,
            "rise_mg_dl_min": 0,
        }
        replay_commands([row], [command], cfg)
        with self.assertRaises(ValueError):
            replay_commands([row], [dict(command, reason="bounded_rise")], cfg)

        pid = Config.parse(example("bounded_pid"))
        pid_command = {
            k: v
            for k, v in command.items()
            if k not in ("extra_u_h", "inventory_u", "rise_mg_dl_min")
        }
        first_pid_correction = (0.001 * 140 / 3) * 60
        pid_command.update(
            reason="bounded_pid",
            pid_correction_u_h=first_pid_correction,
            requested_u_h=1 + first_pid_correction,
            final_basal_u_h=1 + first_pid_correction,
        )
        replay_commands([row], [pid_command], pid)
        with self.assertRaises(ValueError):
            replay_commands([row], [dict(pid_command, pid_correction_u_h=0.1)], pid)


if __name__ == "__main__":
    unittest.main()
