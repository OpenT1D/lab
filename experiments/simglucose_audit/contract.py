"""Strict data contracts shared by the invented consumer and its trusted reader."""

import hashlib
import json
import math
import sys
from pathlib import Path

STEP = 180000
HORIZON = 1800000
UPSTREAM = "a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc"
CONFIG_SCHEMA = "opent1d.simglucose-audit1-fixture/1"
REPORT_SCHEMA = "opent1d.simglucose-audit1-fixture-result/1"
SOURCE_FILES = (
    "__init__.py",
    "__main__.py",
    "bootstrap.py",
    "contract.py",
    "fixture_time.py",
    "consumer.py",
    "_fixture.py",
    "reference.py",
    "reader.py",
    "runtime_sources.py",
    "worker_fixture.py",
    "worker_journal.py",
    "compat_fixture.py",
    "intake_collector.py",
    "source-contract.json",
)
RESOURCES = {
    "params/vpatient_params.csv",
    "params/sensor_params.csv",
    "params/pump_params.csv",
}
AUTHORITY = {
    "runtime_risk_accepted": False,
    "asset_use_approved": False,
    "setup_authorized": False,
    "native_execution_authorized": False,
    "removal_authorized": False,
    "exports_authorized": False,
    "new_authority_granted": False,
    "native_execution_deferred": True,
}


def require(value, reason):
    if not value:
        raise ValueError(reason)


def fields(value, names, reason):
    require(type(value) is dict and set(value) == set(names.split()), reason)


def integer(value, reason, minimum=0):
    require(type(value) is int and value >= minimum, reason)
    return value


def number(value, reason, minimum=0):
    require(type(value) in (int, float), reason)
    try:
        result = float(value)
    except OverflowError as error:
        raise ValueError(reason) from error
    require(math.isfinite(result) and result >= minimum, reason)
    return result


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(raw):
    require(type(raw) is bytes, "raw-bytes")
    return hashlib.sha256(raw).hexdigest()


def decode(raw):
    require(type(raw) is bytes and 0 < len(raw) <= 1024 * 1024, "bounded-json-bytes")

    def unique(pairs):
        result = {}
        for name, value in pairs:
            require(name not in result, "duplicate-json-field")
            result[name] = value
        return result

    def constant(_):
        raise ValueError("nonfinite-json")

    return json.loads(raw, object_pairs_hook=unique, parse_constant=constant)


def source_identity():
    """Fixed local code only; report fields never select paths or executable code."""
    root = Path(__file__).parent
    parent = sys.modules["experiments"]
    initializer = root.parent / "__init__.py"
    require(
        not initializer.exists()
        and not initializer.is_symlink()
        and parent.__file__ is None
        and set(parent.__path__) == {str(root.parent)},
        "fixed-parent-namespace-without-initializer",
    )
    return {name: digest((root / name).read_bytes()) for name in SOURCE_FILES} | {
        "experiments/__init__.py": "namespace-initializer-absent"
    }


def source_contract():
    return decode((Path(__file__).parent / "source-contract.json").read_bytes())


def default_config():
    return {
        "schema": CONFIG_SCHEMA,
        "kind": "invented",
        "variant": "filtered",
        "basal_u_h": 1.2,
        "samples": [120, 180, 60, 150, 170, 130, 125, 110, 140, 135, 155],
        "delivered_rates_u_min": [0.018, 0.020, 0.025, 0.019, 0.021] * 2,
        "initial_history_cgm": 119,
        "fault": "none",
        "close_error": False,
    }


def validate_config(value):
    fields(
        value,
        "schema kind variant basal_u_h samples delivered_rates_u_min initial_history_cgm "
        "fault close_error",
        "fixture-fields",
    )
    require(value["schema"] == CONFIG_SCHEMA and value["kind"] == "invented", "fixture-only")
    require(value["variant"] in ("filtered", "unfiltered", "future80", "fasting"), "variant")
    require(number(value["basal_u_h"], "fixture-basal") <= 3, "fixture-basal")
    for name, count in (("samples", 11), ("delivered_rates_u_min", 10)):
        require(type(value[name]) is list and len(value[name]) == count, "fixture-grid")
        for item in value[name]:
            number(item, "fixture-number")
    number(value["initial_history_cgm"], "fixture-history")
    require(
        value["fault"]
        in (
            "none",
            "cancel-before-reset",
            "reset-error",
            "after-two",
            "cancel-after-two",
            "early-done",
            "terminal-tail",
        ),
        "fixture-fault",
    )
    require(type(value["close_error"]) is bool, "fixture-close-error")
    return decode(encode(value))


def availability(measured, variant):
    if variant in ("filtered", "future80"):
        if measured == 540000:
            return 900000
        if measured in (720000, 900000):
            return None
    return measured
