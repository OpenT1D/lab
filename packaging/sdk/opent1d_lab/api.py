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

    def export_inputs(self, plan, output):
        """Export exact original inputs for an explicitly derived editable study."""
        return self._call("export-inputs", plan=plan, output=_path(output))

    def freeze(self, task, inputs, *, parent=None):
        return self._call(
            "freeze",
            task=task,
            inputs={name: _path(path) for name, path in inputs.items()},
            parent=parent,
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
