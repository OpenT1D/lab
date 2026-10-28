"""Check that G2P2C training uses M1's pinned physiology, not its bundled fork."""

import argparse
import ast
import hashlib
import importlib.util
import json
import tomllib
from pathlib import Path

from .comparator_route_preflight import _g2p2c_source

M1_REV = "a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc"
M1_HASHES = {
    "patient/t1dpatient.py": "7ad1302fbf064805e2294bbcffd482e55448e37e48b63e629a1ed7f11c701547",
    "simulation/env.py": "8c5d16b66df270b22b13cd64f8e059efe0a5f7c732f8673f36af0170d5d0d199",
    "sensor/cgm.py": "97f3e1b3aeb01a9225e9500efa6ca940c41a178f6b8a80c9c41a430ec3a8563d",
    "actuator/pump.py": "54dc4ec98f34ae600dacd1edd2e43fc2701512eb0824ce33acb07f3f756a9719",
    "params/vpatient_params.csv": (
        "662f3b684d160fdf485edd1d7196dd1cd85c14b53650b030fdb86aaa05bb2e50"
    ),
    "params/sensor_params.csv": "a8b514dde8ccaae1e5ec07c127fcadbfce05db03d1f95a1eecb0c97035e9872c",
}
FORK_HASHES = {
    "patient/t1dpatient.py": "9bf0be3a9b12cf8f06f0fce21e73cc8bb176adec50b3c1c22c8dc104a728f5c2",
    "simulation/env.py": "4769ebc5039e831dbeb0300414ca1f6c1096b6b56124e05447519b249ac645da",
    "params/vpatient_params.csv": M1_HASHES["params/vpatient_params.csv"],
    "params/sensor_params.csv": M1_HASHES["params/sensor_params.csv"],
}


def _digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _check_hashes(package, expected):
    actual = {name: _digest(package / name) for name in expected}
    if actual != expected:
        changed = sorted(name for name in expected if actual[name] != expected[name])
        raise ValueError(f"Unexpected simglucose source files: {changed}")
    return actual


def _assignment(path, name):
    tree = ast.parse(path.read_text())
    values = [
        ast.unparse(node.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == name for target in node.targets)
    ]
    if len(values) != 1:
        raise ValueError(f"Expected exactly one {name} assignment in {path.name}")
    return values[0]


def _check_equations(package, *, m1):
    dbar = _assignment(package / "patient/t1dpatient.py", "Dbar")
    done = _assignment(package / "simulation/env.py", "done")
    expected = (
        ("last_Qsto + last_foodtaken * 1000", "BG < 10 or BG > 600")
        if m1
        else ("last_Qsto + last_foodtaken", "BG < 70 or BG > 350")
    )
    if (dbar, done) != expected:
        raise ValueError("Unexpected meal-mass or termination equation")
    return {"stomach_mass_expression": dbar, "termination_expression": done}


def _check_lock(project, root):
    m0 = root / "experiments/m0/simglucose"
    for location in (m0, project):
        config = tomllib.loads((location / "pyproject.toml").read_text())
        rev = config["tool"]["uv"]["sources"]["simglucose"]["rev"]
        lock = tomllib.loads((location / "uv.lock").read_text())
        package = next(item for item in lock["package"] if item["name"] == "simglucose")
        source = package["source"]["git"]
        if rev != M1_REV or not source.endswith(f"#{M1_REV}"):
            raise ValueError(f"simglucose source is not M1-pinned in {location}")


def audit(source, *, project=None):
    root = Path(__file__).resolve().parents[2]
    project = (project or root / "experiments/c1/g2p2c_training_source").resolve()
    source = Path(source).resolve()
    _g2p2c_source(source)
    _check_lock(project, root)

    spec = importlib.util.find_spec("simglucose")
    if spec is None or spec.origin is None:
        raise ValueError("simglucose is absent from the training environment")
    package = Path(spec.origin).resolve().parent
    if not package.is_relative_to(project / ".venv"):
        raise ValueError("simglucose was not imported from the locked C1 training environment")
    fork = source / "environments/simglucose/simglucose"
    m1_hashes = _check_hashes(package, M1_HASHES)
    fork_hashes = _check_hashes(fork, FORK_HASHES)
    m1_equations = _check_equations(package, m1=True)
    fork_equations = _check_equations(fork, m1=False)
    return {
        "schema": "opent1d.c1.g2p2c-training-preflight/1",
        "g2p2c_source_commit": "37f7b7e161e9c1e7b702c8eebdc5cc7eb4f81d70",
        "m1_simglucose_commit": M1_REV,
        "m1_engine_sha256": m1_hashes,
        "g2p2c_bundled_engine_sha256": fork_hashes,
        "m1_equations": m1_equations,
        "g2p2c_bundled_equations": fork_equations,
        "parameter_and_sensor_tables_identical": True,
        "training_engine_matches_m1_pin": True,
        "bundled_engine_matches_m1_physiology": False,
        "trained_policy_available": False,
        "eligible_m1_comparator": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(f"{args.output}: training_engine_matches_m1_pin=True")


if __name__ == "__main__":
    main()
