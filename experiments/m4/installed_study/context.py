"""Current caller-selected attachment and fixed commands, never archived authority."""

from pathlib import Path

from . import profile

CURRENT = None
CANCELLED = []
BOOTSTRAP = Path(__file__).absolute().with_name("bootstrap.py")


def current():
    profile.require(CURRENT is not None, "Explicit current runtime attachment required")
    return CURRENT


def activate(attachment, expected=None):
    global CURRENT
    record, identity = profile.load(attachment, expected)
    CURRENT = {"path": str(profile.path(attachment)), "sha256": identity, "record": record}
    return CURRENT


def command(role, entry, arguments, *, record=None):
    value = record or capture()
    return [
        value["python"],
        "-I",
        "-B",
        "-S",
        value["bootstrap"],
        "--attachment",
        value["attachment"],
        "--expected",
        value["attachment_sha256"],
        "--role",
        role,
        "--entry",
        entry,
        *map(str, arguments),
    ]


def capture():
    value = current()
    return {
        "schema": "opent1d.m4-execution-locations/1",
        "python": value["record"]["interpreter"]["executable"],
        "bootstrap": str(BOOTSTRAP),
        "attachment": value["path"],
        "attachment_sha256": value["sha256"],
    }


def snapshot(destination):
    destination.write_bytes(profile.canonical(current()["record"]))


def provenance(snapshots):
    import platform
    import sys

    from .common import ROOT, digest

    application = current()["record"]["application"]
    return {
        "git_head": application["source"]["revision"],
        "git_dirty": application["source"]["dirty"],
        "python": sys.version,
        "platform": platform.platform(),
        "checkout_path": str(ROOT),
        "sources": {name: digest(raw) for name, raw in sorted(snapshots.items())},
        "application": application,
        "runtime_attachment_sha256": current()["sha256"],
    }
