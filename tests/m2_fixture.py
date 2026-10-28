"""Synthetic format fixture only: not a native simulation or physiological result."""

import copy
import json
import os
import subprocess
from datetime import UTC, datetime, timedelta

from experiments.m0.simglucose.recording import write_json
from experiments.m1.artifacts import digest
from experiments.m1.contracts import MEALS
from experiments.m2.run import ROOT, source_hashes


def fixture(output):
    output.mkdir(parents=True, exist_ok=False)
    cfg = dict(
        engine="lt1_cambridge", profile="reference", controller="lt1_pid", condition="A", seed=101
    )
    write_json(output / "config.json", cfg)
    (output / "protocol.md").write_bytes((ROOT / "docs/research/m2-protocol.md").read_bytes())
    for name in ("package-lock.json", "package.json", "baseline.json"):
        (output / name).write_bytes((ROOT / "experiments/m0/lt1" / name).read_bytes())
    for name in ("native.jsonl", "run.log"):
        (output / name).touch()
    settings = {
        "patient": {
            k: 1
            for k in "Gpeq BW k12 ka1 ka2 ka3 ke VI VG AG tmaxG SIT SID SIE EGP0 F01 tmaxI".split()
        },
        "sensor": dict(samplingTime=5, min=0, max=1000, resolution=0),
        "pump": {
            k: 0
            for k in (
                "inc_bolus inc_basal max_bolus max_basal relerr_bolus "
                "abserr_bolus bias_basal relerr_basal abserr_basal"
            ).split()
        },
        "controller": dict(samplingTime=5, targetBG=120, basalRate=1, kP=0.5, kI=0.01, kD=0),
        "solver": dict(name="SolverRK1_2", relative_error_target=0.001, default_dt_minutes=1),
        "seeds": dict(base=101, sensor=102, controller=103, pump=104, patient=105),
    }
    write_json(
        output / "runtime.json",
        dict(
            upstream_revision="9a6092065bd821f88691cd8d03b0550acd665573",
            node="v22.22.2",
            platform="synthetic-format-fixture",
            packages=json.loads((ROOT / "experiments/m0/lt1/package-lock.json").read_bytes())[
                "packages"
            ],
            settings=settings,
            source_sha256={
                k: "0" * 64
                for k in (
                    "src/core/Simulator.ts",
                    "src/core/models/Cambridge.ts",
                    "src/core/controllers/MPC_Hovorka2004.ts",
                    "src/core/controllers/PID.ts",
                    "LICENSE.md",
                )
            },
        ),
    )
    history = {}
    with (output / "trace.jsonl").open("w") as stream:
        for t in range(2881):
            grams = dict(MEALS).get(t, 0)
            new = []
            if grams:
                stamp = (
                    (datetime(2024, 7, 20, tzinfo=UTC) + timedelta(minutes=t))
                    .isoformat(timespec="milliseconds")
                    .replace("+00:00", "Z")
                )
                history[str(t)] = dict(time=stamp, start=stamp, carbs=grams)
                new = [dict(id=str(t), **history[str(t)])]
            p = dict(
                time_min=t,
                controller_cgm_mg_dl=120,
                controller_source_min=t - t % 5,
                new_announcements=new,
                announced_history=copy.deepcopy(history),
                glucose_mg_dl=120,
                raw_cgm_mg_dl=None if t % 5 else 120,
                sensor_available=True,
                command_u_h=1,
                delivered_u_h=1,
                intake_g_min=sum(g / 15 for m, g in MEALS if m <= t < m + 15),
                true_meal_g=grams,
            )
            stream.write(json.dumps(p) + "\n")
    write_json(output / "result.json", {"status": "completed"})
    revision = (
        os.environ.get("IV_TEST_REVISION")
        or subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    )
    manifest = dict(
        schema="opent1d.cambridge/1",
        status="completed",
        config=cfg,
        completed_rows=2881,
        elapsed_seconds=0,
        source_sha256=source_hashes(),
        revision=revision,
        worktree_dirty=True,
        files_sha256={p.name: digest(p) for p in output.iterdir()},
    )
    write_json(output / "manifest.json", manifest)
    return manifest
