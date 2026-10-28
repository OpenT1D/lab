"""Read-only, simulator-free feasibility gate for a pinned OpenAPS reference."""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

COMMIT = "88cf032aa74ff25f69464a7d9cd601ee3940c0b3"
SOURCE_HASHES = {
    "LICENSE.txt": "5966cdf482e00a7f03459fc3367af609c6fc56e26542ba01d6200e549fb88e02",
    "package.json": "40ac350375740f7ea19d6b1c4abfff149f5c570e958bcc6941063f2ec444197d",
    "bin/oref0-determine-basal.js": (
        "e1a682909c0bd5e16af54ef9e595477962ef34affc903e17b7589d6d24c94a3e"
    ),
    "lib/determine-basal/determine-basal.js": (
        "6d9ce9f726cb23ec95dacab4717d0cf7519627022719e0c62bd21f728667e135"
    ),
    "examples/suggested.json": "b976801e72fa5930186f9c07675636dd6b0056a777db3cd17710c1d6944282b0",
}
EXAMPLE_COMMAND = (
    "node",
    "bin/oref0-determine-basal.js",
    "examples/iob.json",
    "examples/temp_basal.json",
    "examples/glucose.json",
    "examples/profile.json",
    "--auto-sens",
    "examples/autosens.json",
    "--meal",
    "examples/meal.json",
    "--microbolus",
    "--currentTime",
    "1527924300000",
)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def run(*args, cwd):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=False)


def compare_json(expected, actual):
    return {
        key: {"expected": expected.get(key), "actual": actual.get(key)}
        for key in sorted(expected.keys() | actual.keys())
        if expected.get(key) != actual.get(key)
    }


def audit(source):
    source = Path(source).resolve()
    commit = run("git", "rev-parse", "HEAD", cwd=source)
    dirty = run("git", "status", "--porcelain", "--untracked-files=no", cwd=source)
    actual_hashes = {name: sha256((source / name).read_bytes()) for name in SOURCE_HASHES}
    pinned = (
        commit.returncode == 0
        and commit.stdout.strip() == COMMIT
        and dirty.returncode == 0
        and not dirty.stdout.strip()
        and actual_hashes == SOURCE_HASHES
    )
    if not pinned:
        raise ValueError("OpenAPS checkout does not match the clean pinned source")
    if (source / "autotune").exists():
        raise ValueError("Remove autotune: the example would enable a different SMB variant")

    package = json.loads((source / "package.json").read_text())
    license_text = (source / "LICENSE.txt").read_text()
    license_ok = package.get("license") == "MIT" and "MIT License" in license_text

    direct = {}
    for name, spec in sorted(package["dependencies"].items()):
        installed = source / "node_modules" / name / "package.json"
        if not installed.exists():
            raise ValueError(f"Missing npm dependency: {name}; install in the external checkout")
        item = json.loads(installed.read_text())
        direct[name] = {
            "upstream_spec": spec,
            "installed_version": item.get("version"),
            "installed_license": item.get("license"),
        }

    example = run(*EXAMPLE_COMMAND, cwd=source)
    if example.returncode or not example.stdout.strip():
        raise ValueError(f"Upstream example failed with exit {example.returncode}")
    expected = json.loads((source / "examples/suggested.json").read_text())
    actual = json.loads(example.stdout)
    differences = compare_json(expected, actual)

    core = run("./node_modules/.bin/mocha", "-c", "tests/determine-basal.test.js", cwd=source)
    passing = re.search(r"(\d+) passing", core.stdout)
    failing = re.search(r"(\d+) failing", core.stdout)
    core_ok = core.returncode == 0 and passing is not None and failing is None
    full = run("make", "test", cwd=source)
    full_passing = re.search(r"(\d+) passing", full.stdout)
    full_failing = re.search(r"(\d+) failing", full.stdout)

    gates = {
        "source_pinned": "pass",
        "upstream_mit_license": "pass" if license_ok else "fail",
        "upstream_core_tests": "pass" if core_ok else "fail",
        "upstream_full_suite": "pass" if full.returncode == 0 else "fail",
        "upstream_example_parity": "pass" if not differences else "fail",
        "transitive_dependency_lock_and_license_audit": "open",
        "causal_m1_input_mapping": "open",
        "three_minute_temp_basal_fidelity": "open",
        "failure_and_reset_semantics": "open",
        "matched_development_budget": "open",
    }
    return {
        "schema": "opent1d.c1.oref0-preflight/1",
        "reference": "https://github.com/openaps/oref0",
        "commit": COMMIT,
        "variant": "oref0 CLI; example --microbolus is disabled by absent autotune directory",
        "source_sha256": actual_hashes,
        "package_version": package.get("version"),
        "runtime": {
            "node": run("node", "--version", cwd=source).stdout.strip(),
            "npm": run("npm", "--version", cwd=source).stdout.strip(),
        },
        "license": package.get("license"),
        "direct_dependencies": direct,
        "dependency_note": (
            "Upstream has no committed npm lockfile; installed direct versions are observed, "
            "not a transitive reproducibility claim."
        ),
        "example": {
            "command": list(EXAMPLE_COMMAND),
            "expected_sha256": sha256((source / "examples/suggested.json").read_bytes()),
            "actual_sha256": sha256(example.stdout.encode()),
            "differences": differences,
        },
        "core_tests": {
            "command": ["./node_modules/.bin/mocha", "-c", "tests/determine-basal.test.js"],
            "passing": int(passing.group(1)) if passing else None,
            "failing": int(failing.group(1)) if failing else (0 if core_ok else None),
            "exit_code": core.returncode,
        },
        "full_suite": {
            "command": ["make", "test"],
            "passing": int(full_passing.group(1)) if full_passing else None,
            "failing": int(full_failing.group(1)) if full_failing else None,
            "exit_code": full.returncode,
        },
        "gates": gates,
        "eligible_m1_comparator": all(value == "pass" for value in gates.values()),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(f"{args.output}: eligible_m1_comparator={result['eligible_m1_comparator']}")


if __name__ == "__main__":
    main()
