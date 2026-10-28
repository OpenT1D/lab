"""Freeze and execute the bounded IV-001 robustness matrix; reconstruct without engines."""

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import traceback
from collections import Counter
from pathlib import Path

from experiments.m0.simglucose.recording import interruption, write_json
from experiments.m1.artifacts import digest, strict_json
from experiments.m1.contracts import number
from experiments.m1.validation import HASH, REVISION, hashes

from .analysis import read_run, summarize
from .common import ROOT, configurations, identity, sha, validate
from .conditions import PARAMETERS, VARIANTS


def schedule():
    return [
        dict(
            id=f"{i:02}-{variant}",
            config=validate(
                cfg
                | {
                    "schema": "iv001.robust-case/1",
                    "variant": variant,
                    "warmup": {"warmup-0": 0, "warmup-48": 2880}.get(variant, 1440),
                }
            ),
        )
        for i, cfg in enumerate(configurations())
        for variant in VARIANTS
    ]


def freeze(output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    here = identity()
    if here["dirty"]:
        raise ValueError("Commit sources before freezing robustness")
    parameters = {}
    commands = {
        "simglucose": [
            str(ROOT / "experiments/m0/simglucose/.venv/bin/python"),
            "-m",
            "experiments.verification.parameter_probe",
        ],
        "lt1_cambridge": [
            "node",
            "--loader",
            str(ROOT / "experiments/m0/lt1/node_modules/ts-node/esm.mjs"),
            str(ROOT / "experiments/verification/parameter_probe.mjs"),
        ],
    }
    for engine, command in commands.items():
        with (
            (output / f"{engine}.json").open("wb") as stdout,
            (output / f"{engine}.log").open("wb") as stderr,
        ):
            subprocess.run(
                command,
                cwd=ROOT,
                env=dict(
                    os.environ, TS_NODE_PROJECT=str(ROOT / "experiments/m0/lt1/tsconfig.json")
                ),
                stdout=stdout,
                stderr=stderr,
                check=True,
                timeout=120,
            )
        parameters[engine] = strict_json((output / f"{engine}.json").read_bytes())["parameters"]
        for profile in parameters[engine].values():
            for spec in PARAMETERS[engine]:
                if number(profile.get(spec["name"]), spec["name"], 0) <= 0:
                    raise ValueError("Positive native parameter required")
    for case in schedule():
        write_json(output / f"{case['id']}.json", case["config"])
    plan = dict(
        schema="iv001.robust-plan/1",
        identity=here,
        cases=schedule(),
        parameter_definitions=PARAMETERS,
        original_parameters=parameters,
        analysis={
            "comparisons": "complete within-engine/profile/seed pairs only",
            "uncertainty": "range across development pairs; no population confidence interval",
            "reversal": (
                "strict sign change in second-minus-first difference versus baseline; ties separate"
            ),
            "tuning": "none",
            "solver": "native; Cambridge/MPC numerical sensitivity remains a limitation",
        },
        files_sha256={p.name: digest(p) for p in sorted(output.iterdir()) if p.is_file()},
    )
    write_json(output / "plan.json", plan)
    return read_plan(output)[0]


def _read_plan(folder):
    folder = Path(folder)
    files = {p.name: p.read_bytes() for p in folder.iterdir() if p.is_file() and not p.is_symlink()}
    if len(files) != len(list(folder.iterdir())):
        raise ValueError("Invalid frozen plan entries")
    plan = strict_json(files["plan.json"])
    if plan.get("schema") != "iv001.robust-plan/1" or json.dumps(
        plan.get("cases"), sort_keys=True
    ) != json.dumps(schedule(), sort_keys=True):
        raise ValueError("Frozen robustness schedule differs")
    provenance = plan.get("identity")
    if not isinstance(provenance, dict):
        raise ValueError("Missing frozen implementation identity")
    hashes(
        provenance.get("source_sha256"),
        "frozen sources",
        ("experiments/verification/robustness.py", "experiments/verification/conditions.py"),
    )
    hashes(
        provenance.get("locks_sha256"),
        "frozen locks",
        ("uv.lock", "experiments/m0/simglucose/uv.lock", "experiments/m0/lt1/package-lock.json"),
    )
    if type(provenance.get("dirty")) is not bool or provenance["dirty"]:
        raise ValueError("Frozen source must be clean")
    for key, pattern in (("revision", REVISION), ("protocol_sha256", HASH)):
        if not isinstance(provenance.get(key), str) or not pattern.fullmatch(provenance[key]):
            raise ValueError("Missing frozen source/protocol revision")
    if json.dumps(plan.get("parameter_definitions"), sort_keys=True) != json.dumps(
        PARAMETERS, sort_keys=True
    ):
        raise ValueError("Frozen parameter definitions differ")
    if {k: sha(v) for k, v in files.items() if k != "plan.json"} != plan.get("files_sha256"):
        raise ValueError("Frozen parameter probe bytes changed")
    for engine in PARAMETERS:
        if (
            strict_json(files[f"{engine}.json"])["parameters"]
            != plan["original_parameters"][engine]
        ):
            raise ValueError("Plan does not match native parameter probe")
    return plan, {k: sha(v) for k, v in files.items()}


def read_plan(folder):
    try:
        return _read_plan(folder)
    except (KeyError, TypeError, AttributeError, IndexError) as error:
        raise ValueError(f"Invalid or missing frozen plan field: {error}") from error


def metrics(case):
    m = case["metrics"]
    if case["status"] != "completed" or not m or m["observed_minutes"] != 1440:
        return None
    return m["glucose"] | {"delivered_insulin_u": m["delivered_insulin_u"]}


def differences(first, second):
    a, b = metrics(first), metrics(second)
    if a is None or b is None:
        return None
    return {
        k: b[k] - a[k]
        for k in a
        if a[k] is not None and b[k] is not None and k != "observed_minutes"
    }


def comparisons(cases):
    by_id = {c["id"]: c for c in cases}
    within = []
    for i in range(10):
        base = by_id[f"{i:02}-baseline"]
        for variant in VARIANTS:
            case = by_id[f"{i:02}-{variant}"]
            within.append(
                dict(baseline=base["id"], variant=case["id"], delta=differences(base, case))
            )
    pairs = []
    for i in range(0, 10, 2):
        baseline = differences(by_id[f"{i:02}-baseline"], by_id[f"{i + 1:02}-baseline"])
        for variant in VARIANTS:
            first, second = by_id[f"{i:02}-{variant}"], by_id[f"{i + 1:02}-{variant}"]
            delta = differences(first, second)
            reversal = (
                None
                if delta is None or baseline is None
                else {
                    k: (
                        "reversal"
                        if delta[k] * baseline[k] < 0
                        else "tie"
                        if delta[k] == 0 or baseline[k] == 0
                        else "same_sign"
                    )
                    for k in delta
                }
            )
            pairs.append(
                dict(
                    engine=first["config"]["engine"],
                    profile=first["config"]["profile"],
                    seed=first["config"]["seed"],
                    variant=variant,
                    first=first["id"],
                    second=second["id"],
                    statuses=[first["status"], second["status"]],
                    delta_second_minus_first=delta,
                    versus_baseline=reversal,
                )
            )
    ranges = []
    for engine in PARAMETERS:
        for variant in VARIANTS:
            selected = [p for p in pairs if p["engine"] == engine and p["variant"] == variant]
            values = [
                p["delta_second_minus_first"]
                for p in selected
                if p["delta_second_minus_first"] is not None
            ]
            ranges.append(
                dict(
                    engine=engine,
                    variant=variant,
                    planned_pairs=len(selected),
                    complete_pairs=len(values),
                    descriptive_range=None
                    if not values
                    else {
                        k: [min(v[k] for v in values), max(v[k] for v in values)] for k in values[0]
                    },
                    reversal_counts=dict(
                        Counter(
                            k
                            for p in selected
                            if p["versus_baseline"]
                            for k, v in p["versus_baseline"].items()
                            if v == "reversal"
                        )
                    ),
                )
            )
    return dict(within_controller=within, controller_pairs=pairs, development_ranges=ranges)


def reconstruct(output):
    output = Path(output)
    raw = (output / "study.json").read_bytes()
    study = strict_json(raw)
    plan, inputs = read_plan(output / "frozen")
    inputs = {"frozen/" + k: v for k, v in inputs.items()} | {"study.json": sha(raw)}
    if (
        study.get("schema") != "iv001.robust-study/1"
        or study.get("status") not in ("started", "completed", "failed")
        or study.get("plan_sha256") != inputs["frozen/plan.json"]
    ):
        raise ValueError("Invalid robustness study or frozen plan identity")
    if study.get("cases") != plan["cases"] or study.get("identity") != plan["identity"]:
        raise ValueError("Study differs from frozen plan")
    cases = []
    for case in plan["cases"]:
        folder = output / case["id"]
        if not (folder / "manifest.json").exists():
            if folder.exists() and any(folder.iterdir()):
                raise ValueError("Uninventoried case attempt")
            cases.append(case | dict(status="not_attempted", metrics=None, error=None))
            continue
        saved = read_run(folder)
        if saved["config"] != case["config"]:
            raise ValueError("Robustness case differs from planned configuration")
        for k in ("source_sha256", "locks_sha256", "protocol_sha256", "revision", "dirty"):
            if saved["manifest"].get(k) != plan["identity"][k]:
                raise ValueError("Case differs from frozen implementation")
        inputs.update({case["id"] + "/" + k: v for k, v in saved["inputs_sha256"].items()})
        if "runtime.json" in saved["inputs_sha256"]:
            runtime_raw = (folder / "runtime.json").read_bytes()
            if sha(runtime_raw) != saved["inputs_sha256"]["runtime.json"]:
                raise ValueError("Runtime changed during reconstruction")
            runtime = strict_json(runtime_raw)
            probe = runtime.get("settings", {}).get("parameter_probe")
            if saved["rows"] or saved["status"] == "completed":
                cfg = case["config"]
                if probe["original"] != plan["original_parameters"][cfg["engine"]][cfg["profile"]]:
                    raise ValueError("Original parameters differ from pre-run probe")
        cases.append(
            case
            | dict(
                status=saved["status"],
                metrics=summarize(saved),
                error=saved["manifest"].get("error"),
                unfinished_trace_bytes=saved["unfinished_bytes"],
                unfinished_sensor_bytes=saved["unfinished_sensor_bytes"],
            )
        )
    if study["status"] == "completed" and any(
        c["status"] not in ("completed", "terminated") for c in cases
    ):
        raise ValueError("False robustness study completion")
    allowed = {
        "study.json",
        "frozen",
        "report.json",
        "campaign-error.log",
        "report-error.log",
        "launch-logs",
    } | {c["id"] for c in plan["cases"]}
    if any(p.name not in allowed for p in output.iterdir()):
        raise ValueError("Uninventoried robustness attempt or file")
    logs = output / "launch-logs"
    if logs.exists():
        for p in logs.iterdir():
            if (
                not p.is_file()
                or p.is_symlink()
                or p.name not in {c["id"] + ".log" for c in plan["cases"]}
            ):
                raise ValueError("Invalid launch log")
            inputs["launch-logs/" + p.name] = sha(p.read_bytes())
    for name in ("campaign-error.log", "report-error.log"):
        if (output / name).exists():
            inputs[name] = sha((output / name).read_bytes())
    return dict(
        schema="iv001.robust-report/1",
        status=study["status"],
        planned=len(cases),
        status_counts=dict(Counter(c["status"] for c in cases)),
        cases=cases,
        **comparisons(cases),
        inputs_sha256=dict(sorted(inputs.items())),
        analysis_sha256={
            str(p.relative_to(ROOT)): digest(p)
            for p in (
                Path(__file__),
                Path(__file__).with_name("analysis.py"),
                Path(__file__).with_name("conditions.py"),
                Path(__file__).with_name("common.py"),
                ROOT / "experiments/m2/analysis.py",
            )
        },
        limitations=plan["analysis"],
    )


def run(plan_folder, output):
    plan, _ = read_plan(plan_folder)
    if identity() != plan["identity"] or plan["identity"]["dirty"]:
        raise ValueError("Sources changed after robustness freeze")
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    shutil.copytree(plan_folder, output / "frozen")
    study = dict(
        schema="iv001.robust-study/1",
        status="started",
        identity=plan["identity"],
        plan_sha256=digest(output / "frozen/plan.json"),
        cases=plan["cases"],
    )
    write_json(output / "study.json", study)
    (output / "launch-logs").mkdir()
    try:
        failed = False
        with interruption(660 * len(plan["cases"])):
            for case in plan["cases"]:
                command = [
                    sys.executable,
                    "-m",
                    "experiments.verification.run",
                    "--config",
                    str(output / "frozen" / f"{case['id']}.json"),
                    "--output",
                    str(output / case["id"]),
                ]
                with (output / "launch-logs" / f"{case['id']}.log").open("wb") as stream:
                    child = subprocess.Popen(
                        command,
                        cwd=ROOT,
                        stdout=stream,
                        stderr=subprocess.STDOUT,
                        start_new_session=True,
                    )
                    try:
                        code = child.wait(timeout=630)
                    except BaseException:
                        try:
                            os.killpg(child.pid, signal.SIGTERM)
                        except ProcessLookupError:
                            pass
                        try:
                            child.wait(timeout=10)
                        except subprocess.TimeoutExpired:
                            os.killpg(child.pid, signal.SIGKILL)
                            child.wait()
                        raise
                result = strict_json((output / case["id"] / "manifest.json").read_bytes())
                if (code == 0) != (result["status"] in ("completed", "terminated")):
                    raise ValueError("Supervisor and run status disagree")
                failed = failed or result["status"] not in ("completed", "terminated")
                print(case["id"], result["status"], flush=True)
                if result["status"] == "interrupted":
                    raise RuntimeError(
                        "Robustness campaign interrupted; later cases remain not attempted"
                    )
        if identity() != plan["identity"]:
            raise ValueError("Implementation changed during execution")
        study["status"] = "failed" if failed else "completed"
    except BaseException as error:
        study.update(status="failed", error=f"{type(error).__name__}: {error}")
        (output / "campaign-error.log").write_text(traceback.format_exc())
        raise
    finally:
        write_json(output / "study.json", study)
        active = sys.exc_info()[0] is not None
        try:
            write_json(output / "report.json", reconstruct(output))
        except Exception:
            (output / "report-error.log").write_text(traceback.format_exc())
            if not active:
                raise
    return study


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("freeze", "run", "report"))
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--study", type=Path)
    args = parser.parse_args()
    if args.command == "freeze":
        freeze(args.output)
    elif args.command == "report":
        write_json(args.output, reconstruct(args.study))
    else:
        sys.exit(0 if run(args.plan, args.output)["status"] == "completed" else 1)
