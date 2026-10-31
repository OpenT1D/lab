"""Actual-host qualification of the explicit internal M4/connected candidate.

Requires separately prepared reviewed dependency roles. Never downloads native
dependencies, executes archived callbacks or qualifies a public distribution.
Keep the entire fresh output private: native evidence includes parameter data.
"""

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
PREDECESSOR = "b96a288ce4b0a0feaae4929475c992e95e6b7624"
TASKS = ["mmtt-sensitivity", "m4-study-secure", "m4-study-installed", "mmtt-sampling"]


def read(path):
    return json.loads(path.read_bytes())


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(path):
    from scripts.integrated_candidate_probe import hashes

    return hashes(path)


def artifact_identity(label, receipt, actual):
    """An editable build receipt cannot promote the installed capabilities."""
    assert actual["source"] == receipt["source"]
    assert set(actual["source"]) == {"revision", "dirty"}
    assert actual["source"]["dirty"] is False and receipt["source"]["dirty"] is False
    assert re.fullmatch(r"[0-9a-f]{40}", actual["source"]["revision"])
    assert (
        actual["schema"]
        == receipt["descriptor_schema"]
        == ("opent1d.installed-sdk/3" if label == "predecessor" else "opent1d.installed-sdk/5")
    )
    assert actual["tasks"] == receipt["tasks"] == TASKS
    assert (
        actual["native_execution"]
        == receipt["native_execution"]
        == "explicit-reviewed-attachment/1"
    )
    assert actual["descriptor_sha256"] == receipt["descriptor_sha256"]
    assert actual["build_label"] == receipt["build_label"]
    assert receipt["native_runtimes_shipped"] is False and receipt["runtime_dependencies"] == []
    if label == "predecessor":
        assert actual["source"]["revision"] == PREDECESSOR
    else:
        assert actual["source"]["revision"] != PREDECESSOR


def parity(left, right):
    from experiments.m4.feedback.common import numerical_files
    from experiments.m4.initial_load.analysis import numeric_paths, observation_paths

    scenes = ["fasting", "gastric_load_15g"]
    names = set()
    for repeat in ("primary", "repeat"):
        names.update("reference/" + repeat + "/" + p for p in numeric_paths(scenes, True))
        for source in ("dalla_man", "ultradian"):
            names.update(
                "children/" + source + "/" + repeat + "/" + p for p in numeric_paths(scenes)
            )
            names.update(
                "children/" + source + "/observations/" + repeat + "/" + p
                for p in observation_paths(scenes)
            )
    historical = numerical_files(read(ROOT / "experiments/m4/feedback/protocol.json"))
    names.update("historical/" + prefix + p for prefix in ("", "repeat/") for p in historical)
    assert len(names) == 274
    result = {}
    for name in sorted(names):
        assert (left / name).is_file() and (right / name).is_file(), name
        assert (left / name).read_bytes() == (right / name).read_bytes(), name
        result[name] = sha(left / name)
    return result


def materials(root, result, reference, adverse):
    (root / "participant").mkdir(parents=True)
    (root / "facilitator").mkdir()
    artifact = result["artifacts"]["candidate"]
    (root / "participant/Tasks.md").write_text(
        "# Internal synthetic M4 and connected-study exercise\n\n"
        "Use invented data only. Preserve first answers and unsuccessful attempts.\n\n"
        "1. Explain the supplied M4 source/load plans, units and observation window. "
        "Freeze a source/load comparison before execution and interpret its limits.\n"
        "2. Freeze a connected study, explicitly run its forward stage, then materialize "
        "and run its inverse/sampling stage. Explain truth, observations and estimates.\n"
        "3. Compare the complete and missing-observation cases. Explain which planned "
        "rows are unavailable and how schedule selection avoids evaluation evidence.\n"
        "4. Recover the supplied failed first forward without losing its outcome.\n"
        "5. Move the whole project to the declared reader installation, reconstruct "
        "a saved prefix and explain reading versus rerunning.\n\n"
        "Record any help needed. Do not use health records or make clinical decisions.\n"
    )
    (root / "participant/Start.md").write_text(
        "# Candidate-bound local exercise\n\n"
        f"Source: `{artifact['source']['revision']}`. "
        f"Wheel SHA-256: `{artifact['wheel_sha256']}`.\n\n"
        "The facilitator supplies the installed application and a newly attached "
        "reviewed runtime for its exact interpreter. Open recovery-project for task 4.\n\n"
        f"Guide: https://github.com/OpenT1D/lab/blob/{artifact['source']['revision']}/docs/internal-integrated-candidate.md\n"
    )
    shutil.copytree(adverse / "failed-project", root / "participant/recovery-project")
    for name in ("native-report", "m4-comparison", "complete-report", "missing-report"):
        shutil.copytree(reference / name, root / "facilitator" / name)
    (root / "facilitator/Key.md").write_text(
        "# Technical reference — keep apart from participant tasks\n\n"
        "Preparation only; no intended-user session or independent recipient is recorded. "
        "Use the copied actual reports. Native interval completeness differs from point "
        "recovery. Complete/missing retain all 72 rows: respectively 72/36 complete, "
        "0/24 unavailable points. Missing values are not zero. Native whole-body source "
        "rates and C-peptide concentrations have different units. Preserve time origin, "
        "the 0–240 minute forward window and the downstream declared windows. Schedule "
        "selection uses development evidence only. Mismatch controls are model-sensitivity "
        "checks, not biological validation. A comparison precedes execution; first failures "
        "remain selected after retry. Unchanged native readers reconstruct preserved "
        "evidence without old runtimes. Changed native reader migration is unsupported. "
        "Record wrong units/windows, missing-as-zero, passing-subset reasoning, lost "
        "evidence and success-as-validity as critical errors. Keep active, compute and "
        "elapsed time separate. Leave all unobserved fields null.\n"
    )
    write(
        root / "facilitator/observations.template.json",
        {
            "human_sessions": "not_recorded",
            "participant_code": None,
            "recipient_code": None,
            "tasks": [
                {
                    "id": name,
                    "first_answer": None,
                    "active_seconds": None,
                    "compute_seconds": None,
                    "elapsed_seconds": None,
                    "assistance": [],
                    "critical_errors": [],
                    "retests": [],
                }
                for name in ("source-load", "connected", "missing", "recovery", "handoff")
            ],
        },
    )
    write(
        root / "packet.json",
        {
            "schema": "opent1d.internal-integrated-formative-packet/1",
            "evidence_kind": "preparation",
            "candidate": artifact,
            "host": result["host"],
            "human_sessions": "not_recorded",
            "files": inventory(root),
        },
    )


def orchestrate(args):
    from experiments.m4.installed_study import common, profile
    from experiments.shared_services.execution import supervise
    from scripts.build_windows_installer import source_inventory
    from scripts.prepare_m4_runtimes import PROJECTS, validate_policy

    assert platform.system() == "Darwin" and platform.machine() == "arm64"
    assert sys.version_info[:2] == (3, 12) and not sys.flags.optimize
    root = args.output.absolute()
    assert root == root.resolve() and not root.is_relative_to(ROOT), (
        "Fresh canonical directory outside checkout required"
    )
    root.mkdir()
    source = source_inventory(ROOT, allow_dirty=False)
    programs = {}
    for name in ("integrated_candidate_probe.py", "qualify_reader_candidate.py"):
        shutil.copyfile(ROOT / "scripts" / name, root / name)
        programs[name] = sha(root / name)
    environment = {k: v for k, v in os.environ.items() if k not in {"PYTHONPATH", "PYTHONOPTIMIZE"}}
    environment["UV_CACHE_DIR"] = str(root / "cache")
    review = validate_policy()
    assert sha(ROOT / "publication-rights.json") == review["rights"]["inventory_sha256"]
    runtimes = read(args.runtime_receipt)
    assert runtimes["selectors"] == review["selectors"]
    assert runtimes["review_sha256"] == sha(
        ROOT / "experiments/m4/installed_study/runtime-review.json"
    )
    roles = root / "roles"
    roles.mkdir()
    role_receipts = {}
    for role, project in PROJECTS.items():
        original = Path(runtimes["roles"][role]["site_packages"])
        before = profile.inventory(original)
        distribution = profile.distributions(original, common.package_records(project))
        shutil.copytree(original, roles / role)
        assert profile.inventory(original) == before == profile.inventory(roles / role)
        assert profile.distributions(roles / role, common.package_records(project)) == distribution
        role_receipts[role] = {
            "files": len(before),
            "bytes": sum(v["bytes"] for v in before.values()),
            **distribution,
        }
    write(root / "reviewed-roles.json", role_receipts)
    artifacts, interpreters, payloads = {}, {}, {}
    for label in ("predecessor", "candidate", "reader"):
        original_label = "candidate" if label == "reader" else label
        receipt_path = getattr(args, original_label + "_receipt")
        receipt = read(receipt_path)
        wheel = getattr(args, original_label + "_wheel").absolute()
        assert sha(wheel) == receipt["wheel_sha256"]
        destination = root / ("artifact-" + label)
        destination.mkdir()
        shutil.copyfile(wheel, destination / wheel.name)
        shutil.copyfile(receipt_path, destination / "receipt.json")
        envdir = root / ("environment-" + label)
        python = envdir / "bin/python"
        for argv in (
            ["uv", "venv", "--offline", "--python", sys.executable, str(envdir)],
            [
                "uv",
                "pip",
                "install",
                "--offline",
                "--no-deps",
                "--link-mode=copy",
                "--python",
                str(python),
                str(destination / wheel.name),
            ],
        ):
            subprocess.run(
                argv, cwd=root, env=environment, capture_output=True, check=True, timeout=120
            )
        actual = json.loads(
            subprocess.check_output(
                [str(envdir / "bin/opent1d-lab"), "installation"],
                cwd=root,
                env=environment,
                timeout=60,
            )
        )
        artifact_identity(original_label, receipt, actual)
        artifacts[label], interpreters[label] = receipt, python
        payload = envdir / "lib/python3.12/site-packages/opent1d_lab/_payload/app"
        payloads[label] = payload
    assert (
        inventory(payloads["predecessor"])
        == inventory(payloads["candidate"])
        == inventory(payloads["reader"])
    )
    assert artifacts["candidate"]["source"] == {k: source[k] for k in ("revision", "dirty")}
    phases = {}

    def run(name, argv, timeout=900):
        print("Qualification phase:", name, flush=True)
        result = supervise(
            [str(a) for a in argv],
            root / (name + ".log"),
            timeout=timeout,
            grace=30,
            environment=environment,
        )
        phases[name] = result
        write(root / "phases.json", phases)
        assert result["status"] == "completed" and result["remaining_owned_processes"] == [], name

    def probe(label, phase, output, *extra, timeout=900):
        run(
            label + "-" + phase,
            [
                interpreters[label],
                "-I",
                "-B",
                root / "integrated_candidate_probe.py",
                "--phase",
                phase,
                "--output",
                output,
                "--roles",
                roles,
                *extra,
            ],
            timeout,
        )

    predecessor, candidate, adverse = (root / n for n in ("predecessor", "candidate", "adverse"))
    probe("predecessor", "direct-prepare", predecessor)
    requested = read(predecessor / "request.json")
    run(
        "predecessor-direct",
        [
            interpreters["predecessor"],
            "-I",
            "-B",
            "-S",
            payloads["predecessor"] / "experiments/m4/installed_study/bootstrap.py",
            "--attachment",
            requested["attachment"],
            "--expected",
            sha(Path(requested["attachment"])),
            "--role",
            "coordinator",
            "--entry",
            "study",
            "run",
            "--config",
            requested["config"],
            "--output",
            predecessor / "archive",
        ],
        10800,
    )
    probe("predecessor", "direct-finish", predecessor)
    probe("candidate", "candidate", candidate, timeout=12600)
    attached = candidate / "attachment.json"
    for entry, role, location, count in (
        ("numerical-tests", "native", payloads["candidate"], 12),
        ("observer-tests", "observer", ROOT, 15),
        ("beta-cell-tests", "observer", ROOT, 23),
    ):
        run(
            entry,
            [
                interpreters["candidate"],
                "-I",
                "-B",
                "-S",
                location / "experiments/m4/installed_study/bootstrap.py",
                "--attachment",
                attached,
                "--expected",
                sha(attached),
                "--role",
                role,
                "--entry",
                entry,
            ],
        )
        log = (root / (entry + ".log")).read_text()
        assert (
            re.search(rf"Ran {count} tests? in", log)
            and "skipped=" not in log
            and re.search(r"\nOK\s*$", log)
        ), entry
    probe("candidate", "adverse", adverse)
    forward = read(candidate / "result.json")["forward"]
    matched = parity(predecessor / "archive", Path(forward["evidence"]) / "native")
    write(root / "scientific-parity.json", matched)
    for mode, output, extra in (
        ("prepare", root / "mmtt-current", []),
        ("replay", root / "mmtt-transition", ["--source", args.mmtt_predecessor.absolute()]),
    ):
        run(
            "mmtt-" + mode,
            [
                interpreters["candidate"],
                "-I",
                "-B",
                root / "qualify_reader_candidate.py",
                "--probe",
                mode,
                "--output",
                output,
                *extra,
            ],
        )
    moved = root / "relocated"
    moved.mkdir()
    for label in ("predecessor", "candidate"):
        shutil.copytree(root / label, moved / label)
    write(
        moved / "bundle.json", {label: str(moved / label) for label in ("predecessor", "candidate")}
    )
    hidden = []
    try:
        for path in (
            root / "environment-predecessor",
            root / "environment-candidate",
            predecessor,
            candidate,
            roles,
        ):
            unavailable = path.with_name(path.name + "-unavailable")
            path.rename(unavailable)
            hidden.append((path, unavailable))
            assert not path.exists()
        probe("reader", "replay", root / "replay", "--bundle", moved / "bundle.json")
    finally:
        for path, unavailable in reversed(hidden):
            unavailable.rename(path)
    probe("reader", "negative", root / "negative", "--bundle", moved / "bundle.json")
    assert source_inventory(ROOT, allow_dirty=False) == source, (
        "Source changed during qualification"
    )
    result = {
        "schema": "opent1d.internal-integrated-candidate-qualification/1",
        "host": {
            "system": platform.system(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "artifacts": artifacts,
        "program_sha256": programs,
        "roles": role_receipts,
        "phases": phases,
        "scientific_parity_files": len(matched),
        "scientific_parity_sha256": sha(root / "scientific-parity.json"),
        "whole_payload_equal": True,
        "native_reader_transition": "unchanged readers only",
        "mmtt_reader_transition": "pinned PR-43 policy",
        "human_sessions": "not_recorded",
        "public_release": False,
    }
    materials(root / "formative-packet", result, candidate, adverse)
    result["formative_packet_sha256"] = sha(root / "formative-packet/packet.json")
    write(root / "qualification.json", result)
    print(
        json.dumps(
            {
                "passed": True,
                "candidate_source": artifacts["candidate"]["source"],
                "scientific_parity_files": len(matched),
            }
        ),
        flush=True,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for label in ("candidate", "predecessor"):
        parser.add_argument("--" + label + "-wheel", required=True, type=Path)
        parser.add_argument("--" + label + "-receipt", required=True, type=Path)
    parser.add_argument("--runtime-receipt", required=True, type=Path)
    parser.add_argument("--mmtt-predecessor", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if sys.flags.optimize:
        raise ValueError("Qualification requires assertions")
    orchestrate(args)


if __name__ == "__main__":
    main()
