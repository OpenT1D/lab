"""Fixed test-only descriptor counterexamples, never a native command route."""

import os
import sys
from pathlib import Path

node, folder, mode, ack, frame = sys.argv[1:]
if mode not in {"descriptor-alias", "stdio-alias", "regular-descriptor"}:
    raise ValueError("Fixed descriptor case required")
ack, frame = int(ack), int(frame)
held = os.dup(ack), os.dup(frame)
os.dup2(held[0], 3, inheritable=True)
os.dup2(held[0] if mode == "descriptor-alias" else held[1], 4, inheritable=True)
os.set_inheritable(3, True)
os.set_inheritable(4, True)
if mode == "stdio-alias":
    os.dup2(held[0], 1, inheritable=True)
elif mode == "regular-descriptor":
    with open(Path(folder) / "ordinary.txt", "rb") as stream:
        os.dup2(stream.fileno(), 4, inheritable=True)
for fd in {*held, ack, frame} - {0, 1, 2, 3, 4}:
    os.close(fd)
script = Path(__file__).with_name("lt1_native_entry_fixture.mjs")
os.execve(
    node, [node, str(script), mode, folder], {"LANG": "C", "LC_ALL": "C", "PATH": "/usr/bin:/bin"}
)
