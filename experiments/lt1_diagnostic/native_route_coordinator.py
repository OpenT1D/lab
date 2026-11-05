"""Limited fixed C18 coordinator: public wait stage, then exact admitted route.

The public wait stage has a separately admitted start permit. It opens no
private path, candidate or FD3/4. Its actual PID is reviewed before entry/observer
admissions; no code derives or publishes native memberships automatically.
"""

import json
import os
import select
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from experiments.gui.ownership import ProcessTable  # noqa: E402
from experiments.lt1_diagnostic import native_route as route  # noqa: E402


def main(*, invented=False):
    if not invented:
        registry = route.prior._registry(route.legacy._admissions())
        route.need(
            registry["setup"] and registry["execution"], "no reviewed coordinator start authority"
        )
    text = os.environ.get(route.CARRIER, "")
    route.need(0 < len(text.encode()) <= route.CARRIER_LIMIT, "bounded coordinator control")
    control = json.loads(text, object_pairs_hook=route.storage.unique_object)
    route.storage.fields(control, "schema grant audit")
    route.need(
        control["schema"] == "opent1d.lt1-coordinator-start-carrier/2",
        "fixed coordinator bootstrap",
    )
    grant_raw = control["grant"].encode()
    grant = route.decode(grant_raw)
    if not invented:
        registry = route.legacy._admissions()
        route.need(
            route.storage.digest(grant_raw) in registry["execution"]
            and grant["setup_sha256"] in registry["setup"],
            "no reviewed coordinator start permit",
        )
    route.storage.fields(
        grant,
        "schema kind action observer_pid observer_start setup_sha256 entry_sources nonce_sha256",
    )
    route.need(
        grant["schema"] == "opent1d.lt1-coordinator-start/2"
        and grant["kind"] == ("invented" if invented else "native-unadmitted")
        and grant["action"] == "wait-for-reviewed-C18-grants"
        and grant["entry_sources"] == route.prior.grant_sources(route.source_identity())
        and control["audit"] == route.source_identity(),
        "reviewed fixed coordinator source",
    )
    observer = ProcessTable().one(os.getppid())
    route.need(
        observer
        and observer["pid"] == grant["observer_pid"]
        and observer["start"] == grant["observer_start"],
        "actual observer parent",
    )
    delete = os.environ.pop(route.CARRIER)
    del delete
    own = ProcessTable().one(os.getpid())
    print(json.dumps({"schema": "opent1d.lt1-coordinator-ready/2", "identity": own}), flush=True)
    route.need(select.select([sys.stdin], [], [], 300)[0], "bounded public coordinator wait")
    until = time.monotonic() + 30
    incoming = bytearray()
    while b"\n" not in incoming:
        route.need(
            time.monotonic() < until
            and select.select([sys.stdin], [], [], max(0, until - time.monotonic()))[0],
            "coordinator control deadline",
        )
        part = os.read(sys.stdin.fileno(), min(8192, route.CARRIER_LIMIT + 2 - len(incoming)))
        route.need(
            part and len(incoming) + len(part) <= route.CARRIER_LIMIT + 1,
            "bounded coordinator submission",
        )
        incoming.extend(part)
    route.need(
        incoming.endswith(b"\n") and incoming.count(b"\n") == 1, "single coordinator submission"
    )
    request = json.loads(incoming, object_pairs_hook=route.storage.unique_object)
    if invented:
        route.storage.fields(request, "invented_root observed_tooling")
        sys.path.insert(0, str(ROOT / "tests"))
        import lt1_native_route_fixture as fixture

        prepared = fixture.prepare(
            Path(request["invented_root"]),
            case_id="C18",
            slot="blocked",
            timeout=20,
            _observed_tooling=request["observed_tooling"],
        )
        print(
            json.dumps(
                {
                    "control": {
                        "entry": prepared["entry_raw"].decode(),
                        "observation": prepared["observation_raw"].decode(),
                        "audit": prepared["expected_identity"],
                    }
                },
                separators=(",", ":"),
            ),
            flush=True,
        )
        receipt = route._launch_invented(
            prepared["entry_raw"],
            prepared["observation_raw"],
            expected_identity=prepared["expected_identity"],
        )
    else:
        route.storage.fields(request, "schema entry observation audit bootstrap")
        route.need(request["schema"] == "opent1d.lt1-route-carrier/2", "entry submission")
        receipt = route.launch(
            request["entry"].encode(),
            request["observation"].encode(),
            expected_identity=request["audit"],
        )
    print(json.dumps({"actual_route_receipt": receipt}), flush=True)


if __name__ == "__main__":
    main()
