"""Explicit installed readers are bound to clean package source and private runtime bytes."""

from pathlib import Path

from . import storage


def package_manifest(checkout, budget):
    """Read installed metadata; callers still must verify source/runtime inventories."""
    checkout = Path(checkout).absolute()
    path = checkout.parent / "package-manifest.json"
    if checkout.name != "app" or not path.exists():
        return None
    checkout = storage.safe_path(checkout)
    storage.require(not (checkout / ".git").exists(), "Installed source contains Git metadata")
    raw = storage.read_file(checkout.parent, path.name, budget)
    value = storage.strict_json(raw)
    storage.require(
        isinstance(value, dict)
        and value.get("schema") == "opent1d.windows-package/1"
        and isinstance(value.get("source"), dict)
        and set(value["source"]) == {"revision", "dirty", "files"}
        and isinstance(value["source"]["revision"], str)
        and storage.REVISION.fullmatch(value["source"]["revision"])
        and type(value["source"]["dirty"]) is bool
        and isinstance(value["source"]["files"], dict)
        and 0 < len(value["source"]["files"]) <= storage.FILES_LIMIT
        and isinstance(value.get("payload_files"), dict)
        and 0 < len(value["payload_files"]) <= storage.FILES_LIMIT
        and isinstance(value.get("runtime_paths", {}), dict),
        "Unsupported installed source manifest",
    )
    records(value["payload_files"])
    return value


def records(files):
    result = {}
    aliases = set()
    for name, value in files.items():
        storage.relative_name(name)
        storage.require(name.casefold() not in aliases, "Installed path alias")
        aliases.add(name.casefold())
        storage.require(
            isinstance(value, dict)
            and set(value) == {"sha256", "bytes"}
            and isinstance(value["sha256"], str)
            and storage.SHA.fullmatch(value["sha256"])
            and type(value["bytes"]) is int
            and 0 <= value["bytes"] <= storage.FILE_LIMIT,
            "Invalid installed file identity",
        )
        result[name] = {"sha256": value["sha256"], "size": value["bytes"]}
    return result


def runtime(checkout, manifest, budget):
    relative = manifest.get("runtime_paths", {}).get(".", "runtime/python.exe")
    storage.relative_name(relative)
    path = Path(relative)
    storage.require(
        path.name == "python.exe" and len(path.parts) > 1,
        "Installed reader requires its private Python executable",
    )
    expected = records(
        {
            name.removeprefix(path.parent.as_posix() + "/"): value
            for name, value in manifest["payload_files"].items()
            if name.startswith(path.parent.as_posix() + "/")
        }
    )
    storage.require(path.name in expected, "Private reader executable has no bound identity")
    folder = checkout.parent / path.parent
    actual, signatures = storage.inventory(folder, budget)
    storage.require(actual["files"] == expected, "Installed reader runtime bytes changed")
    return checkout.parent / path, signatures


def _identity(checkout, revision, budget, *, destination=None):
    manifest = package_manifest(checkout, budget)
    storage.require(manifest is not None, "Explicit installed source manifest required")
    storage.require(
        manifest["source"]["dirty"] is False,
        "Installed durable reader must come from a clean committed build",
    )
    storage.require(
        manifest["source"]["revision"] == revision,
        "Installed reader revision differs from requested full revision",
    )
    expected = records(manifest["source"]["files"])
    actual, signatures = storage.inventory(checkout, budget, destination=destination)
    storage.require(actual["files"] == expected, "Installed reader source bytes changed")
    executable, runtime_signatures = runtime(checkout, manifest, budget)
    signatures.update({"/runtime/" + name: value for name, value in runtime_signatures.items()})
    signatures["/package-manifest.json"] = storage.read_file(
        checkout.parent, "package-manifest.json", budget
    )
    storage.require(
        storage.strict_json(signatures["/package-manifest.json"]) == manifest,
        "Installed reader manifest changed during inspection",
    )
    return ({"revision": revision, "files": actual["files"]}, signatures), executable


def identity(checkout, revision, budget, *, destination=None):
    return _identity(checkout, revision, budget, destination=destination)[0]


def executable(checkout, budget):
    manifest = package_manifest(checkout, budget)
    if manifest is None:
        return None
    # The same inspection already hashed the complete runtime and checked the
    # manifest again. Return its verified path instead of hashing it twice in
    # succession; later export/reconstruction boundary checks remain fresh.
    return _identity(checkout, manifest["source"]["revision"], budget)[1]
