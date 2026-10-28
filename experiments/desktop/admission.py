"""Fresh packaged audits with clocks separate from the scientific operation.

Only the live coordinator can move from verified child results to dispatch.
Phase files are bounded display information, never reusable admission authority.
"""

import ctypes
import hashlib
import json
import math
import os
import re
import signal
import stat
import subprocess
import tempfile
import time
from pathlib import Path

from experiments.durable_archives import storage
from experiments.platform_files import (
    _windows_file_api,
    native_absolute,
    open_regular,
    replace_windows_handle,
)
from experiments.platform_process import (
    FORCE_SIGNAL,
    close_tree,
    handled_signals,
    signal_tree,
    spawn,
    tree_exists,
)

from .runtime import packaged_manifest, packaged_runtime

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "opent1d.packaged-admission/1"
AUDIT_SECONDS = storage.OPERATION_SECONDS + 30  # Full inventory, then existing metadata probe.
STARTUP_SECONDS = 30
TERM_SECONDS = 20
FORCE_SECONDS = 6
ROOT_WAIT_SECONDS = 2
JOB_CLOSE_SECONDS = 2  # Existing WindowsOwnership.cleanup(0) final observation bound.
CLEANUP_SECONDS = TERM_SECONDS + FORCE_SECONDS + ROOT_WAIT_SECONDS + JOB_CLOSE_SECONDS
JSON_LIMIT = 4 * 1024 * 1024
PHASE_LIMIT = 8192
ARGUMENTS = {
    "config",
    "source",
    "bundle",
    "profile",
    "seed",
    "reference",
    "timeout",
    "timeout_seconds",
    "archive",
    "output",
    "allow_failed",
}


def _seconds(value):
    if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
        raise ValueError("Phase allowance must be finite and positive")
    return float(value)


def _task(task):
    from experiments.workflows.registry import TASKS

    identity = task if isinstance(task, str) else getattr(task, "id", None)
    if not isinstance(identity, str) or identity not in TASKS:
        raise ValueError("Unsupported admission task")
    return TASKS[identity]


def admission_allowance(task, *, reconstruction=False, source_root=None):
    """Declare audit work and cleanup; no cached filesystem result grants admission."""
    from experiments.workflows.checks import runtime_requirements

    if packaged_manifest(ROOT if source_root is None else source_root) is None:
        return 0
    return len(runtime_requirements(_task(task), reconstruction=reconstruction)) * (
        AUDIT_SECONDS + CLEANUP_SECONDS
    )


def coordinator_budget(
    task, prepare_seconds, operation_seconds=None, *, reconstruction=False, source_root=None
):
    """Outer ceiling; unused phase time can never extend the next inner deadline."""
    prepare = _seconds(prepare_seconds)
    operation = None if operation_seconds is None else _seconds(operation_seconds)
    audit = admission_allowance(task, reconstruction=reconstruction, source_root=source_root)
    if not audit:
        return prepare if operation is None else operation
    return (
        STARTUP_SECONDS
        + prepare
        + CLEANUP_SECONDS
        + audit
        + (0 if operation is None else operation + CLEANUP_SECONDS)
    )


def requested(args, *, operation):
    """Optional packaged coordinator; absent flags retain the ordinary CLI path."""
    prepare = getattr(args, "admission_prepare_seconds", None)
    native = getattr(args, "operation_seconds", None)
    state = getattr(args, "phase_state", None)
    if prepare is None:
        if native is not None or state is not None:
            raise ValueError("Phase options require packaged admission preparation")
        return False
    _seconds(prepare)
    if operation == "check":
        if native is not None:
            raise ValueError("A check has no scientific operation allowance")
    elif native is None:
        raise ValueError("Packaged dispatch requires its unchanged operation allowance")
    else:
        _seconds(native)
    if packaged_manifest(ROOT) is None:
        raise ValueError("Explicit packaged phases require an installed package")
    return True


def _read_json(path, limit=JSON_LIMIT):
    path = storage.safe_path(path, directory=False)
    with os.fdopen(open_regular(path), "rb") as stream:
        before = os.fstat(stream.fileno())
        raw = stream.read(limit + 1)
        if (
            before.st_nlink != 1
            or len(raw) > limit
            or storage.signature(before) != storage.signature(os.fstat(stream.fileno()))
        ):
            raise ValueError("Phase record changed or exceeded its bound")
    return storage.strict_json(raw)


def _write_json(path, value):
    raw = json.dumps(value, sort_keys=True, allow_nan=False).encode() + b"\n"
    if len(raw) > JSON_LIMIT:
        raise ValueError("Phase record exceeds its bound")
    with os.fdopen(open_regular(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL), "wb") as stream:
        stream.write(raw)


def _manifest_identity(root):
    path = storage.safe_path(root.parent / "package-manifest.json", directory=False)
    with os.fdopen(open_regular(path), "rb") as stream:
        raw = stream.read(32 * 1024 * 1024 + 1)
    if len(raw) > 32 * 1024 * 1024:
        raise ValueError("Installed manifest exceeds its bound")
    return hashlib.sha256(raw).hexdigest()


def read_phase(path):
    """Read only validated display data; callers must never use this as authority."""
    value = _read_json(path, PHASE_LIMIT)
    keys = {
        "schema",
        "task",
        "operation",
        "phase",
        "project",
        "sequence",
        "phase_limit_seconds",
        "phase_started_monotonic",
        "elapsed_seconds",
        "error_type",
    }
    if not isinstance(value, dict) or set(value) != keys or value["schema"] != SCHEMA:
        raise ValueError("Unsupported packaged phase record")
    if any(not isinstance(value[key], str) for key in ("task", "operation", "phase")):
        raise ValueError("Invalid packaged phase labels")
    if value["project"] is not None and not isinstance(value["project"], str):
        raise ValueError("Invalid packaged phase project")
    _task(value["task"])
    if value["operation"] not in {"check", "run", "reconstruct"} or value["phase"] not in {
        "preparing",
        "auditing",
        "executing",
        "complete",
        "failed",
        "cancelled",
    }:
        raise ValueError("Invalid packaged phase")
    if value["project"] not in {
        None,
        ".",
        "experiments/m0/simglucose_secure",
        "experiments/m0/simglucose",
        "experiments/m4/beta_cell/runtime",
    }:
        raise ValueError("Invalid packaged phase project")
    if type(value["sequence"]) is not int or not 1 <= value["sequence"] <= 32:
        raise ValueError("Invalid packaged phase sequence")
    for key in ("phase_limit_seconds", "phase_started_monotonic", "elapsed_seconds"):
        number = value[key]
        if type(number) not in (int, float) or not math.isfinite(number) or number < 0:
            raise ValueError("Invalid packaged phase timing")
    if value["error_type"] is not None and (
        not isinstance(value["error_type"], str)
        or re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,79}", value["error_type"]) is None
    ):
        raise ValueError("Invalid packaged phase failure")
    return value


def _validate_runtime(value, project, packages):
    """Validate the current child's typed receipt; this does not replace its audit."""
    record = packaged_runtime(project, source_root=ROOT)
    if record is None:
        raise AdmissionFailure("AdmissionRuntimeMismatch")
    required = {
        "project",
        "python",
        "setup",
        "expected_python",
        "expected_packages",
        "ready",
        "reason",
    }
    if not isinstance(value, dict) or set(value) not in (required, required | {"actual"}):
        raise AdmissionFailure("AdmissionRuntimeMismatch")
    if (
        value["project"] != project
        or value["python"] != str(record["executable"])
        or value["expected_packages"] != packages
        or value["expected_python"] != "3.12"
        or value["setup"] != "Verify bundled runtime; rerun this installer if repair is needed"
        or type(value["ready"]) is not bool
    ):
        raise AdmissionFailure("AdmissionRuntimeMismatch")
    if value["ready"]:
        if value["reason"] is not None or "actual" not in value:
            raise AdmissionFailure("AdmissionRuntimeMismatch")
    elif not isinstance(value["reason"], str) or not 1 <= len(value["reason"]) <= 300:
        raise AdmissionFailure("AdmissionRuntimeMismatch")
    if "actual" not in value:
        return
    actual = value["actual"]
    if (
        not isinstance(actual, dict)
        or set(actual) != {"python", "implementation", "packages", "direct_urls"}
        or actual["implementation"] != "CPython"
        or not isinstance(actual["python"], str)
        or actual["python"] != record["manifest"]["runtime"]["version"]
        or not isinstance(actual["packages"], dict)
        or not 1 <= len(actual["packages"]) <= 500
        or actual["packages"] != record["distributions"]
        or any(
            not isinstance(k, str) or not isinstance(v, str) for k, v in actual["packages"].items()
        )
        or not isinstance(actual["direct_urls"], dict)
        or set(actual["direct_urls"]) != set(actual["packages"])
        or any(v is not None and not isinstance(v, dict) for v in actual["direct_urls"].values())
        or (value["ready"] and any(actual["packages"].get(k) != v for k, v in packages.items()))
    ):
        raise AdmissionFailure("AdmissionRuntimeMismatch")
    for name, revision in record["upstream_revisions"].items():
        direct = actual["direct_urls"].get(name) or {}
        if (
            not isinstance(direct.get("vcs_info"), dict)
            or direct["vcs_info"].get("commit_id") != revision
        ):
            raise AdmissionFailure("AdmissionRuntimeMismatch")


def _phase_identity(info):
    if not stat.S_ISREG(info.st_mode) or storage.linked(info) or info.st_nlink != 1:
        raise ValueError("Phase display file must be ordinary and single-link")
    return storage.signature(info)[:2]


def _replace_windows_phase(parent, name, target_name, source_identity, target_identity, raw):
    """Publish an owned pending file while existing GUI read handles remain valid."""
    import msvcrt

    _kernel, create, close, query, Attributes = _windows_file_api()
    source = native_absolute(parent.path / name)
    target = native_absolute(parent.path / target_name)
    # DELETE | GENERIC_READ, share READ | WRITE | DELETE, OPEN_EXISTING and
    # OPEN_REPARSE_POINT. Ancestor handles remain pinned by root_fd throughout.
    handle = create(str(source), 0x80010000, 0x7, None, 3, 0x00200000, None)
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        attributes = Attributes()
        if not query(handle, 9, ctypes.byref(attributes), ctypes.sizeof(attributes)):
            raise ctypes.WinError(ctypes.get_last_error())
        if attributes.attributes & (0x400 | 0x10):
            raise ValueError("Linked or nonregular phase pending file")
        descriptor = msvcrt.open_osfhandle(int(handle), os.O_RDONLY | os.O_BINARY)
    except BaseException:
        close(handle)
        raise
    # open_osfhandle transfers the native handle; os.close is now its sole owner.
    try:
        os.set_inheritable(descriptor, False)
        before = os.fstat(descriptor)
        if _phase_identity(before) != source_identity:
            raise ValueError("Phase pending file was replaced")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            actual = stream.read(PHASE_LIMIT + 1)
        current = storage.regular_entry_info(parent, name)
        if (
            _phase_identity(current) != source_identity
            or actual != raw
            or storage.signature(current) != storage.signature(before)
            or storage.signature(os.fstat(descriptor)) != storage.signature(before)
        ):
            raise ValueError("Phase pending file changed before publication")
        if _phase_identity(storage.regular_entry_info(parent, target_name)) != target_identity:
            raise ValueError("Phase display file was replaced")
        replace_windows_handle(handle, target)
        if _phase_identity(storage.regular_entry_info(parent, target_name)) != source_identity:
            raise ValueError("Published phase display file was replaced")
        return source_identity
    finally:
        os.close(descriptor)


def _remove_windows_pending(parent, name, identity):
    path = parent.path / name
    try:
        current = path.lstat()
    except FileNotFoundError:
        return
    if (
        stat.S_ISREG(current.st_mode)
        and not storage.linked(current)
        and current.st_nlink == 1
        and storage.signature(current)[:2] == identity
    ):
        path.unlink()


class PhaseState:
    """Exclusive fresh target; atomic updates through an owned ordinary directory."""

    def __init__(self, path):
        self.path = None if path is None else native_absolute(path)
        self.identity = None
        if self.path is not None:
            storage.safe_path(self.path, fresh=True)
            with storage.root_fd(self.path.parent) as parent:
                self._write(parent, self.path.name, b"{}\n")
                self.identity = storage.signature(
                    storage.regular_entry_info(parent, self.path.name)
                )[:2]

    @staticmethod
    def _write(parent, name, raw):
        if isinstance(parent, storage.WindowsDirectory):
            descriptor = open_regular(parent.path / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
        else:
            descriptor = os.open(
                name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent
            )
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            return _phase_identity(os.fstat(stream.fileno()))

    def update(self, value):
        if self.path is None:
            return
        raw = json.dumps(value, sort_keys=True, allow_nan=False).encode() + b"\n"
        if len(raw) > PHASE_LIMIT:
            raise ValueError("Phase display record exceeds its bound")
        name = self.path.name + ".pending"
        with storage.root_fd(self.path.parent) as parent:
            current = storage.regular_entry_info(parent, self.path.name)
            if current.st_nlink != 1 or storage.signature(current)[:2] != self.identity:
                raise ValueError("Phase display file was replaced")
            pending_identity = self._write(parent, name, raw)
            try:
                if isinstance(parent, storage.WindowsDirectory):
                    self.identity = _replace_windows_phase(
                        parent, name, self.path.name, pending_identity, self.identity, raw
                    )
                else:
                    os.replace(name, self.path.name, src_dir_fd=parent, dst_dir_fd=parent)
                    self.identity = storage.signature(
                        storage.regular_entry_info(parent, self.path.name)
                    )[:2]
            finally:
                if isinstance(parent, storage.WindowsDirectory):
                    _remove_windows_pending(parent, name, pending_identity)
                else:
                    try:
                        os.unlink(name, dir_fd=parent)
                    except FileNotFoundError:
                        pass


class AdmissionFailure(ValueError):
    def __init__(self, kind, *, forwarded_signal=None):
        super().__init__("Packaged admission: " + kind)
        self.error_type = kind
        self.forwarded_signal = forwarded_signal


class Admission:
    """One live cancellation owner from passive preparation through native dispatch."""

    def __init__(self, task, args, *, operation="check"):
        self.task, self.args, self.operation = _task(task), args, operation
        self.root = ROOT
        self.active = None
        self.soft_sent = False
        self.received = None
        self.cancelled_at = None
        self.previous = {}
        self.state = None
        self.temporary = None
        self.record = None
        self.sequence = 0
        self.manifest = None
        self.admitted = False

    def _forward(self, number, _frame=None):
        if self.received is None:
            self.received, self.cancelled_at = int(number), time.monotonic()
        if self.active is not None and not self.soft_sent:
            self.soft_sent = True
            signal_tree(
                self.active, signal.SIGTERM if number == getattr(signal, "SIGHUP", None) else number
            )

    def assert_active(self):
        if self.received is not None:
            raise AdmissionFailure("GlobalInterruption", forwarded_signal=self.received)

    def __enter__(self):
        try:
            for number in handled_signals():
                self.previous[number] = signal.signal(number, self._forward)
            self.assert_active()
            self.state = PhaseState(getattr(self.args, "phase_state", None))
            self.temporary = tempfile.TemporaryDirectory(prefix="opent1d-admission-")
            self.manifest = _manifest_identity(self.root)
            self.assert_active()
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, kind, error, traceback):
        self.admitted = False
        try:
            if error is not None and self.record is not None:
                failure = getattr(error, "error_type", type(error).__name__)
                self.finish("cancelled" if self.received is not None else "failed", failure)
        finally:
            try:
                if self.temporary is not None:
                    self.temporary.cleanup()
            finally:
                for number, handler in self.previous.items():
                    signal.signal(number, handler)
        return False

    def phase(self, phase, seconds, project=None):
        self.assert_active()
        self.sequence += 1
        self.record = {
            "schema": SCHEMA,
            "task": self.task.id,
            "operation": self.operation,
            "phase": phase,
            "project": project,
            "sequence": self.sequence,
            "phase_limit_seconds": _seconds(seconds),
            "phase_started_monotonic": time.monotonic(),
            "elapsed_seconds": 0,
            "error_type": None,
        }
        self.state.update(self.record)

    def finish(self, status, error_type=None):
        if self.record is None:
            return
        self.sequence += 1
        self.record = dict(
            self.record,
            phase=status,
            sequence=self.sequence,
            elapsed_seconds=max(0, time.monotonic() - self.record["phase_started_monotonic"]),
            error_type=error_type,
        )
        self.state.update(self.record)

    def supervise(self, argv, seconds, env):
        """Fixed phase deadline, then bounded cooperative and owned forced cleanup."""
        self.assert_active()
        deadline = time.monotonic() + _seconds(seconds)
        stopped = None
        failure = None
        forced = False
        process = None
        self.soft_sent = False
        try:
            self.active = process = spawn(
                argv, cwd=self.root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            if self.received is not None:
                self._forward(self.received)
            while True:
                code = process.poll()
                remaining = tree_exists(process)
                now = time.monotonic()
                if self.received is not None:
                    failure = "GlobalInterruption"
                    stopped = (
                        self.cancelled_at if stopped is None else min(stopped, self.cancelled_at)
                    )
                elif stopped is None and now >= deadline:
                    failure, stopped = "PhaseDeadline", now
                elif stopped is None and code is not None and remaining:
                    failure, stopped = "UnreapedWorkerGroup", now
                if code is not None and not remaining:
                    break
                if stopped is not None:
                    if not self.soft_sent:
                        self.soft_sent = True
                        signal_tree(process, signal.SIGTERM)
                    if now - stopped >= TERM_SECONDS and not forced:
                        signal_tree(process, FORCE_SIGNAL)
                        forced = True
                    if now - stopped >= TERM_SECONDS + FORCE_SECONDS:
                        failure = "OwnedCleanupDeadline"
                        break
                time.sleep(0.02)
            if code is not None:
                process.wait(timeout=0)
            if failure is not None:
                raise AdmissionFailure(failure, forwarded_signal=self.received)
            self.assert_active()
            return code, self.received
        finally:
            if process is not None:
                try:
                    # Even unexpected parent errors retain live Job/group ownership.
                    if process.poll() is None or tree_exists(process):
                        signal_tree(process, FORCE_SIGNAL)
                    try:
                        process.wait(timeout=ROOT_WAIT_SECONDS)
                    except subprocess.TimeoutExpired as error:
                        raise AdmissionFailure("OwnedCleanupDeadline") from error
                    finally:
                        close_tree(process)
                finally:
                    self.active = None

    def worker(self, mode, payload, seconds, *, project=None):
        from experiments.workflows.checks import interpreter, safe_environment

        self.phase("preparing" if mode == "prepare" else "auditing", seconds, project)
        directory = Path(self.temporary.name)
        request, result = (
            directory / f"request-{self.sequence}.json",
            directory / f"result-{self.sequence}.json",
        )
        identity = {
            "task": self.task.id,
            "operation": self.operation,
            "mode": mode,
            "project": project,
            "source_root": str(self.root),
            "manifest": self.manifest,
            "sequence": self.sequence,
        }
        _write_json(request, {"identity": identity, "payload": payload})
        argv = [
            str(interpreter(".")),
            "-B",
            "-E",
            "-s",
            "-m",
            "experiments.desktop.admission_worker",
            "--request",
            str(request),
            "--result",
            str(result),
        ]
        code, _ = self.supervise(argv, seconds, safe_environment())
        self.assert_active()
        if code != 0:
            if result.is_file():
                failed = _read_json(result)
                if (
                    isinstance(failed, dict)
                    and set(failed) == {"identity", "error_type"}
                    and failed["identity"] == identity
                    and isinstance(failed["error_type"], str)
                    and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,79}", failed["error_type"])
                ):
                    raise AdmissionFailure(failed["error_type"])
            raise AdmissionFailure("AdmissionWorkerExit")
        response = _read_json(result)
        if (
            not isinstance(response, dict)
            or set(response) != {"identity", "result"}
            or response["identity"] != identity
        ):
            raise AdmissionFailure("AdmissionResultMismatch")
        if _manifest_identity(self.root) != self.manifest:
            raise AdmissionFailure("InstalledManifestChanged")
        return response["result"]

    def check(self):
        from experiments.workflows.checks import assemble_check, runtime_requirements

        self.admitted = False
        arguments = {
            key: str(value) if isinstance(value, Path) else value
            for key, value in vars(self.args).items()
            if key in ARGUMENTS
        }
        prepared = self.worker("prepare", arguments, self.args.admission_prepare_seconds)
        if not isinstance(prepared, dict) or set(prepared) != {
            "metadata",
            "observation_path_issues",
        }:
            raise AdmissionFailure("AdmissionPreparationMismatch")
        reconstruction = self.operation == "reconstruct"
        requirements = runtime_requirements(
            self.task, prepared["metadata"], reconstruction=reconstruction
        )
        runtimes = []
        for project, packages in requirements.items():
            checked = self.worker(
                "audit", {"metadata": prepared["metadata"]}, AUDIT_SECONDS, project=project
            )
            _validate_runtime(checked, project, packages)
            runtimes.append(checked)
            if not checked.get("ready"):
                break
        self.assert_active()
        # A failed audit cannot cause a later audit or native worker to start.
        result = assemble_check(
            self.task, prepared["metadata"], prepared["observation_path_issues"], runtimes
        )
        if len(runtimes) != len(requirements):
            result.update(runtimes_ready=False, ready=False)
        self.admitted = result["runtimes_ready"] is True
        if not self.admitted:
            self.finish("failed", "PackagedRuntimeUnavailable")
        return result

    def run(self, argv, env):
        self.assert_active()
        if not self.admitted:
            raise AdmissionFailure("CurrentAdmissionRequired")
        self.admitted = False  # One dispatch consumes only this live admission.
        if _manifest_identity(self.root) != self.manifest:
            raise AdmissionFailure("InstalledManifestChanged")
        self.phase("executing", self.args.operation_seconds)
        result = self.supervise(argv, self.args.operation_seconds, env)
        self.finish(
            "complete" if result[0] == 0 else "failed", None if result[0] == 0 else "WorkerExit"
        )
        return result
