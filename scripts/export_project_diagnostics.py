"""Export allowlisted counts from a validated synthetic project; never run tasks."""

import argparse
import os
import stat
import sys
import uuid
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiments.catalogue.storage import encoded  # noqa: E402
from experiments.durable_archives.storage import root_fd, safe_path  # noqa: E402
from experiments.shared_services import store  # noqa: E402

SCHEMA = "opent1d.project-diagnostics/1"
EXPORTER = "opent1d.export-project-diagnostics/1"
# Keep the output vocabulary explicit, even if the store later admits more tasks.
TASKS = frozenset(
    {"mmtt-sensitivity", "mmtt-sampling", "m3-compare", "m4-study-secure", "m4-study-installed"}
)
STATUSES = frozenset({"completed", "failed", "interrupted"})


class Refused(ValueError):
    """Only fixed categories cross this developer tool's error boundary."""


def identity(info):
    return info.st_dev, info.st_ino


def unlink_owned(parent, name, owned):
    """A substituted entry is evidence, never authority for deletion."""
    try:
        current = os.stat(name, dir_fd=parent, follow_symlinks=False)
    except FileNotFoundError:
        return
    if identity(current) == owned:
        os.unlink(name, dir_fd=parent)


def destination(output, parent, source):
    """Recheck the live namespace against the pinned destination and source inode."""
    safe_path(output, directory=False, fresh=True)
    with root_fd(output.parent) as current:
        if identity(os.fstat(current)) != identity(os.fstat(parent)):
            raise ValueError("Destination parent changed")
    if any(identity(path.stat()) == source for path in output.parents):
        raise ValueError("Output must be outside project")


def publish(output, raw, source):
    """Stage and exclusively link complete bytes relative to one pinned parent."""
    output = safe_path(output, directory=False, fresh=True)
    with root_fd(output.parent) as parent:
        destination(output, parent, source)
        temporary = ".project-diagnostics-" + uuid.uuid4().hex
        descriptor = os.open(
            temporary,
            os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o600,
            dir_fd=parent,
        )
        owned = identity(os.fstat(descriptor))
        linked = False
        success = False
        try:
            with os.fdopen(descriptor, "w+b") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
                stream.seek(0)
                before = os.fstat(stream.fileno())
                named = os.stat(temporary, dir_fd=parent, follow_symlinks=False)
                if (
                    identity(named) != owned
                    or not stat.S_ISREG(named.st_mode)
                    or named.st_nlink != 1
                    or stream.read(len(raw) + 1) != raw
                ):
                    raise ValueError("Staged file changed")
                destination(output, parent, source)
                # link() is atomic and refuses every existing final entry. Both
                # names are relative to the retained no-link directory descriptor.
                os.link(
                    temporary,
                    output.name,
                    src_dir_fd=parent,
                    dst_dir_fd=parent,
                    follow_symlinks=False,
                )
                linked = True
                published = os.stat(output.name, dir_fd=parent, follow_symlinks=False)
                after = os.fstat(stream.fileno())
                if (
                    identity(published) != owned
                    or not stat.S_ISREG(published.st_mode)
                    or after.st_nlink != 2
                    or after.st_size != len(raw)
                    or (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns)
                ):
                    raise ValueError("Published file changed")
                # The fresh final entry now exists; check its ancestors separately.
                with root_fd(output.parent) as current:
                    if identity(os.fstat(current)) != identity(os.fstat(parent)):
                        raise ValueError("Destination parent changed")
                if any(identity(path.stat()) == source for path in output.parents):
                    raise ValueError("Output moved into project")
            unlink_owned(parent, temporary, owned)
            success = True
        finally:
            # Never unlink a substituted namespace entry, including on refusal.
            try:
                if not success:
                    unlink_owned(parent, temporary, owned)
            finally:
                if not success and linked:
                    unlink_owned(parent, output.name, owned)


def summarize(project):
    """Read only validated in-memory accounting while its shared lease is held."""
    project.require_lease()
    plans = Counter()
    unattempted = Counter()
    attempts = Counter()
    outcomes = {}
    attempted_plans = {row["plan"] for row in project.attempts.values()}
    for identity, (descriptor, _path) in project.plans.items():
        task = descriptor["task"]
        if task not in TASKS:
            raise ValueError("Unsupported diagnostic task")
        plans[task] += 1
        unattempted[task] += identity not in attempted_plans
        outcomes.setdefault(task, Counter())
    for identity, attempt in project.attempts.items():
        task = project.plans[attempt["plan"]][0]["task"]
        attempts[task] += 1
        if identity not in project.finishes:
            outcome = ("unfinished", "unknown", "unknown")
        else:
            finish, _evidence = project.finishes[identity]
            process = finish["receipt"]["status"]
            status = finish["result"]["execution_status"]
            completeness = finish["result"]["completeness"]
            if (
                process not in STATUSES
                or status not in STATUSES
                or completeness not in {"complete", "incomplete"}
            ):
                raise ValueError("Unsupported diagnostic outcome")
            outcome = (process, status, completeness)
        outcomes[task][outcome] += 1
    return {
        "schema": SCHEMA,
        "exporter": EXPORTER,
        "project_schema": store.SCHEMA,
        "plans": len(project.plans),
        "attempts": len(project.attempts),
        "tasks": [
            {
                "task": task,
                "plans": plans[task],
                "plans_without_attempts": unattempted[task],
                "attempts": attempts[task],
                "outcomes": [
                    {
                        "process_status": process,
                        "execution_status": status,
                        "completeness": completeness,
                        "count": count,
                    }
                    for (process, status, completeness), count in sorted(outcomes[task].items())
                ],
            }
            for task in sorted(plans)
        ],
    }


def export(project_path, output):
    """Publish one complete fresh JSON file outside the source under a read lease."""
    if os.name != "posix":
        raise Refused("unsupported_host")
    # Opening owns all ledger/native validation. Never repair or parse a fallback.
    try:
        with store.opened(project_path, write_access=False) as project:
            raw = encoded(summarize(project))
            try:
                publish(output, raw, identity(project.path.stat()))
            except Exception:
                raise Refused("output_refused") from None
    except Refused:
        raise
    except Exception:
        # Store/native validators may encounter malformed structures as well as
        # I/O errors. Their messages can contain paths, inputs or arbitrary text.
        raise Refused("project_refused") from None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, help="Existing synthetic project directory")
    parser.add_argument("--output", required=True, help="Fresh JSON file outside the project")
    args = parser.parse_args(argv)
    try:
        export(args.project, args.output)
    except Refused as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
