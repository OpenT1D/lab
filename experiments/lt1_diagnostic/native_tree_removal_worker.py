"""Fixed isolated worker. Production has no invented registry or hook selector."""

import os
import signal
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from experiments.lt1_diagnostic import native_tree_removal as tree  # noqa: E402


def execute(*, invented=False):
    grants = None if invented else tree.registry()
    tree.need(
        sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode,
        "fixed isolated worker",
    )
    tree.need(len(sys.argv) == 4, "fixed worker arguments")
    path, request_sha, carrier_sha = sys.argv[1:]
    tree.need(
        tree.retention.sha(request_sha) and tree.retention.sha(carrier_sha), "carrier/request pins"
    )
    if not invented:
        tree.need(request_sha in grants["requests"], "worker exact admission before carrier path")
    p = Path(path)
    tree.need(
        p.is_absolute() and p.resolve() == p and p.name.endswith(".control.json"),
        "fixed control path",
    )
    folder = tree._private_directory(p.parent)
    try:
        raw = tree._read_at(folder, p.name, 3 * tree.LIMIT)
    finally:
        os.close(folder)
    carrier = tree.decoded(raw, carrier_sha, 3 * tree.LIMIT)
    tree.retention.fields(carrier, "schema request context audit")
    tree.need(
        carrier["schema"] == "opent1d.lt1-native-tree-carrier/1"
        and type(carrier["request"]) is str
        and type(carrier["context"]) is str,
        "carrier schema",
    )
    request_raw, context_raw = carrier["request"].encode(), bytes.fromhex(carrier["context"])
    tree.need(tree.digest(request_raw) == request_sha, "worker raw membership")
    if invented:
        grants = {"schema": "opent1d.lt1-removal-admissions/1", "requests": [request_sha]}
    tree.admitted(request_raw, grants)
    r = tree.request(request_raw, context_raw, carrier["audit"], invented=invented)
    tree.need(
        p == Path(r["cleanup_parent"]["path"]) / (r["attempt"] + ".control.json"),
        "request carrier location",
    )
    stop = threading.Event()
    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, lambda *_: stop.set())

    def checkpoint(phase):
        if not invented:
            return
        control = tree.decoded(context_raw)
        if control.get("fixture_phase") == phase:
            if control.get("fixture_crash") is True:
                os._exit(61)
            end = time.monotonic() + control.get("fixture_pause", 0)
            while time.monotonic() < end and not stop.is_set():
                time.sleep(0.01)

    result = tree._remove_reviewed(
        request_raw,
        grants,
        context_raw,
        carrier["audit"],
        invented=invented,
        stop=stop.is_set,
        checkpoint=checkpoint,
    )
    return 0 if result["status"] == "namespace-absence-observed" else 2


if __name__ == "__main__":
    raise SystemExit(execute())
