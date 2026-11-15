"""Build the bounded desktop workspace with locked Electron and real CPython."""

import argparse
import json
import os
import platform
import plistlib
import shutil
import stat
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.build_mac_app import extract_runtime as extract_mac  # noqa: E402
from scripts.build_mac_app import runtime_materials  # noqa: E402
from scripts.build_sdk import build as build_sdk  # noqa: E402
from scripts.build_windows_installer import (  # noqa: E402
    sha256,
    source_inventory,
)


def download(lock, destination):
    if destination.exists():
        if sha256(destination) != lock["sha256"]:
            raise ValueError("Cached desktop archive differs from its lock")
        return
    temporary = destination.with_suffix(".download")
    try:
        with urllib.request.urlopen(lock["url"], timeout=90) as source, temporary.open("xb") as out:
            count = 0
            while block := source.read(1024 * 1024):
                count += len(block)
                if count > 512 * 1024 * 1024:
                    raise ValueError("Desktop archive exceeds its download limit")
                out.write(block)
        if sha256(temporary) != lock["sha256"]:
            raise ValueError("Desktop archive checksum differs")
        temporary.rename(destination)
    finally:
        temporary.unlink(missing_ok=True)


def extract_electron(archive, destination):
    """Retain the locked framework aliases; never write through an alias."""
    with zipfile.ZipFile(archive) as bundle:
        entries, names, links, total = [], set(), {}, 0
        for entry in bundle.infolist():
            path = PurePosixPath(entry.filename)
            if (
                path.is_absolute()
                or not path.parts
                or any(p in {".", ".."} or ":" in p for p in path.parts)
                or "\\" in entry.filename
                or entry.filename.casefold() in names
            ):
                raise ValueError("Unsafe or duplicate desktop archive entry")
            names.add(entry.filename.casefold())
            total += entry.file_size
            if total > 2 * 1024**3 or len(names) > 30000:
                raise ValueError("Desktop archive exceeds its extraction limit")
            if stat.S_ISLNK(entry.external_attr >> 16):
                target = bundle.read(entry).decode()
                if (
                    len(target) > 4096
                    or Path(target).is_absolute()
                    or not (destination / path.parent / target)
                    .resolve()
                    .is_relative_to(destination.resolve())
                ):
                    raise ValueError("Desktop framework alias escapes its bundle")
                links[path] = target
            entries.append((path, entry))
        for path, entry in entries:
            if any(parent in links for parent in path.parents):
                raise ValueError("Desktop archive writes through a framework alias")
            target = destination.joinpath(*path.parts)
            if path in links:
                continue
            if entry.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with bundle.open(entry) as source, target.open("xb") as out:
                    shutil.copyfileobj(source, out)
                target.chmod(0o755 if entry.external_attr >> 16 & 0o111 else 0o644)
        for path, link in links.items():
            target = destination.joinpath(*path.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.symlink_to(link)


def rebrand_mac(app):
    for helper in sorted((app / "Contents/Frameworks").glob("Electron Helper*.app")):
        plist = helper / "Contents/Info.plist"
        data = plistlib.loads(plist.read_bytes())
        old = data.get("CFBundleExecutable", helper.stem)
        new = old.replace("Electron", "OpenT1D")
        (helper / "Contents/MacOS" / old).rename(helper / "Contents/MacOS" / new)
        data.update(CFBundleExecutable=new, CFBundleName=new, CFBundleDisplayName=new)
        data["CFBundleIdentifier"] = data["CFBundleIdentifier"].replace(
            "com.github.Electron", "org.opent1d.conceptv1"
        )
        plist.write_bytes(plistlib.dumps(data))
        helper.rename(helper.with_name(helper.name.replace("Electron", "OpenT1D")))
    plist = app / "Contents/Info.plist"
    data = plistlib.loads(plist.read_bytes())
    (app / "Contents/MacOS/Electron").rename(app / "Contents/MacOS/OpenT1D")
    data.update(
        CFBundleExecutable="OpenT1D",
        CFBundleName="OpenT1D",
        CFBundleDisplayName="OpenT1D",
        CFBundleIdentifier="org.opent1d.conceptv1",
        CFBundleShortVersionString="0.0.0",
        CFBundleVersion="0.0.0",
    )
    data.pop("ElectronTeamID", None)
    plist.write_bytes(plistlib.dumps(data))
    return data.get("LSMinimumSystemVersion")


def inventory(directory):
    return {
        path.relative_to(directory).as_posix(): {"link": os.readlink(path)}
        if path.is_symlink()
        else {"bytes": path.stat().st_size, "sha256": sha256(path)}
        for path in sorted(directory.rglob("*"))
        if path.is_symlink() or path.is_file()
    }


def build(output, cache, target, *, allow_dirty=False):
    identity = source_inventory(ROOT, allow_dirty=allow_dirty)
    if target != "darwin-arm64":
        raise ValueError("This increment targets Mac Apple Silicon only")
    if ROOT == output or ROOT in output.parents:
        raise ValueError("Choose a desktop output directory outside the source checkout")
    if output.exists() or output.is_symlink():
        raise ValueError("Choose a fresh desktop build destination")
    if (platform.system(), platform.machine()) != ("Darwin", "arm64"):
        raise ValueError("Build and sign the Mac bundle on Apple Silicon macOS")
    output.mkdir(parents=True)
    cache.mkdir(parents=True, exist_ok=True)
    lock = json.loads((ROOT / "packaging/desktop/runtime-lock.json").read_text())
    selected = lock["targets"][target]
    electron = cache / ("electron-" + target + ".zip")
    python_lock = json.loads((ROOT / selected["python_lock"]).read_text())
    python_archive = cache / selected["python_cache"]
    download(selected, electron)
    download(python_lock, python_archive)
    extracted = output / "application"
    extracted.mkdir()
    extract_electron(electron, extracted)
    application = extracted / "Electron.app"
    application.rename(extracted / "OpenT1D.app")
    application = extracted / "OpenT1D.app"
    minimum = rebrand_mac(application)
    resources = application / "Contents/Resources"
    shutil.copyfile(ROOT / "packaging/desktop/icon.icns", resources / "opent1d.icns")
    plist = application / "Contents/Info.plist"
    data = plistlib.loads(plist.read_bytes())
    data["CFBundleIconFile"] = "opent1d.icns"
    plist.write_bytes(plistlib.dumps(data))
    executable = application / "Contents/MacOS/OpenT1D"
    default = resources / "default_app.asar"
    default.unlink(missing_ok=True)
    shutil.copyfile(ROOT / "packaging/desktop/icon.png", resources / "opent1d.png")
    shell = resources / "app"
    shell.mkdir()
    for name in ("package.json", "main.cjs", "preload.cjs"):
        shutil.copyfile(ROOT / "packaging/desktop" / name, shell / name)
    backend = resources / "backend"
    backend.mkdir()
    extract_mac(python_archive, backend / "runtime", python_lock)
    materials_cache = cache / ("materials-" + target)
    materials_cache.mkdir(exist_ok=True)
    runtime_materials(backend, materials_cache, python_lock)
    sdk = build_sdk(
        output / "sdk-build",
        mmtt_only=True,
        allow_dirty=allow_dirty,
        build_label="concept-v1-desktop",
    )
    site = backend / "lib/python3.12/site-packages"
    site.mkdir(parents=True)
    with zipfile.ZipFile(sdk["wheel"]) as wheel:
        for name in wheel.namelist():
            if name.startswith("opent1d_lab/") and not name.endswith("/"):
                path = PurePosixPath(name)
                if ".." in path.parts:
                    raise ValueError("Invalid SDK wheel entry")
                target_file = site.joinpath(*path.parts)
                target_file.parent.mkdir(parents=True, exist_ok=True)
                target_file.write_bytes(wheel.read(name))
    shutil.copyfile(ROOT / "packaging/desktop/backend.py", backend / "entry.py")
    notices = resources / "licenses"
    notices.mkdir(exist_ok=True)
    for name in ("LICENSE", "NOTICE"):
        shutil.copyfile(ROOT / name, notices / ("OpenT1D-" + name + ".txt"))
    for name in ("LICENSE", "LICENSES.chromium.html"):
        shutil.copyfile(extracted / name, notices / ("Electron-" + name))
    record = {
        "schema": "opent1d.concept-desktop-build/1",
        "kind": "unsigned-internal-desktop-candidate",
        "source": {key: identity[key] for key in ("revision", "dirty")},
        "target": target,
        "minimum_system_declaration": minimum,
        "electron": {"version": lock["electron"], "sha256": selected["sha256"]},
        "python": python_lock,
        "sdk": sdk,
        "scope": "Concept v1 launcher and Study editor; existing two-task MMTT SDK",
        "public_release": False,
    }
    (resources / "desktop-build.json").write_text(json.dumps(record, indent=2) + "\n")
    subprocess.run(
        [
            "/usr/bin/codesign",
            "--force",
            "--deep",
            "--sign",
            "-",
            "--entitlements",
            str(ROOT / "packaging/desktop/entitlements.plist"),
            str(application),
        ],
        check=True,
        capture_output=True,
        timeout=120,
    )
    subprocess.run(
        ["/usr/bin/codesign", "--verify", "--deep", "--strict", str(application)],
        check=True,
        capture_output=True,
        timeout=60,
    )
    if source_inventory(ROOT, allow_dirty=allow_dirty) != identity:
        raise ValueError("Source changed during desktop packaging")
    record.update(
        application=str(application), executable=str(executable), files=inventory(application)
    )
    archive = output / ("OpenT1D-Concept-v1-" + target + ".zip")
    subprocess.run(
        [
            "/usr/bin/ditto",
            "-c",
            "-k",
            "--sequesterRsrc",
            "--keepParent",
            str(application),
            str(archive),
        ],
        check=True,
        timeout=120,
    )
    record.update(archive=str(archive), archive_sha256=sha256(archive))
    (output / "build-result.json").write_text(json.dumps(record, indent=2) + "\n")
    return {key: value for key, value in record.items() if key != "files"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--target", choices=("darwin-arm64",), required=True)
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args()
    print(
        json.dumps(
            build(
                args.output.absolute(),
                args.cache.absolute(),
                args.target,
                allow_dirty=args.allow_dirty,
            ),
            sort_keys=True,
        )
    )
