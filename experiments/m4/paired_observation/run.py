"""Run or reconstruct the standard-library BC-004 boundary preflight."""

import argparse
import hashlib
import json
import platform
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from .contract import VERSION, evaluate

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ARCHIVE = {
    "source-contract.py": HERE / "contract.py",
    "source-run.py": HERE / "run.py",
    "source-forcing.py": ROOT / "experiments/m4/kinetic_inlet/forcing.py",
    "source-test.py": ROOT / "tests/test_m4_paired_observation.py",
    "root-uv.lock": ROOT / "uv.lock",
    "root-pyproject.toml": ROOT / "pyproject.toml",
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    def reject(value):
        raise ValueError(f"Nonfinite JSON {value}")

    return json.loads(Path(path).read_text(), parse_constant=reject)


def dump(path, data):
    Path(path).write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


def hashes(directory):
    return {
        p.name: digest(p)
        for p in sorted(directory.iterdir())
        if p.is_file() and p.name != "manifest.json"
    }


def execute(protocol, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    manifest = {
        "schema": "bc004-run/1",
        "status": "started",
        "implementation": VERSION,
        "started_utc": datetime.now(UTC).isoformat(),
        "files": {},
        "python": platform.python_version(),
    }
    dump(output / "manifest.json", manifest)
    try:
        manifest["git_head"] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=HERE, text=True
        ).strip()
        manifest["git_dirty"] = bool(
            subprocess.check_output(["git", "status", "--porcelain"], cwd=HERE)
        )
        for name, path in ARCHIVE.items():
            shutil.copyfile(path, output / name)
        shutil.copyfile(protocol, output / "protocol.json")
        result = evaluate(read(output / "protocol.json"))
        dump(output / "preflight.json", result)
        if not result["passed"]:
            raise ValueError("BC-004 boundary acceptance failed")
        manifest.update(
            status="completed", finished_utc=datetime.now(UTC).isoformat(), files=hashes(output)
        )
        dump(output / "manifest.json", manifest)
        return result
    except BaseException as exc:
        manifest.update(
            status="failed",
            finished_utc=datetime.now(UTC).isoformat(),
            error={"type": type(exc).__name__, "message": str(exc)},
            files=hashes(output),
        )
        dump(output / "manifest.json", manifest)
        raise


def reconstruct(directory):
    directory = Path(directory)
    manifest = read(directory / "manifest.json")
    if (
        manifest.get("schema") != "bc004-run/1"
        or manifest.get("status") != "completed"
        or manifest.get("implementation") != VERSION
    ):
        raise ValueError("Not a completed BC-004 run of this implementation")
    required = {*ARCHIVE, "protocol.json", "preflight.json"}
    files = manifest.get("files", {})
    if not required.issubset(files):
        raise ValueError("Missing BC-004 artifacts")
    for name, expected in files.items():
        if Path(name).name != name or name in {".", ".."}:
            raise ValueError("Unsafe artifact path")
        path = directory / name
        if path.is_symlink() or not path.is_file() or digest(path) != expected:
            raise ValueError("Changed or missing artifact")
    # Use installed, versioned reader code only; archived Python is never executed.
    result = evaluate(read(directory / "protocol.json"))
    if result != read(directory / "preflight.json") or not result["passed"]:
        raise ValueError("Stored preflight disagrees with reconstructed contract")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, default=HERE / "protocol.json")
    parser.add_argument("--reconstruct", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.reconstruct:
        result = reconstruct(args.reconstruct)
        with args.output.open("x") as stream:
            stream.write(json.dumps(result, indent=2, allow_nan=False) + "\n")
    else:
        result = execute(args.protocol, args.output)
    print(
        json.dumps(
            {
                "passed": result["passed"],
                "coupled_trajectory_executed": False,
                "empirical_freeze": result["empirical_freeze"],
            }
        )
    )


if __name__ == "__main__":
    main()
