"""IV-001 contracts and identities; no native runtime imports."""

import hashlib
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from experiments.m1.artifacts import digest, strict_json
from experiments.m1.contracts import number
from experiments.m2.run import source_hashes as reference_sources
from experiments.m2.study import locks

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = ROOT / "docs/research/internal-verification-protocol.md"
DAILY = ((420, 45), (720, 70), (960, 15), (1080, 80), (1380, 10))


def configurations():
    return [
        dict(
            engine=e,
            profile=p,
            seed=s,
            controller=c,
            factor=1,
            warmup=1440,
            mode="feedback",
            schema="iv001.case/1",
        )
        for e, profiles, seeds, controllers in (
            ("simglucose", ("adult#001", "adult#002"), (101, 102), ("basal_bolus", "pid")),
            ("lt1_cambridge", ("reference",), (101,), ("lt1_pid", "lt1_mpc")),
        )
        for p in profiles
        for s in seeds
        for c in controllers
    ]


def validate(cfg):
    if isinstance(cfg, dict) and cfg.get("schema") == "iv001.robust-case/1":
        from .conditions import VARIANTS

        if set(cfg) != set(configurations()[0]) | {"variant"} or cfg["variant"] not in VARIANTS:
            raise ValueError("Expected a supported one-factor robustness condition")
        expected_warmup = {"warmup-0": 0, "warmup-48": 2880}.get(cfg["variant"], 1440)
        if (
            cfg["mode"] != "feedback"
            or type(cfg["factor"]) is not int
            or cfg["factor"] != 1
            or cfg["warmup"] != expected_warmup
        ):
            raise ValueError("Robustness requires native feedback and the prescribed history")
        validate({k: v for k, v in cfg.items() if k != "variant"} | {"schema": "iv001.case/1"})
        return cfg
    if not isinstance(cfg, dict) or set(cfg) != set(configurations()[0]):
        raise ValueError("Expected the complete IV-001 case contract")
    base = cfg | dict(factor=1, warmup=1440, mode="feedback")
    if base not in configurations() or type(cfg["seed"]) is not int:
        raise ValueError("Unsupported IV-001 development engine/profile/controller/seed")
    for key, allowed in (("factor", (1, 10, 100)), ("warmup", (0, 1440, 2880))):
        if type(cfg[key]) is not int or cfg[key] not in allowed:
            raise ValueError(f"Unsupported {key}")
    if cfg["mode"] not in ("feedback", "replay"):
        raise ValueError("Expected feedback or replay")
    if cfg["mode"] == "replay" and cfg["warmup"] != 1440:
        raise ValueError("Fixed-input replay uses the nominal initialization history")
    return cfg


def meals(cfg):
    from .conditions import change_meals

    return change_meals(
        cfg, [(day + t, g) for day in range(0, cfg["warmup"] + 1440, 1440) for t, g in DAILY]
    )


def start(cfg):
    return datetime(2024, 7, 21) - timedelta(minutes=cfg["warmup"])


def identity():
    return {
        "revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT)),
        "source_sha256": reference_sources()
        | {
            str(p.relative_to(ROOT)): digest(p)
            for p in sorted((ROOT / "experiments/verification").iterdir())
            if p.suffix in (".py", ".mjs")
        },
        "locks_sha256": locks(),
        "protocol_sha256": digest(PROTOCOL),
    }


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read_lines(raw):
    return [strict_json(line) for line in raw.splitlines() if line]


def emit(stream, value):
    stream.write(json.dumps(value, allow_nan=False, separators=(",", ":")) + "\n")
    stream.flush()


def replay_input(path, cfg):
    data = strict_json(Path(path).read_bytes())
    if not isinstance(data, dict) or set(data) != {"config", "status", "trace_sha256", "rows"}:
        raise ValueError("Invalid replay input")
    origin = validate(data["config"])
    if origin != cfg | dict(factor=1, mode="feedback"):
        raise ValueError("Replay must use this configuration's native nominal feedback input")
    if data["status"] not in ("completed", "terminated") or not data["rows"]:
        raise ValueError("Replay needs completed native intervals")
    number(len(data["rows"]), "replay rows", 1)
    return data
