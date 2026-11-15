"""Three fixed invented buffers and an import-only EntryPoint symbol.

Nothing is installed into pkg_resources or any module registry. No engine,
resource path, native asset, Gym or compatibility dependency is imported.
"""

from pathlib import Path

from .contract import AUTHORITY, decode, digest, encode, fields, require, source_identity

SCHEMA = "opent1d.simglucose-audit1-compat-fixture/1"
_BUFFERS = (
    ("params/vpatient_params.csv", b"invented-fixture-only:no-patient-parameters\n"),
    ("params/sensor_params.csv", b"invented-fixture-only:no-sensor-parameters\n"),
    ("params/pump_params.csv", b"invented-fixture-only:no-pump-parameters\n"),
)


class EntryPoint:
    """Importable symbol only. Parsing/loading never receives operational use."""

    @classmethod
    def parse(cls, *_args, **_kwargs):
        raise PermissionError("invented import-only EntryPoint: parse is closed")

    @classmethod
    def load(cls, *_args, **_kwargs):
        raise PermissionError("invented import-only EntryPoint: load is closed")


def fixed_resource_buffers():
    return dict(_BUFFERS)


def default_metadata():
    return {
        "schema": SCHEMA,
        "kind": "invented",
        "resources": [
            {
                "label": label,
                "kind": "invented-buffer",
                "bytes": len(raw),
                "sha256": digest(raw),
                "symlink": False,
            }
            for label, raw in _BUFFERS
        ],
    }


def _identity():
    return source_identity() | {"compat_fixture.py": digest(Path(__file__).read_bytes())}


def run_compat_fixture(resource_buffers, metadata_raw=None):
    """Byte-only fictional binding. Labels are never paths to open."""
    require(
        type(resource_buffers) is dict and set(resource_buffers) == set(dict(_BUFFERS)),
        "exact-three-invented-labels",
    )
    require(
        all(
            type(resource_buffers[label]) is bytes and resource_buffers[label] == raw
            for label, raw in _BUFFERS
        ),
        "fixed-invented-buffers-only",
    )
    metadata_raw = encode(default_metadata()) if metadata_raw is None else metadata_raw
    metadata = decode(metadata_raw)
    fields(metadata, "schema kind resources", "compat-metadata-fields")
    require(encode(metadata) == encode(default_metadata()), "fixed-invented-resource-metadata")
    return {
        "schema": SCHEMA,
        "kind": "invented",
        "status": "blocked",
        "metadata_sha256": digest(metadata_raw),
        "source_identity": _identity(),
        "resources": metadata["resources"],
        "entry_point": "import-only-parse-load-refuse",
        "actual_resources_opened": False,
        "real_import_effects_observed": False,
        "native_acceptance": False,
        "host_or_process_qualified": False,
        "authority": dict(AUTHORITY),
    }


def inspect_compat_report(
    report_raw, expected_report_sha256, resource_buffers, metadata_raw, expected_metadata_sha256
):
    require(
        digest(report_raw) == expected_report_sha256
        and digest(metadata_raw) == expected_metadata_sha256,
        "external-compat-byte-pins",
    )
    identity = _identity()
    report = decode(report_raw)
    require(
        encode(report) == encode(run_compat_fixture(resource_buffers, metadata_raw)),
        "compat-report-reconstruction",
    )
    require(_identity() == identity, "compat-source-changed")
    return {
        "kind": "invented",
        "status": "blocked",
        "native_acceptance": False,
        "host_or_process_qualified": False,
        "authority": dict(AUTHORITY),
    }
