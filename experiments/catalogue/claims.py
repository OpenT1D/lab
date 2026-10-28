"""Schema-selected observations of recorded digest claims; never native validation."""

from pathlib import PurePosixPath, PureWindowsPath

from .storage import SHA, read, require

# These layouts are declared by the corresponding native writers. Bases are
# relative to each manifest's directory; no archived path selects the base.
# The M4 reference seal inventories its reference/ child, not its own directory.
LAYOUTS = {
    "opent1d.local-tool-archive/1": ("files", ".", "sha256_size"),
    "opent1d.simglucose/1": ("files_sha256", ".", "sha256"),
    "opent1d.p1-external-case/1": ("files_sha256", ".", "sha256"),
    "opent1d.m3.researcher/1": ("files", ".", "sha256"),
    "opent1d.m3.comparison/1": ("files", ".", "sha256"),
    "m4-researcher-workflow/1": ("files", ".", "sha256"),
    "m4-causal-run/1": ("files", ".", "sha256"),
    "m4-source-comparison/1": ("files", ".", "sha256"),
    "m4-initial-load-run/1": ("files", ".", "sha256"),
    "m4-secure-study-run/1": ("files", ".", "sha256"),
    "m4-secure-reference-run/1": ("files", ".", "sha256"),
    "m4-initial-load-reference-seal/1": ("files", "reference", "sha256"),
    "bc008-feedback/1": ("files", ".", "sha256"),
    "bc009-hepatic/1": ("files", ".", "sha256"),
    "bc010-feedback-observation/1": ("files", ".", "sha256"),
    "m5-researcher-archive/1": ("files", ".", "sha256"),
    "opent1d.local-campaign/1": ("files", ".", "sha256"),
    "opent1d.maintained-campaign/1": ("files", ".", "sha256"),
}


def claim_path(relative):
    require(
        isinstance(relative, str)
        and bool(relative)
        and "\\" not in relative
        and "\0" not in relative
        and not PurePosixPath(relative).is_absolute()
        and not PureWindowsPath(relative).drive
        and bool(PurePosixPath(relative).parts)
        and ".." not in PurePosixPath(relative).parts
        and relative == PurePosixPath(relative).as_posix(),
        "Unsafe or noncanonical recorded inventory path",
    )
    return PurePosixPath(relative)


def claimed_file(claim, shape):
    if shape == "sha256":
        require(isinstance(claim, str) and SHA.fullmatch(claim), "Malformed recorded digest")
        return {"sha256": claim}
    require(
        isinstance(claim, dict)
        and set(claim) == {"sha256", "size"}
        and isinstance(claim["sha256"], str)
        and SHA.fullmatch(claim["sha256"])
        and type(claim["size"]) is int
        and claim["size"] >= 0,
        "Malformed recorded digest/size claim",
    )
    return claim


def manifest_checks(path, name, files):
    result = {
        "manifest": name,
        "schema": None,
        "base": None,
        "claim_shape": None,
        "status": "unavailable",
        "checked_files": 0,
        "mismatches": [],
        "missing_files": [],
        "changed_files": [],
        "errors": [],
    }
    try:
        manifest = read(path / name)
        require(isinstance(manifest, dict), "Manifest must be a JSON object")
        schema = manifest.get("schema")
        require(isinstance(schema, str) and bool(schema), "Missing or malformed manifest schema")
        result["schema"] = schema
        if schema not in LAYOUTS:
            result["status"] = "unsupported"
            return result
        field, child, shape = LAYOUTS[schema]
        parent = PurePosixPath(name).parent
        base = parent / child
        result.update(base=base.as_posix(), claim_shape=shape)
        expected_name = "reference-manifest.json" if child == "reference" else "manifest.json"
        require(
            PurePosixPath(name).name == expected_name, "Unexpected manifest filename for schema"
        )
        claims = manifest.get(field)
        require(isinstance(claims, dict), "Missing or malformed recorded inventory mapping")
        for relative, claim in claims.items():
            try:
                key = (base / claim_path(relative)).as_posix()
                expected = claimed_file(claim, shape)
            except (ValueError, TypeError) as error:
                result["errors"].append(str(error))
                continue
            result["checked_files"] += 1
            actual = files.get(key)
            if actual is None:
                result["missing_files"].append(key)
            elif any(actual.get(field) != value for field, value in expected.items()):
                result["changed_files"].append(key)
        result["mismatches"] = sorted(result["missing_files"] + result["changed_files"])
        result["status"] = (
            "malformed"
            if result["errors"]
            else "mismatch"
            if result["mismatches"]
            else "matched"
            if result["checked_files"]
            else "unavailable"
        )
    except (OSError, ValueError, TypeError, AttributeError) as error:
        result["status"] = "malformed"
        result["errors"].append(type(error).__name__ + ": " + str(error)[:300])
    return result


def hash_checks(path, files):
    """A match covers supported recorded claims, not all bytes or model validity."""
    manifests = [
        manifest_checks(path, name, files)
        for name in sorted(files)
        if name.endswith("manifest.json")
    ]
    statuses = {item["status"] for item in manifests}
    status = next(
        (
            state
            for state in ("malformed", "mismatch", "unsupported", "matched")
            if state in statuses
        ),
        "unavailable",
    )
    return {
        "status": status,
        "checked_files": sum(item["checked_files"] for item in manifests),
        "mismatches": sorted({name for item in manifests for name in item["mismatches"]}),
        "scope": "recorded_hashes_only",
        "manifests": manifests,
    }
