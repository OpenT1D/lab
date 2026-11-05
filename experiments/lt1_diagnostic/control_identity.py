"""Static trusted control sources, not whole-bootstrap or host qualification."""

import hashlib
import os
import platform
import socket
import sys
from pathlib import Path

from experiments.m4.initial_load.common import source_closure

ROOT = Path(__file__).resolve().parents[2]


def identity(entry):
    names = {Path(entry).resolve().relative_to(ROOT).as_posix()}
    while True:
        closed = set(source_closure(names))
        initializers = {
            Path(*Path(name).parts[:length], "__init__.py").as_posix()
            for name in closed
            for length in range(1, len(Path(name).parts))
        }
        expanded = closed | {name for name in initializers if (ROOT / name).is_file()}
        if expanded == names:
            break
        names = expanded
    return {
        "implementation": {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in sorted(names)
        },
        "python": platform.python_version(),
        "executable_sha256": hashlib.sha256(
            Path(sys.executable).resolve().read_bytes()
        ).hexdigest(),
    }


def host():
    return {
        "platform": sys.platform,
        "machine": platform.machine(),
        "name": socket.gethostname(),
        "uid": os.getuid(),
    }
