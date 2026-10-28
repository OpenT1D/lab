"""Independent M3 numerical, causal, missingness and lifecycle counterexamples."""

import copy
import io
import json
import math
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.m0.simglucose.recording import RunInterrupted
from experiments.m1.artifacts import strict_json
from experiments.m3.analysis import cluster_interval, metrics, validate_point
from experiments.m3.common import ROOT, SCHEMA, digest, finite, provenance, read, save
from experiments.m3.data import (
    blocks,
    history,
    integrate_intervals,
    load_observations,
    observations,
    registry,
    target,
    training_windows,
    validate_conversion,
)
from experiments.m3.estimator import SETTINGS, predict
from experiments.m3.fixtures import generate
from experiments.m3.intake import convert_xml, normalize
from experiments.m3.worker import forecast_rows
from experiments.m3.workflow import fit_plan, supervise


def model():
    lock = tomllib.loads((ROOT / "experiments/m3/runtime/uv.lock").read_text())
    return {
        "method": "sklearn-ridge",
        "settings": SETTINGS,
        "mean": [0] * 6,
        "scale": [1] * 6,
        "coef": [0, 0, 0, 0, 0, 1],
        "intercept": 0,
        "feature_rank": 1,
        "singular_values": [1],
        "training_counts": {"p": 1},
        "packages": {p["name"]: p["version"] for p in lock["package"] if "registry" in p["source"]},
    }


def point(t, value=100, **changes):
    return dict(
        time=t,
        available=t,
        segment="a",
        raw_time=f"synthetic-{t}",
        status="measured",
        value=value,
        bound=None,
        **changes,
    )


def person():
    return {
        "id": "p",
        "source_person": "invented",
        "train": {"start": 0, "end": 500},
        "evaluation": {"start": 600, "end": 800},
    }


class M3Semantics(unittest.TestCase):
    def test_source_person_and_conversion_code_are_bound_before_human_intake(self):
        # Invented metadata exercises the human gate; no human records or authorization.
        person = {"id": "fixture-alias", "source_person": "OhioT1DM:2018:559"}
        receipt = dict(
            schema=SCHEMA,
            kind="human",
            person="fixture-alias",
            source_person="559",
            source_sha256="1" * 64,
            intake_sha256="2" * 64,
            output_sha256="3" * 64,
            provenance=provenance(),
        )
        validate_conversion(receipt, person, "3" * 64)
        for field, replacement in (
            ("person", "another-alias"),
            ("source_person", "563"),
            ("source_person", 559),
            ("intake_sha256", None),
            ("output_sha256", "4" * 64),
            ("provenance", None),
        ):
            changed = dict(receipt, **{field: replacement})
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_conversion(changed, person, "3" * 64)

    def test_strict_required_numbers_and_json_exponent(self):
        for invalid in (True, False, None, "1", math.nan, math.inf, -math.inf):
            with self.subTest(value=repr(invalid)), self.assertRaises((TypeError, ValueError)):
                finite(invalid)
        for invalid in ('{"x":1e999}', '{"x":[-1e999]}', '{"x":NaN}', '{"x":1,"x":2}'):
            with self.assertRaises(ValueError):
                strict_json(invalid)

    def test_independent_units_and_irregular_amounts(self):
        value = {
            "schema": SCHEMA,
            "person": "p",
            "clock": "UTC",
            "unit": "mmol/L",
            "rows": [point(0, 5.5)],
        }
        self.assertEqual(observations(value, "p", "UTC", 0, 5)[0]["value"], 99)
        events = [
            dict(start=0, end=2, kind="basal_command_u_h", status="measured", value=0.6),
            dict(start=2, end=5, kind="basal_command_u_h", status="measured", value=1.2),
            dict(start=5, end=12, kind="basal_command_u_h", status="missing", value=None),
        ]
        result = integrate_intervals(events, 0, 12, "basal_command_u_h")
        # Binary .6/1.2 multiplication and addition differs from exact .08 by one ULP.
        self.assertLessEqual(abs(result["known_amount"] - 0.08), math.ulp(0.08))
        self.assertEqual(result["covered_minutes"], 5)
        self.assertEqual(result["unknown_minutes"], 7)
        self.assertIsNone(integrate_intervals([], 0, 12, "recorded_delivery_u_h")["known_amount"])
        with self.assertRaises(ValueError):
            integrate_intervals(events, 0, 12, "recorded_delivery_u_h")
        with self.assertRaises(ValueError):
            integrate_intervals(events, 0, 12, "bolus_amount_u")

    def test_normalized_numbers_categories_and_clock(self):
        base = {
            "schema": SCHEMA,
            "person": "p",
            "clock": "shifted_local",
            "unit": "mg/dL",
            "rows": [point(0)],
        }
        for field in ("time", "available", "value"):
            for invalid in (True, None, "100", math.inf):
                value = copy.deepcopy(base)
                value["rows"][0][field] = invalid
                with self.assertRaises((ValueError, TypeError)):
                    observations(value, "p", "shifted_local", 0, 10)
        for status in ("missing", "invalid", "censored_low", "censored_high"):
            value = copy.deepcopy(base)
            value["rows"][0].update(
                status=status, value=None, bound=40 if status.startswith("censored") else None
            )
            self.assertEqual(observations(value, "p", "shifted_local", 0, 10)[0]["status"], status)
        for rows in ([point(0), point(0)], [point(5), point(0)]):
            with self.assertRaises(ValueError):
                observations(dict(base, rows=rows), "p", "shifted_local", 0, 10)
        with self.assertRaises(ValueError):
            observations(base, "p", "UTC", 0, 10)

    def test_causal_history_is_unchanged_by_all_future_values(self):
        rows = {t: point(t, 100 + t) for t in range(0, 500, 5)}
        before = history(rows, 100, 0, "development")
        for t in list(rows):
            if t > 100:
                rows[t]["value"] = 500
        self.assertEqual(history(rows, 100, 0, "development"), before)
        rows[100]["available"] = 100.01
        self.assertEqual(history(rows, 100, 0, "development")[1], "history_unavailable")
        rows[100]["available"] = 100
        rows[100]["segment"] = "clock-shift"
        self.assertEqual(history(rows, 100, 0, "development")[1], "clock_discontinuity")

    def test_training_and_initialization_never_cross_splits(self):
        p = person()
        rows = {t: point(t, t + 100) for t in range(0, 800, 5)}
        windows = training_windows(rows, p)
        self.assertTrue(all(o - 25 >= 0 and o + 30 < 400 for o, _, _ in windows))
        self.assertEqual(history(rows, 400, 400, "validation")[1], "history_outside_split")
        self.assertEqual(history(rows, 655, 600, "evaluation")[1], "evaluation_warmup")
        self.assertIsNotNone(history(rows, 660, 600, "evaluation")[0])
        self.assertEqual(target(rows, 770, 800)["status"], "outside_split")
        self.assertEqual(blocks(p)["development"], (0, 400))
        rows[395]["available"] = 401
        self.assertNotIn(365, [o for o, _, _ in training_windows(rows, p)])

    def test_future_missing_target_does_not_suppress_forecast(self):
        p = person()
        rows = {t: point(t) for t in range(600, 800, 5)}
        rows[690].update(status="censored_high", value=None, bound=400)
        stream = io.StringIO()
        forecast_rows(rows, p, "evaluation", model(), stream)
        saved = [json.loads(line) for line in stream.getvalue().splitlines()]
        row = next(r for r in saved if r["origin"] == 660)
        self.assertEqual(row["forecasts"], {"ridge": 100, "persistence": 100})
        self.assertEqual(metrics([row], "ridge")["censored_count"], 1)
        self.assertEqual(metrics([row], "ridge")["mean_censored_absolute_error_lower_bound"], 300)
        self.assertIsNone(metrics([row], "ridge")["mae"])
        validate_point(row, p, "evaluation", model(), 660)
        row["history_rows"][-1]["available"] = 661
        with self.assertRaisesRegex(ValueError, "Causal"):
            validate_point(row, p, "evaluation", model(), 660)

    def test_metrics_are_point_errors_and_clustered_by_person(self):
        rows = [
            {
                "forecasts": {"ridge": 110},
                "target": {"status": "measured", "value": 100, "bound": None},
            },
            {
                "forecasts": {"ridge": 80},
                "target": {"status": "measured", "value": 100, "bound": None},
            },
        ]
        result = metrics(rows, "ridge")
        self.assertEqual(result["mae"], 15)
        self.assertEqual(result["bias"], -5)
        self.assertEqual(result["rmse"], math.sqrt(250))
        self.assertEqual(cluster_interval([1, 1, 1, 1]), [1, 1])
        self.assertIsNone(cluster_interval([1]))
        self.assertEqual(cluster_interval([0, 10]), [0, 10])
        rows[0]["forecasts"]["ridge"] = 1e308
        with self.assertRaises(ValueError):
            metrics(rows, "ridge")

    def test_registry_rejects_person_and_file_overlap_and_rights(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "input"
            generate(root)
            base, _ = registry(root / "registry.json")
            for mutation in ("person", "time", "file", "rights", "boolean"):
                value = copy.deepcopy(base)
                if mutation == "person":
                    value["people"][1]["source_person"] = value["people"][0]["source_person"]
                if mutation == "time":
                    value["people"][0]["evaluation"]["start"] = 0
                if mutation == "file":
                    value["people"][1]["train"]["file"] = value["people"][0]["train"]["file"]
                if mutation == "rights":
                    value.update(kind="human", source="OhioT1DM-2018")
                if mutation == "boolean":
                    value["rights"] = {"synthetic": 1}
                save(root / "bad.json", value)
                with self.assertRaises(ValueError):
                    registry(root / "bad.json")
            p = base["people"][0]
            load_observations(root, p, "train", base["clock"])
            with (root / p["train"]["file"]).open("a") as f:
                f.write(" ")
            with self.assertRaisesRegex(ValueError, "bytes changed"):
                load_observations(root, p, "train", base["clock"])

    def test_stateless_predictions_do_not_carry_people(self):
        m = model()
        a = predict(m, [10] * 6)
        predict(m, [500] * 6)
        self.assertEqual(predict(m, [10] * 6), a)
        self.assertEqual(a, 10)

    def test_conservative_xml_is_not_native_release_validation(self):
        raw = (
            b'<patient id="fixture" weight="99"><glucose_level>'
            b'<event ts="01-01-2024 00:00:00" value="100"/>'
            b'<event ts="01-01-2024 00:07:30" value="0"/>'
            b"</glucose_level><meal/></patient>"
        )
        converted = convert_xml(
            raw, person="p", source_person="fixture", origin_local="01-01-2024 00:00:00"
        )
        self.assertEqual(converted["clock"], "shifted_local")
        self.assertEqual(converted["rows"][1]["time"], 7.5)
        self.assertEqual(converted["rows"][1]["status"], "invalid")
        self.assertIsNone(converted["rows"][1]["value"])
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "source.xml").write_bytes(raw)
            save(
                root / "intake.json",
                dict(
                    kind="synthetic",
                    person="p",
                    source_person="fixture",
                    origin_local="01-01-2024 00:00:00",
                    source_sha256=digest(raw),
                ),
            )
            normalize(root / "source.xml", root / "intake.json", root / "converted")
            receipt, _ = read(root / "converted/conversion.json")
            self.assertEqual(receipt["source_person"], "fixture")
            self.assertEqual(receipt["person"], "p")
            self.assertEqual(receipt["source_sha256"], digest(raw))
            self.assertEqual(receipt["intake_sha256"], digest((root / "intake.json").read_bytes()))
            self.assertEqual(
                receipt["output_sha256"],
                digest((root / "converted/observations.json").read_bytes()),
            )
            self.assertEqual(receipt["provenance"]["sources"], provenance()["sources"])
        for changed in (
            raw.replace(b'value="100"', b'value="NaN"'),
            raw.replace(b'value="100"', b'value="1e999"'),
            raw.replace(b'value="100"', b'value="100" flag="high"'),
            b"<!DOCTYPE x>" + raw,
        ):
            with self.assertRaises(ValueError):
                convert_xml(
                    changed, person="p", source_person="fixture", origin_local="01-01-2024 00:00:00"
                )


class M3Lifecycle(unittest.TestCase):
    def test_conversion_failure_retains_status_without_raw_exception_text(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "input.xml").write_bytes(b"synthetic malformed input")
            save(root / "intake.json", {"kind": "synthetic", "source_sha256": "0" * 64})
            with self.assertRaisesRegex(ValueError, "Native input bytes changed"):
                normalize(root / "input.xml", root / "intake.json", root / "output")
            state, _ = read(root / "output/status.json")
            self.assertEqual(state["status"], "failed")
            self.assertEqual(state["error"]["type"], "ValueError")

    def test_fit_finalization_failure_is_not_completed(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "fit"
            output.mkdir()
            save(output / "state.json", {"status": "completed"})
            with (
                patch(
                    "experiments.m3.workflow.plan_read", return_value=({"kind": "synthetic"}, "sha")
                ),
                patch("experiments.m3.workflow.supervise"),
                self.assertRaises(FileNotFoundError),
            ):
                fit_plan(Path(temp) / "plan.json", output)
            state, _ = read(output / "state.json")
            self.assertEqual(state["status"], "failed")
            self.assertEqual(state["error"]["type"], "FileNotFoundError")

    def test_provenance_initialization_failure_has_empty_output(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "failed"
            with (
                patch("experiments.m3.workflow.provenance", side_effect=OSError("initialization")),
                self.assertRaisesRegex(OSError, "initialization"),
            ):
                supervise(["unused"], output, 1)
            state, _ = read(output / "state.json")
            self.assertEqual(state["stage"], "initializing")
            self.assertEqual(state["status"], "failed")
            self.assertNotIn("provenance", state)
            self.assertEqual((output / "trace.jsonl").read_bytes(), b"")

    def test_failed_diagnostic_preserves_primary_exception(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch("experiments.m3.workflow.subprocess.Popen", side_effect=OSError("primary")):
                with self.assertRaisesRegex(OSError, "primary"):
                    supervise(
                        ["absent"],
                        Path(temp) / "run",
                        30,
                        diagnostic=lambda *_: (_ for _ in ()).throw(RuntimeError("secondary")),
                    )
            state, _ = read(Path(temp) / "run/state.json")
            self.assertEqual(state["error"]["type"], "OSError")
            self.assertEqual(state["diagnostic_error"]["type"], "RuntimeError")
            self.assertEqual((Path(temp) / "run/trace.jsonl").read_bytes(), b"")

    def test_real_deadline_preserves_written_partial_and_isolates_next_run(self):
        command = [
            sys.executable,
            "-c",
            "import sys,time;from pathlib import Path;"
            'p=Path(sys.argv[1]);(p/"trace.jsonl").write_text("checkpoint\\n");time.sleep(30)',
        ]
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "timeout"
            with self.assertRaises((RunInterrupted, subprocess.TimeoutExpired)):
                supervise(command, output, 1)
            self.assertEqual((output / "trace.jsonl").read_text(), "checkpoint\n")
            self.assertEqual(read(output / "state.json")[0]["status"], "interrupted")
            with self.assertRaises(FileExistsError):
                supervise(command, output, 1)
            with self.assertRaises(FileNotFoundError):
                supervise(["/missing/worker"], Path(temp) / "initial-failure", 2)
            self.assertEqual((Path(temp) / "initial-failure/trace.jsonl").read_bytes(), b"")

    def test_worker_success_requires_matching_exit_status(self):
        command = [
            sys.executable,
            "-c",
            "import sys;from pathlib import Path;"
            '(Path(sys.argv[1])/"result.json").write_text(\'{"status":"completed"}\');sys.exit(7)',
        ]
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, "exit/status"):
                supervise(command, Path(temp) / "run", 5)
