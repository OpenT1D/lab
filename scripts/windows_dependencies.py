"""Assemble exact locked Windows wheels without using the target interpreter.

Only four pure Python source distributions need building. Their source archives
and isolated build backends are hash pinned; compiled dependencies must have an
existing compatible wheel in the repository lock. No resolution occurs here.
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tomllib
import urllib.parse
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path, PurePosixPath

PROJECTS = {
    ".": "runtime",
    "experiments/m0/simglucose_secure": "runtimes/native",
    "experiments/m4/beta_cell/runtime": "runtimes/observer",
}


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def safe_name(name):
    path = PurePosixPath(name)
    if (
        not path.parts
        or path.is_absolute()
        or "\\" in name
        or any(part in {".", ".."} or ":" in part for part in path.parts)
    ):
        raise ValueError("Unsafe dependency archive path")
    return path


def fetch(artifact, cache):
    expected = artifact.get("sha256") or artifact["hash"].removeprefix("sha256:")
    filename = urllib.parse.unquote(urllib.parse.urlsplit(artifact["url"]).path.rsplit("/", 1)[1])
    # codeload Git archives end in a commit without an archive extension.
    if "codeload.github.com" in artifact["url"]:
        filename += ".tar.gz"
    path = cache / expected / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        temporary = path.with_suffix(".download")
        try:
            with (
                urllib.request.urlopen(artifact["url"], timeout=90) as source,
                temporary.open("xb") as out,
            ):
                count = 0
                while block := source.read(1024 * 1024):
                    count += len(block)
                    if count > 256 * 1024 * 1024:
                        raise ValueError("Dependency download exceeds its limit")
                    out.write(block)
            if digest(temporary) != expected:
                raise ValueError("Downloaded dependency differs from its locked hash")
            temporary.rename(path)
        finally:
            temporary.unlink(missing_ok=True)
    if digest(path) != expected:
        raise ValueError("Cached dependency differs from its locked hash")
    return path


def wheel_score(url):
    filename = urllib.parse.unquote(url.rsplit("/", 1)[-1])
    if not filename.endswith(".whl"):
        return 0
    _, python, abi, platform = filename[:-4].rsplit("-", 3)
    if platform == "win_amd64" and python == "cp312" and abi == "cp312":
        return 100
    if platform == "win_amd64" and abi == "abi3" and re.fullmatch(r"cp3\d+", python):
        minor = int(python[3:])
        return 50 + minor if minor <= 12 else 0
    if abi == "none" and platform in {"any", "win_amd64"}:
        if "py312" in python.split("."):
            return 40
        if "py3" in python.split("."):
            return 30
    return 0


def selected_packages(lock, root=False):
    by_name = {item["name"]: item for item in lock["package"] if "virtual" not in item["source"]}
    if not root:
        return by_name
    pending = [item["name"] for item in lock["manifest"]["dependency-groups"]["dev"]]
    selected = {}
    while pending:
        name = pending.pop()
        if name in selected:
            continue
        item = by_name[name]
        selected[name] = item
        for dependency in item.get("dependencies", []):
            if set(dependency) - {"name", "marker"}:
                raise ValueError("Unsupported root dependency selector")
            if "marker" in dependency:
                match = re.fullmatch(
                    r"sys_platform\s*(==|!=)\s*['\"]([a-z0-9_]+)['\"]", dependency["marker"]
                )
                if match is None:
                    raise ValueError("Unsupported root platform marker")
                included = (match[2] == "win32") == (match[1] == "==")
                if not included:
                    continue
            pending.append(dependency["name"])
    return selected


def install_wheel(archive, site, *, runtime=None):
    """Install wheel data faithfully; entry-point executables are not used by GUI."""
    names, total = set(), 0
    with zipfile.ZipFile(archive) as bundle:
        for item in bundle.infolist():
            path = safe_name(item.filename)
            if item.is_dir():
                continue
            total += item.file_size
            if (
                item.filename.casefold() in names
                or total > 512 * 1024 * 1024
                or len(names) > 30000
                or (item.external_attr >> 16) & 0o170000 == 0o120000
            ):
                raise ValueError("Unsafe or excessive wheel contents")
            names.add(item.filename.casefold())
            target = site / path
            if path.parts[0].endswith(".data"):
                category = path.parts[1]
                rest = Path(*path.parts[2:])
                if category in {"purelib", "platlib"}:
                    target = site / rest
                elif runtime is not None and category in {"scripts", "data", "headers"}:
                    target = (
                        runtime
                        / {"scripts": "Scripts", "data": "", "headers": "Include"}[category]
                        / rest
                    )
                else:
                    raise ValueError("Unsupported wheel data category")
            target.parent.mkdir(parents=True, exist_ok=True)
            # Namespace packages can share identical __init__.py files.
            content = bundle.read(item)
            if target.exists() and target.read_bytes() != content:
                raise ValueError("Conflicting wheel files: " + str(path))
            target.write_bytes(content)


def unpack_source(archive, destination):
    with tarfile.open(archive, "r:gz") as bundle:
        members = bundle.getmembers()
        total, names = 0, set()
        for item in members:
            safe_name(item.name)
            if not (item.isfile() or item.isdir()) or item.name.casefold() in names:
                raise ValueError("Unsafe source archive")
            names.add(item.name.casefold())
            total += item.size
            if total > 512 * 1024 * 1024 or len(names) > 30000:
                raise ValueError("Source archive exceeds limits")
        destination.mkdir(parents=True, exist_ok=False)
        for item in members:
            target = destination / item.name
            if item.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with bundle.extractfile(item) as source, target.open("xb") as out:
                    shutil.copyfileobj(source, out)
    roots = list(destination.iterdir())
    if len(roots) != 1 or not roots[0].is_dir():
        raise ValueError("Expected one dependency source root")
    return roots[0]


def build_wheel(archive, name, backend, tools, work):
    source = unpack_source(archive, work / name)
    output = work / (name + "-wheel")
    output.mkdir()
    code = (
        "import importlib,os,sys; sys.path[:0]=[sys.argv[1],os.getcwd()]; "
        "backend=importlib.import_module(sys.argv[2]); "
        "backend.build_wheel(sys.argv[3])"
    )
    environment = {k: v for k, v in os.environ.items() if not k.startswith(("PYTHON", "UV_"))}
    environment.update(SOURCE_DATE_EPOCH="315532800", PYTHONDONTWRITEBYTECODE="1")
    with (work / (name + "-build.log")).open("wb") as log:
        subprocess.run(
            [sys.executable, "-I", "-S", "-B", "-c", code, str(tools), backend, str(output)],
            cwd=source,
            env=environment,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=True,
            timeout=180,
        )
    wheels = list(output.glob("*.whl"))
    if len(wheels) != 1 or not wheels[0].name.endswith("none-any.whl"):
        raise ValueError("Source dependency did not produce one pure Python wheel")
    return wheels[0]


def assemble(root, payload, cache, clone_runtime):
    """Return precise per-project installed identities plus input provenance."""
    inputs = json.loads((root / "packaging/windows/dependency-inputs.json").read_bytes())
    records, artifacts, packages = {}, {}, {}
    for project in PROJECTS:
        lock = tomllib.loads((root / project / "uv.lock").read_text())
        packages[project] = selected_packages(lock, project == ".")
        for name, item in packages[project].items():
            key = name + "==" + item["version"]
            previous = artifacts.get(key)
            if "git" in item["source"]:
                source = inputs["vcs"][name]
                if item["source"]["git"].split("#")[-1] != source["commit"]:
                    raise ValueError("Upstream source lock differs from packaging input")
                artifacts[key] = {**source, "kind": "source"}
            else:
                wheels = sorted(
                    item.get("wheels", []),
                    key=lambda x: (wheel_score(x["url"]), x["url"]),
                    reverse=True,
                )
                if wheels and wheel_score(wheels[0]["url"]):
                    artifacts[key] = {**wheels[0], "kind": "wheel"}
                elif name in {"docopt", "gym"}:
                    artifacts[key] = {
                        **item["sdist"],
                        "kind": "source",
                        "backend": "setuptools.build_meta",
                    }
                else:
                    raise ValueError("No locked Windows wheel for " + key)
            if previous is not None and previous != artifacts[key]:
                raise ValueError("Runtime locks disagree about the selected artifact for " + key)
    cache.mkdir(parents=True, exist_ok=True)
    unique = {
        item.get("sha256") or item["hash"].removeprefix("sha256:"): item
        for item in [*artifacts.values(), *inputs["build_tools"]]
    }
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda item: fetch(item, cache), unique.values()))
    work = payload.parent / "dependency-build"
    work.mkdir()
    tools = work / "tools"
    tools.mkdir()
    for item in inputs["build_tools"]:
        install_wheel(fetch(item, cache), tools)
    built = {}
    for key, item in artifacts.items():
        archive = fetch(item, cache)
        built[key] = (
            build_wheel(archive, key.split("==")[0], item["backend"], tools, work)
            if item["kind"] == "source"
            else archive
        )
    sources = payload / "third-party-sources"
    sources.mkdir()
    for key, item in artifacts.items():
        if item["kind"] == "source":
            shutil.copyfile(fetch(item, cache), sources / (key + ".tar.gz"))
    source_materials = {}
    for selected in packages.values():
        for name in inputs["redistributed_sources"]:
            if name in selected:
                item = selected[name]
                key = name + "==" + item["version"]
                archive = fetch(item["sdist"], cache)
                shutil.copyfile(archive, sources / (key + ".tar.gz"))
                source_materials[key] = item["sdist"]
    provider_archive = fetch(inputs["runtime_build_sources"], cache)
    shutil.copyfile(provider_archive, sources / "python-build-standalone-20261021.tar.gz")
    provider_source = unpack_source(provider_archive, work / "runtime-provider-source")
    licenses = payload / "third-party-licenses/python"
    licenses.mkdir(parents=True)
    for license_path in sorted(provider_source.glob("LICENSE*")):
        shutil.copyfile(license_path, licenses / license_path.name)
    provenance = {
        "redistributed_sources": source_materials,
        "runtime_build_sources": inputs["runtime_build_sources"],
    }
    for project, directory in PROJECTS.items():
        runtime = payload / directory
        if project != ".":
            clone_runtime(runtime)
        site = runtime / "Lib/site-packages"
        shutil.rmtree(site)
        site.mkdir()
        expected, upstream = {}, {}
        for name, item in sorted(packages[project].items()):
            key = name + "==" + item["version"]
            wheel = built[key]
            install_wheel(wheel, site, runtime=runtime)
            expected[name] = item["version"]
            original = artifacts[key]
            if "commit" in original:
                upstream[name] = original["commit"]
                metadata = site / (name.replace("-", "_") + "-" + item["version"] + ".dist-info")
                direct = {
                    "url": original["repository"],
                    "vcs_info": {
                        "vcs": "git",
                        "commit_id": original["commit"],
                        "requested_revision": original["commit"],
                    },
                }
                (metadata / "direct_url.json").write_bytes(
                    (json.dumps(direct, sort_keys=True) + "\n").encode()
                )
            provenance[key] = {"input": original, "installed_wheel_sha256": digest(wheel)}
        # A plain path line never executes code, and -S excludes it as expected.
        relative = os.path.relpath(payload / "app", site).replace(os.sep, "/")
        (site / "opent1d-source.pth").write_bytes((relative + "\n").encode("ascii"))
        records[project] = {
            "directory": directory,
            "python": directory + "/python.exe",
            "selectors": {
                name: digest(root / project / name) for name in ("uv.lock", "pyproject.toml")
            },
            "distributions": expected,
            "upstream_revisions": upstream,
        }
    return records, provenance
