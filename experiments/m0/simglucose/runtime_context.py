"""One audited lock extension; retain all original historical output criteria."""

import copy
import hashlib
import json
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASELINES = {
    "m0": "experiments/m0/simglucose/baseline.json",
    "m1": "experiments/m1/baseline.json",
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def reviewed_extension():
    """Verify the exact locks and prove that only pinned GlucoSim was added."""
    folder = ROOT / "experiments/m0/simglucose/runtime-context"
    raw = (folder / "review.json").read_bytes()
    review = json.loads(raw)
    if review["schema"] != "opent1d.runtime-extension/1":
        raise ValueError("Unsupported historical runtime extension")
    old = (folder / "legacy-uv.lock").read_bytes()
    current = (ROOT / "experiments/m0/simglucose/uv.lock").read_bytes()
    if (
        digest(old) != review["historical_lock_sha256"]
        or digest(current) != review["current_lock_sha256"]
    ):
        raise ValueError("Historical runtime extension differs: lock_sha256")
    before = tomllib.loads(old.decode())
    after = tomllib.loads(current.decode())
    installed = {
        package["name"]: package["version"]
        for package in after["package"]
        if package["source"] != {"virtual": "."}
    }
    inventory = {
        re.sub(r"[-_.]+", "-", name).lower(): version
        for name, version in review["m0_packages"].items()
    }
    if len(inventory) != len(review["m0_packages"]) or inventory != installed:
        raise ValueError("Historical M0 package inventory differs from the complete lock")
    added = review["added_lock_package"]
    if added["name"] != "glucosim" or review["added_packages"] != {"glucosim": added["version"]}:
        raise ValueError("Historical runtime extension is not the declared GlucoSim addition")
    matches = [package for package in after["package"] if package["name"] == "glucosim"]
    if matches != [added] or any(package["name"] == "glucosim" for package in before["package"]):
        raise ValueError("Historical runtime extension package differs")
    after["package"].remove(added)
    project = next(
        package
        for package in after["package"]
        if package["name"] == "opent1d-m0-simglucose-reference"
    )
    project["dependencies"].remove({"name": "glucosim"})
    project["metadata"]["requires-dist"].remove(
        {"name": "glucosim", "git": added["source"]["git"].split("#")[0]}
    )
    if after != before:
        raise ValueError("Historical runtime extension changes existing locked dependencies")
    canonical = {}
    for kind, path in BASELINES.items():
        data = (ROOT / path).read_bytes()
        if digest(data) != review["baseline_sha256"][kind]:
            raise ValueError("Historical baseline bytes changed during runtime extension")
        canonical[kind] = json.loads(data)
    if review["packages"] != canonical["m1"]["shared"]["packages"] | review["added_packages"]:
        raise ValueError("Historical runtime extension changes existing package versions")
    if any(
        review["packages"].get(name) != version for name, version in review["m0_packages"].items()
    ):
        raise ValueError("Historical M0 package inventory differs from the reviewed versions")
    if review["m0_packages"].get("glucosim") != review["added_packages"]["glucosim"]:
        raise ValueError("Historical M0 package inventory omits the reviewed GlucoSim version")
    return review, canonical, digest(raw)


def expected_context(kind, baseline, actual_lock, *, platform_key=None, actual_packages=None):
    """Choose original or explicitly reviewed context; never change observed data."""
    expected = copy.deepcopy(
        baseline["environments"][platform_key] if kind == "m0" else baseline.get("shared", {})
    )
    if "lock_sha256" not in expected or actual_lock == expected["lock_sha256"]:
        return expected, None
    review, canonical, review_sha = reviewed_extension()
    if (
        baseline != canonical[kind]
        or expected["lock_sha256"] != review["historical_lock_sha256"]
        or actual_lock != review["current_lock_sha256"]
    ):
        raise ValueError("Historical runtime context differs: lock_sha256; no reviewed extension")
    expected["lock_sha256"] = actual_lock
    if kind == "m0":
        # Legacy pkg_resources exposes setuptools vendored distributions after
        # its first import. Both complete inventories are recorded, not mixed.
        if actual_packages not in (review["m0_packages"], review["packages"]):
            raise ValueError("Historical M0 packages differ from both reviewed inventories")
        expected["packages"] = copy.deepcopy(actual_packages)
    else:
        expected["packages"] = review["packages"]
    evidence = {
        "id": review["id"],
        "review_sha256": review_sha,
        "checker_sha256": digest(Path(__file__).read_bytes()),
        "historical_lock_sha256": review["historical_lock_sha256"],
        "actual_lock_sha256": actual_lock,
        "added_packages": review["added_packages"],
    }
    return expected, evidence
