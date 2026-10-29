"""Recompute declared metadata inventories, without optional runtimes or callbacks."""

import importlib

from experiments.historical_readers import core as historical
from experiments.m3.comparison import common as m3_comparison
from experiments.m3.researcher import common as m3
from experiments.m4.causal_secretion import common as causal
from experiments.m4.comparison import common as m4_comparison
from experiments.m4.feedback import common as feedback
from experiments.m4.initial_load import common as m4_study
from experiments.m4.researcher_workflow import common as m4
from experiments.m4.secure_study import common as m4_secure
from experiments.m5.researcher_workflow import contract as m5
from experiments.mmtt_sampling import plan as sampling
from experiments.observation_analysis import plan as mmtt
from experiments.setup import core as setup
from experiments.workflows.registry import TASKS

from .selected import ROOT, hashes

PROVIDERS = {
    "p1-controller": "experiments.p1_external.__main__.source_code_hashes",
    "m3-forecast": "experiments.m3.researcher.common.provenance.sources",
    "m3-compare": "experiments.m3.comparison.common.provenance.sources",
    "m4-secretion": "experiments.m4.researcher_workflow.common.SOURCES+REUSED",
    "m4-compare": "experiments.m4.comparison.common.SOURCES",
    "m4-study": "experiments.m4.initial_load.common.source_paths",
    "m4-study-secure": "experiments.m4.secure_study.common.source_paths",
    "m5-prognosis": "experiments.m5.researcher_workflow.contract.SOURCES",
    "mmtt-sensitivity": "experiments.observation_analysis.plan.source_identity",
    "mmtt-sampling": "experiments.mmtt_sampling.plan.source_identity",
}

FAMILIES = {
    "p1-controller": "sampled-stateful-control/1-provisional",
    "m3-forecast": "frozen-causal-forecast/1-provisional",
    "m3-compare": "frozen-causal-forecast/1-provisional",
    "m4-secretion": "causal-continuous-source/1-provisional",
    "m4-compare": "causal-continuous-source/1-provisional",
    "m4-study": "causal-continuous-source/1-provisional",
    "m4-study-secure": "causal-continuous-source/1-provisional",
    "m5-prognosis": "frozen-landmark-prognosis/1-provisional",
    "mmtt-sensitivity": "offline-paired-observation-analysis/1-provisional",
    "mmtt-sampling": "offline-sampling-comparison/1-provisional",
}

READER_POLICIES = {
    "p1-controller": (
        "Current LOCAL_SOURCES bytes; supplied controller opaque; verify-actions "
        "is separate execution."
    ),
    "m3-forecast": "Current provenance.sources; supplied predictor/settings opaque.",
    "m3-compare": (
        "Current child and comparison provenance.sources; supplied predictor/settings opaque."
    ),
    "m4-secretion": (
        "Own manifest/protocol plus nested readers; no general own-current-code equality gate."
    ),
    "m4-compare": "Archived sources equal frozen provenance and current source bytes.",
    "m4-study": (
        "Current source path set; archived bytes equal frozen hashes; frozen "
        "protocol/lock identities."
    ),
    "m4-study-secure": (
        "Current source path set; archived bytes equal frozen hashes; maintained "
        "protocols/locks and completed-stage runtime attestations."
    ),
    "m5-prognosis": (
        "Five archived implementation aliases equal current bytes; supplied "
        "model/state opaque; verify original report in place."
    ),
    "mmtt-sensitivity": (
        "Current implementation, protocol and ancestry; opaque snapshots; exact "
        "runtime checked for execution only."
    ),
    "mmtt-sampling": (
        "Current sampling/shared implementation, ancestry, both protocols and "
        "development seal; nested MMTT reader."
    ),
}


def inventory():
    p1 = importlib.import_module("experiments.p1_external.__main__")
    direct = {
        "p1-controller": p1.source_code_hashes(),
        "m3-forecast": m3.provenance()["sources"],
        "m3-compare": m3_comparison.provenance()["sources"],
        "m4-secretion": hashes(
            [f"experiments/m4/researcher_workflow/{name}" for name in m4.SOURCES] + list(m4.REUSED)
        ),
        "m4-compare": hashes(m4_comparison.SOURCES),
        "m4-study": hashes(m4_study.source_paths()),
        "m4-study-secure": hashes(m4_secure.source_paths()),
        "m5-prognosis": hashes(path.relative_to(ROOT).as_posix() for path in m5.SOURCES.values()),
        "mmtt-sensitivity": mmtt.source_identity(),
        "mmtt-sampling": sampling.source_identity(),
    }
    nested_m4 = {
        *(f"experiments/m4/causal_secretion/{name}" for name in causal.SOURCES),
        *causal.REUSED,
        *(f"experiments/m4/feedback/{name}" for name in feedback.SOURCES),
        *feedback.REUSED,
        "experiments/m4/researcher_workflow/protocol.json",
        "experiments/m4/feedback_observation/protocol.json",
        "experiments/m4/causal_secretion/protocol.json",
        "experiments/m4/feedback/protocol.json",
        "experiments/m4/feedback/source-cases.json",
        "experiments/m4/feedback/sources.json",
    }
    additional = {
        "p1-controller": set(),
        "m4-secretion": nested_m4,
        "m5-prognosis": set(),  # Embedded protocol and generated fixture are task payloads.
        "mmtt-sensitivity": {*mmtt.ANCESTRY, mmtt.PROTOCOL.relative_to(ROOT).as_posix()},
        "mmtt-sampling": {
            *sampling.ANCESTRY_FILES,
            sampling.PROTOCOL.relative_to(ROOT).as_posix(),
            mmtt.PROTOCOL.relative_to(ROOT).as_posix(),
        },
    }
    routes = {}
    for task, entry in TASKS.items():
        projects = setup.requirements(task)
        routes[task] = {
            "capability_family": FAMILIES[task],
            "input_option": entry.input_option,
            "guide": entry.guide,
            "run_module": entry.run_module,
            "reader_module": entry.reconstruct_module,
            "reader_fresh_output": entry.reconstruction_output,
            "source_provider": PROVIDERS[task],
            "declared_sources_sha256": dict(sorted(direct[task].items())),
            "additional_static_dependencies_sha256": hashes(
                additional.get(task, set()) - direct[task].keys()
            ),
            "execution_projects": projects,
            "runtime_files_sha256": {project: setup.selectors(project) for project in projects},
            "reader_projects": setup.requirements(task, reconstruction=True),
            "historical_helper_supported": task in historical.TASKS,
            "reader_policy": READER_POLICIES[task],
        }
    return {
        "schema": "opent1d.route-inventory/1",
        "scope": (
            "Declared inventories, not universal import/runtime closure; supplied "
            "assets and installed native provenance are frozen by each task."
        ),
        "routes": routes,
        "administration_sources_sha256": hashes(
            set(setup.SOURCES)
            | set(historical.SOURCES)
            | {
                path.relative_to(ROOT).as_posix()
                for path in (ROOT / "experiments/workflows").glob("*.py")
            }
        ),
        "m5_archive_aliases": {
            name: path.relative_to(ROOT).as_posix() for name, path in m5.SOURCES.items()
        },
    }
