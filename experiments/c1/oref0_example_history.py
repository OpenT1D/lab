"""Replay the published oref0 example at its origin and selected releases."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from collections import Counter
from pathlib import Path

from .oref0_preflight import COMMIT, EXAMPLE_COMMAND, compare_json
from .oref0_preflight import audit as source_audit

REVISIONS = {
    "example_introduction": "9b63e442c9e6d55da2e128566a00cba29671f7cb",
    "v0.7.0": "acb0150021e7bf284b6741a9510076a13f690747",
    "v0.7.1": "69d76737eb84e338b7a794d0784011c161ffcc54",
    "preflight_source": COMMIT,
}
ORIGIN_COMMAND = (
    "node",
    "bin/oref0-determine-basal.js",
    "examples/iob.json",
    "examples/temp_basal.json",
    "examples/glucose.json",
    "examples/profile.json",
    "examples/autosens.json",
    "examples/meal.json",
    "--microbolus",
    "--currentTime",
    "1527924300000",
)


def command(args, cwd, env=None):
    return subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True, check=False)


def checked(args, cwd, env=None):
    result = command(args, cwd, env)
    if result.returncode:
        raise ValueError(f"Command failed: {args[0]} {args[1]} (exit {result.returncode})")
    return result.stdout


def digest(data):
    return hashlib.sha256(data).hexdigest()


def different_fields(expected, actual):
    if isinstance(expected, dict) and isinstance(actual, dict):
        return list(compare_json(expected, actual))
    return [] if expected == actual else ["<array>"]


def current_clean_checkout(source):
    if checked(("git", "rev-parse", "HEAD"), source).strip() != COMMIT:
        raise ValueError("Expected the pinned preflight source checkout")
    if checked(("git", "rev-parse", "--is-shallow-repository"), source).strip() != "false":
        raise ValueError("Fetch full upstream history before replaying revisions")
    if checked(("git", "status", "--porcelain", "--untracked-files=no"), source).strip():
        raise ValueError("The upstream tracked source must be clean")
    if not (source / "node_modules" / "yargs").exists():
        raise ValueError("Install dependencies in the external source checkout")
    declared_lock = Path(__file__).with_name("oref0-package-lock.json").read_bytes()
    local_lock = (source / "package-lock.json").read_bytes()
    if digest(local_lock) != digest(declared_lock):
        raise ValueError("The external checkout must use the OpenT1D oref0 npm lock")
    packages = json.loads(local_lock)["packages"]
    licenses = Counter()
    missing_licenses = []
    for path, item in packages.items():
        if not path:
            continue
        installed = source / path / "package.json"
        if (
            not installed.exists()
            or json.loads(installed.read_text()).get("version") != item["version"]
        ):
            raise ValueError(f"Installed package does not match npm lock: {path}")
        license_name = item.get("license")
        if license_name:
            licenses[license_name] += 1
        else:
            missing_licenses.append(path)
    return {
        "sha256": digest(local_lock),
        "installed_packages": len(packages) - 1,
        "license_expressions": dict(sorted(licenses.items())),
        "packages_without_lock_license": missing_licenses,
    }


def replay_revision(source, revision, root, label):
    if revision == COMMIT:
        checkout = source
    else:
        checkout = root / label
        checked(("git", "worktree", "add", "--detach", str(checkout), revision), source)
    alias = root / f"alias-{label}"
    alias.mkdir()
    (alias / "oref0").symlink_to(checkout, target_is_directory=True)
    env = dict(os.environ, NODE_PATH=f"{alias}:{source / 'node_modules'}")
    example_command = ORIGIN_COMMAND if label == "example_introduction" else EXAMPLE_COMMAND
    output = checked(example_command, checkout, env)
    actual = json.loads(output)
    expected_file = checkout / "examples/suggested.json"
    expected = json.loads(expected_file.read_text())
    item = {
        "commit": checked(("git", "rev-parse", "HEAD"), checkout).strip(),
        "fixture_last_changed_commit": checked(
            ("git", "log", "-1", "--format=%H", "--", "examples/suggested.json"), checkout
        ).strip(),
        "fixture_sha256": digest(expected_file.read_bytes()),
        "command": list(example_command),
        "output_sha256": digest(output.encode()),
        "parity": actual == expected,
        "action": {key: actual.get(key) for key in ("rate", "duration", "insulinReq")},
        "expected_action": {key: expected.get(key) for key in ("rate", "duration", "insulinReq")},
        "different_fields": different_fields(expected, actual),
    }
    return item, checkout, env


def replay_origin_chain(checkout, root, env):
    replay = root / "origin-chain"
    replay.mkdir()
    for path in (checkout / "examples").glob("*.json"):
        shutil.copyfile(path, replay / path.name)
    tools = (
        (
            "iob.json",
            "oref0-calculate-iob.js",
            ("pumphistory.json", "profile.json", "clock.json", "autosens.json"),
        ),
        (
            "meal.json",
            "oref0-meal.js",
            (
                "pumphistory.json",
                "profile.json",
                "clock.json",
                "glucose.json",
                "basal_profile.json",
                "carbhistory.json",
            ),
        ),
        (
            "suggested.json",
            "oref0-determine-basal.js",
            (
                "iob.json",
                "temp_basal.json",
                "glucose.json",
                "profile.json",
                "autosens.json",
                "meal.json",
                "--microbolus",
                "--currentTime",
                "1527924300000",
            ),
        ),
    )
    result = {}
    for name, program, arguments in tools:
        output = checked(("node", str(checkout / "bin" / program), *arguments), replay, env)
        (replay / name).write_text(output)
        expected = json.loads((checkout / "examples" / name).read_text())
        actual = json.loads(output)
        result[name] = {
            "parity": actual == expected,
            "actual_sha256": digest(output.encode()),
            "different_fields": different_fields(expected, actual),
        }
    return result


def audit(source):
    source = Path(source).resolve()
    lock = current_clean_checkout(source)
    report = {
        "schema": "opent1d.c1.oref0-example-history/1",
        "revisions": {},
        "dependency_lock": lock,
        "dependency_scope": (
            "All revisions use the OpenT1D-locked current-source dependency graph; "
            "historical dependency graphs and Node 8 have not been reproduced."
        ),
        "runtime_node": checked(("node", "--version"), source).strip(),
        "runtime_npm": checked(("npm", "--version"), source).strip(),
    }
    with tempfile.TemporaryDirectory(prefix="oref0-example-history-") as temporary:
        root = Path(temporary)
        try:
            for label, revision in REVISIONS.items():
                item, checkout, env = replay_revision(source, revision, root, label)
                report["revisions"][label] = item
                if label == "example_introduction":
                    report["introduction_full_chain"] = replay_origin_chain(checkout, root, env)
        finally:
            for label, revision in REVISIONS.items():
                if revision != COMMIT and (root / label).exists():
                    checked(("git", "worktree", "remove", "--force", str(root / label)), source)
    report["matching_source_fixture_pairs"] = [
        label for label, item in report["revisions"].items() if item["parity"]
    ]
    baseline = json.loads(Path(__file__).with_name("oref0-source-baseline.json").read_text())
    current = source_audit(source)
    current_action = report["revisions"]["preflight_source"]["action"]
    checks = {
        "source_commit": baseline["source_commit"] == COMMIT,
        "npm_lock": baseline["npm_lock_sha256"] == lock["sha256"],
        "node_version": baseline["node_version"] == report["runtime_node"],
        "npm_version": baseline["npm_version"] == report["runtime_npm"],
        "upstream_core_test_file": baseline["source_test_file_sha256"]
        == digest((source / "tests/determine-basal.test.js").read_bytes()),
        "upstream_core_tests": baseline["source_core_tests_passing"]
        == current["core_tests"]["passing"]
        and current["core_tests"]["exit_code"] == 0,
        "locked_cli_output": baseline["locked_cli_output_sha256"]
        == current["example"]["actual_sha256"]
        == report["revisions"]["preflight_source"]["output_sha256"],
        "locked_cli_action": baseline["locked_cli_action"]
        == {
            "rate_u_hour": current_action["rate"],
            "duration_min": current_action["duration"],
            "insulin_req_u": current_action["insulinReq"],
        },
        "upstream_example_remains_different": (
            current["example"]["expected_sha256"] == baseline["upstream_committed_example_sha256"]
            and report["revisions"]["preflight_source"]["parity"]
            == baseline["upstream_committed_example_parity"]
        ),
    }
    report["local_source_baseline"] = {
        "checks": checks,
        "pass": all(checks.values()),
        "role": "Upstream source tests plus local CLI fingerprint; no example parity",
    }
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(f"{args.output}: matching_source_fixture_pairs={result['matching_source_fixture_pairs']}")


if __name__ == "__main__":
    main()
