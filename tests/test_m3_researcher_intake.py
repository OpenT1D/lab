"""Strict source identity, causal callback and isolated JSONL predictor checks."""

import copy
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from experiments.m3.common import ROOT, digest
from experiments.m3.researcher.intake import (
    HISTORY_MINUTES,
    MAX_DECLARATION_BYTES,
    MAX_SETTINGS_BYTES,
    MAX_SOURCE_BYTES,
    SCHEMA,
    load_declaration,
    read_regular,
    validate_bundle,
    validate_declaration,
)
from experiments.m3.researcher.predictor import (
    MAX_REQUEST_BYTES,
    MINUTE_US,
    SuppliedPredictor,
    run,
    validate_prediction,
    validate_request,
)

SOURCE = (
    b"def predict(request, settings):\n"
    b"    return request['values_mg_dl'][-1] + settings['offset']\n"
)


def request():
    origin = 60 * MINUTE_US
    return {
        "origin_us": origin,
        "times_us": [origin + minute * MINUTE_US for minute in HISTORY_MINUTES],
        "values_mg_dl": [100.0, 105.0, 110.0, 115.0, 120.0, 125.0],
    }


def bundle(root, source=SOURCE, settings=b'{ "offset": 7.0 }\n'):
    root = Path(root).resolve()
    source_path, settings_path = root / "forecast.py", root / "settings.json"
    source_path.write_bytes(source)
    settings_path.write_bytes(settings)
    declaration = {
        "schema": SCHEMA,
        "id": "invented_forecaster",
        "reference": "Self-authored synthetic arithmetic test",
        "rights": "self-authored",
        "source": {"file": str(source_path), "sha256": digest(source)},
        "settings": {"file": str(settings_path), "sha256": digest(settings)},
        "training": {"kind": "synthetic", "reference": "No training; invented fixed settings"},
        "contract": {
            "history_minutes": list(HISTORY_MINUTES),
            "horizon_minutes": 30,
            "unit": "mg/dL",
            "stateless": True,
        },
    }
    declaration_path = root / "declaration.json"
    declaration_path.write_text(json.dumps(declaration))
    return declaration_path, declaration, source, settings


class ResearcherIntakeTests(unittest.TestCase):
    def test_load_preserves_original_source_and_settings_bytes(self):
        with tempfile.TemporaryDirectory() as root:
            path, declaration, source, settings = bundle(root)
            self.assertEqual(load_declaration(path), (declaration, source, settings))
            self.assertEqual(validate_bundle(declaration, source, settings), {"offset": 7.0})

    def test_changed_source_and_even_equivalent_settings_are_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            path, declaration, source, settings = bundle(root)
            for changed_source, changed_settings, message in (
                (source + b"# changed\n", settings, "Source hash mismatch"),
                (source, b'{"offset":7.0}', "Settings hash mismatch"),
            ):
                with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                    validate_bundle(declaration, changed_source, changed_settings)
            Path(declaration["source"]["file"]).write_bytes(source + b"# changed\n")
            with self.assertRaisesRegex(ValueError, "Source hash mismatch"):
                load_declaration(path)
            Path(declaration["source"]["file"]).write_bytes(source)
            Path(declaration["settings"]["file"]).write_bytes(b'{"offset":8}')
            with self.assertRaisesRegex(ValueError, "Settings hash mismatch"):
                load_declaration(path)

    def test_strict_settings_and_python_syntax(self):
        with tempfile.TemporaryDirectory() as root:
            for settings in (b"[]", b'{"offset": NaN}', b'{"x": 1e999}', b'{"x":1,"x":2}'):
                with self.subTest(settings=settings):
                    path, *_ = bundle(root, settings=settings)
                    with self.assertRaises(ValueError):
                        load_declaration(path)
            path, *_ = bundle(root, source=b"def predict(:\n")
            with self.assertRaisesRegex(ValueError, "Invalid forecaster Python source"):
                load_declaration(path)

    def test_exact_declaration_and_contract_fields(self):
        with tempfile.TemporaryDirectory() as root:
            _, declaration, *_ = bundle(root)
            changes = (
                ((), "schema", "unsupported"),
                ((), "id", "invalid id"),
                ((), "reference", "  "),
                ((), "rights", "unknown"),
                ((), "extra", "future capability"),
                (("source",), "file", "relative.py"),
                (("source",), "sha256", "A" * 64),
                (("source",), "extra", "ignored"),
                (("settings",), "sha256", "short"),
                (("training",), "kind", "human"),
                (("training",), "reference", ""),
                (("contract",), "history_minutes", [-25, -20, -15, -10, -5, False]),
                (("contract",), "horizon_minutes", 30.0),
                (("contract",), "unit", "mmol/L"),
                (("contract",), "stateless", 1),
                (("contract",), "extra", True),
            )
            for keys, field, value in changes:
                with self.subTest(keys=keys, field=field, value=value):
                    changed = copy.deepcopy(declaration)
                    target = changed
                    for key in keys:
                        target = target[key]
                    target[field] = value
                    with self.assertRaises(ValueError):
                        validate_declaration(changed)

    def test_symlinks_and_nonregular_inputs_refused_without_executing(self):
        with tempfile.TemporaryDirectory() as root:
            path, declaration, *_ = bundle(root)
            for target in (
                path,
                Path(declaration["source"]["file"]),
                Path(declaration["settings"]["file"]),
            ):
                with self.subTest(target=target):
                    real = target.with_suffix(".actual")
                    target.rename(real)
                    target.symlink_to(real)
                    with self.assertRaisesRegex(ValueError, "Symlink"):
                        load_declaration(path)
                    target.unlink()
                    real.rename(target)
            link = Path(root) / "directory-link"
            link.symlink_to(Path(root).resolve(), target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "Symlink"):
                read_regular(link / "forecast.py", MAX_SOURCE_BYTES, "source")
            fifo = Path(root) / "fifo"
            os.mkfifo(fifo)
            with self.assertRaisesRegex(ValueError, "regular file"):
                read_regular(fifo, MAX_SOURCE_BYTES, "source")
            with self.assertRaisesRegex(ValueError, "regular file"):
                read_regular(root, MAX_SOURCE_BYTES, "source")

    def test_file_byte_limits(self):
        with tempfile.TemporaryDirectory() as root:
            path, declaration, *_ = bundle(root)
            for target, limit in (
                (path, MAX_DECLARATION_BYTES),
                (Path(declaration["source"]["file"]), MAX_SOURCE_BYTES),
                (Path(declaration["settings"]["file"]), MAX_SETTINGS_BYTES),
            ):
                with self.subTest(target=target):
                    before = target.read_bytes()
                    target.write_bytes(b" " * (limit + 1))
                    with self.assertRaisesRegex(ValueError, "byte limit"):
                        load_declaration(path)
                    target.write_bytes(before)

    def test_load_does_not_execute_source(self):
        with tempfile.TemporaryDirectory() as root:
            marker = Path(root) / "executed"
            source = f"open({str(marker)!r}, 'w').write('executed')\n".encode()
            path, *_ = bundle(root, source=source)
            load_declaration(path)
            self.assertFalse(marker.exists())


class ResearcherPredictorTests(unittest.TestCase):
    def test_exact_causal_inputs_and_numeric_validation(self):
        good = request()
        self.assertIs(validate_request(good), good)
        for key, value in (
            ("origin_us", True),
            ("origin_us", -1),
            ("origin_us", float(good["origin_us"])),
            ("times_us", good["times_us"][:-1] + [good["origin_us"] + 1]),
            ("times_us", good["times_us"][:-1] + [float(good["origin_us"])]),
            ("times_us", list(reversed(good["times_us"]))),
            ("times_us", good["times_us"][:-1]),
            ("times_us", good["times_us"][:-1] + [True]),
            ("values_mg_dl", good["values_mg_dl"][:-1]),
            ("target_mg_dl", 140),
            ("person", "invented"),
        ):
            with self.subTest(key=key, value=value):
                changed = copy.deepcopy(good)
                changed[key] = value
                with self.assertRaises(ValueError):
                    validate_request(changed)
        for value in (True, None, "125", 0, -1, float("nan"), float("inf"), 10**400):
            with self.subTest(value=value):
                changed = copy.deepcopy(good)
                changed["values_mg_dl"][-1] = value
                with self.assertRaises(ValueError):
                    validate_request(changed)
        changed = copy.deepcopy(good)
        changed["origin_us"] = 0
        changed["times_us"] = [minute * MINUTE_US for minute in HISTORY_MINUTES]
        with self.assertRaisesRegex(ValueError, "causal five-minute"):
            validate_request(changed)

    def test_prediction_preserves_negative_values_and_rejects_invalid_scalars(self):
        self.assertEqual(validate_prediction(-13.5), -13.5)
        self.assertEqual(validate_prediction(0), 0)
        for value in (
            True,
            False,
            None,
            "125",
            [125],
            {"prediction": 125},
            float("nan"),
            float("inf"),
            10**400,
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_prediction(value)

    def test_mutated_request_and_settings_do_not_change_later_calls(self):
        source = (
            b"def predict(request, settings):\n"
            b"    result = request['values_mg_dl'][-1] + settings['nested']['offset'][0]\n"
            b"    request['values_mg_dl'][-1] = 999\n"
            b"    settings['nested']['offset'][0] = 999\n"
            b"    return result\n"
        )
        settings = {"nested": {"offset": [7.0]}}
        supplied = SuppliedPredictor(source, settings)
        original_request = request()
        for _ in range(2):
            self.assertEqual(supplied.predict(original_request), 132.0)
        self.assertEqual(original_request, request())
        self.assertEqual(settings, {"nested": {"offset": [7.0]}})

    def test_callback_signature_and_finite_result_are_required(self):
        with self.assertRaisesRegex(ValueError, "expose predict"):
            SuppliedPredictor(b"predict = 4\n", {})
        with self.assertRaises(TypeError):
            SuppliedPredictor(b"def predict(): return 125\n", {}).predict(request())
        with self.assertRaisesRegex(ValueError, "finite scalar"):
            SuppliedPredictor(b"def predict(request, settings): return True\n", {}).predict(
                request()
            )

    def test_worker_arithmetic_jsonl_and_stdout_chatter_isolation(self):
        source = (
            b"print('module chatter')\n"
            b"def predict(request, settings):\n"
            b"    print('callback chatter')\n"
            b"    return request['values_mg_dl'][-1] + settings['offset']\n"
        )
        with tempfile.TemporaryDirectory() as root:
            _, declaration, *_ = bundle(root, source=source)
            result = subprocess.run(
                [
                    sys.executable,
                    "-S",
                    "-m",
                    "experiments.m3.researcher.predictor",
                    declaration["source"]["file"],
                    declaration["settings"]["file"],
                ],
                input=(json.dumps(request()) + "\n") * 2,
                capture_output=True,
                text=True,
                timeout=10,
                cwd=ROOT,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                [json.loads(line) for line in result.stdout.splitlines()],
                [{"prediction": 132.0}] * 2,
            )
            self.assertIn("module chatter", result.stderr)
            self.assertEqual(result.stderr.count("callback chatter"), 2)

    def test_source_exception_never_emits_its_private_message(self):
        source = (
            b"def predict(request, settings):\n    raise ValueError('private synthetic marker')\n"
        )
        with tempfile.TemporaryDirectory() as root:
            _, declaration, *_ = bundle(root, source=source)
            result = subprocess.run(
                [
                    sys.executable,
                    "-S",
                    "-m",
                    "experiments.m3.researcher.predictor",
                    declaration["source"]["file"],
                    declaration["settings"]["file"],
                ],
                input=json.dumps(request()) + "\n",
                capture_output=True,
                text=True,
                timeout=10,
                cwd=ROOT,
            )
            self.assertEqual(result.returncode, 1)
            self.assertEqual(json.loads(result.stdout), {"error_type": "ValueError"})
            self.assertEqual(result.stderr, "Forecast worker failed (ValueError)\n")
            self.assertNotIn("private synthetic marker", result.stderr)

    def test_jsonl_record_byte_limit_newline_and_duplicate_fields(self):
        with tempfile.TemporaryDirectory() as root:
            _, declaration, *_ = bundle(root)
            for line in (
                b" " * MAX_REQUEST_BYTES + b"\n",
                json.dumps(request()).encode(),
                b'{"origin_us":1,"origin_us":2}\n',
            ):
                with self.subTest(line=line[:100]), self.assertRaises(ValueError):
                    run(
                        declaration["source"]["file"],
                        declaration["settings"]["file"],
                        io.BytesIO(line),
                        io.StringIO(),
                    )


if __name__ == "__main__":
    unittest.main()
