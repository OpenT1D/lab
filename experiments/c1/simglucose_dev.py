"""Separate C1 simglucose development route; M1/M2 artifacts are unchanged."""

import argparse
import contextlib
import hashlib
import json
import platform
import subprocess
import sys
import time
import traceback
import warnings
from dataclasses import asdict, dataclass
from pathlib import Path
from types import SimpleNamespace

from experiments.m0.simglucose.recording import failure_status, interruption, write_json
from experiments.m1.artifacts import ROOT, digest, strict_json
from experiments.m1.contracts import Action, Observation
from experiments.m1.contracts import Config as M1Config

from .core import Settings, TrendOverlay, finite
from .feedback import FeedbackController, FeedbackSettings

SCHEMA = "opent1d.c1-simglucose-development/1"
METHODS = ("trend_overlay", "bounded_pid", "feedback_trend", "feedback_no_rise")


@dataclass(frozen=True)
class Config:
    profile: str
    seed: int
    condition: str
    method: str
    settings: Settings | FeedbackSettings

    @classmethod
    def parse(cls, value):
        if not isinstance(value, dict) or set(value) != {
            "profile",
            "seed",
            "condition",
            "method",
            "settings",
        }:
            raise ValueError("Expected profile, seed, condition, method and settings")
        method = value["method"]
        if method not in METHODS:
            raise ValueError("Unsupported C1 development method")
        native = M1Config(
            profile=value["profile"], seed=value["seed"], condition=value["condition"]
        )
        feedback = method.startswith("feedback_")
        setting_type = FeedbackSettings if feedback else Settings
        if type(value["settings"]) is not dict or set(value["settings"]) != set(
            setting_type.__dataclass_fields__
        ):
            raise ValueError("Explicit complete C1 settings required")
        settings = setting_type(**value["settings"])
        if feedback and (settings.rise_gain_u_h_per_mg_dl_min > 0) != (method == "feedback_trend"):
            raise ValueError("Feedback method and rise gain disagree")
        return cls(native.profile, native.seed, native.condition, method, settings)

    def m1(self):
        return M1Config(profile=self.profile, seed=self.seed, condition=self.condition)


class Controller:
    """Allowlisted M1 observation to basal-only C1 action, with command audit."""

    def __init__(self, config, audit):
        from experiments.m1.control import Controller as NativeController

        self.config = config
        self.audit = audit
        self.base = NativeController(
            SimpleNamespace(profile=config.profile, controller="basal_bolus")
        )
        self.pid = (
            NativeController(SimpleNamespace(profile=config.profile, controller="pid"))
            if config.method == "bounded_pid"
            else None
        )
        self.overlay = TrendOverlay(config.settings) if config.method == "trend_overlay" else None
        self.feedback = (
            FeedbackController(config.settings) if config.method.startswith("feedback_") else None
        )
        self.previous_rate = None

    def reset(self):
        self.base.reset()
        if self.pid is not None:
            self.pid.reset()
        if self.overlay is not None:
            self.overlay.reset()
        if self.feedback is not None:
            self.feedback.reset()
        self.previous_rate = None

    def command(self, observation, announced_g):
        if not isinstance(observation, Observation):
            raise ValueError("Only the allowlisted M1 observation is accepted")
        base = self.base.command(observation, announced_g)
        basal = finite(base.basal_u_min * 60, "base basal U/h", 0)
        bolus = finite(base.bolus_u_min, "base bolus U/min", 0)
        limit = self.config.settings.max_total_u_h
        if basal > limit:
            raise ValueError("Native basal exceeds declared C1 basal limit")
        if self.feedback is not None:
            decision = self.feedback.command(
                time_min=observation.time_min,
                glucose_mg_dl=observation.glucose_mg_dl,
                source_time_min=observation.source_time_min,
                available=observation.available,
                base_u_h=basal,
            )
            final = decision.final_u_h
            detail = {
                "raw_total_u_h": decision.raw_total_u_h,
                "requested_total_u_h": decision.requested_total_u_h,
                "correction_u_h": decision.correction_u_h,
                "integral_mg_dl_min": decision.integral_mg_dl_min,
                "rise_mg_dl_min": decision.rise_mg_dl_min,
                "integral_frozen": decision.integral_frozen,
                "total_clamped": decision.total_clamped,
                "slew_limited": decision.slew_limited,
                "reason": decision.reason,
            }
        elif self.overlay is not None:
            decision = self.overlay.command(
                time_min=observation.time_min,
                glucose_mg_dl=observation.glucose_mg_dl,
                source_time_min=observation.source_time_min,
                available=observation.available,
                base_u_h=basal,
            )
            final = decision.final_u_h
            detail = {
                "extra_u_h": decision.extra_u_h,
                "reason": decision.reason,
                "inventory_u": decision.inventory_u,
                "rise_mg_dl_min": decision.rise_mg_dl_min,
            }
        else:
            correction = self.pid.command(observation, announced_g)
            raw = finite(correction.basal_u_min * 60, "PID correction U/h")
            requested = max(0.0, min(limit, basal + raw))
            final = (
                requested
                if self.previous_rate is None
                else min(requested, self.previous_rate + self.config.settings.max_extra_step_u_h)
            )
            detail = {
                "pid_correction_u_h": raw,
                "requested_u_h": requested,
                "reason": "bounded_pid",
            }
        final = finite(final, "final basal U/h", 0)
        if final > limit:
            raise ValueError("C1 action exceeds declared basal limit")
        self.previous_rate = final
        action = Action(final / 60, bolus)
        self.audit(
            {
                "time_min": observation.time_min,
                "controller_source_min": observation.source_time_min,
                "controller_cgm_mg_dl": observation.glucose_mg_dl,
                "sensor_available": observation.available,
                "announced_g": announced_g,
                "base_basal_u_h": basal,
                "base_bolus_u_min": bolus,
                "final_basal_u_h": final,
                "final_bolus_u_min": action.bolus_u_min,
                **detail,
            }
        )
        return action


def source_hashes():
    paths = sorted((ROOT / "experiments/c1").glob("*.py"))
    paths += sorted((ROOT / "experiments/m1").glob("*.py"))
    paths.append(ROOT / "experiments/m0/simglucose/recording.py")
    paths.append(ROOT / "experiments/platform_files.py")
    return {str(path.relative_to(ROOT)): digest(path) for path in paths}


def native_inventory():
    """Check installed source against the reviewed M0 fingerprints."""
    import simglucose

    package = Path(simglucose.__file__).parent
    mapping = {
        str(path.relative_to(package)): digest(path)
        for path in sorted(package.rglob("*"))
        if path.suffix in (".py", ".csv")
    }
    fingerprint = hashlib.sha256(
        json.dumps(mapping, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    baseline = strict_json((ROOT / "experiments/m0/simglucose/baseline.json").read_bytes())
    if fingerprint not in {e["upstream_files_digest"] for e in baseline["environments"].values()}:
        raise ValueError("Installed simglucose source differs from M0 fingerprint")
    return {
        "upstream_revision": "a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc",
        "upstream_files_digest": fingerprint,
        "upstream_files_sha256": mapping,
        "python": sys.version,
        "platform": platform.platform(),
    }


def execute(config_path, output, timeout_seconds=300):
    """Run one known development case; preserve partial attempts and exact bytes."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    for filename in ("trace.jsonl", "commands.jsonl"):
        (output / filename).touch()
    (output / "run.log").touch()
    manifest = {
        "schema": SCHEMA,
        "status": "started",
        "config": None,
        "completed_rows": 0,
        "command_rows": 0,
        "files_sha256": {},
    }
    write_json(output / "manifest.json", manifest)
    started = time.monotonic()
    caught = []
    try:
        finite(timeout_seconds, "timeout_seconds", 0)
        raw = Path(config_path).read_bytes()
        (output / "config.json").write_bytes(raw)
        cfg = Config.parse(strict_json(raw))
        manifest.update(
            config=asdict(cfg),
            source_sha256=source_hashes(),
            revision=subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            worktree_dirty=bool(
                subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT)
            ),
        )
        for name in ("uv.lock", "protocol-settings.json", "baseline.json"):
            (output / ("simglucose-" + name)).write_bytes(
                (ROOT / "experiments/m0/simglucose" / name).read_bytes()
            )
        method_doc = (
            "c1-feedback-kernel.md"
            if cfg.method.startswith("feedback_")
            else "c1-method-feasibility.md"
        )
        (output / "c1-method.md").write_bytes((ROOT / "docs/research" / method_doc).read_bytes())
        manifest["method_sha256"] = digest(output / "c1-method.md")
        write_json(output / "manifest.json", manifest)
        with (
            interruption(timeout_seconds),
            warnings.catch_warnings(record=True) as caught,
            (output / "run.log").open("w") as log,
            contextlib.redirect_stdout(log),
            contextlib.redirect_stderr(log),
            (output / "trace.jsonl").open("a") as trace,
            (output / "commands.jsonl").open("a") as commands,
        ):
            warnings.simplefilter("always")
            from experiments.m1.adapter import Simglucose
            from experiments.m1.simulation import simulate

            write_json(output / "runtime.json", native_inventory())
            engine = Simglucose(cfg.profile, cfg.seed)

            def audit(record):
                commands.write(json.dumps(record, allow_nan=False) + "\n")
                commands.flush()

            def checkpoint(row):
                trace.write(json.dumps(asdict(row), allow_nan=False) + "\n")
                trace.flush()

            def initial(snapshot):
                write_json(output / "initial.json", asdict(snapshot))

            controller = Controller(cfg, audit)
            status = simulate(cfg.m1(), checkpoint, initial, engine=engine, controller=controller)
            (output / "native-diagnostic.csv").write_text(engine.native_history().to_csv())
            if status not in ("completed", "terminated"):
                raise ValueError("Invalid native completion status")
            manifest["status"] = status
            if status == "terminated":
                manifest["error"] = "Native simglucose terminal glucose threshold"
    except BaseException as error:
        manifest.update(status=failure_status(error), error=f"{type(error).__name__}: {error}")
        (output / "failure.log").write_text(traceback.format_exc())
        raise
    finally:
        write_json(
            output / "warnings.json",
            [
                {
                    "category": item.category.__name__,
                    "message": str(item.message),
                    "filename": item.filename,
                    "line": item.lineno,
                }
                for item in caught
            ],
        )
        manifest.update(
            elapsed_seconds=time.monotonic() - started,
            completed_rows=(output / "trace.jsonl").read_bytes().count(b"\n"),
            command_rows=(output / "commands.jsonl").read_bytes().count(b"\n"),
        )
        manifest["files_sha256"] = {
            p.name: digest(p)
            for p in sorted(output.iterdir())
            if p.is_file() and p.name != "manifest.json"
        }
        write_json(output / "manifest.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=float, default=300)
    args = parser.parse_args()
    execute(args.config, args.output, args.timeout_seconds)


if __name__ == "__main__":
    main()
