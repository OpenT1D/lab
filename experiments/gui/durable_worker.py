"""Owned fixed durable operations; preserved package readers are always data."""

import argparse
import subprocess
import sys
from pathlib import Path

from experiments.workflows.checks import safe_environment

from .durable import ARTIFACTS, OPERATIONS, REQUEST, RESULT
from .library_paths import resolve_archive, validate_identity
from .service import MAX_REPORT, bounded_bytes, decode_json, digest, encode, read_json


def current_revision(checkout):
    """Resolve declared revision only; durable core verifies bytes before use."""
    from experiments.durable_archives import installed, storage

    budget = storage.Budget()
    manifest = installed.package_manifest(checkout, budget)
    if manifest is not None:
        # Like Git rev-parse below, this is selection rather than authorization.
        # Both callers immediately enter core, whose initial identity check
        # precedes reader execution and whose final check precedes publication.
        return manifest["source"]["revision"]
    result = subprocess.run(
        ["git", "-C", str(checkout), "rev-parse", "HEAD"],
        env=safe_environment(),
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    revision = result.stdout.strip()
    if (
        result.returncode
        or len(revision) != 40
        or any(char not in "0123456789abcdef" for char in revision)
    ):
        raise ValueError("The current trusted reader must be a Git checkout at a full revision")
    return revision


def execute(request, output):
    if (
        not isinstance(request, dict)
        or set(request)
        != {
            "schema",
            "operation",
            "entry_id",
            "root_identity",
            "path",
            "archive_identity",
            "expected_identity",
            "source",
            "checkout",
        }
        or request["schema"] != REQUEST
        or request["operation"] not in OPERATIONS
    ):
        raise ValueError("Unsupported durable worker request")
    result = {
        "schema": RESULT,
        "request_sha256": digest(encode(request)),
        "operation": request["operation"],
        "entry_id": request["entry_id"],
        "status": "failed",
        "native": None,
        "reconstruction": "not_requested",
        "report_completeness": "unavailable",
        "artifacts_sha256": {},
        "error": None,
    }
    try:
        from experiments.durable_archives import core

        operation = request["operation"]
        root = validate_identity(request["root_identity"])
        if operation == "durable_export":
            package = root / request["path"]
            if (
                package.parent != root
                or not package.name.startswith("package-")
                or package.exists()
                or package.is_symlink()
            ):
                raise ValueError("Durable export requires a fresh opaque store child")
            source = request["source"]
            archive = validate_identity(source["identity"])
            if str(archive) != source["path"]:
                raise ValueError("Frozen export source differs")
            checkout = Path(request["checkout"])
            revision = current_revision(checkout)
            native = core.export_archive(source["task"], archive, checkout, revision, package)
            report = package / "evidence" / "reconstructed"
        else:
            package, _ = resolve_archive(
                request["root_identity"], request["path"], request["archive_identity"]
            )
            native = core.verify_package(package)
            if (
                request["expected_identity"] is not None
                and native["package_identity"] != request["expected_identity"]
            ):
                raise ValueError("Durable package identity changed since registration")
            result["native"] = native
            report = None
            if operation == "durable_reconstruct":
                checkout = Path(request["checkout"])
                revision = current_revision(checkout)
                if revision != native["reader_revision"]:
                    result["reconstruction"] = "reader_mismatch"
                    raise ValueError(
                        "Current reader revision differs. Open the retained matching installation "
                        "or use the durable archive CLI with a caller-trusted clean checkout at "
                        + native["reader_revision"]
                        + "; no archived reader is executed automatically."
                    )
                result["reconstruction"] = "checking"
                native = core.reconstruct_package(
                    package, checkout, revision, output / "reconstructed"
                )
                report = output / "reconstructed" / "evidence" / "reconstructed"
        result["native"] = native
        if native.get("status") != "completed" or not native.get("integrity_verified"):
            raise ValueError("Authoritative durable operation did not verify package integrity")
        if native.get("reconstruction_verified"):
            result["reconstruction"] = "checking"
            manifest_raw = bounded_bytes(package / "manifest.json", 8388608)
            if digest(manifest_raw) != native["package_identity"]:
                raise ValueError("Verified durable manifest changed before report capture")
            manifest = decode_json(manifest_raw)
            expected_artifacts = manifest["reconstruction"]["artifacts"]
            target = output / "native-report"
            target.mkdir()
            for name in ARTIFACTS:
                path = report / name
                if path.exists():
                    raw = bounded_bytes(path, MAX_REPORT)
                    if expected_artifacts.get(name) != {"sha256": digest(raw), "size": len(raw)}:
                        raise ValueError(
                            "Native artifact differs from its authoritative descriptor"
                        )
                    (target / name).write_bytes(raw)
                    result["artifacts_sha256"][name] = digest(raw)
            if not {"report.json", "report.md"}.issubset(result["artifacts_sha256"]):
                raise ValueError("Authoritative durable operation lacks native report artifacts")
            result["reconstruction"] = "verified_snapshot"
        result["report_completeness"] = (
            "complete"
            if native.get("complete") is True
            else "failed"
            if native.get("complete") is False
            else "unavailable"
        )
        result["status"] = "completed"
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        RecursionError,
        subprocess.SubprocessError,
    ) as error:
        result["error"] = type(error).__name__ + ": " + str(error)[:1000]
        if result["reconstruction"] in {"checking", "verified_snapshot"}:
            result["reconstruction"] = "verification_failed"
    (output / "worker-result.json").write_bytes(encode(result))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve(strict=True)
    if args.request.parent.resolve(strict=True) != output:
        raise ValueError("Durable request must be frozen in its owned job folder")
    result = execute(read_json(args.request), output)
    print(encode(result).decode(), end="")
    return 0 if result["status"] == "completed" else 1


if __name__ == "__main__":
    sys.exit(main())
