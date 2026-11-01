"""Small installed API over the original immutable project services."""

from pathlib import Path

from ._client import invoke


def _path(value):
    return str(Path(value).absolute())


class Project:
    def __init__(self, path):
        self.path = _path(path)

    def _call(self, action, **fields):
        return invoke({"action": action, "project": self.path, **fields})

    def info(self):
        return self._call("info")

    def plan(self, plan):
        """Read an immutable plan and its recorded parent without executing it."""
        return self._call("plan", plan=plan)

    def comparison_options(self, plan):
        """Read task-owned selectors for an existing immutable plan."""
        return self._call("comparison-options", plan=plan)

    def freeze_study(self, name, question, *, forward_plan=None, observation_case="complete"):
        """Freeze the connected study before forward execution; optionally create its M4 plan."""
        return self._call(
            "freeze-study",
            name=name,
            question=question,
            forward_plan=forward_plan,
            observation_case=observation_case,
        )

    def study(self, study, *, at=None):
        """Read fixed stage identities, next explicit action and the complete planned support."""
        return self._call("study", study=study, at=at)

    def materialize_study(self, study):
        """Verify forward evidence and resume publication of exact downstream inputs/plans."""
        return self._call("materialize-study", study=study)

    def reconstruct_study(self, study, output, *, at=None):
        """Verify a saved connected chain without rerunning its forward model."""
        return self._call("reconstruct-study", study=study, output=_path(output), at=at)

    def freeze_comparison(self, definition):
        """Freeze the complete comparison roster before any selected plan runs."""
        return self._call("freeze-comparison", definition=definition)

    def comparison(self, comparison, *, at=None):
        return self._call("comparison", comparison=comparison, at=at)

    def reconstruct_comparison(self, comparison, output, *, at=None):
        """Reconstruct fixed first attempts at an explicit saved ledger tip."""
        return self._call(
            "reconstruct-comparison", comparison=comparison, at=at, output=_path(output)
        )

    def export_inputs(self, plan, output):
        """Export exact original inputs for an explicitly derived editable study."""
        return self._call("export-inputs", plan=plan, output=_path(output))

    def freeze(self, task, inputs, *, parent=None, expected_input_sha256=None):
        return self._call(
            "freeze",
            task=task,
            inputs={name: _path(path) for name, path in inputs.items()},
            parent=parent,
            **(
                {"expected_input_sha256": expected_input_sha256}
                if expected_input_sha256 is not None
                else {}
            ),
        )

    def check(self, plan, *, runtime_attachment=None):
        return self._call(
            "check",
            plan=plan,
            runtime_attachment=None if runtime_attachment is None else _path(runtime_attachment),
        )

    def run(self, plan, *, retry_of=None, timeout=600, cancel=None, runtime_attachment=None):
        return invoke(
            {
                "action": "run",
                "project": self.path,
                "plan": plan,
                "retry_of": retry_of,
                "timeout": timeout,
                "runtime_attachment": None
                if runtime_attachment is None
                else _path(runtime_attachment),
            },
            cancel=cancel,
        )

    def reconstruct(self, attempt, output, *, allow_failed=False):
        return self._call(
            "reconstruct", attempt=attempt, output=_path(output), allow_failed=allow_failed
        )

    def import_attempt(self, plan, archive, *, retry_of=None):
        return self._call("import", plan=plan, archive=_path(archive), retry_of=retry_of)

    def relocate(self, output):
        return self._call("relocate", output=_path(output))

    def recover(self, attempt, *, execution_stopped=False):
        return self._call("recover", attempt=attempt, execution_stopped=execution_stopped)


def create_project(path, name):
    result = invoke({"action": "create", "project": _path(path), "name": name})
    return Project(result["project"])


def open_project(path):
    project = Project(path)
    project.info()
    return project


def example(task, output, *, case="complete"):
    return invoke({"action": "example", "task": task, "output": _path(output), "case": case})


def validate(task, inputs):
    return invoke(
        {
            "action": "validate",
            "task": task,
            "inputs": {name: _path(path) for name, path in inputs.items()},
        }
    )


def inspect_inputs(task, inputs):
    """Admit native inputs and summarize observations without estimation."""
    return invoke(
        {
            "action": "inspect",
            "task": task,
            "inputs": {name: _path(path) for name, path in inputs.items()},
        }
    )


def prepare_development(package, csv, design, output):
    return invoke(
        {
            "action": "prepare-development",
            "package": _path(package),
            "csv": _path(csv),
            "design": _path(design),
            "output": _path(output),
        }
    )


def installation():
    return invoke({"action": "installation"})


def attach_runtimes(native_site, observer_site, output):
    return invoke(
        {
            "action": "attach",
            "native_site": _path(native_site),
            "observer_site": _path(observer_site),
            "output": _path(output),
        }
    )
