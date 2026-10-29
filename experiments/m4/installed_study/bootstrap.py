"""Fixed isolated source/dependency overlay entry for each fresh M4 process."""

import argparse
import hashlib
import json
import os
import runpy
import signal
import stat
import sys
import tempfile
from pathlib import Path, PurePosixPath


def regular_bytes(path, limit=16 * 1024 * 1024):
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("Linked bootstrap input")
    descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0))
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > limit:
            raise ValueError("Bounded regular bootstrap input required")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            raw = stream.read(limit + 1)
        after, current = os.fstat(descriptor), path.stat(follow_symlinks=False)

        def signature(info):
            return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)

        if (
            len(raw) > limit
            or signature(before) != signature(after)
            or signature(after) != signature(current)
        ):
            raise ValueError("Bootstrap input changed during read")
        return raw
    finally:
        os.close(descriptor)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attachment", type=Path, required=True)
    parser.add_argument("--expected", required=True)
    parser.add_argument("--role", choices=("coordinator", "native", "observer"), required=True)
    parser.add_argument(
        "--entry",
        choices=(
            "study",
            "reference",
            "worker",
            "numerical-tests",
            "observer-tests",
            "beta-cell-tests",
        ),
        required=True,
    )
    args, remaining = parser.parse_known_args()
    allowed = {
        "study": "coordinator",
        "reference": "coordinator",
        "numerical-tests": "native",
        "observer-tests": "observer",
        "beta-cell-tests": "observer",
    }
    if args.entry in allowed and args.role != allowed[args.entry]:
        raise ValueError("Wrong fixed process role")
    if args.entry == "worker":
        kind = remaining[remaining.index("--kind") + 1] if "--kind" in remaining else None
        expected_role = "observer" if kind == "observer" else "native"
        if (
            kind not in {"baseline", "reference", "source", "observer"}
            or args.role != expected_role
        ):
            raise ValueError("Worker dependency role differs from scientific stage")
    received = []

    def queue(signum, _frame):
        received.append(signum)

    if args.role == "coordinator":
        for number in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            signal.signal(number, queue)
    root = Path(__file__).absolute().parents[3]
    raw = regular_bytes(args.attachment)
    if hashlib.sha256(raw).hexdigest() != args.expected:
        raise ValueError("Current attachment changed before process startup")
    # Verify the current source tree before importing any local package/init.
    descriptor = json.loads(raw)
    sources = descriptor["source_files"]
    required = {
        "experiments/m4/installed_study/__init__.py",
        "experiments/m4/installed_study/profile.py",
        "experiments/m4/installed_study/context.py",
        "experiments/m4/installed_study/bootstrap.py",
    }
    if not isinstance(sources, dict) or not required <= set(sources) or len(sources) > 2000:
        raise ValueError("Incomplete source bootstrap inventory")
    for name in sources:
        relative = PurePosixPath(name)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("Unsafe source bootstrap name")
        for parent in relative.parents:
            if parent.parts:
                initializer = (parent / "__init__.py").as_posix()
                if (root / initializer).exists() and initializer not in sources:
                    raise ValueError("Unlisted source package initializer")
    for name, expected in sources.items():
        relative = PurePosixPath(name)
        if (
            relative.is_absolute()
            or relative.as_posix() != name
            or ".." in relative.parts
            or any(c in name for c in ("\\", ":", "\0"))
        ):
            raise ValueError("Unsafe source bootstrap name")
        path = root.joinpath(*relative.parts)
        data = regular_bytes(path)
        if expected != {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}:
            raise ValueError("Current source bootstrap identity differs")
    with tempfile.TemporaryDirectory(prefix="opent1d-m4-pycache-") as cache:
        sys.pycache_prefix = cache
        os.environ["MPLCONFIGDIR"] = str(Path(cache) / "matplotlib")
        os.environ["MPLBACKEND"] = "Agg"
        sys.path.append(str(root))
        os.chdir(root)
        from experiments.m4.installed_study import context

        context.activate(args.attachment, args.expected)
        context.CANCELLED = received
        if args.role != "coordinator":
            sys.path.insert(
                len(sys.path) - 1, context.current()["record"]["roles"][args.role]["site_packages"]
            )
        if args.entry == "beta-cell-tests":
            # This preserved script historically ran from its runtime directory
            # and imports its two fixed local helper modules by simple names.
            sys.path.insert(len(sys.path) - 1, str(root / "experiments/m4/beta_cell/runtime"))
        modules = {
            "study": "experiments.m4.installed_study",
            "reference": "experiments.m4.installed_study.reference",
            "worker": "experiments.m4.installed_study.worker",
            "numerical-tests": "experiments.m4.installed_study.test_numerical",
            "observer-tests": "experiments.m4.c_peptide.test_model",
            "beta-cell-tests": "experiments.m4.beta_cell.runtime.test_model",
        }
        sys.argv = [modules[args.entry], *remaining]
        runpy.run_module(modules[args.entry], run_name="__main__", alter_sys=True)


if __name__ == "__main__":
    main()
