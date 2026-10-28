"""Resolve immutable installed runtimes without Git, uv or host Python.

The package manifest records payload identity; it is not a signature or a claim
that the scientific model has been validated. Source checkouts retain their
separate locked development environments.
"""

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path, PurePosixPath

from experiments.platform_files import is_link, open_regular

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "opent1d.windows-package/1"
SOURCE_FILES = (
    "experiments/desktop/runtime.py",
    "experiments/durable_archives/__init__.py",
    "experiments/durable_archives/storage.py",
    "experiments/platform_files.py",
)


def _root(root=None):
    return Path(root).resolve() if root is not None else ROOT


def _path(base, relative):
    value = PurePosixPath(relative)
    if (
        not value.parts
        or value.is_absolute()
        or "\\" in relative
        or any(part in {".", ".."} or ":" in part for part in value.parts)
    ):
        raise ValueError("Invalid packaged runtime path")
    path = base.joinpath(*value.parts)
    if is_link(path) or any(is_link(p) for p in path.parents):
        raise ValueError("Packaged runtime cannot contain links")
    return path


def packaged_manifest(source_root=None):
    root = _root(source_root)
    path = root.parent / "package-manifest.json"
    if not path.exists():
        return None
    if root.name != "app" or is_link(path) or any(is_link(p) for p in path.parents):
        raise ValueError("Invalid installed source layout")
    with os.fdopen(open_regular(path), "rb") as stream:
        content = stream.read(32 * 1024 * 1024 + 1)
    if len(content) > 32 * 1024 * 1024:
        raise ValueError("Installed manifest is too large")
    data = json.loads(content)
    if data.get("schema") != SCHEMA or not isinstance(data.get("runtime_paths"), dict):
        raise ValueError("Unsupported installed package manifest")
    source = data.get("source", {})
    if (
        not re.fullmatch(r"[0-9a-f]{40}", source.get("revision", ""))
        or type(source.get("dirty")) is not bool
    ):
        raise ValueError("Invalid installed source identity")
    return data


def packaged_runtime(project=".", source_root=None):
    root = _root(source_root)
    manifest = packaged_manifest(root)
    if manifest is None:
        return None
    if project not in manifest["runtime_paths"]:
        raise ValueError("This project is not included in the installed runtime: " + project)
    record = manifest["runtime_projects"][project]
    if not isinstance(record, dict) or set(record) != {
        "directory",
        "python",
        "selectors",
        "distributions",
        "upstream_revisions",
    }:
        raise ValueError("Invalid packaged runtime descriptor")
    expected_directories = {
        ".": "runtime",
        "experiments/m0/simglucose_secure": "runtimes/native",
        "experiments/m4/beta_cell/runtime": "runtimes/observer",
    }
    if record["directory"] != expected_directories.get(project):
        raise ValueError("Unexpected packaged runtime directory")
    directory = _path(root.parent, record["directory"])
    if (
        set(record["selectors"]) != {"uv.lock", "pyproject.toml"}
        or any(
            not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value)
            for value in record["selectors"].values()
        )
        or not record["distributions"]
        or len(record["distributions"]) > 500
        or any(
            not isinstance(value, str) or not re.fullmatch(r"[0-9][a-zA-Z0-9.+!-]{0,79}", value)
            for value in record["distributions"].values()
        )
        or any(
            not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{40}", value)
            for value in record["upstream_revisions"].values()
        )
        or any(not re.fullmatch(r"[a-z0-9][a-z0-9.-]*", name) for name in record["distributions"])
        or not set(record["upstream_revisions"]) <= set(record["distributions"])
    ):
        raise ValueError("Invalid packaged runtime lock inventory")
    python = _path(root.parent, manifest["runtime_paths"][project])
    if python.parent != directory:
        raise ValueError("Packaged interpreter lies outside its runtime")
    if record["python"] != manifest["runtime_paths"][project]:
        raise ValueError("Packaged interpreter identity differs")
    return {**record, "executable": python, "manifest": manifest}


def interpreter(project=".", source_root=None):
    root = _root(source_root)
    bundled = packaged_runtime(project, root)
    if bundled is not None:
        return bundled["executable"]
    return root / project / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def revision(source_root=None):
    manifest = packaged_manifest(source_root)
    return None if manifest is None else dict(manifest["source"])


def _digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify_packaged_project(project, source_root=None):
    """Verify installed bytes and complete lock metadata, without importing a model."""
    from experiments.durable_archives import storage

    root = _root(source_root)
    record = packaged_runtime(project, root)
    if record is None:
        raise ValueError("An installed package is required")
    manifest, base = record["manifest"], root.parent
    for name, expected in record["selectors"].items():
        if _digest(root / project / name) != expected:
            raise ValueError("Installed runtime lock changed")
    prefix = record["directory"] + "/"
    files = {
        name: value for name, value in manifest["payload_files"].items() if name.startswith(prefix)
    }
    # Traverse through checked directory handles instead of rechecking every
    # absolute ancestor for every file. On Windows the handles pin ancestors
    # against replacement. Every call still hashes the complete runtime and
    # rejects links, hardlinks, special entries and changes during a read.
    try:
        observed, _ = storage.inventory(base / record["directory"], storage.Budget())
    except (OSError, ValueError) as error:
        raise ValueError(
            "Installed runtime cannot be read safely; repair this installer"
        ) from error
    actual_files = {prefix + name: value for name, value in observed["files"].items()}
    if set(actual_files) != set(files):
        raise ValueError("Installed runtime file inventory differs; repair this installer")
    for name, expected in files.items():
        actual = actual_files[name]
        if actual["size"] != expected["bytes"] or actual["sha256"] != expected["sha256"]:
            raise ValueError("Installed runtime bytes changed; repair this installer")
    script = (
        "import importlib.metadata as m,json,platform,re; "
        "d={re.sub(r'[-_.]+','-',x.metadata['Name']).lower():x for x in m.distributions()}; "
        "print(json.dumps({'python':platform.python_version(),'implementation':"
        "platform.python_implementation(),'packages':{n:x.version for n,x in d.items()},"
        "'direct_urls':{n:json.loads(x.read_text('direct_url.json') or 'null') "
        "for n,x in d.items()}}))"
    )
    checked = subprocess.run(
        [str(record["executable"]), "-I", "-B", "-c", script],
        cwd=root,
        stdin=subprocess.DEVNULL,
        creationflags=0x00000008 if os.name == "nt" else 0,  # DETACHED_PROCESS
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    actual = json.loads(checked.stdout)
    if (
        actual["implementation"] != "CPython"
        or actual["python"] != manifest["runtime"]["version"]
        or actual["packages"] != record["distributions"]
    ):
        raise ValueError("Installed runtime distribution inventory differs")
    for name, commit in record["upstream_revisions"].items():
        direct = actual["direct_urls"].get(name) or {}
        if direct.get("vcs_info", {}).get("commit_id") != commit:
            raise ValueError("Installed upstream revision differs")
    return actual
