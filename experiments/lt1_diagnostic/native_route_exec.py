"""Fixed exec shim. No raw grant occurs in argv; no native CLI selector exists."""

import json
import os
import re
import stat
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from experiments.lt1_diagnostic import native_route as route  # noqa: E402


def execute(*, invented=False):
    if not invented:
        registry = route.legacy._admissions()
        route.need(registry["setup"] and registry["execution"], "no reviewed route grants")
    route.need(
        sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode,
        "isolated fixed shim",
    )
    extras = set(os.environ) - set(route.transport.owner.ENVIRONMENT) - {route.CARRIER}
    route.need(
        not extras
        or (
            sys.platform == "darwin"
            and extras == {"__CF_USER_TEXT_ENCODING"}
            and re.fullmatch(
                r"0x[0-9A-Fa-f]+:0x[0-9A-Fa-f]+:0x[0-9A-Fa-f]+",
                os.environ["__CF_USER_TEXT_ENCODING"],
            )
            and int(os.environ["__CF_USER_TEXT_ENCODING"].split(":")[0], 16) == os.getuid()
        ),
        "bounded runtime-added shim environment",
    )
    route.need(
        set(os.environ) - extras == set(route.transport.owner.ENVIRONMENT) | {route.CARRIER}
        and all(os.environ[k] == v for k, v in route.transport.owner.ENVIRONMENT.items()),
        "exact four-key startup environment",
    )
    raw = os.environ[route.CARRIER].encode()
    route.need(0 < len(raw) <= route.CARRIER_LIMIT, "bounded startup carrier")
    control = json.loads(raw, object_pairs_hook=route.storage.unique_object)
    route.storage.fields(control, "schema entry observation audit bootstrap")
    route.need(control["schema"] == "opent1d.lt1-route-carrier/2", "carrier version")
    entry_raw, observation_raw = control["entry"].encode(), control["observation"].encode()
    if invented:
        e = route.decode(entry_raw)
        registry = {
            "schema": "opent1d.lt1-native-admissions/1",
            "setup": [e["setup_sha256"]],
            "execution": [
                route.storage.digest(entry_raw),
                route.storage.digest(observation_raw),
                e["engine_sha256"],
                e["integration_sha256"],
            ],
        }
    entry, observation, _ = route.admit(entry_raw, observation_raw, registry, invented)
    route.need(
        control["audit"] == route.source_identity()
        and entry["entry_sources"] == route.prior.grant_sources(control["audit"]),
        "shim current source",
    )
    expected = entry["process_argv"]
    route.need(
        sys.argv[3:] == expected
        and len(expected) == 5
        and expected[1] == str(route.FIXTURE if invented else route.ENTRY),
        "fixed exec argv",
    )
    if invented:
        executable = Path(expected[0])
        route.need(
            executable.is_absolute()
            and executable.name == "node"
            and executable.resolve() == executable
            and observation["entry_executable"] == str(executable)
            and route.storage.digest(executable.read_bytes())
            == observation["runtime"]["executable_sha256"],
            "parent-observed fixed tooling executable",
        )
    else:
        route.need(
            expected[0] == entry["roots"]["staging"] + "/runtime/bin/node",
            "fixed candidate executable",
        )
    ack, frame = int(sys.argv[1]), int(sys.argv[2])
    route.need(ack > 2 and frame > 2 and ack != frame, "separate inherited channels")
    info = [os.fstat(fd) for fd in (ack, frame)]
    tokens = [(s.st_dev, s.st_ino) for s in info]
    route.need(
        all(stat.S_ISSOCK(s.st_mode) for s in info) and tokens[0] != tokens[1],
        "separate inherited sockets",
    )
    for fd in (0, 1, 2):
        try:
            s = os.fstat(fd)
        except OSError:
            continue
        route.need((s.st_dev, s.st_ino) not in tokens, "protocol descriptor aliases stdio")
    held = (os.dup(ack), os.dup(frame))
    try:
        os.dup2(held[0], 3, inheritable=True)
        os.dup2(held[1], 4, inheritable=True)
        os.set_inheritable(3, True)
        os.set_inheritable(4, True)
        for fd in {ack, frame, *held} - {0, 1, 2, 3, 4}:
            os.close(fd)
        command = (
            expected
            if invented
            else [
                str(route.legacy.SANDBOX),
                "-p",
                route.profile(
                    entry["roots"], control["audit"], case_id=entry["case_id"], slot=entry["slot"]
                ),
                *expected,
            ]
        )
        control["bootstrap"] = {
            "supplied_environment_keys": sorted(
                [*route.transport.owner.ENVIRONMENT, route.CARRIER]
            ),
            "observed_environment_keys": sorted(os.environ),
            "runtime_added_environment_keys": sorted(extras),
        }
        control_raw = route.encoded(control).decode()
        route.need(
            len(control_raw.encode()) <= route.CARRIER_LIMIT, "post-bootstrap carrier ceiling"
        )
        env = {**route.transport.owner.ENVIRONMENT, route.CARRIER: control_raw}
        os.execve(command[0], command, env)
    finally:
        for fd in held:
            try:
                os.close(fd)
            except OSError:
                pass


if __name__ == "__main__":
    execute()
