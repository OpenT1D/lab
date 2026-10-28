"""Replay synthetic confirmed pump events through pinned source-native IOB."""

import argparse
import json
import math
import subprocess
from pathlib import Path

from .oref0_adapter import (
    PumpBolusReceipt,
    PumpTempReceipt,
    _timestamp,
    pump_history,
    source_decision_on_m1_grid,
)
from .oref0_example_history import current_clean_checkout, digest
from .oref0_preflight import COMMIT

SOURCE_HASHES = {
    "lib/iob/index.js": "f2ced62827d172abf11aef0589202ceed69c12f00cff007fff3c9e25bd13c7ea",
    "lib/iob/history.js": "0e61cdf63ca90a302a44f74fc79600b864b32328c75ae7abc94c98bb12963d89",
    "lib/iob/calculate.js": "ca8b738cd5c4db037760949c09028448e01b155680f0bac6c3c081e24300d348",
    "lib/iob/total.js": "6c093cf78af2952bdfd096f46a49b1d7972e4fefdfde6594355b8ffeb63a8b59",
    "examples/profile.json": "cbfbecc5c29fbcac64f68ef534d8bfe228b79c5300a704dd3e60dd1a7dcc29bb",
}
NODE_SCRIPT = (
    "const iob=require('./lib/iob');"
    "const input=JSON.parse(process.argv[1]);"
    "console.log(JSON.stringify(iob(input,true)[0]));"
)


def source_iob(source, profile, receipts):
    payload = {
        "history": pump_history(receipts, decision_min=60),
        "profile": profile,
        "clock": _timestamp(60),
    }
    run = subprocess.run(
        ("node", "-e", NODE_SCRIPT, json.dumps(payload, sort_keys=True)),
        cwd=source,
        capture_output=True,
        text=True,
        check=False,
    )
    if run.returncode:
        raise ValueError(f"Pinned source IOB failed with exit {run.returncode}")
    return json.loads(run.stdout)


def audit(source):
    source = Path(source).resolve()
    lock = current_clean_checkout(source)
    hashes = {name: digest((source / name).read_bytes()) for name in SOURCE_HASHES}
    if hashes != SOURCE_HASHES:
        raise ValueError("Pinned IOB source/profile hash mismatch")
    profile = json.loads((source / "examples/profile.json").read_text())
    baseline = source_iob(source, profile, ())
    temp = source_iob(source, profile, (PumpTempReceipt(0, 2, 30),))
    bolus = source_iob(source, profile, (PumpBolusReceipt(30, 1),))
    combined = source_iob(source, profile, (PumpTempReceipt(0, 2, 30), PumpBolusReceipt(30, 1)))
    # Fixed synthetic source fingerprint. These are source outputs, not M1
    # controller inputs, clinical estimates, or values fitted to outcomes.
    expected = (
        (baseline["iob"], 0),
        (temp["iob"], 0.425),
        (bolus["iob"], 0.93),
        (combined["iob"], 1.355),
        (combined["basaliob"], 0.425),
        (combined["bolusiob"], 0.93),
        (combined["iob"], temp["iob"] + bolus["iob"]),
    )
    if not all(
        math.isclose(actual, reference, rel_tol=0, abs_tol=1e-12) for actual, reference in expected
    ):
        raise ValueError("Synthetic source IOB fingerprint changed")
    node = subprocess.run(
        ("node", "--version"), cwd=source, capture_output=True, text=True, check=True
    )
    return {
        "schema": "opent1d.c1.oref0-adapter-preflight/1",
        "source_commit": COMMIT,
        "source_sha256": hashes,
        "dependency_lock_sha256": lock["sha256"],
        "runtime_node": node.stdout.strip(),
        "profile_role": "upstream example profile, not an M1 patient profile",
        "synthetic_receipts": {
            "baseline_iob_u": baseline["iob"],
            "temp_iob_u": temp["iob"],
            "bolus_iob_u": bolus["iob"],
            "combined_iob_u": combined["iob"],
            "combined_basal_iob_u": combined["basaliob"],
            "combined_bolus_iob_u": combined["bolusiob"],
        },
        "clock": {
            "source_decision_5_min_on_m1_grid": source_decision_on_m1_grid(5),
            "source_decision_15_min_on_m1_grid": source_decision_on_m1_grid(15),
        },
        "gates": {
            "source_iob_synthetic_receipts": "pass",
            "m1_confirmed_pump_history_causal_input": "open",
            "five_minute_decision_on_three_minute_grid": "fail",
            "m1_profile_mapping": "open",
            "m1_strong_comparator": "closed",
        },
        "eligible_m1_comparator": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(f"{args.output}: eligible_m1_comparator={result['eligible_m1_comparator']}")


if __name__ == "__main__":
    main()
