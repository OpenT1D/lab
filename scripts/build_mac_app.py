"""Build a clean-source, unsigned two-task Mac application with private CPython."""

import argparse
import hashlib
import json
import os
import platform
import plistlib
import re
import shutil
import stat
import subprocess
import tarfile
from pathlib import Path, PurePosixPath

try:
    from scripts.build_windows_installer import download_runtime, sha256, source_inventory
except ModuleNotFoundError:
    from build_windows_installer import download_runtime, sha256, source_inventory

ROOT = Path(__file__).resolve().parents[1]
TASKS = ["mmtt-sensitivity", "mmtt-sampling"]
MAX_UNPACKED = 256 * 1024 * 1024


def dump(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")


def extract_runtime(archive, destination, lock):
    """Omit only declared aliases; every staged entry remains an ordinary file."""
    if sha256(archive) != lock["sha256"]:
        raise ValueError("Mac runtime archive hash differs")
    if destination.exists() or any(p.is_symlink() for p in (destination, *destination.parents)):
        raise ValueError("Runtime staging requires a fresh unlinked directory")
    records, aliases, total = {}, {}, 0
    with tarfile.open(archive, "r:gz") as bundle:
        for member in bundle:
            path = PurePosixPath(member.name)
            if (
                path.is_absolute()
                or not path.parts
                or path.parts[0] != "python"
                or ".." in path.parts
                or "\\" in member.name
                or member.name in records
                or any(":" in part for part in path.parts)
            ):
                raise ValueError("Unsafe or duplicate runtime archive path")
            relative = path.relative_to("python").as_posix()
            records[member.name] = member
            total += member.size
            if total > MAX_UNPACKED or len(records) > 10000:
                raise ValueError("Mac runtime exceeds its bounded inventory")
            if member.issym():
                target = PurePosixPath(member.linkname)
                if (
                    target.is_absolute()
                    or len(target.parts) != 1
                    or target.name in {".", ".."}
                    or "\\" in member.linkname
                    or ":" in member.linkname
                    or lock["omitted_alias_links"].get(relative) != member.linkname
                ):
                    raise ValueError("Unexpected runtime link")
                aliases[relative] = member.linkname
            elif not member.isfile():
                raise ValueError("Runtime archive must contain regular files or declared aliases")
        if aliases != lock["omitted_alias_links"]:
            raise ValueError("Runtime alias inventory differs")
        for name in records:
            relative = PurePosixPath(name).relative_to("python")
            if any(p.as_posix() in aliases for p in relative.parents):
                raise ValueError("Runtime alias cannot be an archive parent")
        for name, member in records.items():
            if member.issym():
                continue
            relative = PurePosixPath(name).relative_to("python")
            if (
                "__pycache__" in relative.parts
                or relative.suffix in {".pyc", ".pyo"}
                or "site-packages" in relative.parts
                or "ensurepip" in relative.parts
                or (relative.parts[0] == "bin" and relative.name.startswith("pip"))
            ):
                continue
            target = destination.joinpath(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with bundle.extractfile(member) as source, target.open("xb") as output:
                shutil.copyfileobj(source, output)
            target.chmod(0o755 if member.mode & 0o111 else 0o644)
    return {"omitted_alias_links": aliases, "removed": ["pip", "ensurepip", "bytecode"]}


def _version(value):
    return tuple(map(int, value.split("."))) + (0,) * (3 - len(value.split(".")))


def _internal_path(value, binary, runtime):
    for prefix, base in (("@loader_path/", binary.parent), ("@executable_path/", runtime / "bin")):
        if value.startswith(prefix):
            candidate = (base / value[len(prefix) :]).resolve()
            if candidate.is_relative_to(runtime.resolve()):
                return candidate
    raise ValueError("Runtime library search path escapes the private runtime")


def macho_inventory(runtime, minimum, *, require_python=True):
    result = {}
    for path in sorted(runtime.rglob("*")):
        if not path.is_file():
            continue
        with path.open("rb") as stream:
            magic = stream.read(4)
        if magic in {
            b"\xca\xfe\xba\xbe",
            b"\xbe\xba\xfe\xca",
            b"\xce\xfa\xed\xfe",
            b"\xfe\xed\xfa\xce",
            b"\xfe\xed\xfa\xcf",
        }:
            raise ValueError("Only thin ARM64 Mach-O binaries may be delivered")
        if magic != b"\xcf\xfa\xed\xfe":
            continue
        architecture = subprocess.check_output(["/usr/bin/lipo", "-archs", path], text=True).strip()
        commands = subprocess.check_output(["/usr/bin/otool", "-l", path], text=True)
        targets = re.findall(r"\n\s+minos ([0-9.]+)", commands)
        if (
            architecture != "arm64"
            or not targets
            or any(_version(value) > _version(minimum) for value in targets)
        ):
            raise ValueError("Mach-O architecture or minimum OS differs")
        dependencies = []
        search_paths = [runtime / "lib"]
        for block in commands.split("Load command"):
            if re.search(r"\bcmd LC_RPATH\b", block):
                value = re.search(r"\n\s+path (.+?) \(offset", block).group(1)
                search_paths.append(_internal_path(value, path, runtime))
        for block in commands.split("Load command"):
            if re.search(r"\bcmd LC_(?:LOAD|LOAD_WEAK|REEXPORT)_DYLIB\b", block):
                dependency = re.search(r"\n\s+name (.+?) \(offset", block).group(1)
                if dependency.startswith("@rpath/"):
                    candidates = [
                        (p / dependency.removeprefix("@rpath/")).resolve() for p in search_paths
                    ]
                    if not any(
                        p.is_relative_to(runtime.resolve()) and p.is_file() for p in candidates
                    ):
                        raise ValueError(
                            "Runtime library dependency is missing or outside the runtime"
                        )
                elif dependency.startswith(("@loader_path/", "@executable_path/")):
                    if not _internal_path(dependency, path, runtime).is_file():
                        raise ValueError("Runtime library dependency is missing")
                elif not dependency.startswith(("/usr/lib/", "/System/Library/")):
                    raise ValueError("Runtime depends on a non-system external library")
                dependencies.append(dependency)
        result[path.relative_to(runtime).as_posix()] = {
            "architecture": architecture,
            "minimum_os": targets,
            "dependencies": dependencies,
        }
    if require_python and "bin/python3.12" not in result:
        raise ValueError("An actual ARM64 CPython executable is required")
    return result


def runtime_materials(payload, cache, lock):
    metadata = cache / "full.tar.zst"
    provider = cache / "provider.tar.gz"
    download_runtime(lock["metadata_archive"], metadata)
    download_runtime(lock["provider_sources"], provider)
    raw = subprocess.check_output(
        ["/usr/bin/tar", "-xOf", metadata, "python/PYTHON.json"], timeout=60
    )
    data = json.loads(raw)
    if (
        data["python_version"] != lock["version"]
        or data["target_triple"] != "aarch64-apple-darwin"
        or data["apple_sdk_deployment_target"] != lock["minimum_macos"]
    ):
        raise ValueError("Upstream runtime build metadata differs")
    (payload / "runtime-metadata").mkdir()
    (payload / "runtime-metadata/PYTHON.json").write_bytes(raw)
    sources = payload / "third-party-sources"
    sources.mkdir()
    shutil.copyfile(provider, sources / "python-build-standalone.tar.gz")
    licenses = payload / "third-party-licenses/python"
    licenses.mkdir(parents=True)
    with tarfile.open(provider) as bundle:
        for member in bundle:
            relative = PurePosixPath(member.name)
            if len(relative.parts) == 2 and relative.name.startswith("LICENSE"):
                if not member.isfile() or member.size > 1024 * 1024:
                    raise ValueError("Unsafe provider license")
                (licenses / relative.name).write_bytes(bundle.extractfile(member).read())
    if not (licenses / "LICENSE.cpython.txt").is_file():
        raise ValueError("Provider license inventory is incomplete")


def selected_source(identity):
    # Keep the current shared stdlib import/source-identity closure. Earlier task
    # helper names are ancestry, not permission to ship their native projects.
    python_directories = {
        "experiments/desktop",
        "experiments/gui",
        "experiments/workflows",
        "experiments/observation_analysis",
        "experiments/mmtt_sampling",
    }
    required = {
        "LICENSE",
        "NOTICE",
        "experiments/platform_files.py",
        "experiments/platform_process.py",
        "experiments/catalogue/storage.py",
        "experiments/durable_archives/storage.py",
        "experiments/m0/simglucose/recording.py",
        "experiments/m1/artifacts.py",
        "experiments/m1/contracts.py",
        "experiments/m1/metrics.py",
        "experiments/m1/validation.py",
        "experiments/m3/common.py",
        "experiments/m3/researcher/intake.py",
        "experiments/gui/contract.json",
        "experiments/observation_analysis/protocol.json",
        "experiments/mmtt_sampling/protocol.json",
        "experiments/mmtt_sampling/fixtures/design.json",
        "experiments/mmtt_sampling/fixtures/numerical-reference.json",
        "experiments/m4/c_peptide/model.py",
        "experiments/m4/c_peptide/reference.py",
        "experiments/m4/c_peptide/protocol.json",
        "experiments/ot053_feasibility/handoff.json",
        "docs/decisions/0067-mmtt-feasibility-boundary.md",
        "docs/decisions/0068-synthetic-observation-analysis-contract.md",
        "docs/decisions/0069-mmtt-sampling-reuse.md",
    }
    names = {
        name
        for name in identity["files"]
        if name in required
        or (PurePosixPath(name).parent.as_posix() in python_directories and name.endswith(".py"))
        or name.startswith(("experiments/gui/static/", "LICENSES/", "packaging/mac/"))
    }
    for name in tuple(names):
        for parent in PurePosixPath(name).parents:
            initializer = (parent / "__init__.py").as_posix()
            if initializer in identity["files"]:
                names.add(initializer)
    return {name: record for name, record in identity["files"].items() if name in names}


def build(root, output, cache):
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise ValueError("This candidate must be built and inspected on Apple Silicon macOS")
    identity = source_inventory(root)
    if output.exists() or output.is_symlink() or root == output or root in output.parents:
        raise ValueError("Choose a fresh output directory outside the source checkout")
    lock = json.loads((root / "packaging/mac/runtime-lock.json").read_text())
    if (lock["implementation"], lock["architecture"], lock["minimum_macos"]) != (
        "CPython",
        "arm64",
        "11.0",
    ):
        raise ValueError("Unsupported Mac runtime lock")
    cache.mkdir(parents=True, exist_ok=True)
    archive = cache / "runtime.tar.gz"
    download_runtime(lock, archive)
    output.mkdir(parents=True)
    app = output / "OpenT1D.app"
    contents = app / "Contents"
    payload = contents / "Resources/payload"
    source = payload / "app"
    source.mkdir(parents=True)
    delivered = selected_source(identity)
    for name, expected in delivered.items():
        target = source / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / name, target)
        if sha256(target) != expected["sha256"]:
            raise ValueError("Source changed during Mac packaging")
    transform = extract_runtime(archive, payload / "runtime", lock)
    binaries = macho_inventory(payload / "runtime", lock["minimum_macos"])
    runtime_materials(payload, cache, lock)
    shutil.copyfile(
        root / "packaging/mac/THIRD-PARTY-NOTICES.txt", payload / "THIRD-PARTY-NOTICES.txt"
    )
    compiler = Path(
        subprocess.check_output(["/usr/bin/xcrun", "--find", "clang"], text=True).strip()
    )
    sdk = Path(subprocess.check_output(["/usr/bin/xcrun", "--show-sdk-path"], text=True).strip())
    tool = {
        "path": str(compiler),
        "sha256": sha256(compiler),
        "version": subprocess.check_output([compiler, "--version"], text=True),
        "sdk": subprocess.check_output(["/usr/bin/xcrun", "--show-sdk-version"], text=True).strip(),
        "sdk_settings_sha256": sha256(sdk / "SDKSettings.json"),
    }
    build_id = (
        "mac-mmtt-"
        + identity["revision"][:12]
        + "-"
        + hashlib.sha256(
            json.dumps({"files": delivered, "runtime": lock, "tool": tool}, sort_keys=True).encode()
        ).hexdigest()[:12]
    )
    executable = contents / "MacOS/OpenT1D"
    executable.parent.mkdir()
    subprocess.run(
        [
            compiler,
            "-isysroot",
            sdk,
            "-fobjc-arc",
            "-arch",
            "arm64",
            "-mmacosx-version-min=11.0",
            "-Wl,-no_uuid",
            "-framework",
            "Cocoa",
            root / "packaging/mac/Launcher.m",
            "-o",
            executable,
        ],
        check=True,
        timeout=60,
    )
    launcher = macho_inventory(executable.parent, lock["minimum_macos"], require_python=False)
    if set(launcher) != {"OpenT1D"}:
        raise ValueError("The native application launcher is missing")
    with (contents / "Info.plist").open("wb") as stream:
        plistlib.dump(
            {
                "CFBundleExecutable": "OpenT1D",
                "CFBundleIdentifier": "org.opent1d.mmtt.internal",
                "CFBundleName": "OpenT1D MMTT",
                "CFBundlePackageType": "APPL",
                "LSMinimumSystemVersion": "11.0",
                "OpenT1DBuildID": build_id,
            },
            stream,
        )
    manifest = {
        "schema": "opent1d.desktop-package/2",
        "kind": "unsigned-internal-candidate",
        "build_id": build_id,
        "source": {**identity, "files": delivered},
        "runtime": lock,
        "toolchain": tool,
        "platform": {"system": "Darwin", "architecture": "arm64", "minimum_release": "11.0"},
        "capabilities": {"schema": "opent1d.desktop-capabilities/2", "tasks": TASKS},
        "runtime_paths": {".": "runtime/bin/python3.12"},
        "runtime_projects": {
            ".": {
                "directory": "runtime",
                "python": "runtime/bin/python3.12",
                "selectors": {
                    "packaging/mac/runtime-lock.json": sha256(
                        source / "packaging/mac/runtime-lock.json"
                    )
                },
                "distributions": {},
                "upstream_revisions": {},
            }
        },
        "runtime_transformation": transform,
        "runtime_binary_inspection": binaries,
        "launcher_binary_inspection": launcher,
        "payload_files": {
            p.relative_to(payload).as_posix(): {"sha256": sha256(p), "bytes": p.stat().st_size}
            for p in sorted(payload.rglob("*"))
            if p.is_file()
        },
    }
    dump(payload / "package-manifest.json", manifest)
    epoch = int(subprocess.check_output(["git", "show", "-s", "--format=%ct", "HEAD"], cwd=root))
    files = {}
    for path in sorted(app.rglob("*")):
        if path.is_symlink() or (not path.is_dir() and not stat.S_ISREG(path.stat().st_mode)):
            raise ValueError("The final Mac bundle contains a nonregular entry")
        if path.is_file():
            os.utime(path, (epoch, epoch))
            files[path.relative_to(app).as_posix()] = {
                "sha256": sha256(path),
                "bytes": path.stat().st_size,
            }
    result = {
        "schema": "opent1d.mac-build-result/1",
        "build_id": build_id,
        "source_revision": identity["revision"],
        "application": app.name,
        "files": files,
        "developer_id": False,
        "notarised": False,
    }
    dump(output / "build-result.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    args = parser.parse_args()
    result = build(ROOT, args.output.resolve(), args.cache.resolve())
    print(
        json.dumps(
            {
                "build_id": result["build_id"],
                "application": str(args.output / result["application"]),
            }
        )
    )


if __name__ == "__main__":
    main()
