"""Invented input and stateless adapters; no human records or model-quality claim."""

import tomllib

from experiments.m3.external.fixtures import generate

from .common import ROOT, SCHEMA, digest, fresh_directory, read, save

TREND_SOURCE = """def predict(request, settings):
    values = request["values_mg_dl"]
    change = 6 * (values[-1] - values[-2])
    limit = settings["limit_mg_dl"]
    return values[-1] + max(-limit, min(limit, change))
"""
RIDGE_SOURCE = """from experiments.m3.estimator import predict as ridge_predict, validate_model

def predict(request, settings):
    validate_model(settings["model"])
    return ridge_predict(settings["model"], request["values_mg_dl"])
"""


def write_predictor(folder, source, settings, *, name, reference):
    folder.mkdir()
    (folder / "source.py").write_bytes(source.encode("utf-8"))
    save(folder / "settings.json", settings)
    declaration = {
        "schema": "opent1d.m3.forecaster/1",
        "id": name,
        "reference": reference,
        "rights": "self-authored",
        "source": {
            "file": str(folder / "source.py"),
            "sha256": digest((folder / "source.py").read_bytes()),
        },
        "settings": {
            "file": str(folder / "settings.json"),
            "sha256": digest((folder / "settings.json").read_bytes()),
        },
        "training": {"kind": "synthetic", "reference": reference},
        "contract": {
            "history_minutes": [-25, -20, -15, -10, -5, 0],
            "horizon_minutes": 30,
            "unit": "mg/dL",
            "stateless": True,
        },
    }
    save(folder / "declaration.json", declaration)
    return folder / "declaration.json"


def demo_model():
    """Shape-valid invented coefficients, deliberately not a fitted-model claim."""
    lock = tomllib.loads((ROOT / "experiments/m3/runtime/uv.lock").read_text())
    return {
        "method": "sklearn-ridge",
        "settings": {"alpha": 1.0, "fit_intercept": True, "solver": "svd"},
        "mean": [0.0] * 6,
        "scale": [1.0] * 6,
        "coef": [0.0] * 5 + [1.0],
        "intercept": 0.0,
        "feature_rank": 1,
        "singular_values": [1.0],
        "training_counts": {"invented-coefficient-fixture": 1},
        "packages": {p["name"]: p["version"] for p in lock["package"] if "registry" in p["source"]},
    }


def fixture(output, *, ridge_model=None):
    output = fresh_directory(output)
    generate(output / "observations", gaps=True)
    registry, _ = read(output / "observations/registry.json")
    trend = write_predictor(
        output / "trend",
        TREND_SOURCE,
        {"limit_mg_dl": 30.0},
        name="invented-bounded-trend",
        reference="Self-authored bounded trend; no training or human evidence",
    )
    ridge = write_predictor(
        output / "ridge",
        RIDGE_SOURCE,
        {"model": demo_model() if ridge_model is None else ridge_model},
        name="ridge-coefficient-fixture"
        if ridge_model is None
        else "unchanged-synthetic-donor-ridge",
        reference="Invented coefficients exercising existing Ridge arithmetic; "
        "not a fitted reference"
        if ridge_model is None
        else "Unchanged existing AZT1D Ridge fit on invented donor observations",
    )
    config = {
        "schema": SCHEMA,
        "kind": "synthetic",
        "source": registry["source"],
        "prior_access": registry["prior_access"],
        "predictor": str(trend),
        "people": registry["people"],
    }
    save(output / "config.json", config)
    save(output / "ridge-config.json", dict(config, predictor=str(ridge)))
    return config
