"""Pinned, simulator-free no-go for oref0 and G2P2C replacement-route scan."""

import argparse
import ast
import csv
import hashlib
import json
import math
import subprocess
from pathlib import Path
from types import SimpleNamespace

from experiments.m1.contracts import STEP, Action

from .g2p2c_boundary import _scale, pump_rate
from .oref0_adapter import (
    PriorCommand,
    TempBasalProjection,
    pump_history,
    source_decision_on_m1_grid,
)
from .oref0_example_history import current_clean_checkout
from .oref0_preflight import COMMIT as OREF0_COMMIT

G2P2C_COMMIT = "37f7b7e161e9c1e7b702c8eebdc5cc7eb4f81d70"
G2P2C_HASHES = {
    "LICENSE.txt": "b5639b69d968c64b90c38e5f84c301eaf2898ab59d05400b53395c9a19c14dfb",
    "agents/g2p2c/parameters.py": (
        "e749454ae3190e15d843f2752ba27018c30bb3ba424c40252ae011afd1f87aa2"
    ),
    "agents/g2p2c/worker.py": "dce23cbffed66445a61218f1ae484e0948cec9c2884ffc9b05be50e4d72bbef7",
    "agents/g2p2c/models.py": "d3bfc0d57015d15a9a380425fc8eddc17080dfa2bdc08f2f8b8739a5297be44d",
    "utils/statespace.py": "532c8b867d3bc2446683c706d163fdf5424e91c14bb4ff86af644851f5f919df",
    "utils/pumpAction.py": "5e0a9e92e7ab9072be87b2f9b9aaa439608a7d0c0bbe440c4337c352da8cd259",
    "utils/core.py": "7da87cfd16fdf630addb44c7f54d3f452e439b783603241cc8536373d42f28bb",
    "utils/options.py": "2a98198af3556b5374a377f9ae18c707ac349a311785cb24d3faef61b8cde67b",
    "environments/simglucose/simglucose/params/sensor_params.csv": (
        "a8b514dde8ccaae1e5ec07c127fcadbfce05db03d1f95a1eecb0c97035e9872c"
    ),
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def _source_function(path, name, *, class_name=None, namespace=None):
    tree = ast.parse(path.read_text())
    nodes = tree.body
    if class_name:
        nodes = next(
            node.body
            for node in nodes
            if isinstance(node, ast.ClassDef) and node.name == class_name
        )
    function = next(
        node for node in nodes if isinstance(node, ast.FunctionDef) and node.name == name
    )
    scope = {} if namespace is None else dict(namespace)
    exec(
        compile(
            ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[])),
            str(path),
            "exec",
        ),
        scope,
    )
    return scope[name]


def _option_defaults(path):
    defaults = {}
    names = {
        "--sensor",
        "--action_type",
        "--insulin_min",
        "--glucose_min",
        "--glucose_max",
        "--expert_bolus",
        "--expert_cf",
    }
    for node in ast.walk(ast.parse(path.read_text())):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        if not isinstance(node.func, ast.Attribute) or node.func.attr != "add_argument":
            continue
        name = ast.literal_eval(node.args[0])
        if name not in names:
            continue
        for keyword in node.keywords:
            if keyword.arg == "default":
                defaults[name] = ast.literal_eval(keyword.value)
    return defaults


def _m1_command_contract():
    root = Path(__file__).resolve().parents[1]
    path = root / "m1" / "simulation.py"
    tree = ast.parse(path.read_text())
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "controller"
        and node.func.attr == "command"
    ]
    if (
        len(calls) != 1
        or [ast.unparse(arg) for arg in calls[0].args] != ["observation", "announced"]
        or calls[0].keywords
    ):
        raise ValueError("M1 controller callback changed; review causal boundary")
    return {
        "simulation_sha256": digest(path.read_bytes()),
        "callback_args": ["observation", "announced"],
    }


def _oref0_no_go():
    if source_decision_on_m1_grid(5) or STEP != 3:
        raise ValueError("Expected five/three-minute grid mismatch")
    projection = TempBasalProjection(1)
    projection.accept(0, {"duration": 30, "rate": 2})
    try:
        projection.accept(5, {"duration": 30, "rate": 3})
    except ValueError as error:
        if "inside an M1 interval" not in str(error):
            raise
    else:
        raise ValueError("Unmodified source transition silently fitted M1")
    try:
        pump_history((PriorCommand(0, Action(1 / 60, 0)),), decision_min=3)
    except ValueError as error:
        if "pump receipt" not in str(error):
            raise
    else:
        raise ValueError("M1 command was silently treated as pump delivery")
    return {
        "minute_5_on_m1_grid": False,
        "off_grid_temp_rejected": True,
        "command_as_pump_receipt_rejected": True,
    }


def _g2p2c_source(source):
    source = Path(source).resolve()
    run = subprocess.run(
        ("git", "rev-parse", "HEAD"), cwd=source, capture_output=True, text=True, check=True
    )
    dirty = subprocess.run(
        ("git", "status", "--porcelain", "--untracked-files=no"),
        cwd=source,
        capture_output=True,
        text=True,
        check=True,
    )
    hashes = {name: digest((source / name).read_bytes()) for name in G2P2C_HASHES}
    if run.stdout.strip() != G2P2C_COMMIT or dirty.stdout.strip() or hashes != G2P2C_HASHES:
        raise ValueError("G2P2C checkout does not match pinned clean source")
    if "MIT License" not in (source / "LICENSE.txt").read_text():
        raise ValueError("Pinned G2P2C license declaration changed")

    params = _source_function(source / "agents/g2p2c/parameters.py", "set_args")(
        SimpleNamespace(return_type="average", debug=0)
    )
    if (
        params.n_features,
        params.feature_history,
        params.use_meal_announcement,
        params.use_carb_announcement,
        params.use_tod_announcement,
        params.use_handcraft,
    ) != (2, 12, False, False, False, 0):
        raise ValueError("G2P2C source policy feature configuration changed")

    with (source / "environments/simglucose/simglucose/params/sensor_params.csv").open() as stream:
        sensors = {row["Name"]: float(row["sample_time"]) for row in csv.DictReader(stream)}
    options = _option_defaults(source / "utils/options.py")
    if (
        sensors["Dexcom"] != STEP
        or sensors["GuardianRT"] != 5
        or {
            name: options[name]
            for name in (
                "--sensor",
                "--action_type",
                "--insulin_min",
                "--glucose_min",
                "--glucose_max",
                "--expert_bolus",
                "--expert_cf",
            )
        }
        != {
            "--sensor": "GuardianRT",
            "--action_type": "exponential",
            "--insulin_min": 0,
            "--glucose_min": 39,
            "--glucose_max": 600,
            "--expert_bolus": False,
            "--expert_cf": False,
        }
    ):
        raise ValueError("G2P2C sensor cadence assumption changed")

    upstream_scale = _source_function(source / "utils/core.py", "linear_scaling")
    upstream_action = _source_function(
        source / "utils/pumpAction.py", "action", class_name="Pump", namespace={"math": math}
    )
    pump = SimpleNamespace(
        use_bolus=False, action_type="exponential", action_scale=5, pump_min=0, pump_max=5, bolus=0
    )
    for value, low, high in (
        (39, 39, 600),
        (140, 39, 600),
        (600, 39, 600),
        (0, 0, 5),
        (0.02, 0, 5),
        (5, 0, 5),
    ):
        if _scale(value, low, high) != upstream_scale(value, low, high):
            raise ValueError("G2P2C state normalization mismatch")
    for policy_action in (-1.0, -0.5, 0.0, 0.5, 1.0):
        source_rate, source_command = upstream_action(pump, agent_action=policy_action)
        adapted = pump_rate(policy_action)
        if not math.isclose(
            adapted.basal_u_min, source_rate, rel_tol=0, abs_tol=1e-12
        ) or not math.isclose(adapted.basal_u_min, source_command, rel_tol=0, abs_tol=1e-12):
            raise ValueError("G2P2C pump action mismatch")

    tracked = subprocess.run(
        ("git", "ls-files", "*.pt", "*.pth", "*.ckpt", "*.onnx"),
        cwd=source,
        capture_output=True,
        text=True,
        check=True,
    )
    worker = (source / "agents/g2p2c/worker.py").read_text()
    models = (source / "agents/g2p2c/models.py").read_text()
    if "info['future_carb']" not in worker or "info['meal_type']" not in worker:
        raise ValueError("Review upstream worker's private-info boundary again")
    if "if self.use_handcraft == 1:" not in models or "torch.clamp(action, -1, 1)" not in models:
        raise ValueError("Review source policy feature/action boundary again")
    return {
        "commit": G2P2C_COMMIT,
        "source_sha256": hashes,
        "declared_license": "MIT",
        "training_default_sensor": "GuardianRT (5 min)",
        "m1_sensor_choice": (
            "Dexcom (3 min); requires separate training or verified policy transfer"
        ),
        "policy_features": "12 past normalized CGM/command pairs; meal and carb flags disabled",
        "source_normalization_action_parity": "pass",
        "tracked_checkpoint_files": tracked.stdout.splitlines(),
        "native_worker_uses_private_scenario_info": True,
        "eligible_m1_comparator": False,
    }


def audit(oref0_source, g2p2c_source):
    oref0_lock = current_clean_checkout(Path(oref0_source).resolve())
    m1 = _m1_command_contract()
    no_go = _oref0_no_go()
    g2p2c = _g2p2c_source(g2p2c_source)
    return {
        "schema": "opent1d.c1.comparator-route-preflight/1",
        "m1": m1,
        "oref0": {
            "commit": OREF0_COMMIT,
            "dependency_lock_sha256": oref0_lock["sha256"],
            "unmodified_m1_route": "no-go",
            "checks": no_go,
        },
        "selected_replacement_feasibility_candidate": "G2P2C source method, not a qualified policy",
        "g2p2c": g2p2c,
        "eligible_m1_comparator": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--oref0-source", type=Path, required=True)
    parser.add_argument("--g2p2c-source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.oref0_source, args.g2p2c_source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(f"{args.output}: eligible_m1_comparator={result['eligible_m1_comparator']}")


if __name__ == "__main__":
    main()
