"""Explicit invented preparation reusing the existing two predictor structures."""

from experiments.m3.common import read
from experiments.m3.researcher.fixtures import fixture as researcher_fixture

from .common import SCHEMA, save


def fixture(output, *, ridge_model=None):
    base = researcher_fixture(output, ridge_model=ridge_model)
    from pathlib import Path

    output = Path(output).absolute()
    ridge, _ = read(output / "ridge-config.json")
    declarations = [base["predictor"], ridge["predictor"]]
    config = {
        "schema": SCHEMA,
        **{key: base[key] for key in ("kind", "source", "prior_access", "people")},
        "candidates": [{"id": read(path)[0]["id"], "declaration": path} for path in declarations],
        "timeout_seconds": 120,
    }
    save(output / "comparison.json", config)
    return config
