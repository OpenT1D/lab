"""Small JSONL child process for trusted local source; no estimator dependencies."""

import contextlib
import copy
import json
import math
import re
import sys
import types
from pathlib import Path

from experiments.m1.artifacts import strict_json
from experiments.m3.common import require

from .intake import HISTORY_MINUTES, MAX_SETTINGS_BYTES, MAX_SOURCE_BYTES, read_regular

MAX_REQUEST_BYTES = 16 * 1024
MINUTE_US = 60_000_000


def validate_prediction(value):
    """Do not clip finite, nonphysiological predictions: scoring retains them."""
    try:
        valid = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        valid = False
    require(valid, "Prediction must be a finite scalar number")
    return value


def validate_request(request):
    """The callback sees six exact-time causal values, never a future target."""
    require(
        isinstance(request, dict) and set(request) == {"origin_us", "times_us", "values_mg_dl"},
        "Unsupported forecast request fields",
    )
    origin = request["origin_us"]
    times = request["times_us"]
    values = request["values_mg_dl"]
    require(
        type(origin) is int and origin >= 0,
        "Forecast origin must be a nonnegative integer microsecond time",
    )
    require(
        isinstance(times, list)
        and all(type(value) is int and value >= 0 for value in times)
        and times == [origin + minute * MINUTE_US for minute in HISTORY_MINUTES],
        "Forecast history must have the six exact causal five-minute times",
    )
    require(isinstance(values, list) and len(values) == 6, "Forecast history needs six values")
    for value in values:
        validate_prediction(value)
        require(value > 0, "Forecast CGM history must be positive")
    return request


class SuppliedPredictor:
    """Execute source once; give each call fresh copies of the frozen arguments."""

    def __init__(self, source_bytes, settings, *, filename="<m3-forecaster>"):
        require(isinstance(settings, dict), "Forecaster settings must be a JSON object")
        self.settings = copy.deepcopy(settings)
        module = types.ModuleType("_m3_supplied_forecaster")
        module.__file__ = str(filename)
        # Registration lets ordinary standard-library decorators inspect this module.
        previous = sys.modules.get(module.__name__)
        sys.modules[module.__name__] = module
        try:
            with contextlib.redirect_stdout(sys.stderr):
                exec(compile(source_bytes, str(filename), "exec"), module.__dict__)
            callback = getattr(module, "predict", None)
            require(callable(callback), "Forecaster source must expose predict(request, settings)")
            self.callback = callback
        except BaseException:
            if previous is None:
                sys.modules.pop(module.__name__, None)
            else:
                sys.modules[module.__name__] = previous
            raise

    def predict(self, request):
        validate_request(request)
        with contextlib.redirect_stdout(sys.stderr):
            result = self.callback(copy.deepcopy(request), copy.deepcopy(self.settings))
        return validate_prediction(result)


def run(source_path, settings_path, input_stream, output_stream):
    """Serve only bounded newline-terminated JSON records from the parent worker."""
    source = read_regular(source_path, MAX_SOURCE_BYTES, "source")
    settings = strict_json(read_regular(settings_path, MAX_SETTINGS_BYTES, "settings"))
    supplied = SuppliedPredictor(source, settings, filename=Path(source_path))
    while True:
        line = input_stream.readline(MAX_REQUEST_BYTES + 1)
        if not line:
            return
        require(
            len(line) <= MAX_REQUEST_BYTES and line.endswith(b"\n"),
            "Invalid forecast request byte limit or newline",
        )
        prediction = supplied.predict(strict_json(line))
        output_stream.write(json.dumps({"prediction": prediction}, allow_nan=False) + "\n")
        output_stream.flush()


def main():
    try:
        require(len(sys.argv) == 3, "Source and settings paths required")
        run(sys.argv[1], sys.argv[2], sys.stdin.buffer, sys.stdout)
    except BaseException as error:
        # A source exception can include arbitrary observation/settings text.
        name = type(error).__name__
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,127}", name):
            name = "SuppliedPredictorError"
        with contextlib.suppress(OSError, ValueError):
            print(json.dumps({"error_type": name}), flush=True)
        print(f"Forecast worker failed ({name})", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
