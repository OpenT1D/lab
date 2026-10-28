"""Verify a new C1 runtime without relabeling historical Torch 2.2 training.

Native replay uses only the two declared historical checkpoints. Reconstruction
is stdlib-only and checks saved evidence; it does not execute or requalify actors.
"""

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
import signal
import subprocess
import sys
import time
import tomllib
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = ROOT / "experiments/c1/g2p2c-security-runtime.json"
PROTOCOL_SHA256 = "eac14c224ee17d28152a9cb752254d943184c6981f4cbd9d473ae03f424dc478"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    from experiments.m1.artifacts import strict_json

    return strict_json(Path(path).read_bytes())


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def implementation():
    paths = sorted((ROOT / "experiments/c1").glob("*.py"))
    paths += sorted((ROOT / "experiments/m1").glob("*.py"))
    paths += sorted((ROOT / "experiments/m0/simglucose").glob("*.py"))
    for project in ("g2p2c_policy_source", "g2p2c_training_source"):
        paths += [
            ROOT / "experiments/c1" / project / name for name in ("pyproject.toml", "uv.lock")
        ]
    paths += [
        PROTOCOL,
        ROOT / "experiments/c1/evidence-index.json",
        ROOT / "experiments/c1/g2p2c-training.json",
        ROOT / "experiments/c1/g2p2c-native-smoke.json",
        ROOT / "experiments/m0/simglucose/uv.lock",
        ROOT / "experiments/m0/simglucose/pyproject.toml",
    ]
    return {str(path.relative_to(ROOT)): sha(path) for path in sorted(paths)}


def historical_inputs(historical_root, profile, protocol):
    """Require original declared artifacts, without comparing to the new lock."""
    directory = Path(historical_root) / "results"
    tag = profile.replace("#", "")
    index = read(ROOT / "experiments/c1/evidence-index.json")[f"g2p2c_{tag}_trained_gate"]
    case = next(
        case for case in protocol["acceptance"]["native_cases"] if case["profile"] == profile
    )
    training = directory / f"c1-g2p2c-training-{tag}"
    native = directory / f"c1-g2p2c-native-smoke-{tag}-d101"
    paths = {
        "attempt.json": (training / "attempt.json", index["training_attempt_sha256"]),
        "experiment_summary.csv": (
            training / "experiment_summary.csv",
            index["training_summary_sha256"],
        ),
        "actor.pt": (training / "actor-final-state-dict.pt", case["checkpoint_sha256"]),
        "training-plan.json": (
            training / "training-plan.json",
            protocol["ancestry"]["training_plan_sha256"],
        ),
        "old-report.json": (native / "report.json", index["native_smoke_report_sha256"]),
        "old-trace.jsonl": (native / "trace.jsonl", index["native_smoke_trace_sha256"]),
        "old-initial.json": (native / "initial.json", index["native_smoke_initial_sha256"]),
    }
    attempt = read(training / "attempt.json")
    paths["source-preflight.json"] = (
        training / "source-preflight.json",
        attempt["source_preflight_sha256"],
    )
    if any(sha(path) != expected for path, expected in paths.values()):
        raise ValueError("Historical C1 artifacts differ from their declared hashes")
    if (
        attempt["training_lock_sha256"] != protocol["ancestry"]["historical_training_lock_sha256"]
        or attempt["actor_tensor_sha256"] != case["actor_tensor_sha256"]
        or attempt["checkpoint_sha256"] != case["checkpoint_sha256"]
        or attempt["source_completed"] is not True
        or attempt["source_commit"] != protocol["ancestry"]["g2p2c_commit"]
        or attempt["simglucose_commit"] != protocol["ancestry"]["simglucose_commit"]
    ):
        raise ValueError("Historical training identity differs")
    return {name: path for name, (path, _expected) in paths.items()}


def runtime_identity():
    import torch

    from .g2p2c_checkpoint import require_runtime
    from .g2p2c_runtime_parity import CORE, _lock_versions

    require_runtime()
    project = ROOT / "experiments/c1/g2p2c_training_source"
    if Path(sys.prefix).resolve() != (project / ".venv").resolve():
        raise ValueError("Run native verification in the locked C1 training environment")
    core = {name: importlib.metadata.version(name) for name in CORE}
    if (
        core != _lock_versions(project / "uv.lock")
        or core != _lock_versions(ROOT / "experiments/m0/simglucose/uv.lock")
        or sys.version_info[:2] != (3, 12)
    ):
        raise ValueError("Native numeric core or Python differs from the frozen boundary")
    for name in ("torch", "numpy"):
        lock = tomllib.loads((project / "uv.lock").read_text())
        expected = next(
            package["version"] for package in lock["package"] if package["name"] == name
        )
        if importlib.metadata.version(name) != expected:
            raise ValueError(f"Installed {name} differs from lock")
    return {
        "python": sys.version.split()[0],
        "torch": torch.__version__,
        "core_versions": core,
        "training_lock_sha256": sha(project / "uv.lock"),
        "policy_lock_sha256": sha(ROOT / "experiments/c1/g2p2c_policy_source/uv.lock"),
    }


def differences(left, right):
    """Descriptive field differences only; no cross-version acceptance threshold."""
    counts, maxima = {}, {}
    if len(left) != len(right):
        return {"exact": False, "left_rows": len(left), "right_rows": len(right)}
    for old, new in zip(left, right):
        if set(old) != set(new):
            raise ValueError("Historical/native row fields differ")
        for field in old:
            if old[field] != new[field]:
                counts[field] = counts.get(field, 0) + 1
                if type(old[field]) in (int, float) and type(new[field]) in (int, float):
                    maxima[field] = max(maxima.get(field, 0), abs(old[field] - new[field]))
    return {
        "exact": not counts,
        "rows": len(left),
        "changed_values_by_field": counts,
        "max_absolute_difference_by_field": maxima,
    }


def worker(source, archive, profile, output):
    import torch

    from experiments.m1.contracts import Config, validate_rows
    from experiments.m1.simulation import simulate

    from .comparator_route_preflight import _g2p2c_source
    from .g2p2c_architecture_preflight import audit as architecture_audit
    from .g2p2c_native_smoke import replay_commands
    from .g2p2c_policy_adapter import load_source_state_dict
    from .g2p2c_trained_preflight import (
        PROFILE_BASAL_U_MIN,
        _invented_stream,
        verify_trained_source_forward,
    )
    from .g2p2c_training_preflight import audit as engine_audit
    from .g2p2c_training_run import _tensor_digest, validated_plan

    plan = read(archive / "plan.json")
    if implementation() != plan["implementation_sha256"]:
        raise ValueError("C1 implementation changed after freeze")
    if _g2p2c_source(source) != plan["source"]:
        raise ValueError("Pinned source changed after freeze")
    protocol = plan["protocol"]
    case = next(
        case for case in protocol["acceptance"]["native_cases"] if case["profile"] == profile
    )
    runtime = runtime_identity()
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    source_report = engine_audit(source)
    architecture = architecture_audit(source)
    checkpoint = archive / "historical" / profile.replace("#", "") / "actor.pt"
    controller = load_source_state_dict(
        source,
        checkpoint,
        sha256=case["checkpoint_sha256"],
        seed=24,
        missing_fallback_basal_u_min=PROFILE_BASAL_U_MIN[profile],
    )
    if _tensor_digest(controller.actor.state_dict()) != case["actor_tensor_sha256"]:
        raise ValueError("Historical actor tensor values changed in patched runtime")
    before = torch.get_rng_state().clone()
    states = verify_trained_source_forward(
        source, validated_plan(), profile, checkpoint, controller.actor
    )
    synthetic = _invented_stream(controller)
    controller.reset()
    if _invented_stream(controller) != synthetic or not torch.equal(before, torch.get_rng_state()):
        raise ValueError("Causal synthetic repeat or RNG ownership failed")
    output.mkdir()
    rows = []
    snapshots = []

    def initial(snapshot):
        snapshots.append(asdict(snapshot))
        save(output / "initial.json", asdict(snapshot))

    def append(row):
        rows.append(row)
        with (output / "trace.jsonl").open("a") as stream:
            stream.write(json.dumps(asdict(row), sort_keys=True, allow_nan=False) + "\n")

    status = simulate(Config(profile, 101, "pid", "D"), append, initial, controller=controller)
    endpoint = validate_rows(rows)
    replay = replay_commands(rows, controller)
    if not torch.equal(before, torch.get_rng_state()):
        raise ValueError("Native causal actor changed caller RNG")
    masked = [row for row in rows if row.controller_source_min < row.start_min]
    passed = (
        status == "completed"
        and endpoint == 2880
        and len(rows) == 960
        and len(snapshots) == 1
        and len(masked) == 10
        and replay == 960
        and all(0 <= row.basal_u_min <= 5 and row.bolus_u_min == 0 for row in rows)
        and all(row.basal_u_min == PROFILE_BASAL_U_MIN[profile] for row in masked)
    )
    if implementation() != plan["implementation_sha256"]:
        raise ValueError("C1 implementation changed during replay")
    if _g2p2c_source(source) != plan["source"]:
        raise ValueError("Pinned source changed during replay")
    report = {
        "schema": "opent1d.c1.g2p2c-security-case/1",
        "profile": profile,
        "protocol_sha256": plan["protocol_sha256"],
        "runtime": runtime,
        "checkpoint_sha256": case["checkpoint_sha256"],
        "actor_tensor_sha256": case["actor_tensor_sha256"],
        "source_preflight": source_report,
        "architecture": architecture,
        "trained_forward_states": states,
        "synthetic_commands": 741,
        "synthetic_commands_sha256": synthetic,
        "caller_rng_preserved": True,
        "native_status": status,
        "intervals": len(rows),
        "endpoint_min": endpoint,
        "masked_intervals": len(masked),
        "saved_command_replay_intervals": replay,
        "initial_sha256": sha(output / "initial.json"),
        "trace_sha256": sha(output / "trace.jsonl"),
        "passed": passed,
        "eligible_m1_comparator": False,
    }
    save(output / "report.json", report)
    if not passed:
        raise ValueError("Patched runtime failed the frozen native integration gate")
    return report


def _group_signal(process, signum):
    try:
        os.killpg(process.pid, signum)
    except ProcessLookupError:
        pass


class Control:
    def __init__(self):
        self.signal = None
        self.active = None

    def stop(self, signum, _frame=None):
        if self.signal is None:
            self.signal = int(signum)
        if self.active is not None:
            _group_signal(self.active, signum)


def _supervise(args, log, timeout, control=None, *, grace_seconds=10):
    """Own/reap the full worker group, including cleanup after leader exit."""
    with log.open("x") as stream:
        stream.write(json.dumps({"argv": args, "timeout_seconds": timeout}) + "\n")
        stream.flush()
        env = {
            key: value
            for key, value in os.environ.items()
            if key not in {"PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV"}
            and not key.startswith(("UV_", "TORCH_FORCE_"))
        }
        process = subprocess.Popen(
            args, cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True
        )
        control = control or Control()
        control.active = process
        error = None
        deadline = time.monotonic() + timeout
        stopped_at = None
        try:
            while process.poll() is None:
                now = time.monotonic()
                if stopped_at is None and (control.signal is not None or now >= deadline):
                    stopped_at = now
                    error = "GlobalInterruption" if control.signal is not None else "WorkerDeadline"
                    _group_signal(process, signal.SIGTERM)
                if stopped_at is not None and now - stopped_at >= grace_seconds:
                    _group_signal(process, signal.SIGKILL)
                time.sleep(0.02)
            code = process.wait()
            if control.signal is not None:
                error = "GlobalInterruption"
            elif code and error is None:
                error = "WorkerExit"
        except BaseException:
            _group_signal(process, signal.SIGKILL)
            process.wait()
            raise
        finally:
            # A direct worker owns no descendants, but do not leak an unexpected
            # child just because its leader exited before cleanup.
            try:
                os.killpg(process.pid, 0)
            except ProcessLookupError:
                pass
            else:
                if error is None:
                    error = "UnreapedWorkerGroup"
                _group_signal(process, signal.SIGKILL)
            process.wait()
            control.active = None
    return code, error


def run(source, historical_root, output):
    from .comparator_route_preflight import _g2p2c_source

    runtime_identity()
    source = Path(source).resolve()
    protocol = read(PROTOCOL)
    if sha(PROTOCOL) != PROTOCOL_SHA256:
        raise ValueError("The frozen security protocol changed")
    source_identity = _g2p2c_source(source)
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(f"Verification output exists: {output}")
    inputs = {
        case["profile"]: historical_inputs(historical_root, case["profile"], protocol)
        for case in protocol["acceptance"]["native_cases"]
    }
    output.mkdir(parents=True)
    plan = {
        "schema": "opent1d.c1.g2p2c-security-execution/1",
        "protocol": protocol,
        "protocol_sha256": sha(PROTOCOL),
        "implementation_sha256": implementation(),
        "source": source_identity,
        "git_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "git_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT)),
        "historical_input_sha256": {
            profile: {name: sha(path) for name, path in files.items()}
            for profile, files in inputs.items()
        },
    }
    save(output / "plan.json", plan)
    (output / "protocol.json").write_bytes(PROTOCOL.read_bytes())
    for profile, files in inputs.items():
        directory = output / "historical" / profile.replace("#", "")
        directory.mkdir(parents=True)
        for name, path in files.items():
            (directory / name).write_bytes(path.read_bytes())
    attempts = [
        {
            "profile": profile,
            "repetition": repetition,
            "exit_code": None,
            "error": "Unattempted",
            "duration_seconds": None,
        }
        for profile in inputs
        for repetition in ("primary", "repeat")
    ]
    save(output / "attempts.json", attempts)
    control = Control()
    handlers = {
        signum: signal.getsignal(signum)
        for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)
    }
    for signum in handlers:
        signal.signal(signum, control.stop)
    try:
        for attempt in attempts:
            if control.signal is not None:
                break
            profile, repetition = attempt["profile"], attempt["repetition"]
            tag = f"{profile.replace('#', '')}-{repetition}"
            command = [
                sys.executable,
                "-B",
                "-E",
                "-s",
                "-m",
                "experiments.c1.g2p2c_security_runtime",
                "worker",
                "--source",
                str(source),
                "--archive",
                str(output),
                "--profile",
                profile,
                "--output",
                str(output / tag),
            ]
            start = time.monotonic()
            try:
                code, error = _supervise(command, output / f"{tag}.log", 600, control)
            except OSError as failure:
                code, error = None, type(failure).__name__
            attempt.update(
                {"exit_code": code, "error": error, "duration_seconds": time.monotonic() - start}
            )
            save(output / "attempts.json", attempts)
    finally:
        for signum, handler in handlers.items():
            signal.signal(signum, handler)
    files = {
        str(path.relative_to(output)): sha(path) for path in output.rglob("*") if path.is_file()
    }
    save(
        output / "manifest.json",
        {"schema": "opent1d.c1.g2p2c-security-manifest/1", "files_sha256": files},
    )
    report = reconstruct(output)
    save(output / "report.json", report)
    return report


def reconstruct(archive):
    """Recompute saved accounting and cross-version differences using stdlib."""
    archive = Path(archive).resolve()
    manifest = read(archive / "manifest.json")
    files = manifest["files_sha256"]
    actual_files = {
        str(path.relative_to(archive))
        for path in archive.rglob("*")
        if path.is_file() and str(path.relative_to(archive)) not in {"manifest.json", "report.json"}
    }
    if set(files) != actual_files or any(path.is_symlink() for path in archive.rglob("*")):
        raise ValueError("Security verification archive file inventory differs")
    if manifest["schema"] != "opent1d.c1.g2p2c-security-manifest/1" or any(
        Path(name).is_absolute() or ".." in Path(name).parts or sha(archive / name) != expected
        for name, expected in files.items()
    ):
        raise ValueError("Security verification archive integrity differs")
    plan = read(archive / "plan.json")
    if (
        sha(archive / "protocol.json") != PROTOCOL_SHA256
        or plan["protocol_sha256"] != PROTOCOL_SHA256
        or read(archive / "protocol.json") != plan["protocol"]
    ):
        raise ValueError("Frozen security protocol identity differs")
    for profile, inputs in plan["historical_input_sha256"].items():
        for name, expected in inputs.items():
            path = archive / "historical" / profile.replace("#", "") / name
            if sha(path) != expected:
                raise ValueError("Frozen historical input identity differs")
    attempts = read(archive / "attempts.json")
    roster = [
        (case["profile"], repetition)
        for case in plan["protocol"]["acceptance"]["native_cases"]
        for repetition in ("primary", "repeat")
    ]
    if [(item["profile"], item["repetition"]) for item in attempts] != roster or any(
        item["exit_code"] is not None
        and type(item["exit_code"]) is not int
        or item["duration_seconds"] is not None
        and (
            type(item["duration_seconds"]) not in (int, float)
            or not math.isfinite(item["duration_seconds"])
            or item["duration_seconds"] < 0
        )
        for item in attempts
    ):
        raise ValueError("Security attempt roster or terminal accounting differs")
    cases = []
    for case in plan["protocol"]["acceptance"]["native_cases"]:
        profile = case["profile"]
        tag = profile.replace("#", "")
        pair = [
            next(
                item
                for item in attempts
                if item["profile"] == profile and item["repetition"] == repeat
            )
            for repeat in ("primary", "repeat")
        ]
        accepted = all(item["exit_code"] == 0 and item["error"] is None for item in pair)
        result = {"profile": profile, "passed": False, "attempts": pair}
        if accepted:
            primary = archive / f"{tag}-primary"
            repeat = archive / f"{tag}-repeat"
            native = read(primary / "report.json")
            from experiments.m1.artifacts import strict_json
            from experiments.m1.contracts import Row, validate_rows

            from .g2p2c_trained_preflight import PROFILE_BASAL_U_MIN

            rows = [
                Row(**strict_json(line))
                for line in (primary / "trace.jsonl").read_bytes().splitlines()
            ]
            endpoint = validate_rows(rows)
            masked = [row for row in rows if row.controller_source_min < row.start_min]
            if (
                native["profile"] != profile
                or native["protocol_sha256"] != PROTOCOL_SHA256
                or native["checkpoint_sha256"] != case["checkpoint_sha256"]
                or native["actor_tensor_sha256"] != case["actor_tensor_sha256"]
                or native["initial_sha256"] != sha(primary / "initial.json")
                or native["trace_sha256"] != sha(primary / "trace.jsonl")
                or native["runtime"]["torch"].split("+")[0] != "2.13.0"
                or native["runtime"]["training_lock_sha256"]
                != plan["implementation_sha256"]["experiments/c1/g2p2c_training_source/uv.lock"]
                or native["runtime"]["policy_lock_sha256"]
                != plan["implementation_sha256"]["experiments/c1/g2p2c_policy_source/uv.lock"]
                or native["trained_forward_states"] != 16
                or native["synthetic_commands"] != 741
                or native["caller_rng_preserved"] is not True
                or native["source_preflight"]["training_engine_matches_m1_pin"] is not True
                or native["source_preflight"]["g2p2c_source_commit"]
                != plan["protocol"]["ancestry"]["g2p2c_commit"]
                or native["source_preflight"]["m1_simglucose_commit"]
                != plan["protocol"]["ancestry"]["simglucose_commit"]
                or len(native["architecture"]["profiles"]) != 2
                or any(
                    item["exact_constructor_tensor_and_forward_parity"] is not True
                    or item["source_state_dict_weights_only_roundtrip"] is not True
                    for item in native["architecture"]["profiles"]
                )
                or native["intervals"] != 960
                or native["endpoint_min"] != 2880
                or native["masked_intervals"] != 10
                or native["saved_command_replay_intervals"] != 960
                or native["native_status"] != "completed"
                or endpoint != 2880
                or len(rows) != 960
                or rows[-1].terminal
                or len(masked) != 10
                or any(row.bolus_u_min != 0 or not 0 <= row.basal_u_min <= 5 for row in rows)
                or any(row.basal_u_min != PROFILE_BASAL_U_MIN[profile] for row in masked)
            ):
                raise ValueError("Saved native case differs from the frozen integration boundary")
            same = all(
                (primary / name).read_bytes() == (repeat / name).read_bytes()
                for name in ("initial.json", "trace.jsonl", "report.json")
            )
            historical = archive / "historical" / tag
            old = [
                json.loads(line)
                for line in (historical / "old-trace.jsonl").read_text().splitlines()
            ]
            new = [json.loads(line) for line in (primary / "trace.jsonl").read_text().splitlines()]
            result.update(
                {
                    "passed": native["passed"] is True and same,
                    "native": native,
                    "fresh_process_byte_exact": same,
                    "historical_initial_exact": read(historical / "old-initial.json")
                    == read(primary / "initial.json"),
                    "historical_trace_difference": differences(old, new),
                }
            )
        cases.append(result)
    report = {
        "schema": "opent1d.c1.g2p2c-security-report/1",
        "protocol_sha256": plan["protocol_sha256"],
        "manifest_sha256": sha(archive / "manifest.json"),
        "git_revision": plan["git_revision"],
        "git_dirty": plan["git_dirty"],
        "passed": all(case["passed"] for case in cases),
        "cases": cases,
        "historical_training_requalified": False,
        "eligible_m1_comparator": False,
        "reader_scope": (
            "Saved integrity, accounting and descriptive differences; "
            "no actor or simulator execution"
        ),
    }
    if (archive / "report.json").exists() and read(archive / "report.json") != report:
        raise ValueError("Saved security report differs from reconstruction")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    runner = commands.add_parser("run")
    runner.add_argument("--source", type=Path, required=True)
    runner.add_argument("--historical-root", type=Path, required=True)
    runner.add_argument("--output", type=Path, required=True)
    child = commands.add_parser("worker")
    child.add_argument("--source", type=Path, required=True)
    child.add_argument("--archive", type=Path, required=True)
    child.add_argument("--profile", choices=("adult#001", "adult#002"), required=True)
    child.add_argument("--output", type=Path, required=True)
    reader = commands.add_parser("reconstruct")
    reader.add_argument("--archive", type=Path, required=True)
    reader.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "worker":
        worker(args.source, args.archive, args.profile, args.output)
    elif args.command == "run":
        report = run(args.source, args.historical_root, args.output)
        print(f"{args.output}: passed={report['passed']}")
        raise SystemExit(0 if report["passed"] else 1)
    else:
        report = reconstruct(args.archive)
        with args.output.open("x") as stream:
            stream.write(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
        print(args.output)


if __name__ == "__main__":
    main()
