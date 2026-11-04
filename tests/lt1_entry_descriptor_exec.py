"""Test-only POSIX remap into fixed descriptors, followed by ordinary tooling Node."""

import os
import sys

node, script, folder, mode, ack, frame = sys.argv[1:]
ack, frame = int(ack), int(frame)
# Duplicate first so a low-numbered destination cannot clobber the other source.
held = os.dup(ack), os.dup(frame)
os.dup2(held[0], 3, inheritable=True)
os.dup2(held[1], 4, inheritable=True)
if mode == "stdio-alias":
    os.dup2(held[0], 1, inheritable=True)
for fd in {*held, ack, frame} - {0, 1, 2, 3, 4}:
    os.close(fd)
os.execv(node, [node, script, "entry", "descriptor-refusal", folder])
