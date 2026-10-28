"""Bounded frozen-model M5 workflow on unchanged invented observations only."""

import argparse
import contextlib
import math
import os
import signal
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

from experiments.m5.synthetic_prognosis.run import fit, fixture, predict

from .contract import (
    ARCHIVE_FILES,
    BUNDLE_FILES,
    HERE,
    PROTOCOL,
    ROOT,
    SOURCES,
    declaration,
    decode,
    encode,
    read_bytes,
    request,
    rows,
    runtime,
    sha,
    snapshot,
    worker_result,
)
from .report import from_snapshot, markdown, reconstruct


def write(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp")
    try:
        temporary.write_bytes(encode(value))
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def export_example(output):
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError("Choose a new example directory")
    development = rows()[0]
    state = fit([row for _, row in development], include_function=True)
    state["feature_names"] = [
        "prior_insulin_u_day",
        "prior_glycemic_status_mg_dl",
        "landmark_day_after_first_infusion",
        "observed_function_index",
    ]
    source = read_bytes(HERE / "example_model.py")
    frozen = encode(state)
    model = {
        "schema": "m5-prognostic-model/1",
        "model_id": "invented-development-ridge",
        "rights_basis": "Original OpenT1D Apache-2.0 example; invented observations only",
        "input_schema": "m5-landmark-input/1",
        "output_unit": "U/day",
        "source_sha256": sha(source),
        "state_sha256": sha(frozen),
        "runtime": {"python_major_minor": runtime()["python_major_minor"], "dependencies": []},
        "training": {
            "phase": "development_only",
            "fixture_sha256": sha(encode(fixture())),
            "participant_aliases": [alias for alias, _ in development],
        },
    }
    declaration(model, source, frozen)
    output.mkdir(parents=True, exist_ok=False)
    (output / "model.py").write_bytes(source)
    (output / "state.json").write_bytes(frozen)
    write(output / "model.json", model)
    return model


@contextlib.contextmanager
def termination_as_interrupt():
    """Make CLI termination clean up active workers and retain interruption evidence."""
    if threading.current_thread() is not threading.main_thread():
        yield
        return

    def interrupt(signum, frame):
        raise KeyboardInterrupt(f"M5 execution interrupted by signal {signum}")

    signals = [signal.SIGTERM]
    if hasattr(signal, "SIGHUP"):
        signals.append(signal.SIGHUP)
    previous = {sig: signal.getsignal(sig) for sig in signals}
    try:
        for sig in signals:
            signal.signal(sig, interrupt)
        yield
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)


def _cleanup(process):
    # Also terminate children left behind after a worker exits or times out.
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait()


def attempt(bundle, record, index, timeout_seconds):
    result = {
        "attempt": index,
        "status": "worker_failed",
        "prediction_u_day": None,
        "runtime": None,
    }
    with tempfile.TemporaryDirectory(prefix="opent1d-m5-worker-") as scratch:
        directory = Path(scratch)
        for name in ("model.py", "state.json"):
            (directory / name).write_bytes(bundle[name])
        (directory / "worker.py").write_bytes(read_bytes(HERE / "worker.py"))
        (directory / "input.json").write_bytes(encode(record))
        try:
            process = subprocess.Popen(
                [sys.executable, "-I", "-S", "worker.py"],
                cwd=directory,
                env={"PATH": os.defpath},
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except OSError:
            return result
        try:
            try:
                returncode = process.wait(timeout=timeout_seconds)
            except subprocess.TimeoutExpired:
                result["status"] = "timeout"
                return result
        finally:
            _cleanup(process)
        if returncode != 0:
            return result
        try:
            value = worker_result(
                decode(read_bytes(directory / "output.json")),
                decode(bundle["model.json"]),
                expected_runtime=runtime(),
            )
        except (ValueError, OSError, RecursionError):
            result["status"] = "invalid_output"
            return result
        result.update(
            status="completed", prediction_u_day=value["prediction_u_day"], runtime=value["runtime"]
        )
    return result


def seal(output):
    inputs = ARCHIVE_FILES - {"report.json", "report.md"}
    data = {name: read_bytes(output / name) for name in inputs}
    report = from_snapshot(data)
    write(output / "report.json", report)
    (output / "report.md").write_bytes(markdown(report))
    write(
        output / "manifest.json",
        {
            "schema": "m5-researcher-archive/1",
            "files": {name: sha(read_bytes(output / name)) for name in sorted(ARCHIVE_FILES)},
        },
    )
    return report


def execute(bundle_directory, output, *, timeout_seconds=5.0):
    if (
        type(timeout_seconds) not in (int, float)
        or not math.isfinite(timeout_seconds)
        or not 0 < timeout_seconds <= 60
    ):
        raise ValueError("Worker timeout must be finite and in (0, 60] seconds")
    bundle = snapshot(bundle_directory, BUNDLE_FILES)
    declaration(decode(bundle["model.json"]), bundle["model.py"], bundle["state.json"])
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError("Choose a new output directory")
    development, evaluation, _ = rows()
    baseline = fit([row for _, row in development], include_function=False)
    predictions = [
        {
            "alias": alias,
            "request": request(row),
            "attempts": [],
            "baseline_prediction_u_day": predict(baseline, row, include_function=False),
        }
        for alias, row in evaluation
    ]
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    output.mkdir(parents=True, exist_ok=False)
    for name, content in bundle.items():
        (output / name).write_bytes(content)
    for name, path in SOURCES.items():
        (output / name).write_bytes(read_bytes(path))
    (output / "tooling-uv.lock").write_bytes(read_bytes(ROOT / "uv.lock"))
    write(
        output / "provenance.json",
        {
            "schema": "m5-researcher-provenance/1",
            "git_revision": revision,
            "host_runtime": runtime(),
            "worker_timeout_seconds": timeout_seconds,
            "source_identity": (
                "saved source bytes; git revision alone does not identify local edits"
            ),
        },
    )
    write(output / "protocol.json", PROTOCOL)
    write(output / "fixture.json", fixture())
    write(output / "baseline.json", baseline)
    write(output / "predictions.json", predictions)
    seal(output)
    with termination_as_interrupt():
        try:
            for saved in predictions:
                for index in (1, 2):
                    try:
                        result = attempt(bundle, saved["request"], index, timeout_seconds)
                    except BaseException:
                        saved["attempts"].append(
                            {
                                "attempt": index,
                                "status": "interrupted",
                                "prediction_u_day": None,
                                "runtime": None,
                            }
                        )
                        write(output / "predictions.json", predictions)
                        seal(output)
                        raise
                    saved["attempts"].append(result)
                    write(output / "predictions.json", predictions)
                    seal(output)
        except BaseException:
            # Retry the progress write after a controlled interruption of atomic replacement.
            write(output / "predictions.json", predictions)
            seal(output)
            raise
    return reconstruct(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("export-example").add_argument("output", type=Path)
    run_parser = commands.add_parser("run")
    run_parser.add_argument("bundle", type=Path)
    run_parser.add_argument("output", type=Path)
    run_parser.add_argument("--timeout-seconds", type=float, default=5.0)
    commands.add_parser("reconstruct").add_argument("archive", type=Path)
    args = parser.parse_args()
    if args.command == "export-example":
        result = export_example(args.output)
    elif args.command == "run":
        result = execute(args.bundle, args.output, timeout_seconds=args.timeout_seconds)
    else:
        result = reconstruct(args.archive)
    print(encode(result).decode(), end="")


if __name__ == "__main__":
    main()
