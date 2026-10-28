"""Invented observations and hand-authored coefficients; never a fitted human model."""

import tomllib

from experiments.m3.azt1d.common import SCHEMA as OBSERVATION_SCHEMA
from experiments.m3.common import ROOT
from experiments.m3.estimator import SETTINGS

from .common import MINUTE, SECOND

FIXTURE = "invented-timing-example/1"


def model():
    """Use the historical parameter shape solely to test unchanged arithmetic.

    Rank/count/package fields satisfy the existing model contract. They describe
    test metadata, not an executed training job or use of scikit-learn here.
    """
    lock = tomllib.loads((ROOT / "experiments/m3/runtime/uv.lock").read_text())
    return {
        "method": "sklearn-ridge",
        "settings": dict(SETTINGS),
        "mean": [100.0] * 6,
        "scale": [20.0] * 6,
        "coef": [-2.0, -1.0, 0.0, 1.0, 3.0, 19.0],
        "intercept": 100.0,
        "feature_rank": 0,
        "singular_values": [0.0] * 6,
        "training_counts": {"invented-no-fit": 1},
        "packages": {
            package["name"]: package["version"]
            for package in lock["package"]
            if "registry" in package["source"]
        },
    }


def observations():
    """Regular, one-second and four-second blocks with selected gaps/statuses."""
    documents = {}
    for person, length in (("invented-a", 840), ("invented-b", 900)):
        rows = []
        for index in range(length):
            if index in (449, 630):
                continue
            jitter = (index % 2) * SECOND if 360 <= index < 600 else 0
            if 600 <= index < 780:
                jitter = (index % 2) * 4 * SECOND
            time = index * 5 * MINUTE + jitter
            status = {483: "ambiguous", 704: "censored_low"}.get(index, "measured")
            rows.append(
                {
                    "time_us": time,
                    "available_us": time,
                    "segment": "invented-clock",
                    "raw_time": f"invented-row-{index}",
                    "status": status,
                    "value": float(100 + 2 * (index % 20) + index // 50 % 3)
                    if status == "measured"
                    else None,
                    "bound": None,
                    "source_rows": [index + 1],
                }
            )
        documents[person] = {
            "schema": OBSERVATION_SCHEMA,
            "person": person,
            "clock": "local_elapsed",
            "unit": "mg/dL",
            "bounds_us": [0, rows[-1]["time_us"] + 5 * MINUTE],
            "rows": rows,
        }
    return documents
