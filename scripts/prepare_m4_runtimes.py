"""Explicit reviewed internal M4 candidate installation; no historical project setup."""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
PROJECTS = {
    role: "experiments/m4/installed_study/" + role
    for role in ("native", "observer", "build_inputs")
}


def validate_policy(root=ROOT):
    from experiments.m4.installed_study.common import protocol
    from experiments.setup.publication import check_install

    check_install(root, list(PROJECTS.values()))
    policy = json.loads((root / "publication-security.json").read_bytes())
    reviews = [
        x
        for x in policy.get("reviewed_native_candidates", [])
        if x.get("id") == "M4-STUDY-INSTALLED/1"
    ]
    if len(reviews) != 1 or set(reviews[0]["projects"]) != set(PROJECTS.values()):
        raise ValueError("Exact reviewed M4 candidate policy required")
    item = reviews[0]
    if item["review_file"] != "experiments/m4/installed_study/runtime-review.json":
        raise ValueError("Fixed M4 runtime review path required")
    raw = (root / item["review_file"]).read_bytes()
    if hashlib.sha256(raw).hexdigest() != item["review_sha256"]:
        raise ValueError("Runtime review changed")
    review = json.loads(raw)
    expected = {
        project + "/" + name
        for project in PROJECTS.values()
        for name in ("pyproject.toml", "uv.lock")
    }
    if set(review["selectors"]) != expected:
        raise ValueError("Complete six-selector review required")
    for name, identity in review["selectors"].items():
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != identity:
            raise ValueError("Reviewed runtime selector changed: " + name)
    protocol()
    return review


def prepare(output):
    from experiments.m4.installed_study.common import package_records
    from experiments.m4.installed_study.profile import distributions
    from experiments.platform_files import atomic_write_bytes
    from experiments.shared_services.execution import supervise
    from experiments.shared_services.store import encoded, safe_path
    from scripts.build_windows_installer import source_inventory

    review = validate_policy()
    output = safe_path(output, fresh=True)
    executable = shutil.which("uv")
    version = (
        ""
        if executable is None
        else subprocess.check_output([executable, "--version"], text=True).strip()
    )
    if version.split()[:2] != ["uv", "0.11.16"]:
        raise ValueError("Reviewed uv 0.11.16 required")
    source = source_inventory(ROOT, allow_dirty=True)
    output.mkdir()
    receipt = {
        "uv": version,
        "source": {k: source[k] for k in ("revision", "dirty")},
        "review_sha256": hashlib.sha256(
            (ROOT / "experiments/m4/installed_study/runtime-review.json").read_bytes()
        ).hexdigest(),
        "roles": {},
        "scientific_acceptance": "not established by installation",
        "public_bundle": False,
    }
    # The supervisor normally filters inherited UV selectors. Each role gets
    # an explicit current preparation environment, not an archive-owned value.
    for role, project in PROJECTS.items():
        environment = output / role
        args = [
            executable,
            "sync",
            "--locked",
            "--no-dev",
            "--no-default-groups",
            "--link-mode",
            "copy",
            "--project",
            str(ROOT / project),
            "--python",
            sys.executable,
        ]
        from experiments.setup.core import environment as setup_environment

        environment_variables = setup_environment(output / "cache", offline=False)
        environment_variables.update(
            UV_PROJECT_ENVIRONMENT=str(environment), UV_CACHE_DIR=str(output / "cache")
        )
        status = supervise(
            args,
            output / (role + ".log"),
            timeout=1800,
            grace=30,
            header={"project": project, "action": "explicit-candidate-install"},
            environment=environment_variables,
        )
        receipt["roles"][role] = {"environment": str(environment), "supervision": status}
        atomic_write_bytes(output / "receipt.json", encoded(receipt))
        if status["status"] != "completed" or status["remaining_owned_processes"] != []:
            raise ValueError("Candidate installation failed; retain receipt/logs")
        site = environment / "lib/python3.12/site-packages"
        receipt["roles"][role].update(
            site_packages=str(site), **distributions(site, package_records(project))
        )
        atomic_write_bytes(output / "receipt.json", encoded(receipt))
    if source_inventory(ROOT, allow_dirty=True) != source:
        raise ValueError("Source changed during candidate installation")
    receipt["selectors"] = review["selectors"]
    atomic_write_bytes(output / "receipt.json", encoded(receipt))
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.output), sort_keys=True))


if __name__ == "__main__":
    main()
