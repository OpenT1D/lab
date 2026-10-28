"""Immutable archive verification and report reconstruction; standard library only."""

import html
import json
import math
from itertools import combinations
from pathlib import Path

from experiments.m4.causal_secretion.common import declaration

from .analysis import assess_numeric, assess_observer, contrast, numeric_paths, observation_paths
from .common import (
    ARTIFACTS,
    PROTOCOL_OBJECT_SHA256,
    PROTOCOL_SHA256,
    REPORT_SCHEMA,
    SCENARIOS,
    VERSION,
    digest,
    encoded,
    inventory,
    read,
    require,
    source_paths,
    validate_config,
    verify_reference_snapshot,
)


def validate_frozen(directory, files):
    plan = read(directory / "plan.json")
    require(plan.get("schema") == VERSION, "Unsupported study plan")
    require(
        digest(files["config.json"]) == plan.get("config_sha256"),
        "Raw configuration binding changed",
    )
    config = validate_config(read(directory / "config.json"))
    require(config == plan.get("configuration"), "Configuration disagrees with frozen plan")
    p = plan.get("protocol")
    require(
        digest(encoded(p)) == PROTOCOL_OBJECT_SHA256
        and digest(files["sources/experiments/m4/initial_load/protocol.json"]) == PROTOCOL_SHA256
        and read(directory / "sources/experiments/m4/initial_load/protocol.json") == p,
        "Frozen study protocol changed",
    )
    hashes = plan.get("provenance", {}).get("sources")
    require(
        isinstance(hashes, dict) and set(hashes) == set(source_paths()),
        "Incomplete implementation/helper inventory",
    )
    for name, expected in hashes.items():
        require(
            digest(files["sources/" + name]) == expected, f"Implementation snapshot changed: {name}"
        )
    for group in ("protocol_files_sha256", "runtime_files_sha256"):
        for name, expected in p["conditions"][group].items():
            require(
                digest(files["sources/" + name]) == expected,
                f"Frozen scientific/runtime snapshot changed: {name}",
            )
    names = [item["id"] for item in config["sources"]]
    require(set(plan.get("sources", {})) == set(names), "Frozen source roster changed")
    for name in names:
        frozen = plan["sources"][name]
        declared = declaration(read(directory / "frozen" / name / "model.json"))
        require(
            declared == frozen.get("declaration")
            and digest(files[f"frozen/{name}/model.json"]) == frozen.get("declaration_sha256")
            and digest(files[f"frozen/{name}/model.py"])
            == frozen.get("source_sha256")
            == declared["source_sha256"],
            "Frozen model/declaration/parameter binding changed",
        )
    return plan


def owner_state(owner):
    require(
        isinstance(owner, dict)
        and owner.get("status") in {"not_attempted", "completed", "failed", "interrupted"}
        and isinstance(owner.get("attempts"), list),
        "Invalid terminal owner state",
    )
    for attempt in owner["attempts"]:
        require(
            isinstance(attempt, dict)
            and attempt.get("status") in {"completed", "failed", "interrupted"}
            and isinstance(attempt.get("argv"), list),
            "Unsealed stage attempt",
        )
        require(
            type(attempt.get("exit_code")) is int
            or (
                attempt.get("exit_code") is None
                and attempt["status"] == "failed"
                and isinstance(attempt.get("error_type"), str)
            ),
            "Invalid launch/exit evidence",
        )
        require(
            (attempt["status"] == "completed")
            == (attempt["exit_code"] == 0 and attempt.get("error_type") is None),
            "Stage exit/status disagreement",
        )
    if owner["status"] == "not_attempted":
        require(
            not owner["attempts"]
            and owner.get("stage") is None
            and owner.get("error_type") is None,
            "Unattempted owner contains attempt evidence",
        )
    if owner["status"] == "completed":
        require(
            owner.get("stage") == "verification"
            and owner.get("error_type") is None
            and all(item["status"] == "completed" for item in owner["attempts"]),
            "Completed owner has failed stages",
        )


def expected_stage(plan, stage, name=None):
    output = plan["archive_original_path"]
    checkout = plan["provenance"]["checkout_path"]
    if stage == "historical":
        return [
            plan["coordinator_executable"],
            "-B",
            "-S",
            "-m",
            "experiments.m4.feedback.run",
            "--output",
            output + "/historical",
        ], "historical.log"
    kind, label = stage.rsplit("_", 1)
    project = (
        "experiments/m4/beta_cell/runtime" if kind == "observer" else "experiments/m0/simglucose"
    )
    args = [
        checkout + "/" + project + "/.venv/bin/python",
        "-B",
        "-E",
        "-s",
        "-m",
        "experiments.m4.initial_load.worker",
        output,
        "--kind",
        kind,
        "--label",
        label,
    ]
    if name is not None:
        args += ["--source", name]
    return args, f"{name}-{kind}-{label}.log" if name is not None else f"reference-{label}.log"


def ledger(directory, owner, expected, plan, name=None):
    stages = [attempt.get("stage") for attempt in owner["attempts"]]
    require(stages == expected[: len(stages)], "Wrong or repeated stage ledger")
    if owner["status"] == "completed":
        require(stages == expected, "Completed owner is missing required stages")
    for attempt in owner["attempts"]:
        args, logfile = expected_stage(plan, attempt["stage"], name)
        require(attempt["argv"] == args, "Stage command does not bind frozen source/runtime/label")
        budget = attempt.get("timeout_seconds")
        require(
            type(budget) in (int, float)
            and math.isfinite(budget)
            and 0 < budget <= plan["configuration"]["timeout_seconds"],
            "Stage budget changed",
        )
        if name is not None:
            require(
                budget <= plan["configuration"]["source_timeout_seconds"], "Source budget changed"
            )
        try:
            first = (directory / "logs" / logfile).read_bytes().splitlines()[0]
            header = json.loads(first)
        except (OSError, ValueError, IndexError):
            require(
                attempt["exit_code"] is None and attempt["status"] == "failed",
                "Missing supervised command log",
            )
        else:
            require(
                header == {"argv": args, "timeout_seconds": budget},
                "Command log/state disagreement",
            )
    if name is not None and owner["status"] == "completed":
        duration = owner.get("duration_seconds")
        require(
            type(duration) in (int, float)
            and math.isfinite(duration)
            and 0 <= duration <= plan["configuration"]["source_timeout_seconds"],
            "Completed source exceeded whole-source budget",
        )


def validate_state(directory, state, plan):
    names = [item["id"] for item in plan["configuration"]["sources"]]
    require(
        state.get("schema") == VERSION
        and state.get("status") in {"completed", "failed", "interrupted"}
        and set(state.get("sources", {})) == set(names),
        "Incomplete terminal source roster",
    )
    owner_state(state.get("reference"))
    ledger(
        directory,
        state["reference"],
        (["historical"] if plan["historical_manifest_sha256"] is None else [])
        + ["reference_primary", "reference_repeat"],
        plan,
    )
    for name, owner in state["sources"].items():
        owner_state(owner)
        ledger(
            directory,
            owner,
            ["source_primary", "source_repeat", "observer_primary", "observer_repeat"],
            plan,
            name,
        )
        if owner["status"] == "not_attempted":
            require(
                not (directory / "children" / name).exists(),
                "Unattempted source contains numerical attempt evidence",
            )
    interrupted = state.get("interruption_signal")
    require(
        (state["status"] == "interrupted") == (interrupted in (1, 2, 15)),
        "Interruption provenance/state mismatch",
    )
    if state["status"] == "completed":
        require(
            state["reference"]["status"] == "completed"
            and all(owner["status"] == "completed" for owner in state["sources"].values()),
            "Completed study has incomplete owners",
        )
    if state["reference"]["status"] != "completed":
        require(
            all(owner["status"] == "not_attempted" for owner in state["sources"].values()),
            "Source dispatched without accepted common reference",
        )
    if interrupted is not None:
        unattempted = False
        for name in names:
            owner = state["sources"][name]
            unattempted |= owner["status"] == "not_attempted"
            require(
                not unattempted or owner["status"] == "not_attempted",
                "Later source started after interrupted roster boundary",
            )


def missing(directory, base, expected):
    return sorted(str(base / name) for name in expected if not (directory / base / name).is_file())


def diagnostic_worker(directory, path):
    try:
        return read(directory / path)
    except (ValueError, OSError):
        return {"status": "missing_or_invalid_diagnostic", "path": str(path)}


def assessment(directory, plan, state):
    config = plan["configuration"]
    scenes = config["scenarios"]
    reference = {
        "status": state["reference"]["status"],
        "accepted": False,
        "execution": state["reference"],
        "missing_evidence": [],
    }
    for label in ("primary", "repeat"):
        reference["missing_evidence"] += missing(
            directory, Path("reference") / label, numeric_paths(scenes, True)
        )
    if state["reference"]["status"] == "completed":
        verify_reference_snapshot(directory)
        numeric, _ = assess_numeric(directory, plan)
        require(numeric["passed"], "Reference marked completed despite failed numerical gates")
        reference.update(accepted=True, numerical=numeric)
    elif not reference["missing_evidence"] and (directory / "reference-binding.json").is_file():
        try:
            numeric, _ = assess_numeric(directory, plan)
            reference["numerical"] = numeric
        except (ValueError, OSError, KeyError, TypeError):
            reference["numerical"] = {
                "passed": False,
                "reason": "Incomplete or invalid failed-reference diagnostics",
            }
    sources, accepted_curves = {}, {}
    for item in config["sources"]:
        name, owner = item["id"], state["sources"][item["id"]]
        source = {
            **plan["sources"][name],
            "status": owner["status"],
            "accepted": False,
            "execution": owner,
            "scenarios": {
                scene: {
                    "initial_gastric_solid_mg": SCENARIOS[scene],
                    "status": owner["status"],
                    "accepted": False,
                }
                for scene in scenes
            },
            "missing_evidence": [],
        }
        for label in ("primary", "repeat"):
            source["missing_evidence"] += missing(
                directory, Path("children") / name / label, numeric_paths(scenes)
            )
            source["missing_evidence"] += missing(
                directory,
                Path("children") / name / "observations" / label,
                observation_paths(scenes),
            )
        if owner["status"] == "completed":
            require(reference["accepted"], "Completed source has no accepted common reference")
            numeric, records = assess_numeric(directory, plan, name)
            observed, curves = assess_observer(directory, plan, name, records)
            require(
                numeric["passed"] and observed["passed"],
                "Source marked completed despite failed numerical gates",
            )
            source.update(accepted=True, numerical=numeric, observer=observed, curves=curves)
            for scene in scenes:
                source["scenarios"][scene].update(status="completed", accepted=True)
            accepted_curves[name] = curves
        else:
            source["diagnostics"] = {
                label: diagnostic_worker(directory, Path("children") / name / label / "worker.json")
                for label in ("primary", "repeat")
            }
            attempts = source["diagnostics"]["primary"].get("attempts", [])
            for scene in scenes:
                selected = [attempt for attempt in attempts if attempt.get("scenario") == scene]
                source["scenarios"][scene]["status"] = (
                    "not_attempted"
                    if not selected
                    else "completed"
                    if len(selected) == 6
                    and all(attempt.get("status") == "completed" for attempt in selected)
                    else "interrupted"
                    if owner["status"] == "interrupted"
                    else "failed"
                )
        sources[name] = source
    common_controls = {
        "passed": reference["accepted"],
        "reason": None if reference["accepted"] else "Common reference is incomplete or failed",
    }
    if accepted_curves:
        first = next(iter(accepted_curves.values()))
        common_controls["trajectories"] = {
            f"{scene}--{mode}": {
                "times_min": first[scene][mode]["times"],
                "glucose_mg_dl": first[scene][mode]["glucose"],
                "insulin_pmol_l": first[scene][mode]["insulin"],
                "cpeptide_pmol_l": first[scene][mode]["cpeptide"],
            }
            for scene in scenes
            for mode in ("host_constant_basal", "bc008_reference")
        }
        for curves in accepted_curves.values():
            if any(
                curves[scene][mode] != first[scene][mode]
                for scene in scenes
                for mode in ("host_constant_basal", "bc008_reference")
            ):
                common_controls = {
                    "passed": False,
                    "reason": "Accepted sources disagree on common control/reference curves",
                }
    pairs = []
    for left, right in combinations(sources, 2):
        supported = (
            sources[left]["accepted"] and sources[right]["accepted"] and common_controls["passed"]
        )
        reason = (
            None
            if supported
            else common_controls["reason"]
            or "Both entire selected-load source workflows must be accepted"
        )
        pairs.append(
            {
                "left": left,
                "right": right,
                "direction": "left_minus_right",
                "accepted": supported,
                "reason": reason,
                "scenarios": {
                    scene: {
                        "accepted": supported,
                        "reason": reason,
                        "metrics": contrast(
                            sources[left]["curves"][scene]["candidate"],
                            sources[right]["curves"][scene]["candidate"],
                        )
                        if supported
                        else None,
                    }
                    for scene in scenes
                },
            }
        )
    passed = (
        state["status"] == "completed"
        and reference["accepted"]
        and common_controls["passed"]
        and all(source["accepted"] for source in sources.values())
    )
    return {
        "schema": REPORT_SCHEMA,
        "protocol": plan["protocol"]["id"],
        "passed": passed,
        "status": state["status"],
        "configuration": config,
        "provenance": plan["provenance"],
        "reference": reference,
        "common_controls": common_controls,
        "scenarios": [
            {"id": scene, "initial_gastric_solid_mg": SCENARIOS[scene]} for scene in scenes
        ],
        "sources": sources,
        "pairs": pairs,
        "denominators": {
            "sources": len(sources),
            "accepted_sources": sum(source["accepted"] for source in sources.values()),
            "source_scenarios": len(sources) * len(scenes),
            "accepted_source_scenarios": sum(source["accepted"] for source in sources.values())
            * len(scenes),
            "pairs": len(pairs),
            "accepted_pairs": sum(pair["accepted"] for pair in pairs),
        },
        "limitations": plan["protocol"]["excluded"],
        "interruption_signal": state.get("interruption_signal"),
    }


def markdown(report):
    rows = [
        f"# {report['protocol']} — Synthetic initial gastric-load study",
        "",
        f"Status: **{report['status']}**; "
        f"numerical acceptance: **{str(report['passed']).lower()}**.",
        "",
        "Initial gastric solid loads are synthetic initial conditions. "
        "This report establishes no human calibration, dosing, "
        "biological ranking or treatment benefit.",
        "",
        "| Source | Ancestry | Status | Accepted |",
        "| --- | --- | --- | --- |",
    ]

    def safe(value):
        return str(value).replace("|", "\\|").replace("\n", " ")

    for name, source in report["sources"].items():
        rows.append(
            f"| {safe(name)} | {safe(source['declaration']['ancestry'])} | "
            f"{source['status']} | {str(source['accepted']).lower()} |"
        )
    rows += [
        "",
        "Accepted source/load cases: "
        f"{report['denominators']['accepted_source_scenarios']}/"
        f"{report['denominators']['source_scenarios']}. "
        f"Accepted pairs: {report['denominators']['accepted_pairs']}/"
        f"{report['denominators']['pairs']}.",
        "",
        "![Complete accepted trajectories](figure.svg)",
        "",
        "## Descriptive source-pair contrasts",
        "",
        "Direction follows frozen roster order: left minus right. "
        "AUC units are the signal unit multiplied by minutes; time means "
        "and maximum absolute differences retain the signal unit.",
        "",
        "| Pair | Initial load | Signal | Signed AUC | Signed time mean | "
        "Maximum absolute difference |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for pair in report["pairs"]:
        for scene, item in pair["scenarios"].items():
            if item["accepted"]:
                for signal, values in item["metrics"].items():
                    rows.append(
                        f"| {safe(pair['left'])} − {safe(pair['right'])} | {scene} | "
                        f"{signal} | {values['signed_auc_difference']:.10g} | "
                        f"{values['signed_time_mean_difference']:.10g} | "
                        f"{values['maximum_absolute_pointwise_difference']:.10g} |"
                    )
            else:
                rows.append(
                    f"| {safe(pair['left'])} − {safe(pair['right'])} | {scene} | "
                    f"{safe(item['reason'])} | null | null | null |"
                )
    rows += [
        "",
        "## Numerical evidence and failures",
        "",
        "Full check values, limits, solver/refinement evidence, fresh-process "
        "repeats, execution stages and planned missing artifacts are retained "
        "in report.json and the immutable numerical archive.",
    ]
    for name, source in report["sources"].items():
        if not source["accepted"]:
            rows += [
                "",
                f"{safe(name)}: {source['status']}; stage={source['execution']['stage']}; "
                f"error={source['execution']['error_type']}; "
                f"missing artifacts={len(source['missing_evidence'])}. "
                "Every selected scenario remains unaccepted.",
            ]
    if not report["reference"]["accepted"]:
        rows += ["", "The common reference failed or is incomplete; dependent contrasts are null."]
    rows += ["", "## Evidence limits", "", *(f"- {value}" for value in report["limitations"])]
    return "\n".join(rows) + "\n"


def figure(report):
    scenes = report["scenarios"]
    height = 180 + 260 * len(scenes)
    output = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="1320" height="{height}" '
        f'viewBox="0 0 1320 {height}" role="img" '
        'aria-label="Synthetic complete accepted glucose, insulin and C-peptide trajectories">',
        '<rect width="100%" height="100%" fill="white"/>',
        "<style>text{font:13px sans-serif;fill:#18212d}"
        ".title{font-size:19px;font-weight:bold}.axis{stroke:#52606d;stroke-width:1}"
        ".grid{stroke:#e4e9ed;stroke-width:1}.curve{fill:none;stroke-width:1.8}</style>",
        f'<text class="title" x="35" y="30">{html.escape(report["protocol"])}: '
        "initial gastric-load study</text>",
        f'<text x="35" y="55">Status {report["status"]}; accepted '
        f"{report['denominators']['accepted_sources']}/{report['denominators']['sources']} "
        "sources. Descriptive synthetic curves; no ranking.</text>",
    ]
    palette = (
        "#1f77b4",
        "#d62728",
        "#9467bd",
        "#2ca02c",
        "#8c564b",
        "#e377c2",
        "#17becf",
        "#bc8f00",
    )
    tracks = [
        (name, source["curves"], "candidate", palette[index])
        for index, (name, source) in enumerate(report["sources"].items())
        if source["accepted"]
    ]
    if tracks:
        tracks += [
            ("host constant basal", tracks[0][1], "host_constant_basal", "#929292"),
            ("BC-008 reference", tracks[0][1], "bc008_reference", "#151515"),
        ]
    for index, (name, _, _, color) in enumerate(tracks):
        x, y = 35 + (index % 5) * 255, 85 + (index // 5) * 24
        output += [
            f'<line x1="{x}" x2="{x + 24}" y1="{y}" y2="{y}" stroke="{color}" stroke-width="2"/>',
            f'<text x="{x + 31}" y="{y + 4}">{html.escape(name)}</text>',
        ]
    for row, scene in enumerate(scenes):
        name = scene["id"]
        for col, (signal, unit) in enumerate(
            (("glucose", "mg/dL"), ("insulin", "pmol/L"), ("cpeptide", "pmol/L"))
        ):
            x, y, width, graph_height = 65 + col * 430, 180 + row * 260, 340, 170
            output.append(f'<text x="{x}" y="{y - 35}">{name}: {signal} ({unit})</text>')
            values = [
                value for _, curves, mode, _ in tracks for value in curves[name][mode][signal]
            ]
            if not values:
                output.append(f'<text x="{x}" y="{y + 55}">No accepted complete trajectory</text>')
                continue
            low, high = min(values), max(values)
            margin = max((high - low) * 0.08, abs(high) * 0.01, 0.01)
            low, high = low - margin, high + margin
            for tick in range(5):
                time = tick * 60
                px = x + width * tick / 4
                py = y + graph_height * tick / 4
                value = high - (high - low) * tick / 4
                output += [
                    f'<line class="grid" x1="{x}" x2="{x + width}" y1="{py}" y2="{py}"/>',
                    f'<text text-anchor="end" x="{x - 7}" y="{py + 4}">{value:.4g}</text>',
                    f'<text text-anchor="middle" x="{px}" '
                    f'y="{y + graph_height + 21}">{time}</text>',
                ]
            output += [
                f'<path class="axis" fill="none" d="M{x},{y}V{y + graph_height}H{x + width}"/>',
                f'<text text-anchor="middle" x="{x + width / 2}" '
                f'y="{y + graph_height + 43}">Elapsed time (min)</text>',
            ]
            for _, curves, mode, color in tracks:
                points = " ".join(
                    f"{x + time / 240 * width:.3f},"
                    f"{y + (high - value) / (high - low) * graph_height:.3f}"
                    for time, value in zip(
                        curves[name][mode]["times"], curves[name][mode][signal], strict=True
                    )
                )
                output.append(f'<polyline class="curve" stroke="{color}" points="{points}"/>')
    output.append("</svg>\n")
    return "\n".join(output)


def artifacts(report):
    return {
        "report.json": json.dumps(report, indent=2, sort_keys=True, allow_nan=False).encode()
        + b"\n",
        "report.md": markdown(report).encode(),
        "figure.svg": figure(report).encode(),
    }


def write_reports(directory, report):
    """Internal initial render; never repair or overwrite an existing saved report."""
    directory = Path(directory)
    require(
        not any((directory / name).exists() for name in ARTIFACTS - {"manifest.json"}),
        "Reports already exist; refuse overwrite",
    )
    for name, raw in artifacts(report).items():
        with (directory / name).open("xb") as handle:
            handle.write(raw)


def reconstruct(archive, write_to=None, allow_failed=False):
    directory = Path(archive).absolute()
    require(
        directory.is_dir() and not directory.is_symlink(), "Archive must be a regular directory"
    )
    directory = directory.resolve()
    files = inventory(directory)
    manifest = read(directory / "manifest.json")
    require(
        manifest.get("schema") == VERSION
        and manifest.get("files") == {name: digest(raw) for name, raw in files.items()},
        "Archive inventory differs from manifest",
    )
    plan = validate_frozen(directory, files)
    state = read(directory / "state.json")
    validate_state(directory, state, plan)
    require(
        allow_failed or state["status"] == "completed",
        "Failed/interrupted reconstruction requires explicit allow_failed",
    )
    report = assessment(directory, plan, state)
    require(allow_failed or report["passed"], "Complete numerical acceptance required")
    outputs = artifacts(report)
    present = {name for name in outputs if (directory / name).exists()}
    require(not present or present == set(outputs), "Incomplete saved derived reports")
    for name in present:
        require(
            not (directory / name).is_symlink()
            and (directory / name).read_bytes() == outputs[name],
            f"Saved {name} differs from authoritative reconstruction",
        )
    require(inventory(directory) == files, "Archive changed during reconstruction")
    if write_to is not None:
        output = Path(write_to).absolute()
        require(not output.is_symlink(), "Output cannot be a symlink")
        output = output.resolve()
        require(
            output != directory
            and output not in directory.parents
            and directory not in output.parents,
            "Reconstruction output overlaps archive",
        )
        output.mkdir(parents=True, exist_ok=False)
        require(inventory(directory) == files, "Archive changed before reconstruction write")
        write_reports(output, report)
    return report
