"""Prespecified pilot, threshold gate, numerical matrix and simulator-free reporting."""

import argparse
import json
import os
import signal
import subprocess
import sys
import traceback
from pathlib import Path

from experiments.m0.simglucose.recording import interruption, write_json
from experiments.m1.artifacts import digest, strict_json

from .analysis import compare, read_run, summarize
from .common import ROOT, configurations, identity, sha


def schedule(phase):
    if phase not in ("pilot", "numerical"):
        raise ValueError("Expected pilot or numerical phase")
    configs = configurations()
    if phase == "pilot":
        configs = [configs[0], configs[-2]]
    cases = []
    for index, cfg in enumerate(configs):
        for mode in ("feedback", "replay"):
            for factor in (1, 10, 100):
                cases.append(
                    dict(
                        id=f"{index:02}-{mode}-{factor}",
                        config=cfg | dict(mode=mode, factor=factor),
                        nominal=f"{index:02}-feedback-1",
                    )
                )
        if phase == "numerical":
            for warmup in (0, 2880):
                cases.append(
                    dict(
                        id=f"{index:02}-warmup-{warmup}",
                        config=cfg | dict(warmup=warmup),
                        nominal=f"{index:02}-feedback-1",
                    )
                )
    return cases


def freeze(pilot, output, limits, rationale):
    if Path(output).exists():
        raise FileExistsError(output)
    report = reconstruct(pilot)
    here = identity()
    if here["dirty"]:
        raise ValueError("Commit the reviewed implementation before freezing")
    if (
        report["phase"] != "pilot"
        or report["status"] != "completed"
        or any(c["status"] != "completed" for c in report["cases"])
    ):
        raise ValueError("Pilot must be complete before threshold freeze")
    previous = strict_json((Path(pilot) / "study.json").read_bytes())["identity"]
    for key in ("source_sha256", "locks_sha256", "protocol_sha256"):
        if here[key] != previous[key]:
            raise ValueError("Pilot source/lock/protocol differs")
    expected = {
        "max_abs_glucose_mg_dl",
        "mean_abs_glucose_mg_dl",
        "max_abs_exposure_pp",
        "abs_insulin_u",
    }
    from experiments.m1.contracts import number

    if not isinstance(limits, dict) or set(limits) != expected:
        raise ValueError("Specify all signal limits")
    if (
        not isinstance(rationale, dict)
        or set(rationale) != expected
        or any(not isinstance(v, str) or not v for v in rationale.values())
    ):
        raise ValueError("Require a rationale for every numerical signal")
    for k, v in limits.items():
        number(v, k, 0)
    data = dict(
        schema="iv001.thresholds/1",
        identity=here,
        limits=limits,
        rationale=rationale,
        pilot_report_sha256=sha(json.dumps(report, sort_keys=True).encode()),
        pilot_inputs=report["inputs_sha256"],
        cases=schedule("numerical"),
    )
    write_json(Path(output), data)
    return data


def run(output, phase, threshold_path=None):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    here = identity()
    study = dict(
        schema="iv001.study/1", phase=phase, status="started", identity=here, cases=schedule(phase)
    )
    write_json(output / "study.json", study)
    (output / "inputs").mkdir()
    if phase == "numerical":
        thresholds = strict_json(Path(threshold_path).read_bytes())
        if (
            thresholds.get("schema") != "iv001.thresholds/1"
            or thresholds.get("cases") != study["cases"]
        ):
            raise ValueError("Missing frozen numerical schedule")
        if here["dirty"]:
            raise ValueError("Numerical execution requires clean committed sources")
        for key in ("source_sha256", "locks_sha256", "protocol_sha256"):
            if thresholds["identity"][key] != here[key]:
                raise ValueError("Sources changed after threshold freeze")
        (output / "thresholds.json").write_bytes(Path(threshold_path).read_bytes())
    failed = False
    try:
        with interruption(660 * len(study["cases"])):
            for case in study["cases"]:
                name = case["id"]
                cfg = case["config"]
                config_path = output / "inputs" / f"{name}.json"
                write_json(config_path, cfg)
                command = [
                    sys.executable,
                    "-m",
                    "experiments.verification.run",
                    "--config",
                    str(config_path),
                    "--output",
                    str(output / name),
                ]
                if cfg["mode"] == "replay":
                    nominal = read_run(output / case["nominal"])
                    replay_path = output / "inputs" / f"{name}-replay.json"
                    write_json(
                        replay_path,
                        dict(
                            config=nominal["config"],
                            status=nominal["status"],
                            trace_sha256=nominal["inputs_sha256"]["trace.jsonl"],
                            rows=nominal["rows"],
                        ),
                    )
                    command += ["--replay", str(replay_path)]
                with (output / "inputs" / f"{name}.log").open("wb") as log:
                    child = subprocess.Popen(
                        command,
                        cwd=ROOT,
                        stdout=log,
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
                case["returncode"] = code
                failed = failed or code != 0
                write_json(output / "study.json", study)
                print(name, read_run(output / name)["status"], flush=True)
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


def reconstruct(output):
    output = Path(output)
    raw = (output / "study.json").read_bytes()
    study = strict_json(raw)
    if study.get("schema") != "iv001.study/1" or study.get("status") not in (
        "started",
        "failed",
        "completed",
    ):
        raise ValueError("Invalid study")
    expected = schedule(study["phase"])
    if [{k: v for k, v in c.items() if k != "returncode"} for c in study["cases"]] != expected:
        raise ValueError("Planned cases differ from protocol")
    limits = None
    inputs = {"study.json": sha(raw)}
    if (output / "thresholds.json").exists():
        threshold_raw = (output / "thresholds.json").read_bytes()
        threshold = strict_json(threshold_raw)
        limits = threshold["limits"]
        inputs["thresholds.json"] = sha(threshold_raw)
        if threshold.get("cases") != expected:
            raise ValueError("Threshold schedule differs")
        for k in ("source_sha256", "locks_sha256", "protocol_sha256"):
            if threshold["identity"][k] != study["identity"][k]:
                raise ValueError("Threshold provenance differs")
    elif study["phase"] == "numerical" and study["status"] == "completed":
        raise ValueError("Completed matrix without thresholds")
    runs = {}
    result = []
    for case in study["cases"]:
        name = case["id"]
        if not (output / name / "manifest.json").exists():
            result.append(
                dict(id=name, status="not_attempted", config=case["config"], metrics=None)
            )
            continue
        saved = read_run(output / name)
        runs[name] = saved
        for filename, value in saved["inputs_sha256"].items():
            inputs[f"{name}/{filename}"] = value
        if saved["config"] is not None and saved["config"] != case["config"]:
            raise ValueError("Case configuration differs")
        if "returncode" in case:
            good = saved["status"] in ("completed", "terminated", "input_exhausted")
            if (case["returncode"] == 0) != good:
                raise ValueError("Study and run process status disagree")
        for k in ("source_sha256", "locks_sha256", "protocol_sha256"):
            if k in saved["manifest"] and saved["manifest"][k] != study["identity"][k]:
                raise ValueError("Case implementation differs from frozen study")
        result.append(
            dict(id=name, status=saved["status"], config=case["config"], metrics=summarize(saved))
        )
    if study["status"] == "completed" and any(
        c["status"] not in ("completed", "terminated", "input_exhausted") for c in result
    ):
        raise ValueError("False study completion")
    for case in study["cases"]:
        if case["config"]["mode"] != "replay" or case["id"] not in runs:
            continue
        saved = runs[case["id"]]
        if "replay.json" not in saved["inputs_sha256"]:
            continue
        replay_raw = (output / case["id"] / "replay.json").read_bytes()
        if sha(replay_raw) != saved["inputs_sha256"]["replay.json"]:
            raise ValueError("Replay changed during reconstruction")
        replay = strict_json(replay_raw)
        nominal = runs[case["nominal"]]
        if (
            replay["rows"] != nominal["rows"]
            or replay["trace_sha256"] != nominal["inputs_sha256"]["trace.jsonl"]
        ):
            raise ValueError("Replay does not identify the consumed nominal source")
        if saved["rows"]:
            compare(saved, nominal, fixed=True)
    comparisons = []
    for i in range(2 if study["phase"] == "pilot" else 10):
        for mode in ("feedback", "replay"):
            for a, b in ((1, 10), (10, 100), (1, 100)):
                left = f"{i:02}-{mode}-{a}"
                right = f"{i:02}-{mode}-{b}"
                if left in runs and right in runs:
                    comparisons.append(
                        dict(
                            left=left,
                            right=right,
                            kind="refinement",
                            **compare(runs[left], runs[right], limits, fixed=mode == "replay"),
                        )
                    )
        for warmup in (0, 2880):
            left = f"{i:02}-feedback-1"
            right = f"{i:02}-warmup-{warmup}"
            if left in runs and right in runs:
                comparisons.append(
                    dict(
                        left=left,
                        right=right,
                        kind="initialization",
                        **compare(runs[left], runs[right], limits),
                    )
                )
    return dict(
        schema="iv001.report/1",
        phase=study["phase"],
        status=study["status"],
        cases=result,
        comparisons=comparisons,
        inputs_sha256=inputs,
        analysis_sha256={
            str(p.relative_to(ROOT)): digest(p)
            for p in (
                Path(__file__),
                Path(__file__).with_name("analysis.py"),
                Path(__file__).with_name("common.py"),
                ROOT / "experiments/m2/analysis.py",
            )
        },
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=("pilot", "numerical", "report", "freeze"))
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--study", type=Path)
    p.add_argument("--thresholds", type=Path)
    p.add_argument("--criteria", type=Path)
    args = p.parse_args()
    if args.command == "report":
        write_json(args.output, reconstruct(args.study))
    elif args.command == "freeze":
        criteria = strict_json(args.criteria.read_bytes())
        freeze(args.study, args.output, criteria["limits"], criteria["rationale"])
    else:
        outcome = run(args.output, args.command, args.thresholds)
        sys.exit(0 if outcome["status"] == "completed" else 1)
