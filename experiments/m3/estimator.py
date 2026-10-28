"""Existing scikit-learn estimator; imported only inside the isolated fit worker."""

import importlib.metadata
import tomllib

from .common import ROOT, finite, require

SETTINGS = {"alpha": 1.0, "fit_intercept": True, "solver": "svd"}


def packages():
    lock = tomllib.loads((ROOT / "experiments/m3/runtime/uv.lock").read_text())
    expected = {p["name"]: p["version"] for p in lock["package"] if "registry" in p["source"]}
    actual = {name: importlib.metadata.version(name) for name in expected}
    require(actual == expected, "Installed estimator packages differ from lock")
    return actual


def fit(samples):
    import numpy as np
    from sklearn.linear_model import Ridge
    from sklearn.preprocessing import StandardScaler

    require(
        samples and all(samples.values()), "Every planned person needs eligible development windows"
    )
    x, y, weights = [], [], []
    for windows in samples.values():
        for _, features, value in windows:
            x.append(features)
            y.append(value)
            weights.append(1 / len(windows))
    scaler = StandardScaler().fit(x, sample_weight=weights)
    scaled = scaler.transform(x)
    model = Ridge(**SETTINGS).fit(scaled, y, sample_weight=weights)
    fitted = {
        "method": "sklearn-ridge",
        "settings": SETTINGS,
        "mean": scaler.mean_.tolist(),
        "scale": scaler.scale_.tolist(),
        "coef": model.coef_.tolist(),
        "intercept": float(model.intercept_),
        "feature_rank": int(np.linalg.matrix_rank(scaled)),
        "singular_values": np.linalg.svd(scaled, compute_uv=False).tolist(),
        "training_counts": {p: len(w) for p, w in samples.items()},
        "packages": packages(),
    }
    validate_model(fitted)
    return fitted


def validate_model(model):
    require(
        isinstance(model, dict) and model.get("method") == "sklearn-ridge", "Missing fitted model"
    )
    require(model.get("settings") == SETTINGS, "Estimator settings changed")
    finite(model["settings"]["alpha"], "ridge alpha", 0)
    require(model["settings"]["fit_intercept"] is True, "Intercept setting changed")
    for field in ("mean", "scale", "coef"):
        require(
            isinstance(model.get(field), list) and len(model[field]) == 6,
            "Invalid fitted feature dimensions",
        )
        for value in model[field]:
            finite(value, "fitted coefficient")
    require(all(v > 0 for v in model["scale"]), "Invalid scale")
    finite(model.get("intercept"), "intercept")
    require(
        type(model.get("feature_rank")) is int and 0 <= model["feature_rank"] <= 6,
        "Missing rank diagnostic",
    )
    require(
        isinstance(model.get("singular_values"), list) and model["singular_values"],
        "Missing singular values",
    )
    for value in model["singular_values"]:
        finite(value, "singular value", 0)
    counts = model.get("training_counts")
    require(
        isinstance(counts, dict)
        and counts
        and all(type(n) is int and n > 0 for n in counts.values()),
        "Missing training coverage",
    )
    lock = tomllib.loads((ROOT / "experiments/m3/runtime/uv.lock").read_text())
    expected = {p["name"]: p["version"] for p in lock["package"] if "registry" in p["source"]}
    require(model.get("packages") == expected, "Missing or changed estimator package provenance")


def predict(model, features):
    require(len(features) == 6, "Six features required")
    for value in features:
        finite(value, "feature", 0)
    value = model["intercept"] + sum(
        c * ((x - m) / s)
        for c, x, m, s in zip(model["coef"], features, model["mean"], model["scale"], strict=True)
    )
    return finite(value, "forecast")
