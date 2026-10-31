"""Build an internal dependency-free task wheel from an explicit source closure."""

import argparse
import hashlib
import importlib.metadata
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def copy_source(name, destination, source):
    from experiments.m3.researcher.intake import read_regular

    raw = read_regular(ROOT / name, 16 * 1024 * 1024, "SDK build source")
    if (
        name not in source["files"]
        or hashlib.sha256(raw).hexdigest() != source["files"][name]["sha256"]
    ):
        raise ValueError("Source changed during SDK staging: " + name)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(raw)


def source_closure():
    from experiments.observation_analysis import plan as mmtt
    from experiments.shared_contracts.inventory import reader_source_inventory
    from experiments.shared_contracts.selected import FIXTURES
    from experiments.shared_services import routes, sampling

    names = set(
        reader_source_inventory("experiments.shared_services.installed")[
            "reader_static_dependencies_sha256"
        ]
    )
    names.update(mmtt.ANCESTRY)
    names.add(mmtt.PROTOCOL.relative_to(ROOT).as_posix())
    for task in routes.TASKS:
        metadata = routes.reader_identity(task)
        names.update(metadata["trusted_sources_sha256"])
        names.update(metadata["reader_static_dependencies_sha256"])
        if task == "mmtt-sampling":
            names.update(sampling.native.ANCESTRY_FILES)
            names.update(routes.runtime_paths(sampling.binding()))
            names.update(
                {
                    "experiments/mmtt_sampling/protocol.json",
                    "experiments/mmtt_sampling/fixtures/design.json",
                }
            )
            continue
        if task == "m4-study-installed":
            from experiments.shared_services.installed_m4 import FIXTURES as native_fixtures

            payload = {"config.json": (native_fixtures / "m4-fasting.json").read_bytes()}
            names.update(
                path.relative_to(ROOT).as_posix()
                for path in native_fixtures.iterdir()
                if path.is_file()
            )
        else:
            payload = (
                {"config.json": (FIXTURES / "m4-fasting.json").read_bytes()}
                if task == "m4-study-secure"
                else {
                    name: (FIXTURES / ("mmtt-" + name)).read_bytes()
                    for name in ("package.json", "observations.csv", "settings.json")
                }
            )
        names.update(routes.runtime_paths(routes.boundary(task, payload)["binding"]))
    names.update(path.relative_to(ROOT).as_posix() for path in FIXTURES.iterdir() if path.is_file())
    for source in json.loads((FIXTURES / "m4-fasting.json").read_bytes())["sources"]:
        for key in ("model", "declaration"):
            names.add((FIXTURES / source[key]).resolve().relative_to(ROOT).as_posix())
    names.update(
        {
            "LICENSE",
            "NOTICE",
            "publication-snapshot.json",
            "publication-security.json",
            "experiments/setup/contract.json",
            "experiments/shared_services/connected_protocol.json",
            "experiments/shared_services/reader_compatibility.json",
        }
    )
    return sorted(names)


def build(output, *, allow_dirty=False, build_label="internal", mmtt_only=False):
    from experiments.durable_archives.storage import safe_path
    from scripts.build_windows_installer import source_inventory

    if importlib.metadata.version("setuptools") != "84.2.1":
        raise ValueError("Build with the separately locked root tooling (setuptools 84.2.1)")
    source = source_inventory(ROOT, allow_dirty=allow_dirty)
    output = safe_path(output, fresh=True)
    output.mkdir()
    project = output / "source"
    package = project / "opent1d_lab"
    package.mkdir(parents=True)
    facade = ROOT / "packaging/sdk"
    for path in sorted((facade / "opent1d_lab").glob("*.py")):
        copy_source(path.relative_to(ROOT).as_posix(), package / path.name, source)
    for path in sorted((facade / "opent1d_lab/_gui_assets").glob("*")):
        if path.is_file():
            copy_source(
                path.relative_to(ROOT).as_posix(), package / "_gui_assets" / path.name, source
            )
    (package / "_build_info.py").write_text("BUILD_LABEL = " + repr(build_label) + "\n")
    for name in ("pyproject.toml", "opent1d-lab"):
        copy_source((facade / name).relative_to(ROOT).as_posix(), project / name, source)
    (project / "opent1d-lab").chmod(0o755)
    copy_source("LICENSE", project / "LICENSE", source)
    for name in source_closure():
        destination = package / "_payload/app" / name
        copy_source(name, destination, source)
    files = {}
    for path in sorted(package.rglob("*")):
        if path.is_file():
            raw = path.read_bytes()
            files[path.relative_to(package).as_posix()] = {
                "sha256": hashlib.sha256(raw).hexdigest(),
                "bytes": len(raw),
            }
    descriptor = {
        "schema": "opent1d.installed-sdk/4" if mmtt_only else "opent1d.installed-sdk/3",
        "source": {key: source[key] for key in ("revision", "dirty")},
        "build_label": build_label,
        "files": files,
        "tasks": ["mmtt-sensitivity", "mmtt-sampling"]
        if mmtt_only
        else ["mmtt-sensitivity", "m4-study-secure", "m4-study-installed", "mmtt-sampling"],
        "native_execution": "unavailable-public-policy"
        if mmtt_only
        else "explicit-reviewed-attachment/1",
    }
    (package / "_manifest.json").write_text(json.dumps(descriptor, indent=2, sort_keys=True) + "\n")
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            "from setuptools.build_meta import build_wheel; build_wheel('dist')",
        ],
        cwd=project,
        capture_output=True,
        text=True,
        timeout=120,
    )
    (output / "build.log").write_text(result.stdout + result.stderr)
    result.check_returncode()
    wheels = list((project / "dist").glob("*.whl"))
    if len(wheels) != 1:
        raise ValueError("Expected exactly one SDK wheel")
    wheel = output / wheels[0].name
    shutil.copyfile(wheels[0], wheel)
    if source_inventory(ROOT, allow_dirty=allow_dirty) != source:
        raise ValueError("Source checkout changed before SDK build completed")
    receipt = {
        "source": descriptor["source"],
        "build_label": build_label,
        "wheel": str(wheel),
        "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
        "payload_files": len(files),
        "runtime_dependencies": [],
        "native_runtimes_shipped": False,
        "public_release": False,
        "tasks": descriptor["tasks"],
        "descriptor_schema": descriptor["schema"],
        "native_execution": descriptor["native_execution"],
        "descriptor_sha256": hashlib.sha256(
            (json.dumps(descriptor, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
        ).hexdigest(),
    }
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="development fixtures only; retained in artifact identity",
    )
    parser.add_argument("--build-label", default="internal")
    parser.add_argument("--mmtt-only", action="store_true", help="bounded internal MMTT candidate")
    args = parser.parse_args()
    print(
        json.dumps(
            build(
                args.output,
                allow_dirty=args.allow_dirty,
                build_label=args.build_label,
                mmtt_only=args.mmtt_only,
            ),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
