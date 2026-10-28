"""Native imports and runtime provenance, excluded from report reconstruction."""

import hashlib
import importlib.metadata
import json
import os
from pathlib import Path

import numpy as np
import simglucose
from simglucose.controller.basal_bolus_ctrller import BBController

from experiments.m0.simglucose.recording import write_json

from .adapter import Simglucose
from .artifacts import ROOT, digest
from .simulation import simulate


def native_run(config, checkpoint, initial, output, manifest, *, controller=None):
    package = Path(simglucose.__file__).parent
    upstream = {
        str(p.relative_to(package)): digest(p)
        for p in sorted(package.rglob("*"))
        if p.suffix in (".py", ".csv")
    }
    fingerprint = hashlib.sha256(
        json.dumps(upstream, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    baseline = json.loads((ROOT / "experiments/m0/simglucose/baseline.json").read_text())
    if fingerprint not in {
        env["upstream_files_digest"] for env in baseline["environments"].values()
    }:
        raise ValueError("Installed native sources differ from reviewed M0 source fingerprint")
    manifest.update(
        upstream_files_sha256=upstream,
        upstream_files_digest=fingerprint,
        upstream_revision="a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc",
        packages=dict(
            sorted((p.metadata["Name"], p.version) for p in importlib.metadata.distributions())
        ),
        numpy_disabled_features=os.environ.get("NPY_DISABLE_CPU_FEATURES"),
        numpy_cpu_features={
            k: bool(v) for k, v in np.core._multiarray_umath.__cpu_features__.items()
        },
    )
    engine = Simglucose(config.profile, config.seed)
    bb = BBController()
    quest = bb.quest[bb.quest.Name == config.profile].iloc[0]
    params = bb.patient_params[bb.patient_params.Name == config.profile].iloc[0]
    integrator = engine._env.patient._odesolver._integrator
    manifest["effective_settings"] = {
        "basal_u_min": float(params.u2ss * params.BW / 6000),
        "CR_g_U": float(quest.CR),
        "CF_mg_dl_U": float(quest.CF),
        "controller_target_mg_dl": 140,
        "pid": {"P": 0.001, "I": 0.00001, "D": 0.001},
        "solver": {
            "method": "dopri5",
            "rtol": float(integrator.rtol),
            "atol": float(integrator.atol),
        },
        "sensor": "Dexcom",
        "pump": "Insulet",
        "sensor_seed": config.seed,
        "patient_random_initialization": False,
        "patient_seed": None,
        "pump_parameters": {
            k: (str(v) if k == "Name" else float(v)) for k, v in engine._env.pump._params.items()
        },
    }
    write_json(output / "manifest.json", manifest)

    def diagnostic():
        # Diagnostic history never contributes to metrics or completed coverage.
        (output / "native-diagnostic.csv").write_text(engine.native_history().to_csv())

    try:
        status = simulate(config, checkpoint, initial, engine=engine, controller=controller)
    except BaseException:
        try:
            diagnostic()
        except Exception as error:
            manifest["diagnostic_error"] = f"{type(error).__name__}: {error}"
        raise  # Preserve the simulation failure, even if diagnostic export also fails.
    diagnostic()  # Missing diagnostics on an otherwise complete run remain an error.
    return status
