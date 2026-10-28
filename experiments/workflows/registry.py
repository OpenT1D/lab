"""The explicit supported task list, without candidate imports or new model APIs."""

from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERSION = "opent1d.workflow-entry/1"
NATIVE_PROJECT = "experiments/m0/simglucose"
SECURE_NATIVE_PROJECT = "experiments/m0/simglucose_secure"
OBSERVER_PROJECT = "experiments/m4/beta_cell/runtime"


@dataclass(frozen=True)
class Task:
    id: str
    title: str
    input_option: str
    guide: str
    run_module: str
    reconstruct_module: str
    run_project: str = "."
    reconstruction_output: bool = True

    def describe(self):
        return {
            "id": self.id,
            "task": self.id,
            "title": self.title,
            "input_option": self.input_option,
            "guide": str(ROOT / self.guide),
            "execution_project": self.run_project,
            "reconstruction_output": "fresh directory required"
            if self.reconstruction_output
            else "verifies existing report bytes; no output directory",
            "source_and_training_rights": "researcher attestations; not independently verified",
            "scope": "existing bounded synthetic task; no human-data route",
        }


TASKS = {
    task.id: task
    for task in (
        Task(
            "p1-controller",
            "One supplied rate controller in the fixed M1 task",
            "source",
            "docs/p1-external-controller.md",
            "experiments.p1_external",
            "experiments.p1_external",
            run_project=NATIVE_PROJECT,
        ),
        Task(
            "m3-forecast",
            "One frozen CGM predictor against persistence",
            "config",
            "docs/m3-researcher-forecast.md",
            "experiments.m3.researcher",
            "experiments.m3.researcher",
        ),
        Task(
            "m3-compare",
            "Frozen CGM candidates on their shared paired forecast task",
            "config",
            "docs/m3-candidate-comparison.md",
            "experiments.m3.comparison",
            "experiments.m3.comparison",
        ),
        Task(
            "m4-secretion",
            "One causal secretion source with glucose, insulin and C-peptide",
            "config",
            "docs/m4-researcher-workflow.md",
            "experiments.m4.researcher_workflow.run",
            "experiments.m4.researcher_workflow.report",
        ),
        Task(
            "m4-compare",
            "Frozen secretion sources on their shared synthetic M4 task",
            "config",
            "docs/m4-source-comparison.md",
            "experiments.m4.comparison",
            "experiments.m4.comparison",
        ),
        Task(
            "m4-study",
            "Frozen secretion sources across selected initial gastric loads",
            "config",
            "docs/m4-configurable-study.md",
            "experiments.m4.initial_load",
            "experiments.m4.initial_load",
        ),
        Task(
            "m4-study-secure",
            "Initial gastric-load study in an explicitly maintained native runtime",
            "config",
            "docs/m4-maintained-study.md",
            "experiments.m4.secure_study",
            "experiments.m4.secure_study",
        ),
        Task(
            "m5-prognosis",
            "One frozen prognostic model on the invented M5 task",
            "bundle",
            "docs/m5-researcher-workflow.md",
            "experiments.m5.researcher_workflow.run",
            "experiments.m5.researcher_workflow.run",
            reconstruction_output=False,
        ),
        Task(
            "mmtt-sensitivity",
            "Paired total-secretion sensitivity on invented observations",
            "config",
            "docs/observation-analysis.md",
            "experiments.observation_analysis",
            "experiments.observation_analysis",
        ),
        Task(
            "mmtt-sampling",
            "Information loss from fewer measured synthetic MMTT times",
            "config",
            "docs/mmtt-sampling.md",
            "experiments.mmtt_sampling",
            "experiments.mmtt_sampling",
        ),
    )
}
