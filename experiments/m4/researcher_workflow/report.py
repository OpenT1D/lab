"""Reconstruct readable M4 reports without a simulator or supplied model imports."""

import argparse
import html
from pathlib import Path

from experiments.m4.causal_secretion.common import declaration
from experiments.m4.causal_secretion.report import reconstruct as causal_report
from experiments.m4.paired_kinetics.common import verify_files

from .common import (
    REUSED,
    SOURCES,
    VERSION,
    dump_reports,
    observer_settings,
    read,
    sha256,
    validate_config,
    validate_protocol,
)
from .observation import assess, case_ids, numerical_files, parent_records, validate_worker


def required():
    return {
        "config.json",
        "protocol.json",
        "observation-protocol.json",
        "model.py",
        "model.json",
        "observer-uv.lock",
        "observer-pyproject.toml",
        "reference.log",
        "reference/manifest.json",
        "causal/manifest.json",
        "observation-primary.log",
        "observation-repeat.log",
        *(f"source-{name}" for name in SOURCES),
        *("source-" + name.replace("/", "__") for name in REUSED),
        *(
            f"observations/{label}/{name}"
            for label in ("primary", "repeat")
            for name in numerical_files()
        ),
    }


def failure_read(path):
    """Retain a truncated artifact as invalid evidence, without hiding the failure."""
    try:
        value = read(path)
        if not isinstance(value, dict):
            raise ValueError("Evidence JSON must contain an object")
        return value
    except (OSError, ValueError) as exc:
        return {
            "status": "invalid",
            "error": {"type": type(exc).__name__, "message": str(exc)[:500]},
        }


def accounting(directory):
    result = {}
    for label in ("primary", "repeat"):
        rows = {}
        for case_id in case_ids():
            path = directory / "observations" / label / "cases" / (case_id + ".json")
            rows[case_id] = (
                failure_read(path).get("status", "invalid") if path.is_file() else "not_attempted"
            )
        result[label] = rows
    return result


def failure_report(directory, manifest):
    declared = (
        failure_read(directory / "model.json") if (directory / "model.json").is_file() else {}
    )
    return {
        "schema": VERSION,
        "protocol": "M4-RESEARCHER/1",
        "status": "failed",
        "passed": False,
        "stage": manifest.get("stage"),
        "recorded_verification_checks": manifest.get("verification_checks", {}),
        "error": manifest.get("error"),
        "model_id": declared.get("model_id", "unavailable"),
        "expected_observation_cases_per_process": 6,
        "accepted_observation_cases": 0,
        "case_accounting": accounting(directory),
        "missing_evidence": sorted(required() - manifest["files"].keys()),
        "scenarios": {},
        "trajectories": {},
        "limitations": ["Incomplete workflow; no complete-workflow contrasts accepted"],
    }


def reconstruct(directory, *, allow_pending=False, allow_failed=False):
    directory = Path(directory)
    if directory.is_symlink():
        raise ValueError("Workflow archive cannot be a symlink")
    manifest = read(directory / "manifest.json")
    statuses = (
        {"completed"}
        | ({"calculated"} if allow_pending else set())
        | ({"failed"} if allow_failed else set())
    )
    if manifest.get("schema") != VERSION or manifest.get("status") not in statuses:
        raise ValueError("Workflow archive is incomplete or unsupported")
    failed = manifest["status"] == "failed"
    need = (
        set()
        if failed
        else required() | (set() if allow_pending else {"report.json", "report.md", "figure.svg"})
    )
    verify_files(directory, manifest, need)
    if (directory / "protocol.json").is_file():
        validate_protocol(read(directory / "protocol.json"))
    if failed:
        return failure_report(directory, manifest)
    p = validate_protocol(read(directory / "protocol.json"))
    validate_config(read(directory / "config.json"))
    op = observer_settings(directory)
    declared = declaration(read(directory / "model.json"))
    if (
        sha256(directory / "model.py") != declared["source_sha256"]
        or read(directory / "causal/model.json") != declared
        or sha256(directory / "causal/model.py") != declared["source_sha256"]
        or manifest.get("protocol") != p["id"]
    ):
        raise ValueError("Changed supplied source, declaration or workflow identity")
    parent = causal_report(directory / "causal")
    if not parent["passed"]:
        raise ValueError("Failed causal parent cannot support workflow results")
    if (
        sha256(directory / "causal/manifest.json") != manifest.get("causal_manifest_sha256")
        or sha256(directory / "reference/manifest.json")
        != manifest.get("reference_manifest_sha256")
        or sha256(directory / "causal/reference/manifest.json")
        != manifest.get("reference_manifest_sha256")
    ):
        raise ValueError("Changed parent or copied-reference identity")
    # Verify the original reference independently as well as its causal copy.
    from experiments.m4.causal_secretion.common import reference

    _, native, _, _ = reference(directory / "reference")
    expected_numerics = {
        f"observations/{label}/{name}"
        for label in ("primary", "repeat")
        for name in numerical_files()
    }
    actual_numerics = {name for name in manifest["files"] if name.startswith("observations/")}
    if actual_numerics != expected_numerics:
        raise ValueError("Observation matrix has missing or unexpected files")
    workers = {}
    for label in ("primary", "repeat"):
        worker = read(directory / "observations" / label / "worker.json")
        validate_worker(op, worker, label)
        workers[label] = {k: v for k, v in worker.items() if k != "label"}
    changed = []
    for case_id in case_ids():
        name = f"cases/{case_id}.json"
        if sha256(directory / "observations/primary" / name) != sha256(
            directory / "observations/repeat" / name
        ):
            changed.append(name)
    if workers["primary"] != workers["repeat"]:
        changed.append("worker.json (excluding process label)")
    metrics = {k: 0.0 for k in op["criteria"] if k != "sampling_ratio_floor_pmol_l"}
    observation_cases, trajectories = {}, {}
    for case_id in case_ids():
        item = read(directory / "observations/primary/cases" / (case_id + ".json"))
        if item.get("id") != case_id:
            raise ValueError("Mislabeled observation case")
        source, tight = parent_records(directory, case_id)
        assessment = assess(op, item, source, tight)
        observation_cases[case_id] = assessment
        for key, value in assessment["checks"].items():
            metrics[key] = max(metrics[key], value)
        volume = item["boundary"]["parameters"]["volume_l_kg"]
        trajectories[case_id] = {
            "times_min": source["times"],
            "glucose_mg_dl": [row[3] / native["parameters"]["Vg"] for row in source["states"]],
            "insulin_pmol_l": [row[5] / native["parameters"]["Vi"] for row in source["states"]],
            "cpeptide_pmol_l": [row[0] / volume for row in item["states"]["reference"]],
        }
    metrics["repeat_artifact_differences"] = len(changed)
    checks = {
        k: {"value": v, "limit": op["criteria"][k], "passed": v <= op["criteria"][k]}
        for k, v in metrics.items()
    }
    scenarios = {}
    for scenario in p["scenarios"]:
        candidate = trajectories[f"{scenario}--candidate"]
        contrasts = {}
        for mode in ("host_constant_basal", "bc008_reference"):
            control = trajectories[f"{scenario}--{mode}"]
            contrasts[mode] = {
                key: max(abs(a - b) for a, b in zip(candidate[key], control[key], strict=True))
                for key in ("glucose_mg_dl", "insulin_pmol_l", "cpeptide_pmol_l")
            }
        scenarios[scenario] = {
            "glucose_insulin": parent["scenarios"][scenario],
            "cpeptide": {mode: observation_cases[f"{scenario}--{mode}"] for mode in p["modes"]},
            "maximum_absolute_candidate_contrast": contrasts,
        }
    passed = all(c["passed"] for c in checks.values())
    report = {
        "schema": VERSION,
        "protocol": p["id"],
        "status": "completed" if passed else "verification_failed",
        "passed": passed,
        "claim": p["claim"],
        "model_id": declared["model_id"],
        "model_source_sha256": declared["source_sha256"],
        "ancestry": declared["ancestry"],
        "rights_basis": declared["rights_basis"],
        "reference_manifest_sha256": manifest["reference_manifest_sha256"],
        "causal_manifest_sha256": manifest["causal_manifest_sha256"],
        "expected_observation_cases_per_process": 6,
        "accepted_observation_cases": 6 if passed else 0,
        "case_accounting": accounting(directory),
        "causal_checks": parent["metrics"],
        "observation_checks": checks,
        "repeat_changed": changed,
        "scenarios": scenarios,
        "trajectories": trajectories,
        "limitations": p["excluded"],
    }
    if not allow_pending:
        if read(directory / "report.json") != report:
            raise ValueError("Saved workflow report differs from reconstruction")
        if (directory / "report.md").read_text() != markdown(report) or (
            directory / "figure.svg"
        ).read_text() != figure(report):
            raise ValueError("Readable report or figure differs from reconstruction")
    return report


def text(value):
    return str(value).replace("\n", " ").replace("\r", " ").replace("|", "\\|").replace("`", "'")


def markdown(report):
    lines = [
        "# M4 synthetic researcher workflow",
        "",
        f"Model: **{text(report['model_id'])}**. Protocol: {report['protocol']}.",
        "",
        f"Verification: **{report['status']}**. Accepted observation cases: "
        f"{report['accepted_observation_cases']}/6.",
        "",
        "These invented scenarios describe software and model composition. They do not establish "
        "human accuracy, treatment benefit or an insulin requirement.",
        "",
    ]
    if not report["passed"]:
        lines += [
            f"Failed stage: {text(report.get('stage', 'verification'))}.",
            "",
            f"Error: {text(report.get('error'))}.",
            "",
        ]
    else:
        lines += [
            "![Synthetic glucose, insulin and C-peptide trajectories](figure.svg)",
            "",
            f"Source SHA-256: `{report['model_source_sha256']}`.",
            "",
            f"Ancestry: {text(report['ancestry'])}",
            "",
            "## Outcomes",
            "",
            "| Scenario | Source | Glucose peak (mg/dL) | Insulin peak (pmol/L) | "
            "C-peptide peak (pmol/L) | Final C-peptide (pmol/L) |",
            "| --- | --- | ---: | ---: | ---: | ---: |",
        ]
        for case_id, values in report["trajectories"].items():
            scenario, mode = case_id.split("--", 1)
            lines.append(
                f"| {scenario} | {mode} | {max(values['glucose_mg_dl']):.6g} | "
                f"{max(values['insulin_pmol_l']):.6g} | {max(values['cpeptide_pmol_l']):.6g} | "
                f"{values['cpeptide_pmol_l'][-1]:.6g} |"
            )
        lines += [
            "",
            "The host constant-basal control and BC-008 secretion reference use the same fixed SC "
            "schedule and initial state. The C-peptide observer reads total pancreatic appearance "
            "once; it adds no basal, portal delay or hepatic extraction.",
            "",
            "## Numerical verification",
            "",
            "The unchanged native parent criteria passed. C-peptide checks below apply to all six "
            "cases and their independent-process repeat.",
            "",
            "| Check | Maximum discrepancy | Limit | Passed |",
            "| --- | ---: | ---: | --- |",
        ]
        for key, check in report["observation_checks"].items():
            lines.append(
                f"| {key} | {check['value']:.6g} | {check['limit']:.6g} | {check['passed']} |"
            )
    if report.get("recorded_verification_checks"):
        lines += [
            "",
            "## Recorded failed numerical verification",
            "",
            "| Check | Discrepancy | Limit | Passed |",
            "| --- | ---: | ---: | --- |",
        ]
        for key, check in report["recorded_verification_checks"].items():
            lines.append(
                f"| {key} | {check['value']:.6g} | {check['limit']:.6g} | {check['passed']} |"
            )
    lines += [
        "",
        "## Complete case accounting",
        "",
        "| Observation case | Primary | Repeat |",
        "| --- | --- | --- |",
    ]
    for case_id in case_ids():
        lines.append(
            f"| {case_id} | {report['case_accounting']['primary'][case_id]} | "
            f"{report['case_accounting']['repeat'][case_id]} |"
        )
    lines += [
        "",
        "## Evidence limits",
        "",
        "All concentrations and contrasts are conditional on the frozen synthetic initialization, "
        "kinetics and component adaptations. Source coarsening checks use the archived 0.25-minute "
        "interpolant; they do not prove continuous-source accuracy below that grid.",
        "",
    ]
    lines += [f"- {text(item)}" for item in report["limitations"]]
    return "\n".join(lines) + "\n"


def figure(report):
    """Deterministic, dependency-free diagnostic curves from verified saved values."""
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1040" height="850" '
        'viewBox="0 0 1040 850" role="img" aria-labelledby="title desc">',
        '<title id="title">Synthetic M4 glucose, insulin and C-peptide trajectories</title>',
        '<desc id="desc">Two synthetic scenarios. Candidate, constant-basal control and BC-008 '
        "reference, with elapsed time in minutes. No human observations.</desc>",
        '<rect width="1040" height="850" fill="white"/>',
        '<g font-family="sans-serif" font-size="13" fill="#17212b">',
        '<text x="30" y="28" font-size="18">M4 synthetic model composition</text>',
    ]
    if not report["trajectories"]:
        parts += [
            '<text x="30" y="70">Incomplete workflow: no accepted trajectories.</text>',
            "</g></svg>",
        ]
        return "\n".join(parts) + "\n"
    colors = {
        "candidate": "#155eac",
        "host_constant_basal": "#aa4f00",
        "bc008_reference": "#267146",
    }
    for index, (mode, color) in enumerate(colors.items()):
        x = 30 + index * 315
        parts.append(
            f'<line x1="{x}" y1="50" x2="{x + 28}" y2="50" stroke="{color}" stroke-width="2"/>'
            f'<text x="{x + 36}" y="55">{mode}</text>'
        )
    panels = (
        ("glucose_mg_dl", "Glucose (mg/dL)"),
        ("insulin_pmol_l", "Insulin (pmol/L)"),
        ("cpeptide_pmol_l", "C-peptide (pmol/L)"),
    )
    for column, scenario in enumerate(("fasting", "gastric_load_30g")):
        for row, (key, title) in enumerate(panels):
            x, y, width, height = 80 + column * 510, 110 + row * 235, 410, 160
            values = [
                v for mode in colors for v in report["trajectories"][f"{scenario}--{mode}"][key]
            ]
            lo, hi = min(values), max(values)
            span = max(hi - lo, abs(hi) * 0.05, 1.0)
            lo, hi = lo - span * 0.08, hi + span * 0.08
            parts.append(
                f'<text x="{x}" y="{y - 18}">{html.escape(scenario)} — {html.escape(title)}</text>'
            )
            parts.append(
                f'<rect x="{x}" y="{y}" width="{width}" height="{height}" '
                'fill="none" stroke="#8795a2"/>'
            )
            for tick in range(5):
                xx = x + width * tick / 4
                value = lo + (hi - lo) * tick / 4
                yy = y + height - height * tick / 4
                parts.append(
                    f'<line x1="{x}" y1="{yy:.3f}" x2="{x + width}" y2="{yy:.3f}" '
                    f'stroke="#e5e9ed"/><text x="{x - 8}" y="{yy + 4:.3f}" '
                    f'text-anchor="end">{value:.4g}</text><text x="{xx:.3f}" '
                    f'y="{y + height + 18}" text-anchor="middle">{tick * 60}</text>'
                )
            for mode, color in colors.items():
                series = report["trajectories"][f"{scenario}--{mode}"]
                points = " ".join(
                    f"{x + t / 240 * width:.3f},{y + height - (v - lo) / (hi - lo) * height:.3f}"
                    for t, v in zip(series["times_min"], series[key], strict=True)
                )
                dashed = ' stroke-dasharray="6 3"' if mode == "bc008_reference" else ""
                parts.append(
                    f'<polyline points="{points}" fill="none" stroke="{color}" '
                    f'stroke-width="1.7"{dashed}/>'
                )
            parts.append(
                f'<text x="{x + width / 2}" y="{y + height + 38}" '
                'text-anchor="middle">Elapsed time (min)</text>'
            )
    parts += [
        '<text x="30" y="830">Invented scenarios; frozen component assumptions; no human '
        "predictive or treatment evidence.</text>",
        "</g></svg>",
    ]
    return "\n".join(parts) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--allow-failed", action="store_true")
    args = parser.parse_args()
    report = reconstruct(args.directory, allow_failed=args.allow_failed)
    args.output.mkdir(parents=True, exist_ok=False)
    dump_reports(args.output, report)
    if not report["passed"] and not args.allow_failed:
        raise SystemExit("Workflow numerical checks failed")


if __name__ == "__main__":
    main()
