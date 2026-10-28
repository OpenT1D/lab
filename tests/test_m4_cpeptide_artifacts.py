"""Archive contract tests with hand-authored fixtures; no scientific dependencies.

The synthetic sensitivity metadata here is a parser fixture, not model evidence.
Bolus inventories obey the independently hand-calculated one-compartment limit.
"""

import csv
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from experiments.m4.c_peptide.report import (
    CHECKS,
    COLUMNS,
    SCHEMA,
    SOURCES,
    digest,
    dump,
    read_json,
    reconstruct,
)

ROOT = Path(__file__).resolve().parents[1]


def fixture(directory):
    p = read_json(ROOT / "experiments/m4/c_peptide/protocol.json")
    for profile in p["profiles"].values():
        profile["k1"] = 0
    inputs = {}
    for case in p["cases"]:
        case["input"] = {"edges": [0, 1], "left": [0], "right": [0]}
        if case["name"] != "bolus":
            case["initial"] = {"kind": "zero"}
        for profile, params in p["profiles"].items():
            name = f"{profile}--{case['name']}"
            dose = 100 if case["name"] == "bolus" else 0
            inputs[name] = {
                "forcing": {**case["input"], "units": "pmol/(kg min)"},
                "initial": [dose, 0, 0, 0],
                "evidence": case["evidence"],
            }
            with (directory / f"{name}.csv").open("w", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(COLUMNS)
                for t in (0, 0.5, 1):
                    central = dose * math.exp(-params["k3"] * t)
                    c = central / params["volume_l_kg"]
                    writer.writerow([t, 0, central, 0, dose - central, 0, c, c, c, c, c])
    # Positive nominal parameters are required for log-recovery metadata. The
    # parser fixture uses a separate profile for identification, no forward claim.
    p["profiles"]["t1d_mean"]["k1"] = 0.037
    # The t1d trace now includes a zero peripheral initial and untested dynamics;
    # artifact checks test conservation, while native tests check the ODE itself.
    dump(directory / "protocol.json", p)
    dump(directory / "inputs.json", inputs)
    spec = p["identifiability"]
    nominal = [p["profiles"]["t1d_mean"][k] for k in spec["parameter_order"]]
    count = len(spec["times_min"])
    ident = {
        "schema": "bc003-synthetic-identifiability/1",
        "times_min": spec["times_min"],
        "parameter_order": spec["parameter_order"],
        "dose_pmol_kg": spec["dose_pmol_kg"],
        "nominal_parameters": nominal,
        "observations_pmol_l": [1] * count,
        "sensitivity_matrix_pmol_l": [[1] * 4] * count,
        "joint_sensitivity_matrix_pmol_l": [[1] * 5] * count,
        "sensitivity_refinement_relative_error": 0,
        "amplitude_volume_confounding": [
            {"factor": f, "max_concentration_difference_pmol_l": 0}
            for f in spec["confounding_factors"]
        ],
        "fits": [
            {"start_factors": f, "estimated_parameters": nominal, "predictions_pmol_l": [1] * count}
            for f in spec["recovery_start_factors"]
        ],
        "designs": {},
    }
    for name, n, cols, values in (
        ("full_known_input", count, 4, [4, 3, 2, 1]),
        ("full_unknown_amplitude", count, 5, [4, 3, 2, 1, 0]),
        ("early_known_input", 6, 4, [4, 3, 2, 1]),
        ("sparse_known_input", 3, 4, [4, 3, 2]),
    ):
        ident["designs"][name] = {
            "rows": n,
            "columns": cols,
            "singular_values_pmol_l": values,
            "rank": sum(v > 0 for v in values),
        }
    dump(directory / "identifiability.json", ident)
    dump(
        directory / "verification.json",
        {
            "schema": "bc003-verification/1",
            "protocol": p["id"],
            "passed": True,
            "checks": {k: {"value": 0, "passed": True} for k in CHECKS},
        },
    )
    for name in (
        *[f"source-{s}" for s in SOURCES],
        "source-forcing.py",
        "runtime-uv.lock",
        "runtime-pyproject.toml",
        "report.json",
        "figure.svg",
    ):
        (directory / name).write_text("Parser fixture. Never execute archived source.")
    dump(
        directory / "manifest.json",
        {"schema": SCHEMA, "status": "completed", "model": p["model"], "files": {}},
    )
    rehash(directory)


def rehash(directory):
    manifest = read_json(directory / "manifest.json")
    manifest["files"] = {
        p.name: digest(p) for p in directory.iterdir() if p.name != "manifest.json" and p.is_file()
    }
    dump(directory / "manifest.json", manifest)


class ArtifactTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)
        fixture(self.directory)

    def mutate(self, name, change):
        path = self.directory / name
        data = read_json(path)
        change(data)
        dump(path, data)
        rehash(self.directory)

    def test_standard_library_reconstruction(self):
        self.assertTrue(reconstruct(self.directory)["passed"])
        result = subprocess.run(
            [
                sys.executable,
                "-S",
                "-m",
                "experiments.m4.c_peptide.report",
                str(self.directory),
                "--output",
                str(self.directory / "rebuilt.json"),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_modified_artifact_hash_rejected(self):
        (self.directory / "source-model.py").write_text("modified")
        with self.assertRaisesRegex(ValueError, "Changed/missing"):
            reconstruct(self.directory)

    def test_unfinished_status_rejected(self):
        for status in ("started", "calculated", "failed"):
            self.mutate("manifest.json", lambda d: d.update(status=status))
            with self.assertRaisesRegex(ValueError, "not complete"):
                reconstruct(self.directory)

    def test_missing_case_rejected(self):
        (self.directory / "normal_mean--zero.csv").unlink()
        rehash(self.directory)
        with self.assertRaisesRegex(ValueError, "Incomplete"):
            reconstruct(self.directory)

    def test_truncated_trace_rejected_even_with_updated_hash(self):
        path = self.directory / "normal_mean--bolus.csv"
        path.write_text("\n".join(path.read_text().splitlines()[:-1]) + "\n")
        rehash(self.directory)
        with self.assertRaisesRegex(ValueError, "grid"):
            reconstruct(self.directory)

    def test_false_verification_summary_cannot_hide_failure(self):
        self.mutate("verification.json", lambda d: d["checks"]["mass_balance"].update(value=1))
        self.assertFalse(reconstruct(self.directory)["passed"])

    def test_missing_check_rejected(self):
        self.mutate("verification.json", lambda d: d["checks"].pop("equilibrium"))
        with self.assertRaises(ValueError):
            reconstruct(self.directory)

    def test_boolean_measurement_rejected(self):
        self.mutate("verification.json", lambda d: d["checks"]["equilibrium"].update(value=False))
        with self.assertRaises(ValueError):
            reconstruct(self.directory)

    def test_wrong_units_rejected(self):
        self.mutate("protocol.json", lambda d: d["units"].update(concentration="ng/mL"))
        with self.assertRaisesRegex(ValueError, "units"):
            reconstruct(self.directory)

    def test_changed_fit_parameters_fail_recovery(self):
        self.mutate(
            "identifiability.json", lambda d: d["fits"][0].update(estimated_parameters=[1] * 4)
        )
        self.assertFalse(reconstruct(self.directory)["passed"])

    def test_initial_state_rejected(self):
        self.mutate("inputs.json", lambda d: d["normal_mean--bolus"].update(initial=[99, 0, 0, 0]))
        with self.assertRaisesRegex(ValueError, "initial state"):
            reconstruct(self.directory)

    def test_mass_loss_fails_even_with_updated_hash(self):
        path = self.directory / "normal_mean--bolus.csv"
        with path.open() as stream:
            rows = list(csv.reader(stream))
        rows[-1][4] = "0"
        with path.open("w", newline="") as stream:
            csv.writer(stream).writerows(rows)
        rehash(self.directory)
        self.assertFalse(reconstruct(self.directory)["passed"])

    def test_unsafe_path_and_symlink_rejected(self):
        self.mutate("manifest.json", lambda d: d["files"].update({"../outside": "unused"}))
        # mutate rehashes by design, so add the unsafe entry after that operation.
        path = self.directory / "manifest.json"
        data = read_json(path)
        data["files"]["../outside"] = "unused"
        dump(path, data)
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            reconstruct(self.directory)
        rehash(self.directory)
        target = self.directory / "source-model.py"
        target.unlink()
        target.symlink_to(self.directory / "source-report.py")
        with self.assertRaisesRegex(ValueError, "Changed/missing"):
            reconstruct(self.directory)
