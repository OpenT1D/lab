"""Check the M1 and C1 training environments share native numeric dependencies."""

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import subprocess
import sys
import tomllib
from pathlib import Path

from .g2p2c_training_preflight import audit as engine_audit

ROOT = Path(__file__).resolve().parents[2]
M0 = ROOT / "experiments/m0/simglucose"
C1 = ROOT / "experiments/c1/g2p2c_training_source"
CORE = ("simglucose", "numpy", "scipy", "pandas", "gym", "pathos", "python-dateutil")


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _lock_versions(path):
    packages = tomllib.loads(path.read_text())["package"]
    versions = {item["name"]: item["version"] for item in packages}
    if len(versions) != len(packages) or not set(CORE) <= versions.keys():
        raise ValueError("Native dependency lock has duplicates or missing core packages")
    return {name: versions[name] for name in CORE}


def _installed():
    spec = importlib.util.find_spec("simglucose")
    if spec is None or spec.origin is None:
        raise ValueError("Installed simglucose package is absent")
    return {
        "python": sys.version.split()[0],
        "simglucose_file": str(Path(spec.origin).resolve()),
        "versions": {name: importlib.metadata.version(name) for name in CORE},
    }


def _m0_installed():
    script = (
        "import importlib.metadata, importlib.util, json, sys; "
        f"names={CORE!r}; "
        "spec=importlib.util.find_spec('simglucose'); "
        "print(json.dumps({'python':sys.version.split()[0], "
        "'simglucose_file':spec.origin, "
        "'versions':{name:importlib.metadata.version(name) for name in names}}))"
    )
    completed = subprocess.run(
        [str(M0 / ".venv/bin/python"), "-c", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(completed.stdout)


def _require_parity(m0_lock, c1_lock, m0_installed, c1_installed):
    if (
        m0_lock != c1_lock
        or m0_lock != m0_installed["versions"]
        or c1_lock != c1_installed["versions"]
        or m0_installed["python"] != c1_installed["python"]
        or not Path(m0_installed["simglucose_file"]).is_relative_to(M0 / ".venv")
        or not Path(c1_installed["simglucose_file"]).is_relative_to(C1 / ".venv")
    ):
        raise ValueError("M1 and C1 installed numeric runtime or locks differ")


def audit(source):
    preflight = engine_audit(source)
    m0_lock = _lock_versions(M0 / "uv.lock")
    c1_lock = _lock_versions(C1 / "uv.lock")
    m0_installed = _m0_installed()
    c1_installed = _installed()
    _require_parity(m0_lock, c1_lock, m0_installed, c1_installed)
    return {
        "schema": "opent1d.c1.g2p2c-runtime-parity/1",
        "m0_lock_sha256": _sha(M0 / "uv.lock"),
        "c1_training_lock_sha256": _sha(C1 / "uv.lock"),
        "g2p2c_source_commit": preflight["g2p2c_source_commit"],
        "m1_simglucose_commit": preflight["m1_simglucose_commit"],
        "python": c1_installed["python"],
        "core_versions": c1_lock,
        "m0_simglucose_file": m0_installed["simglucose_file"],
        "c1_simglucose_file": c1_installed["simglucose_file"],
        "native_core_runtime_parity": True,
        "native_trajectory_replayed": False,
        "eligible_m1_comparator": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"Runtime parity report already exists: {args.output}")
    result = audit(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
