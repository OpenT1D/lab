"""Reconstruct a frozen multiple-source M4 report without numerical or supplied code."""

import html
import json
import re
from pathlib import Path

from experiments.m1.artifacts import strict_json
from experiments.m1.validation import Snapshot
from experiments.m4.causal_secretion import common as causal
from experiments.m4.researcher_workflow import common as native_common
from experiments.m4.researcher_workflow.report import reconstruct as reconstruct_child

from . import common
from .analysis import MODES, SCENARIOS, SIGNALS, TIMES, summarize

SHA = re.compile(r"[0-9a-f]{64}\Z")
ATTEMPT_KEYS = {"status", "error_type", "exit_code", "manifest_sha256"}
REPORTS = ("report.json", "report.md", "figure.svg")


def same(left, right):
    return common.encoded(left) == common.encoded(right)


def _attempt(value):
    common.require(
        isinstance(value, dict) and set(value) == ATTEMPT_KEYS and value["status"] in common.STATES,
        "Invalid coordinator attempt",
    )
    common.require(
        value["error_type"] is None or isinstance(value["error_type"], str),
        "Invalid recorded attempt error",
    )
    common.require(
        value["exit_code"] is None or type(value["exit_code"]) is int,
        "Invalid recorded attempt exit code",
    )
    identity = value["manifest_sha256"]
    common.require(
        identity is None or isinstance(identity, str) and SHA.fullmatch(identity),
        "Invalid attempt manifest hash",
    )
    if value["status"] in {"not_attempted", "started"}:
        common.require(
            value["error_type"] is None and value["exit_code"] is None,
            "Unfinished attempt has terminal evidence",
        )
        if value["status"] == "not_attempted":
            common.require(identity is None, "Unattempted source has a manifest identity")
    elif value["status"] == "completed":
        common.require(
            value["exit_code"] == 0 and value["error_type"] is None and identity is not None,
            "Completed attempt lacks successful terminal evidence",
        )
    else:
        common.require(bool(value["error_type"]), "Failed or interrupted attempt lacks its error")


def _plan(files):
    common.require(
        {"config.json", "plan.json", "state.json"}.issubset(files), "Missing frozen comparison plan"
    )
    plan, state = (strict_json(files[name]) for name in ("plan.json", "state.json"))
    common.require(
        isinstance(plan, dict)
        and set(plan) == {"schema", "protocol", "config", "config_sha256", "sources", "provenance"}
        and plan["schema"] == common.VERSION,
        "Invalid frozen comparison plan",
    )
    common.validate_protocol(plan["protocol"])
    config = common.validate_config(plan["config"])
    common.require(
        common.digest(files["config.json"]) == plan["config_sha256"]
        and same(strict_json(files["config.json"]), config),
        "Original configuration differs from frozen plan",
    )
    order = [item["id"] for item in config["sources"]]
    common.require(
        isinstance(plan["sources"], dict) and set(plan["sources"]) == set(order),
        "Frozen source roster differs",
    )
    for identity in order:
        item = plan["sources"][identity]
        common.require(
            isinstance(item, dict)
            and set(item)
            == {"declaration", "source_sha256", "declaration_sha256", "effective_config"},
            "Invalid frozen source identity",
        )
        prefix = "frozen/" + identity + "/"
        common.require(
            all(prefix + name in files for name in ("model.py", "model.json", "config.json")),
            "Frozen source files missing",
        )
        declared = causal.declaration(strict_json(files[prefix + "model.json"]))
        expected = {
            "schema": "m4-researcher-config/1",
            "model": "model.py",
            "declaration": "model.json",
            "timeout_seconds": config["timeout_seconds"],
        }
        common.require(
            common.digest(files[prefix + "model.py"])
            == item["source_sha256"]
            == declared["source_sha256"]
            and common.digest(files[prefix + "model.json"]) == item["declaration_sha256"]
            and same(declared, item["declaration"])
            and same(item["effective_config"], expected)
            and same(strict_json(files[prefix + "config.json"]), expected),
            "Frozen source, parameters, declaration or worker budget differs",
        )
    provenance = plan["provenance"]
    common.require(
        isinstance(provenance, dict)
        and set(provenance) == {"git_head", "git_dirty", "python", "platform", "sources"}
        and isinstance(provenance["git_head"], str)
        and re.fullmatch(r"[0-9a-f]{40}", provenance["git_head"])
        and type(provenance["git_dirty"]) is bool
        and all(isinstance(provenance[k], str) and provenance[k] for k in ("python", "platform"))
        and isinstance(provenance["sources"], dict)
        and set(provenance["sources"]) == set(common.SOURCES),
        "Comparison implementation or protocol provenance differs",
    )
    for name, expected in provenance["sources"].items():
        raw = files.get("sources/" + name)
        common.require(
            isinstance(expected, str)
            and SHA.fullmatch(expected)
            and raw is not None
            and common.digest(raw) == expected == common.sha256(common.ROOT / name),
            "Comparison source/protocol/runtime snapshot differs: " + name,
        )
    common.require(
        isinstance(state, dict)
        and set(state) == {"status", "interruption_signal", "reference", "sources"}
        and state["status"] in {"started", "completed", "failed", "interrupted"}
        and isinstance(state["sources"], dict)
        and set(state["sources"]) == set(order),
        "Invalid coordinator state or source roster",
    )
    signal = state["interruption_signal"]
    common.require(
        signal is None or type(signal) is int and signal > 0, "Invalid interruption signal"
    )
    common.require(
        (state["status"] == "interrupted") == (signal is not None),
        "Coordinator interruption evidence disagrees",
    )
    _attempt(state["reference"])
    for identity in order:
        _attempt(state["sources"][identity])
    attempts = [state["reference"], *(state["sources"][identity] for identity in order)]
    common.require(
        state["status"] != "completed" or all(item["status"] == "completed" for item in attempts),
        "Completed coordinator has incomplete attempts",
    )
    common.require(
        not any(item["status"] == "interrupted" for item in attempts)
        or state["status"] == "interrupted",
        "Interrupted attempt without global interruption",
    )
    common.require(
        state["reference"]["status"] in {"completed", "failed"}
        or all(item["status"] == "not_attempted" for item in state["sources"].values()),
        "Sources ran without a completed common reference",
    )
    unfinished = False
    for identity in order:
        status = state["sources"][identity]["status"]
        common.require(
            not unfinished or status == "not_attempted",
            "Source order contradicts interruption/unattempted history",
        )
        unfinished |= status in {"started", "interrupted", "not_attempted"}
    if state["status"] != "started":
        common.require(
            all(item["status"] != "started" for item in attempts),
            "Final coordinator retains an active attempt",
        )
    return plan, state


def _sealed(directory, files, prefix, attempt, global_status):
    """Check native manifest coverage independently of its unchanged reader."""
    subset = {name[len(prefix) :]: raw for name, raw in files.items() if name.startswith(prefix)}
    if attempt["status"] == "not_attempted":
        common.require(not subset, "Unattempted source contains child artifacts")
        return None
    raw = subset.get("manifest.json")
    identity = None if raw is None else common.digest(raw)
    common.require(
        identity == attempt["manifest_sha256"]
        or global_status == "started"
        and attempt["status"] == "started"
        and attempt["manifest_sha256"] is None,
        "Recorded native manifest identity differs",
    )
    if raw is None:
        common.require(attempt["status"] != "completed", "Completed attempt has no native archive")
        return None
    try:
        manifest = strict_json(raw)
    except ValueError:
        common.require(
            attempt["status"] != "completed", "Completed attempt has a truncated native manifest"
        )
        return None
    if not isinstance(manifest, dict):
        common.require(
            attempt["status"] != "completed", "Completed attempt has an invalid native manifest"
        )
        return None
    if manifest.get("status") in {"completed", "failed"}:
        common.require(
            manifest.get("files")
            == {
                name: common.digest(value)
                for name, value in subset.items()
                if name != "manifest.json"
            },
            "Native manifest inventory differs from complete saved child bytes",
        )
    elif attempt["status"] == "completed":
        raise ValueError("Completed attempt contains an unsealed native archive")
    return manifest


def _bindings():
    result = {
        "protocol.json": "experiments/m4/researcher_workflow/protocol.json",
        "observation-protocol.json": "experiments/m4/feedback_observation/protocol.json",
        "observer-uv.lock": "experiments/m4/beta_cell/runtime/uv.lock",
        "observer-pyproject.toml": "experiments/m4/beta_cell/runtime/pyproject.toml",
    }
    for prefix, package in (("", native_common), ("causal/", causal)):
        for name in package.SOURCES:
            result[prefix + "source-" + name] = (
                package.HERE.relative_to(common.ROOT).as_posix() + "/" + name
            )
        for name in package.REUSED:
            result[prefix + "source-" + name.replace("/", "__")] = name
    result["causal/protocol.json"] = "experiments/m4/causal_secretion/protocol.json"
    for name in ("uv.lock", "pyproject.toml"):
        result["causal/" + name] = "experiments/m0/simglucose/" + name
    return result


def reconstruct(directory, write_to=None, allow_failed=False):
    directory = Path(directory).absolute()
    snapshot = Snapshot(directory)
    manifest_raw = snapshot.read("manifest.json")
    manifest = strict_json(manifest_raw)
    common.require(
        isinstance(manifest, dict)
        and set(manifest) == {"schema", "files"}
        and manifest["schema"] == common.VERSION
        and isinstance(manifest["files"], dict)
        and all(
            isinstance(value, str) and SHA.fullmatch(value) for value in manifest["files"].values()
        ),
        "Invalid comparison manifest",
    )
    files = common.inventory(directory)
    common.require(
        manifest["files"] == {name: common.digest(raw) for name, raw in files.items()},
        "Comparison artifact inventory changed",
    )
    plan, state = _plan(files)
    order = [source["id"] for source in plan["config"]["sources"]]
    allowed = {"config.json", "plan.json", "state.json", "logs/reference.log"}
    allowed.update("sources/" + name for name in common.SOURCES)
    for identity in order:
        allowed.update(
            "frozen/" + identity + "/" + name for name in ("model.py", "model.json", "config.json")
        )
        allowed.add("logs/" + identity + ".log")
    common.require(
        all(
            name in allowed
            or name.startswith("reference/")
            or any(name.startswith("children/" + identity + "/") for identity in order)
            for name in files
        ),
        "Unexpected comparison artifact or source outside frozen roster",
    )
    reference_manifest = _sealed(
        directory, files, "reference/", state["reference"], state["status"]
    )
    reference_context = {
        "accepted": False,
        "attempt": state["reference"],
        "manifest_sha256": state["reference"]["manifest_sha256"],
        "checks": {},
    }
    if state["reference"]["status"] == "completed":
        common.require(
            reference_manifest is not None and reference_manifest.get("status") == "completed",
            "Common reference did not complete",
        )
        _, _, _, native_reference = common.verify_reference(directory / "reference")
        reference_context.update(accepted=True, checks=native_reference["checks"])
    children = {}
    for identity in order:
        attempt = state["sources"][identity]
        prefix = "children/" + identity + "/"
        native_manifest = _sealed(directory, files, prefix, attempt, state["status"])
        if attempt["status"] == "not_attempted":
            common.require(
                "logs/" + identity + ".log" not in files,
                "Unattempted source contains an execution log",
            )
        for name in ("model.py", "model.json", "config.json"):
            if prefix + name in files:
                common.require(
                    files[prefix + name] == files["frozen/" + identity + "/" + name],
                    "Child supplied source/configuration differs from frozen roster",
                )
        for name, original in _bindings().items():
            if prefix + name in files:
                common.require(
                    files[prefix + name] == files["sources/" + original],
                    "Child scientific protocol, runtime or source snapshot differs",
                )
        for nested in ("reference/manifest.json", "causal/reference/manifest.json"):
            if prefix + nested in files:
                common.require(
                    files[prefix + nested] == files.get("reference/manifest.json"),
                    "Child common-reference identity differs",
                )
        child = None
        if native_manifest is not None and native_manifest.get("status") in {"completed", "failed"}:
            child = reconstruct_child(directory / "children" / identity, allow_failed=True)
            if native_manifest["status"] == "completed":
                common.require(
                    child.get("passed") is True, "Completed child failed numerical reconstruction"
                )
            common.require(
                prefix + "model.json" not in files
                or child.get("model_id") == plan["sources"][identity]["declaration"]["model_id"],
                "Child model identity differs from the frozen source",
            )
        common.require(
            attempt["status"] != "completed" or child is not None and child.get("passed") is True,
            "Completed source lacks an accepted complete native workflow",
        )
        children[identity] = child
    summary = summarize(plan, state, children, reference_context)
    report = {
        "schema": common.VERSION,
        "protocol": plan["protocol"]["id"],
        "kind": "synthetic",
        "claim": plan["protocol"]["claim"],
        "provenance": plan["provenance"],
        "coordinator": state,
        "reference": reference_context,
        "conditions": {
            "scenarios": list(SCENARIOS),
            "modes": list(MODES),
            "horizon_min": 240,
            "sample_step_min": 0.25,
            "sample_count": len(TIMES),
            "units": SIGNALS,
            "fixed_conditions": plan["protocol"]["conditions"],
        },
        **summary,
        "human_evaluation": False,
        "reconstruction_scope": "saved native evidence, exact shared conditions and descriptive "
        "trajectory arithmetic; supplied sources and numerical runtimes are not executed",
        "limitations": plan["protocol"]["excluded"],
    }
    common.require(common.inventory(directory) == files, "Archive changed during reconstruction")
    snapshot.verify_unchanged()
    common.require(
        report["passed"] or allow_failed,
        "Comparison is failed or incomplete; explicit --allow-failed required",
    )
    rendered = {
        "report.json": (
            json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
        ).encode(),
        "report.md": markdown(report).encode(),
        "figure.svg": figure(report).encode(),
    }
    internal_write = write_to is not None and Path(write_to).absolute() == directory
    existing_reports = [name for name in rendered if (directory / name).exists()]
    if internal_write and existing_reports:
        common.require(len(existing_reports) == 3, "Partially rendered comparison report set")
    if not internal_write or existing_reports:
        for name, raw in rendered.items():
            path = directory / name
            if path.exists():
                common.require(
                    snapshot.read(name) == raw,
                    "Saved comparison report or figure differs from reconstruction",
                )
            else:
                common.require(
                    allow_failed and not report["passed"],
                    "Missing saved comparison report or figure",
                )
    snapshot.verify_unchanged()
    if write_to is not None:
        destination = Path(write_to).absolute()
        common.require(not destination.is_symlink(), "Report destination cannot be a symlink")
        destination = destination.resolve()
        if not internal_write:
            common.require(
                destination != directory.resolve()
                and destination not in directory.resolve().parents
                and directory.resolve() not in destination.parents,
                "Reconstruction output and archive must be separate",
            )
            common.require(not destination.exists(), "Reconstruction output already exists")
            destination.mkdir(parents=True, exist_ok=False)
        for name, raw in rendered.items():
            path = destination / name
            common.require(not path.is_symlink(), "Report output cannot be a symlink")
            path.write_bytes(raw)
    return report


def _text(value):
    return str(value).replace("\n", " ").replace("\r", " ").replace("|", "\\|").replace("`", "'")


def markdown(report):
    lines = [
        "# M4 synthetic source comparison",
        "",
        f"Protocol: **{report['protocol']}**. Verification: **{report['status']}**.",
        "",
        f"Accepted sources: {report['accepted_source_count']}/{report['planned_source_count']}; "
        f"accepted source/scenario cases: {report['accepted_source_scenario_count']}/"
        f"{report['planned_source_scenario_count']}.",
        "",
        "Invented conditions describe model composition and trajectory separation. These results "
        "do not establish human accuracy, biological superiority, insulin need "
        "or treatment benefit.",
        "",
        "![Synthetic glucose, insulin and C-peptide source comparison](figure.svg)",
        "",
        "## Frozen source roster",
        "",
        "| Source | Model | Version/source SHA-256 | Parameters | "
        "Coordinator status | Accepted | Reason |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    failure_notes = []
    for identity in report["source_order"]:
        source = report["sources"][identity]
        model = source["model"]
        lines.append(
            f"| {_text(identity)} | {_text(model['model_id'])} | `{model['source_sha256']}` | "
            f"{_text(json.dumps(model['parameters'], sort_keys=True))} | "
            f"{source['attempt']['status']} | {source['accepted']} | "
            f"{_text(source['null_reason'])} |"
        )
    for identity in report["source_order"]:
        model = report["sources"][identity]["model"]
        lines += [
            "",
            f"{_text(identity)} ancestry: {_text(model['ancestry'])}. "
            f"Rights basis: {_text(model['rights_basis'])}.",
        ]
    lines += [
        "## Planned source/scenario accounting",
        "",
        "| Source | Scenario | Coordinator status | Entire source accepted | Reason |",
        "| --- | --- | --- | --- | --- |",
    ]
    for identity in report["source_order"]:
        for scenario, item in report["sources"][identity]["scenarios"].items():
            lines.append(
                f"| {_text(identity)} | {scenario} | {item['status']} | {item['accepted']} | "
                f"{_text(item['null_reason'])} |"
            )
    controls = report["common_controls"]
    lines += [
        "",
        f"Shared control agreement: **{controls['status']}**. {_text(controls['null_reason'])}.",
        "",
        "## Direct descriptive contrasts",
        "",
        "Left minus right follows frozen roster order. AUC has the signal unit times minutes; "
        "time mean and maximum absolute pointwise separation have the signal unit. "
        "All accepted comparisons use all 961 exact times from 0 to 240 minutes.",
        "",
        "| Left | Right | Scenario | Signal/unit | Signed AUC | Signed time mean | "
        "Maximum absolute separation | Reason |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | --- |",
    ]
    for pair in report["pairs"]:
        for scenario, values in pair["scenarios"].items():
            for signal, item in values["signals"].items():
                metrics = item["metrics"]
                cells = (
                    ["null"] * 3
                    if metrics is None
                    else [
                        f"{metrics[key]:.9g}"
                        for key in (
                            "signed_auc_difference",
                            "signed_time_mean_difference",
                            "maximum_absolute_pointwise_difference",
                        )
                    ]
                )
                lines.append(
                    f"| {_text(pair['left'])} | {_text(pair['right'])} | {scenario} | "
                    f"{signal} ({item['unit']}) | {' | '.join(cells)} | "
                    f"{_text(values['null_reason'])} |"
                )
    lines += [
        "",
        "## Preserved numerical checks and failure evidence",
        "",
        "| Source | Stage/check | Value | Limit | Passed/status |",
        "| --- | --- | ---: | ---: | --- |",
    ]
    for key, check in report["reference"]["checks"].items():
        lines.append(
            f"| common reference | {_text(key)} | {check['value']:.9g} | "
            f"{check['limit']:.9g} | {check['passed']} |"
        )
    for identity in report["source_order"]:
        source = report["sources"][identity]
        child = source["single_source"]
        if child is None:
            lines.append(
                f"| {_text(identity)} | no sealed native report | — | — | "
                f"{source['attempt']['status']} |"
            )
            continue
        for key, value in child.get("causal_checks", {}).items():
            lines.append(
                f"| {_text(identity)} | causal/{_text(key)} | {value:.9g} | "
                "inherited native gate | accepted by native reader |"
            )
        for group in ("observation_checks", "recorded_verification_checks"):
            for key, check in child.get(group, {}).items():
                lines.append(
                    f"| {_text(identity)} | {group}/{_text(key)} | {check['value']:.9g} | "
                    f"{check['limit']:.9g} | {check['passed']} |"
                )
        if not child.get("passed"):
            failure_notes.append(
                f"{_text(identity)} failed stage: {_text(child.get('stage'))}; "
                f"error: {_text(child.get('error'))}."
            )
        for label, cases in child.get("case_accounting", {}).items():
            for case_id, status in cases.items():
                lines.append(
                    f"| {_text(identity)} | {label}/{_text(case_id)} | — | — | {_text(status)} |"
                )
    for note in failure_notes:
        lines += ["", note]
    lines += [
        "",
        "## Provenance and evidence limits",
        "",
        f"Recorded Git revision: `{report['provenance']['git_head']}`; "
        f"dirty checkout: {report['provenance']['git_dirty']}.",
        "",
        f"Common reference manifest: `{report['reference']['manifest_sha256']}`.",
        "",
        _text(report["reconstruction_scope"]),
        "",
    ]
    lines.extend(f"- {_text(item)}" for item in report["limitations"])
    return "\n".join(lines) + "\n"


def figure(report):
    """Deterministic standard-library SVG; only complete accepted source curves."""
    accepted = [
        identity for identity in report["source_order"] if report["sources"][identity]["accepted"]
    ]
    palette = (
        "#155eac",
        "#b12669",
        "#6941a6",
        "#b35c00",
        "#087e8b",
        "#775a26",
        "#365b91",
        "#8f423d",
    )
    curves = [
        (identity, palette[index], None)
        for index, identity in enumerate(report["source_order"])
        if identity in accepted
    ]
    matched = report["common_controls"]["status"] == "matched"
    if matched:
        curves += [("host_constant_basal", "#555555", "6 3"), ("bc008_reference", "#267146", "2 3")]
    legend_height = 26 * ((len(curves) + 2) // 3)
    top = 112 + legend_height
    height = top + 720 + 28 * len(report["source_order"])
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="{height}" '
        f'viewBox="0 0 1100 {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">Synthetic M4 source comparison</title>',
        '<desc id="desc">Glucose, plasma insulin and central C-peptide over two fixed '
        "invented scenarios. Failed sources remain listed; only entire accepted sources "
        "have curves. No human observations.</desc>",
        f'<rect width="1100" height="{height}" fill="white"/>',
        '<g font-family="sans-serif" font-size="13" fill="#17212b">',
        '<text x="30" y="28" font-size="19">M4 synthetic source comparison</text>',
        f'<text x="30" y="52">Accepted {len(accepted)}/{len(report["source_order"])} '
        f"sources; shared controls: {html.escape(report['common_controls']['status'])}</text>",
    ]
    if not matched:
        parts.append(
            '<text x="30" y="76">No verified shared-control overlay; '
            "direct contrasts require matching controls.</text>"
        )
    for index, (identity, color, dash) in enumerate(curves):
        x, y = 30 + index % 3 * 350, 96 + index // 3 * 26
        extra = f' stroke-dasharray="{dash}"' if dash else ""
        parts.append(
            f'<line x1="{x}" y1="{y}" x2="{x + 24}" y2="{y}" stroke="{color}" '
            f'stroke-width="2"{extra}/><text x="{x + 32}" y="{y + 4}">'
            f"{html.escape(identity)}</text>"
        )
    panels = (
        ("glucose_mg_dl", "Glucose (mg/dL)"),
        ("insulin_pmol_l", "Plasma insulin (pmol/L)"),
        ("cpeptide_pmol_l", "Central C-peptide (pmol/L)"),
    )
    for column, scenario in enumerate(SCENARIOS):
        for row, (signal, title) in enumerate(panels):
            x, y, width, panel_height = 90 + column * 535, top + row * 230, 420, 158
            series = {}
            for identity, _, _ in curves:
                if identity in accepted:
                    series[identity] = report["sources"][identity]["single_source"]["trajectories"][
                        f"{scenario}--candidate"
                    ][signal]
                else:
                    series[identity] = report["common_controls"]["trajectories"][
                        f"{scenario}--{identity}"
                    ][signal]
            values = [value for sequence in series.values() for value in sequence]
            lo, hi = (min(values), max(values)) if values else (0.0, 1.0)
            span = max(hi - lo, abs(hi) * 0.05, 1.0)
            lo, hi = lo - span * 0.08, hi + span * 0.08
            parts += [
                f'<text x="{x}" y="{y - 18}">{html.escape(scenario)} — {html.escape(title)}</text>',
                f'<rect x="{x}" y="{y}" width="{width}" height="{panel_height}" '
                'fill="none" stroke="#8795a2"/>',
            ]
            for tick in range(5):
                xx, yy = x + width * tick / 4, y + panel_height * (1 - tick / 4)
                value = lo + (hi - lo) * tick / 4
                parts.append(
                    f'<line x1="{x}" y1="{yy:.3f}" x2="{x + width}" y2="{yy:.3f}" '
                    f'stroke="#e5e9ed"/><text x="{x - 8}" y="{yy + 4:.3f}" '
                    f'text-anchor="end">{value:.4g}</text><text x="{xx:.3f}" '
                    f'y="{y + panel_height + 18}" text-anchor="middle">{tick * 60}</text>'
                )
            for identity, color, dash in curves:
                points = " ".join(
                    f"{x + t / 240 * width:.3f},"
                    f"{y + panel_height - (value - lo) / (hi - lo) * panel_height:.3f}"
                    for t, value in zip(TIMES, series[identity], strict=True)
                )
                extra = f' stroke-dasharray="{dash}"' if dash else ""
                parts.append(
                    f'<polyline points="{points}" fill="none" stroke="{color}" '
                    f'stroke-width="1.7"{extra}/>'
                )
            if not values:
                parts.append(
                    f'<text x="{x + 20}" y="{y + 70}">'
                    "No accepted complete source trajectory.</text>"
                )
            parts.append(
                f'<text x="{x + width / 2}" y="{y + panel_height + 38}" '
                'text-anchor="middle">Elapsed time (min)</text>'
            )
    for index, identity in enumerate(report["source_order"]):
        source = report["sources"][identity]
        label = f"{identity}: {source['attempt']['status']}; "
        label += f"entire workflow accepted={source['accepted']}"
        parts.append(f'<text x="30" y="{top + 690 + index * 28}">{html.escape(label)}</text>')
    parts += [
        f'<text x="30" y="{height - 18}">Invented conditions; descriptive separation; '
        "no model ranking or treatment evidence.</text>",
        "</g></svg>",
    ]
    return "\n".join(parts) + "\n"
