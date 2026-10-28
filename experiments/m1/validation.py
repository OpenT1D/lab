"""Strict saved-artifact validation and stable file snapshots; standard library only."""

import hashlib
import os
import re
from pathlib import Path

from experiments.platform_files import is_link, open_regular

from .contracts import number

HASH = re.compile(r"[0-9a-f]{64}\Z")
REVISION = re.compile(r"[0-9a-f]{40}\Z")
PROTOCOL_SHA256 = "6aab9c5268ef0bb10cd01a4b6fd0bb91edc7db3375b5ff987bf745e06678de3d"
RUN_STATUSES = ("started", "completed", "terminated", "failed", "interrupted")
SOURCE_FILES = tuple(
    f"experiments/m1/{name}.py"
    for name in (
        "artifacts",
        "adapter",
        "control",
        "simulation",
        "runtime",
        "contracts",
        "metrics",
        "report",
    )
) + ("experiments/m0/simglucose/recording.py", "experiments/platform_files.py")


def text_value(value, name):
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a nonempty string")


def object_value(value, name):
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")


def hashes(value, name, required=()):
    object_value(value, name)
    if not set(required) <= value.keys():
        raise ValueError(f"Missing required {name} entries")
    for key, digest in value.items():
        text_value(key, name)
        if not isinstance(digest, str) or not HASH.fullmatch(digest):
            raise ValueError(f"Invalid {name} hash: {key}")


def validate_manifest(manifest):
    object_value(manifest, "manifest")
    if manifest.get("status") not in RUN_STATUSES:
        raise ValueError("Unknown run status")
    count = manifest.get("completed_rows")
    if type(count) is not int or count < 0:
        raise ValueError("completed_rows must be a nonnegative integer")
    hashes(manifest.get("files_sha256"), "artifact inventory")
    if "config" not in manifest:
        raise ValueError("Missing configuration field")
    if manifest["status"] != "started" or "elapsed_seconds" in manifest:
        number(manifest.get("elapsed_seconds"), "elapsed_seconds", 0)
    if manifest["status"] in ("failed", "interrupted", "terminated"):
        text_value(manifest.get("error"), "failure reason")
    if manifest["config"] is not None:
        object_value(manifest["config"], "configuration")
        hashes(manifest.get("source_sha256"), "source provenance", SOURCE_FILES)
        if not isinstance(manifest.get("revision"), str) or not REVISION.fullmatch(
            manifest["revision"]
        ):
            raise ValueError("Missing or invalid implementation revision")
        for key in ("python", "platform"):
            text_value(manifest.get(key), key)
        if type(manifest.get("worktree_dirty")) is not bool:
            raise ValueError("worktree_dirty must be boolean")


def validate_native_provenance(manifest):
    text_value(manifest.get("upstream_revision"), "upstream revision")
    if not REVISION.fullmatch(manifest["upstream_revision"]):
        raise ValueError("Invalid upstream revision")
    mapping = manifest.get("upstream_files_sha256")
    hashes(mapping, "native source")
    if not mapping:
        raise ValueError("Empty native source inventory")
    # Verify the recorded mapping, not a live imported engine during reconstruction.
    import json

    fingerprint = hashlib.sha256(
        json.dumps(mapping, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    if manifest.get("upstream_files_digest") != fingerprint:
        raise ValueError("Native source inventory digest differs")
    packages = manifest.get("packages")
    object_value(packages, "packages")
    for key in ("simglucose", "numpy", "scipy", "pandas", "setuptools"):
        text_value(packages.get(key), f"package {key}")
    settings = manifest.get("effective_settings")
    object_value(settings, "effective settings")
    for key in ("basal_u_min", "CR_g_U", "CF_mg_dl_U", "controller_target_mg_dl"):
        number(settings.get(key), key, 0)
    for key in ("sensor", "pump"):
        text_value(settings.get(key), key)
    if (
        settings.get("sensor_seed") != manifest["config"]["seed"]
        or type(settings.get("sensor_seed")) is not int
    ):
        raise ValueError("Effective sensor seed differs from configuration")
    if (
        settings.get("patient_random_initialization") is not False
        or settings.get("patient_seed", "missing") is not None
    ):
        raise ValueError("Unsupported native patient initialization")
    for group, fields in (("pid", ("P", "I", "D")), ("solver", ("rtol", "atol"))):
        object_value(settings.get(group), group)
        for key in fields:
            number(settings[group].get(key), key, 0)
    text_value(settings["solver"].get("method"), "solver method")
    pump = settings.get("pump_parameters")
    object_value(pump, "pump parameters")
    text_value(pump.get("Name"), "pump Name")
    required = {
        "inc_basal",
        "inc_bolus",
        "max_basal",
        "max_bolus",
        "min_basal",
        "min_bolus",
        "sample_time",
    }
    if not required <= pump.keys():
        raise ValueError("Missing numeric pump parameters")
    for key, value in pump.items():
        if key != "Name":
            number(value, f"pump {key}", 0)


def validate_warnings(warnings):
    if not isinstance(warnings, list):
        raise ValueError("Warnings must be a list")
    for warning in warnings:
        object_value(warning, "warning")
        for key in ("category", "filename"):
            text_value(warning.get(key), key)
        if not isinstance(warning.get("message"), str):
            raise ValueError("Warning message must be a string")
        if type(warning.get("line")) is not int or warning["line"] < 1:
            raise ValueError("Warning line must be a positive integer")


class Snapshot:
    """Read each file once; hashes identify those bytes, including unfinished traces."""

    def __init__(self, root):
        self.root = Path(root)
        if is_link(self.root):
            raise ValueError("Artifact directory must not be a symlink")
        self.data = {}
        self.signatures = {}

    def path(self, name):
        if not isinstance(name, str) or Path(name).name != name or name in (".", ".."):
            raise ValueError("Invalid artifact path")
        path = self.root / name
        if is_link(path):
            raise ValueError("Artifact file must not be a symlink")
        return path

    @staticmethod
    def signature(path):
        stat = path.stat()
        return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns

    def read(self, name, *, optional=False):
        if name not in self.data:
            path = self.path(name)
            if optional and not path.exists():
                self.data[name], self.signatures[name] = None, None
            else:
                before = self.signature(path)
                with os.fdopen(open_regular(path), "rb") as stream:
                    self.data[name] = stream.read()
                after = self.signature(path)
                if before != after:
                    raise ValueError(f"Artifact changed during reconstruction: {name}")
                self.signatures[name] = after
        if self.data[name] is None and not optional:
            raise FileNotFoundError(self.root / name)
        return self.data[name]

    def sha256(self):
        return {
            name: hashlib.sha256(data).hexdigest()
            for name, data in self.data.items()
            if data is not None
        }

    def verify_unchanged(self):
        for name, previous in self.signatures.items():
            path = self.path(name)
            current = self.signature(path) if path.exists() else None
            if current != previous:
                raise ValueError(f"Artifact changed during reconstruction: {name}")
