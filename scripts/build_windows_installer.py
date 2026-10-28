"""Build an offline Windows candidate from tracked source and locked portable runtimes."""

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "opent1d.windows-package/1"
MAX_RUNTIME_BYTES = 64 * 1024 * 1024
MAX_UNPACKED_BYTES = 512 * 1024 * 1024
MAX_SOURCE_BYTES = 512 * 1024 * 1024
BUILD_ID = re.compile(r"[a-z0-9][a-z0-9.-]{0,79}\Z")
EXCLUDED = {".git", ".venv", "__pycache__", "node_modules", "results", "private", "raw"}


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def dump(path, value):
    path.write_bytes((json.dumps(value, sort_keys=True, indent=2) + "\n").encode("utf-8"))


def git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root, timeout=60)


def source_inventory(root, *, allow_dirty=False):
    """Only tracked, regular files; never sweep a working directory into a release."""
    revision = git(root, "rev-parse", "HEAD").decode().strip()
    dirty = bool(git(root, "status", "--porcelain", "--untracked-files=all"))
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Invalid source revision")
    committed = {}
    for entry in git(root, "ls-tree", "-r", "-z", revision).split(b"\0"):
        if not entry:
            continue
        metadata, name = entry.split(b"\t", 1)
        mode, kind, object_id = metadata.split()
        if kind != b"blob" or mode not in {b"100644", b"100755"}:
            raise ValueError("Only regular committed source files may be packaged")
        committed[name.decode("utf-8")] = object_id.decode("ascii")
    names = sorted(
        name.decode("utf-8") for name in git(root, "ls-files", "-z").split(b"\0") if name
    )
    # Index flags and clean filters can make `git status` hide byte differences.
    # A clean package must bind the actual delivered bytes to this exact commit.
    dirty |= set(names) != set(committed)
    total, files = 0, {}
    for name in names:
        parts = PurePosixPath(name).parts
        if any(part in EXCLUDED or part == ".env" or part.startswith(".env.") for part in parts):
            raise ValueError("Tracked private/generated material is not permitted in an installer")
        path = root / name
        if any(parent.is_symlink() for parent in (path, *path.parents)):
            raise ValueError("Linked source paths are not permitted in an installer")
        try:
            info = path.lstat()
        except FileNotFoundError as exc:
            raise ValueError("A tracked source file is missing") from exc
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("Only regular tracked source files may be packaged")
        total += info.st_size
        if total > MAX_SOURCE_BYTES or len(files) >= 20000:
            raise ValueError("Source payload exceeds its size/count limit")
        contents = path.read_bytes()
        if len(contents) != info.st_size:
            raise ValueError("Source changed during inventory")
        object_id = hashlib.sha1(b"blob " + str(len(contents)).encode() + b"\0" + contents)
        dirty |= object_id.hexdigest() != committed.get(name)
        files[name] = {"sha256": hashlib.sha256(contents).hexdigest(), "bytes": len(contents)}
    if dirty and not allow_dirty:
        raise ValueError(
            "Commit the complete source before building; --allow-dirty is for local tests"
        )
    return {"revision": revision, "dirty": dirty, "files": files}


def download_runtime(lock, destination):
    if destination.exists():
        if sha256(destination) != lock["sha256"]:
            raise ValueError("Cached CPython archive does not match the runtime lock")
        return
    temporary = destination.with_suffix(".download")
    try:
        with (
            urllib.request.urlopen(lock["url"], timeout=60) as response,
            temporary.open("xb") as out,
        ):
            total = 0
            while block := response.read(1024 * 1024):
                total += len(block)
                if total > MAX_RUNTIME_BYTES:
                    raise ValueError("CPython download exceeds its byte limit")
                out.write(block)
        if sha256(temporary) != lock["sha256"]:
            raise ValueError("Downloaded CPython archive does not match the runtime lock")
        temporary.rename(destination)
    finally:
        temporary.unlink(missing_ok=True)


def extract_runtime(archive, destination, lock):
    if archive.stat().st_size > MAX_RUNTIME_BYTES or sha256(archive) != lock["sha256"]:
        raise ValueError("CPython archive does not match the runtime lock")
    if lock.get("archive_format") == "tar.gz":
        extract_portable(archive, destination, lock)
        return
    with zipfile.ZipFile(archive) as bundle:
        names, total = set(), 0
        for entry in bundle.infolist():
            path = PurePosixPath(entry.filename)
            if (
                not path.parts
                or path.is_absolute()
                or any(part in {".", ".."} or ":" in part for part in path.parts)
                or "\\" in entry.filename
                or entry.filename.casefold() in names
                or stat.S_ISLNK(entry.external_attr >> 16)
            ):
                raise ValueError("Unsafe or duplicate CPython archive entry")
            names.add(entry.filename.casefold())
            total += entry.file_size
            if total > MAX_UNPACKED_BYTES or len(names) > 1000:
                raise ValueError("CPython archive exceeds its unpacked limits")
        destination.mkdir()
        for entry in bundle.infolist():
            target = destination / entry.filename
            if entry.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with bundle.open(entry) as source, target.open("xb") as out:
                    shutil.copyfileobj(source, out)
    digits = "".join(lock["version"].split(".")[:2])
    for required in ("python.exe", "pythonw.exe", f"python{digits}.zip", lock["license_file"]):
        if not (destination / required).is_file():
            raise ValueError("CPython archive is missing a required runtime component")
    # -S/-m workers retain a real interpreter and the same fixed source root.
    # Do not import site, consume PYTHONPATH or expose user-installed packages.
    (destination / f"python{digits}._pth").write_bytes(
        f"python{digits}.zip\n.\n../app\n".encode("ascii")
    )


def extract_portable(archive, destination, lock):
    with tarfile.open(archive, "r:gz") as bundle:
        entries, names, total = [], set(), 0
        for entry in bundle.getmembers():
            name = entry.name.removeprefix(lock["archive_prefix"])
            if not name:
                continue
            path = PurePosixPath(name)
            if (
                not entry.name.startswith(lock["archive_prefix"])
                or path.is_absolute()
                or any(part in {".", ".."} or ":" in part for part in path.parts)
                or "\\" in name
                or name.casefold() in names
                or not (entry.isfile() or entry.isdir())
            ):
                raise ValueError("Unsafe or duplicate portable Python entry")
            total += entry.size
            names.add(name.casefold())
            if total > MAX_UNPACKED_BYTES or len(names) > 30000:
                raise ValueError("Portable Python archive exceeds limits")
            entries.append((entry, path))
        destination.mkdir(parents=True)
        for entry, relative in entries:
            target = destination / relative
            if entry.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with bundle.extractfile(entry) as source, target.open("xb") as out:
                    shutil.copyfileobj(source, out)
    for required in (
        "python.exe",
        "pythonw.exe",
        "python312.dll",
        "Lib/os.py",
        lock["license_file"],
    ):
        if not (destination / required).is_file():
            raise ValueError("Portable Python archive lacks a required component")
    # Bytecode contains build-host paths and is regenerable; keep source and licenses.
    for path in list(destination.rglob("__pycache__")):
        shutil.rmtree(path)


def require_private_native_build(root):
    """Public source preparation does not clear native-runtime redistribution."""
    if (root / "publication-snapshot.json").exists():
        raise ValueError(
            "Public source snapshots exclude bundled native Windows builds; "
            "see docs/publication-security.md. Use a reviewed private integration checkout."
        )


def stage_payload(
    root, destination, archive, lock, *, build_id=None, allow_dirty=False, dependency_cache=None
):
    root = root.resolve()
    require_private_native_build(root)
    identity = source_inventory(root, allow_dirty=allow_dirty)
    label = build_id or "ot058-" + identity["revision"][:12]
    if not BUILD_ID.fullmatch(label):
        raise ValueError("Build id must contain 1–80 lowercase letters, digits, dots or hyphens")
    destination.mkdir(parents=True, exist_ok=False)
    source = destination / "app"
    for name, expected in identity["files"].items():
        target = source / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / name, target)
        if sha256(target) != expected["sha256"]:
            raise ValueError("Source changed during packaging")
    extract_runtime(archive, destination / "runtime", lock)
    notices = root / "packaging/windows/THIRD-PARTY-NOTICES.txt"
    shutil.copyfile(notices, destination / "THIRD-PARTY-NOTICES.txt")
    runtime_projects, dependencies = {}, {}
    if lock.get("archive_format") == "tar.gz":
        # Script invocation and import-as-module both resolve this sibling module.
        try:
            from scripts.windows_dependencies import assemble
        except ModuleNotFoundError:
            from windows_dependencies import assemble
        cache = dependency_cache or destination.parent / "dependency-cache"
        runtime_projects, dependencies = assemble(
            root,
            destination,
            cache,
            lambda target: extract_runtime(archive, target, lock),
        )
    manifest = {
        "schema": SCHEMA,
        "build_id": None,
        "kind": "internal-installation-candidate",
        "source": identity,
        "runtime": lock,
        "platform": {"system": "Windows", "minimum_release": "11", "architecture": "amd64"},
        "workflows": [
            "mmtt-sensitivity",
            "mmtt-sampling",
            "m3-forecast",
            "m3-compare",
            "m4-study-secure",
            "maintained-campaigns",
            "durable-readers",
            "m5-report",
        ],
        "runtime_projects": runtime_projects,
        "runtime_paths": {
            project: record["python"] for project, record in runtime_projects.items()
        },
        "dependencies": dependencies,
        "native_windows_verification": "not-established-by-packaging",
        "payload_files": {
            path.relative_to(destination).as_posix(): {
                "sha256": sha256(path),
                "bytes": path.stat().st_size,
            }
            for path in sorted(destination.rglob("*"))
            if path.is_file()
        },
    }
    fingerprint = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()[:16]
    manifest["build_id"] = label + "-" + fingerprint
    dump(destination / "package-manifest.json", manifest)
    epoch = int(git(root, "show", "-s", "--format=%ct", "HEAD").decode().strip())
    for path in destination.rglob("*"):
        if path.is_file():
            os.utime(path, (epoch, epoch))
    return manifest


def nsis_literal(value):
    """Escape NSIS preprocessor literals without permitting directive injection."""
    if any(char in str(value) for char in "\r\n\0"):
        raise ValueError("Invalid installer path")
    return str(value).replace("$", "$$").replace('"', '$\\"')


def compile_installer(root, payload, output, manifest, compiler):
    version = subprocess.check_output([compiler, "-VERSION"], text=True, timeout=30).strip()
    if version != "v" + manifest["runtime"]["nsis_version"]:
        raise ValueError("Use the NSIS compiler version declared in runtime-lock.json")
    output = output.resolve()
    generated = output.parent / "build.nsi"
    generated.write_text(
        "\n".join(
            f'!define {key} "{nsis_literal(value)}"'
            for key, value in {
                "PAYLOAD": payload.resolve(),
                "OUTPUT_FILE": output,
                "BUILD_ID": manifest["build_id"],
                "SOURCE_ROOT": root.resolve(),
            }.items()
        )
        + f'\n!include "{nsis_literal(root.resolve() / "packaging/windows/opent1d.nsi")}"\n',
        encoding="utf-8",
    )
    environment = os.environ.copy()
    environment["SOURCE_DATE_EPOCH"] = (
        git(root, "show", "-s", "--format=%ct", "HEAD").decode().strip()
    )
    subprocess.run([compiler, "-V2", str(generated)], check=True, env=environment, timeout=900)
    with output.open("rb") as stream:
        signature = stream.read(2)
    if signature != b"MZ":
        raise ValueError("Compiler did not produce a Windows executable")
    checksum = sha256(output)
    output.with_suffix(output.suffix + ".sha256").write_text(
        f"{checksum}  {output.name}\n", encoding="ascii"
    )
    return {
        "file": output.name,
        "sha256": checksum,
        "bytes": output.stat().st_size,
        "nsis": version,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, required=True, help="New build output directory")
    parser.add_argument(
        "--runtime-archive", type=Path, help="Existing locked Python archive; otherwise download"
    )
    parser.add_argument(
        "--dependency-cache", type=Path, help="Reusable hash-verified download cache"
    )
    parser.add_argument("--makensis", default="makensis")
    parser.add_argument("--build-id")
    parser.add_argument(
        "--allow-dirty", action="store_true", help="Local test only; records dirty state"
    )
    parser.add_argument("--stage-only", action="store_true", help="Do not compile an installer")
    args = parser.parse_args()
    root, output = args.source_root.resolve(), args.output.resolve()
    if output.exists():
        parser.error("Choose a new output directory; existing builds are never overwritten")
    try:
        require_private_native_build(root)
        lock = json.loads(
            (root / "packaging/windows/runtime-lock.json").read_text(encoding="utf-8")
        )
        source_inventory(root, allow_dirty=args.allow_dirty)
        output.mkdir(parents=True)
        archive = args.runtime_archive
        if archive is None:
            archive = output / (
                "python-" + lock["version"] + "." + lock.get("archive_format", "zip")
            )
            download_runtime(lock, archive)
        manifest = stage_payload(
            root,
            output / "payload",
            archive,
            lock,
            build_id=args.build_id,
            allow_dirty=args.allow_dirty,
            dependency_cache=args.dependency_cache,
        )
        result = {"build_id": manifest["build_id"], "source": manifest["source"]["revision"]}
        if not args.stage_only:
            installer = output / f"OpenT1D-{manifest['build_id']}-windows-x64.exe"
            result["installer"] = compile_installer(
                root,
                output / "payload",
                installer,
                manifest,
                args.makensis,
            )
        dump(output / "build-result.json", result)
        print(json.dumps(result, indent=2))
    except (OSError, ValueError, subprocess.SubprocessError, zipfile.BadZipFile) as error:
        print(f"Windows packaging failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
