"""A narrow, trusted local Python controller intake for the M1 rate-action task."""

import hashlib
import importlib.metadata
import importlib.util
import re
import sys
from pathlib import Path

from experiments.m1.artifacts import strict_json
from experiments.m1.contracts import STEP, Action, Observation, number

SCHEMA = "opent1d.p1-controller/1"
OBSERVATION = "held-cgm-with-age/1"
ACTION = "simglucose-pump-rate-u-min/1"
NAME = re.compile(r"[a-z][a-z0-9_]{0,31}\Z")
PACKAGE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
HASH = re.compile(r"[0-9a-f]{64}\Z")
RIGHTS = ("author-owned", "licensed", "authorized-private")


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def declaration(source):
    """Check a two-file source bundle without executing its code."""
    source = Path(source)
    if source.is_symlink() or not source.is_dir():
        raise ValueError("Controller source must be a regular directory")
    paths = {p.name: p for p in source.iterdir()}
    if set(paths) != {"controller.json", "controller.py"} or any(
        p.is_symlink() or not p.is_file() for p in paths.values()
    ):
        raise ValueError("Controller source needs exactly two regular files")
    metadata = strict_json(paths["controller.json"].read_bytes())
    if not isinstance(metadata, dict) or set(metadata) != {
        "schema",
        "name",
        "source_sha256",
        "source_identity",
        "rights",
        "license",
        "dependencies",
        "step_minutes",
        "observation",
        "action",
        "missing_sensor",
    }:
        raise ValueError("Unsupported controller declaration fields")
    if (
        metadata["schema"] != SCHEMA
        or not isinstance(metadata["name"], str)
        or not NAME.fullmatch(metadata["name"])
    ):
        raise ValueError("Unsupported controller declaration or name")
    if not isinstance(metadata["source_sha256"], str) or not HASH.fullmatch(
        metadata["source_sha256"]
    ):
        raise ValueError("Invalid controller source hash")
    if sha256(paths["controller.py"].read_bytes()) != metadata["source_sha256"]:
        raise ValueError("Controller source hash mismatch")
    for key in ("source_identity", "license"):
        if not isinstance(metadata[key], str) or not metadata[key].strip():
            raise ValueError(f"Missing controller {key}")
    if metadata["rights"] not in RIGHTS:
        raise ValueError("Unsupported rights declaration")
    dependencies = metadata["dependencies"]
    if not isinstance(dependencies, dict) or any(
        not isinstance(name, str)
        or not PACKAGE.fullmatch(name)
        or not isinstance(version, str)
        or not version
        for name, version in dependencies.items()
    ):
        raise ValueError("Dependencies must map package names to exact versions")
    if (
        type(metadata["step_minutes"]) is not int
        or metadata["step_minutes"] != STEP
        or metadata["observation"] != OBSERVATION
        or metadata["action"] != ACTION
        or metadata["missing_sensor"] is not True
    ):
        raise ValueError("Controller lacks required M1 capabilities")
    return metadata


def check_dependencies(metadata):
    for name, expected in metadata["dependencies"].items():
        try:
            actual = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError as error:
            raise ValueError(f"Missing controller dependency: {name}") from error
        if actual != expected:
            raise ValueError(f"Controller dependency {name}: expected {expected}, got {actual}")


class SuppliedController:
    """Pass only the declared causal fields to trusted local source code."""

    def __init__(self, source, metadata, *, seed):
        check_dependencies(metadata)
        path = Path(source) / "controller.py"
        if sha256(path.read_bytes()) != metadata["source_sha256"]:
            raise ValueError("Controller changed before loading")
        spec = importlib.util.spec_from_file_location(f"p1_supplied_{metadata['name']}", path)
        if spec is None or spec.loader is None:
            raise ValueError("Cannot load controller source")
        module = importlib.util.module_from_spec(spec)
        previous_bytecode = sys.dont_write_bytecode
        try:
            sys.dont_write_bytecode = True
            spec.loader.exec_module(module)
        finally:
            sys.dont_write_bytecode = previous_bytecode
        factory = getattr(module, "make_controller", None)
        if not callable(factory):
            raise ValueError("Controller source must define make_controller(seed)")
        self.impl = factory(seed)
        if not callable(getattr(self.impl, "reset", None)) or not callable(
            getattr(self.impl, "command", None)
        ):
            raise ValueError("Controller needs reset() and command(observation, announced_g)")

    def reset(self):
        self.impl.reset()

    def command(self, observation, announced_g):
        if not isinstance(observation, Observation):
            raise ValueError("Expected the M1 observation record")
        number(announced_g, "announced_g", 0)
        released = {
            "time_min": observation.time_min,
            "glucose_mg_dl": observation.glucose_mg_dl,
            "source_time_min": observation.source_time_min,
            "available": observation.available,
            "age_min": observation.age_min,
        }
        result = self.impl.command(released, announced_g)
        if not isinstance(result, dict) or set(result) != {"basal_u_min", "bolus_u_min"}:
            raise ValueError("Controller must return basal_u_min and bolus_u_min")
        action = Action(result["basal_u_min"], result["bolus_u_min"])
        if not 0 <= action.basal_u_min <= 0.2 or not 0 <= action.bolus_u_min <= 2.0:
            raise ValueError("Controller rate exceeds the P1 research bound")
        return action


def replay(source, metadata, seed, rows):
    """Recompute commands from the recorded causal inputs, without the simulator."""
    controller = SuppliedController(source, metadata, seed=seed)
    controller.reset()
    for row in rows:
        obs = Observation(
            row.start_min,
            row.controller_cgm_mg_dl,
            row.controller_source_min,
            row.controller_source_min == row.start_min,
        )
        actual = controller.command(obs, row.announced_g)
        if (actual.basal_u_min, actual.bolus_u_min) != (
            row.basal_u_min,
            row.bolus_u_min,
        ):
            raise ValueError(f"Controller action replay differs at minute {row.start_min}")


def smoke(source, metadata):
    """Exercise reset, a fresh sample, a held sample and recovery on invented input."""
    controller = SuppliedController(source, metadata, seed=101)
    controller.reset()
    for time_min, source_min in ((0, 0), (3, 0), (6, 6)):
        controller.command(Observation(time_min, 140.0, source_min, time_min == source_min), 0.0)
    controller.reset()
    controller.command(Observation(0, 140.0, 0, True), 0.0)
