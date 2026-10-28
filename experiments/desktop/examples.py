"""Seed immutable supplied input copies without mixing program files and analyses."""

import hashlib
import os
from pathlib import Path

from experiments.platform_files import is_link, open_regular

FILES = (
    "experiments/m4/causal_secretion/example_model.py",
    "experiments/m4/causal_secretion/example_model.json",
    "experiments/m4/ultradian_secretion/model.py",
    "experiments/m4/ultradian_secretion/model.json",
)


def prepare(source, workspace):
    source, workspace = Path(source), Path(workspace)
    content = {name: (source / name).read_bytes() for name in FILES}
    identity = hashlib.sha256()
    for name, raw in content.items():
        identity.update(name.encode() + b"\0" + hashlib.sha256(raw).digest())
    prefix = "examples/" + identity.hexdigest()[:24]
    for name, raw in content.items():
        destination = workspace / prefix / name
        for component in (destination, *destination.parents):
            if is_link(component):
                raise ValueError("Supplied example paths must not contain linked directories")
            if component == workspace:
                break
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            descriptor = open_regular(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
        except FileExistsError:
            descriptor = open_regular(destination)
            with os.fdopen(descriptor, "rb") as existing:
                if existing.read(len(raw) + 1) != raw:
                    raise ValueError(
                        "A supplied example was changed. Move its examples folder aside "
                        "to keep your edits, then restart OpenT1D."
                    ) from None
        else:
            with os.fdopen(descriptor, "wb") as output:
                output.write(raw)
    return prefix
