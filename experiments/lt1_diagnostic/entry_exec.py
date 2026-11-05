"""Internal trusted exec shim; no packet intake or selected-runtime admission."""

import os
import stat
import sys

ENVIRONMENT = {"LANG": "C", "LC_ALL": "C", "PATH": "/usr/bin:/bin"}


def main(args):
    if len(args) < 3:
        raise ValueError("Two inherited sockets and a trusted command required")
    ack, frame = int(args[0]), int(args[1])
    command = args[2:]
    if ack <= 2 or frame <= 2 or ack == frame or not os.path.isabs(command[0]):
        raise ValueError("Fixed channel/command intake")
    info = [os.fstat(fd) for fd in (ack, frame)]
    tokens = [(s.st_dev, s.st_ino) for s in info]
    if not all(stat.S_ISSOCK(s.st_mode) for s in info) or tokens[0] == tokens[1]:
        raise ValueError("Separate inherited sockets required")
    for fd in (0, 1, 2):
        try:
            s = os.fstat(fd)
        except OSError:
            continue
        if (s.st_dev, s.st_ino) in tokens:
            raise ValueError("Protocol descriptor aliases stdio")
    # Preserve both sources before touching fixed low-numbered destinations.
    held = os.dup(ack), os.dup(frame)
    os.dup2(held[0], 3, inheritable=True)
    os.dup2(held[1], 4, inheritable=True)
    # dup2(fd, fd) can be a no-op: explicitly clear close-on-exec on both targets.
    os.set_inheritable(3, True)
    os.set_inheritable(4, True)
    for fd in {*held, ack, frame} - {0, 1, 2, 3, 4}:
        os.close(fd)
    os.execve(command[0], command, ENVIRONMENT)


if __name__ == "__main__":
    main(sys.argv[1:])
