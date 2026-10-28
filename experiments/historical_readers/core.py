"""Keep strict historical readers usable from a current standard-library Python."""

import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

from experiments.catalogue.formats import reconstruction_args, report_complete
from experiments.catalogue.storage import (
    ROOT,
    digest,
    dump,
    fresh,
    inventory,
    read,
    regular,
    require,
    seal,
    source_hashes,
    supervise,
)

SCHEMA = "opent1d.historical-reader-receipt/1"
REVISION = re.compile(r"[0-9a-f]{40}\Z")
TASKS = (
    "p1-controller",
    "m3-forecast",
    "m3-compare",
    "m4-secretion",
    "m4-compare",
    "m4-study",
    "m4-study-secure",
    "m5-prognosis",
    "campaign",
)
SOURCES = (
    "experiments/historical_readers/__init__.py",
    "experiments/historical_readers/__main__.py",
    "experiments/historical_readers/core.py",
    "experiments/catalogue/__init__.py",
    "experiments/catalogue/formats.py",
    "experiments/catalogue/storage.py",
)


def environment():
    """No inherited Python, Git, uv or virtual-environment selectors."""
    return {"PATH": os.defpath, "LANG": "C", "PYTHONDONTWRITEBYTECODE": "1"}


def git_command(executable, checkout, *args):
    return subprocess.check_output(
        [
            str(executable),
            "--no-optional-locks",
            "-c",
            "core.fsmonitor=false",
            "-c",
            "core.untrackedCache=false",
            "-C",
            str(checkout),
            *args,
        ],
        env=environment(),
        stdin=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        timeout=30,
    )


def checkout_snapshot(checkout, revision, git):
    """Require an explicit, clean, exact Git checkout; hash all tracked bytes."""
    root = git_command(git, checkout, "rev-parse", "--show-toplevel").decode().strip()
    require(Path(root).resolve() == checkout, "Trusted checkout must be its Git root")
    head = git_command(git, checkout, "rev-parse", "HEAD").decode().strip()
    require(head == revision, "Trusted checkout revision differs")
    status = git_command(
        git,
        checkout,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
        "--ignore-submodules=all",
    )
    require(not status, "Trusted checkout must have clean tracked and nonignored untracked files")
    names = git_command(git, checkout, "ls-files", "-z").decode().split("\0")
    files = {}
    for name in sorted(set(names) - {""}):
        relative = Path(name)
        require(not relative.is_absolute() and ".." not in relative.parts, "Invalid tracked path")
        path = checkout / relative
        contained = (path, *path.relative_to(checkout).parents)
        require(
            not any(
                (part if part.is_absolute() else checkout / part).is_symlink() for part in contained
            ),
            "Trusted checkout contains a symlink path",
        )
        regular(path)
        before = path.stat()
        raw = path.read_bytes()
        after = path.stat()
        require(
            (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns),
            "Trusted checkout changed while being read",
        )
        files[name] = {"sha256": digest(raw), "size": len(raw)}
    require(files, "Trusted checkout has no tracked files")
    return {"revision": head, "files": files}


def reader_args(task, archive, output, allow_failed):
    require(task in TASKS, "Unregistered historical reader task")
    if task == "m4-study-secure":
        args = [
            "-m",
            "experiments.m4.secure_study",
            "reconstruct",
            "--archive",
            str(archive),
            "--output",
            str(output),
        ]
        if allow_failed:
            args.append("--allow-failed")
        return args
    if task == "campaign":
        args = [
            "-m",
            "experiments.campaigns",
            "reconstruct",
            "--campaign",
            str(archive),
            "--output",
            str(output),
        ]
        if allow_failed:
            args.append("--allow-failed")
        return args
    return reconstruction_args(task, archive, output, allow_failed)


def reconstruct(
    task, archive, checkout, revision, output, *, timeout_seconds=120, allow_failed=False
):
    """Run only a known reader from a caller-trusted checkout, never archived code."""
    require(task in TASKS, "Unregistered historical reader task")
    require(isinstance(revision, str) and REVISION.fullmatch(revision), "Use a full Git revision")
    require(
        type(timeout_seconds) is int and 1 <= timeout_seconds <= 1800,
        "Reader timeout must be an integer in [1, 1800] seconds",
    )
    require(type(allow_failed) is bool, "Invalid failed-archive option")
    archive, checkout = Path(archive).absolute(), Path(checkout).absolute()
    require(not archive.is_symlink() and not checkout.is_symlink(), "Symlink directories refused")
    archive, checkout = archive.resolve(), checkout.resolve()
    require(checkout.is_dir(), "Trusted checkout must exist")
    git_path = shutil.which("git")
    require(git_path is not None, "Git is required for trusted-checkout verification")
    git = regular(Path(git_path).resolve())
    checkout_before = checkout_snapshot(checkout, revision, git)
    archive_before = inventory(archive)
    require(archive_before, "Source archive is empty")
    helper_before = source_hashes(SOURCES)
    output = fresh(output, [archive, checkout, ROOT])
    rebuilt = output / "reconstructed"
    args = [
        sys.executable,
        "-B",
        "-E",
        "-s",
        "-S",
        *reader_args(task, archive, rebuilt, allow_failed),
    ]
    receipt = {
        "schema": SCHEMA,
        "task": task,
        "archive": str(archive),
        "trusted_checkout": str(checkout),
        "revision": revision,
        "allow_failed": allow_failed,
        "timeout_seconds": timeout_seconds,
        "argv": args,
        "status": "failed",
        "verified_reconstruction": False,
        "complete": None,
        "exit_code": None,
        "interruption_signal": None,
        "errors": [],
        "runtime": {
            "python": sys.version,
            "platform": platform.platform(),
            "executable": sys.executable,
        },
        "git": {"executable": str(git), "sha256": digest(git.read_bytes())},
        "helper_sources_sha256": helper_before,
        "checkout_before": checkout_before,
        "checkout_after": None,
        "archive_before": archive_before,
        "archive_after": None,
        "archive_unchanged": False,
        "checkout_unchanged": False,
        "scope": "Saved-evidence reconstruction only; no simulation or supplied model execution",
    }
    try:
        operation = supervise(args, output / "reader.log", checkout, environment(), timeout_seconds)
        receipt.update(status=operation["status"], exit_code=operation["exit_code"])
        receipt["interruption_signal"] = operation.get("signal")
        if operation["status"] == "completed":
            report = read((archive if task == "m5-prognosis" else rebuilt) / "report.json")
            if task == "campaign":
                require(type(report.get("passed")) is bool, "Invalid campaign completeness")
                receipt["complete"] = report["passed"]
            else:
                receipt["complete"] = report_complete(task, report)
            receipt["verified_reconstruction"] = True
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        receipt["errors"].append(type(error).__name__)
    # Always check both inputs, including after reader failure, timeout or interruption.
    for label, check in (
        ("archive", lambda: inventory(archive)),
        ("checkout", lambda: checkout_snapshot(checkout, revision, git)),
    ):
        try:
            receipt[label + "_after"] = check()
            receipt[label + "_unchanged"] = receipt[label + "_after"] == receipt[label + "_before"]
            require(receipt[label + "_unchanged"], label + " changed during reconstruction")
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            receipt["errors"].append(label + ": " + type(error).__name__)
    try:
        require(source_hashes(SOURCES) == helper_before, "Historical-reader helper changed")
    except (OSError, ValueError) as error:
        receipt["errors"].append("helper: " + type(error).__name__)
    if receipt["errors"]:
        receipt.update(status="failed", verified_reconstruction=False, complete=None)
    dump(output / "receipt.json", receipt)
    seal(output)
    return receipt
