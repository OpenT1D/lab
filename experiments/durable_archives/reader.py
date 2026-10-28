"""Explicit clean checkouts or verified installations authorize fixed saved readers."""

import hashlib
import os
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time

from . import installed, storage

TASKS = {
    "m4-study-secure": ("experiments.m4.secure_study", "reconstruct", "--archive"),
    "maintained-campaign": ("experiments.maintained_campaigns", "reconstruct", "--campaign"),
    "m3-forecast": ("experiments.m3.researcher", "report", "--study"),
    "m3-compare": ("experiments.m3.comparison", "reconstruct", "--study"),
}
REPORTS = {
    "m4-study-secure": ("report.json", "report.md", "figure.svg"),
    "maintained-campaign": ("report.json", "report.md"),
    "m3-forecast": ("report.json", "report.md"),
    "m3-compare": ("report.json", "report.md"),
}
SCHEMAS = {
    "m4-study-secure": "m4-secure-study-report/1",
    "maintained-campaign": "opent1d.maintained-campaign-report/1",
    "m3-forecast": "opent1d.m3.researcher/1",
    "m3-compare": "opent1d.m3.comparison/1",
}
M3_TASKS = frozenset({"m3-forecast", "m3-compare"})
LOG_LIMIT = 4 * 1024 * 1024
REPORT_LIMIT = 64 * 1024 * 1024


def environment():
    return {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("PYTHON", "GIT_", "UV_"))
        and key not in {"VIRTUAL_ENV", "__PYVENV_LAUNCHER__"}
    }


def git(checkout, *args, budget):
    budget.check()
    deadline = min(budget.deadline, time.monotonic() + 30)
    process = None
    previous = None
    main = threading.current_thread() is threading.main_thread()

    def interrupted(_number, _frame):
        raise KeyboardInterrupt("Git reader inspection cancelled")

    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        try:
            if main:
                previous = signal.signal(signal.SIGTERM, interrupted)
            process = subprocess.Popen(
                [
                    "git",
                    "--no-optional-locks",
                    "-c",
                    "core.fsmonitor=false",
                    "-c",
                    "core.hooksPath=/dev/null",
                    *args,
                ],
                cwd=checkout,
                env=environment(),
                stdout=out,
                stderr=err,
                stdin=subprocess.DEVNULL,
                creationflags=0x00000008 if os.name == "nt" else 0,  # DETACHED_PROCESS
                start_new_session=os.name == "posix",
            )
            while process.poll() is None:
                storage.require(
                    time.monotonic() < deadline, "Trusted Git inspection deadline exceeded"
                )
                storage.require(
                    os.fstat(out.fileno()).st_size <= storage.MANIFEST_LIMIT
                    and os.fstat(err.fileno()).st_size <= storage.MANIFEST_LIMIT,
                    "Git inventory exceeds limit",
                )
                time.sleep(0.01)
            storage.require(process.returncode == 0, "Trusted checkout Git inspection failed")
            out.seek(0)
            raw = out.read(storage.MANIFEST_LIMIT + 1)
            storage.require(len(raw) <= storage.MANIFEST_LIMIT, "Git inventory exceeds limit")
            return raw
        finally:
            if process is not None and process.poll() is None:
                if os.name == "posix":
                    os.killpg(process.pid, signal.SIGKILL)
                else:
                    process.kill()
                process.wait(timeout=5)
            if main and previous is not None:
                signal.signal(signal.SIGTERM, previous)


def checkout_identity(checkout, revision, budget, *, destination=None):
    checkout = storage.safe_path(checkout)
    storage.require(
        isinstance(revision, str) and storage.REVISION.fullmatch(revision),
        "Reader requires a full lowercase Git revision",
    )
    if installed.package_manifest(checkout, budget) is not None:
        return installed.identity(checkout, revision, budget, destination=destination)
    storage.require(
        git(checkout, "rev-parse", "--show-toplevel", budget=budget).decode().strip()
        == str(checkout),
        "Reader must be the exact trusted checkout root",
    )
    storage.require(
        git(checkout, "rev-parse", "HEAD", budget=budget).decode().strip() == revision,
        "Trusted reader revision differs from requested full revision",
    )
    storage.require(
        not git(checkout, "status", "--porcelain=v1", "--untracked-files=all", "-z", budget=budget),
        "Trusted reader checkout must be clean",
    )
    tree = git(checkout, "ls-tree", "-r", "-z", revision, budget=budget)
    entries = [item for item in tree.split(b"\0") if item]
    storage.require(0 < len(entries) <= storage.FILES_LIMIT, "Reader tracked file limit exceeded")
    records, aliases, total = {}, set(), 0
    signatures = {}
    with storage.root_fd(checkout) as root:
        for entry in entries:
            budget.check()
            header, raw_name = entry.split(b"\t", 1)
            mode, kind, object_id = header.split(b" ")
            storage.require(
                mode in {b"100644", b"100755"} and kind == b"blob", "Linked Git entry refused"
            )
            name = storage.relative_name(raw_name.decode("utf-8"))
            storage.require(name.casefold() not in aliases, "Tracked reader path alias")
            aliases.add(name.casefold())
            parents, descriptor = [], root
            try:
                for component in name.split("/")[:-1]:
                    descriptor = storage._open_directory(component, dir_fd=descriptor)
                    parents.append(descriptor)
                basename = name.rsplit("/", 1)[-1]
                record, observed = storage.stream_file(descriptor, basename, budget=budget)
                total += record["size"]
                storage.require(total <= storage.TOTAL_LIMIT, "Reader byte limit exceeded")
                # Git index flags can hide changed files from status. Independently
                # bind every working byte to its committed SHA-1 Git object.
                fd = storage.open_file(descriptor, basename)
                with os.fdopen(fd, "rb") as handle:
                    opened = os.fstat(handle.fileno())
                    storage.require(
                        stat.S_ISREG(opened.st_mode)
                        and opened.st_nlink == 1
                        and storage.signature(opened) == observed,
                        "Tracked reader file replaced before committed-byte verification",
                    )
                    committed = hashlib.sha1(
                        b"blob " + str(record["size"]).encode() + b"\0", usedforsecurity=False
                    )
                    copied_sha = hashlib.sha256()
                    copied_size = 0
                    target = None
                    if destination is not None:
                        path = destination / name
                        path.parent.mkdir(parents=True, exist_ok=True)
                        target = open(path, "xb")
                    try:
                        while True:
                            budget.check()
                            raw = handle.read(storage.CHUNK)
                            if not raw:
                                break
                            copied_size += len(raw)
                            storage.require(
                                copied_size <= storage.FILE_LIMIT, "Reader file limit exceeded"
                            )
                            committed.update(raw)
                            copied_sha.update(raw)
                            if target is not None:
                                target.write(raw)
                    finally:
                        if target is not None:
                            target.close()
                    storage.require(
                        committed.hexdigest() == object_id.decode()
                        and copied_size == record["size"]
                        and copied_sha.hexdigest() == record["sha256"]
                        and storage.signature(os.fstat(handle.fileno())) == observed,
                        "Reader working bytes differ from recorded Git revision: " + name,
                    )
                records[name], signatures[name] = record, observed
            finally:
                for parent in reversed(parents):
                    storage.close_directory(parent)
    storage.require(
        git(checkout, "rev-parse", "HEAD", budget=budget).decode().strip() == revision
        and not git(
            checkout, "status", "--porcelain=v1", "--untracked-files=all", "-z", budget=budget
        ),
        "Trusted reader checkout changed during inspection",
    )
    return {"revision": revision, "files": records}, signatures


def command(task, archive, checkout, output):
    storage.require(task in TASKS, "Unsupported durable archive task")
    module, operation, flag = TASKS[task]
    argv = [
        str(installed.executable(checkout, storage.Budget()) or sys.executable),
        "-B",
        "-E",
        "-s",
        "-S",
        "-m",
        module,
        operation,
        flag,
        str(archive),
        "--output",
        str(output),
    ]
    # M3's saved readers already accept sealed failed/partial coverage and do
    # not define --allow-failed. Never substitute a run or candidate module.
    if task not in M3_TASKS:
        argv.append("--allow-failed")
    return argv


def completeness(task, report):
    storage.require(
        isinstance(report, dict) and report.get("schema") == SCHEMAS[task],
        "Fixed reader returned an unsupported report",
    )
    if task in M3_TASKS:
        section = report.get("evaluation" if task == "m3-forecast" else "common")
        storage.require(
            report.get("kind") == "synthetic"
            and report.get("human_evaluation") is False
            and isinstance(section, dict)
            and type(section.get("complete_cohort")) is bool,
            "Fixed M3 reader returned an unsupported synthetic cohort report",
        )
        return section["complete_cohort"]
    storage.require(
        type(report.get("passed")) is bool, "Fixed reader returned an unsupported report"
    )
    return report["passed"]


def reconstruct(task, archive, checkout, evidence, budget, timeout_seconds):
    storage.require(
        type(timeout_seconds) is int and 1 <= timeout_seconds <= 1800,
        "Reader timeout must be an integer from 1 to 1800 seconds",
    )
    evidence.mkdir()
    output = evidence / "reconstructed"
    argv = command(task, archive, checkout, output)
    reader_python = sys.version
    if os.path.realpath(argv[0]) != os.path.realpath(sys.executable):
        reader_python = (
            subprocess.check_output(
                [argv[0], "-I", "-S", "-B", "-c", "import sys; print(sys.version)"],
                stdin=subprocess.DEVNULL,
                creationflags=0x00000008 if os.name == "nt" else 0,  # DETACHED_PROCESS
                cwd=checkout,
                env=environment(),
                timeout=10,
            )
            .decode()
            .strip()
        )
        storage.require(0 < len(reader_python) <= 8192, "Reader runtime identity exceeds limit")
    started = time.monotonic()
    deadline = min(budget.deadline, started + timeout_seconds)
    process = None
    previous_handler = None
    is_main = threading.current_thread() is threading.main_thread()

    def interrupted(_number, _frame):
        raise KeyboardInterrupt("Durable reader operation cancelled")

    def stop():
        if process is None or process.poll() is not None:
            return
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGTERM)
        else:
            process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            if os.name == "posix":
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
            process.wait(timeout=5)

    stdout, stderr = evidence / "reader-stdout.log", evidence / "reader-stderr.log"
    try:
        if is_main:
            previous_handler = signal.signal(signal.SIGTERM, interrupted)
        with stdout.open("xb") as out, stderr.open("xb") as err:
            process = subprocess.Popen(
                argv,
                cwd=checkout,
                env=environment(),
                stdout=out,
                stderr=err,
                stdin=subprocess.DEVNULL,
                creationflags=0x00000008 if os.name == "nt" else 0,  # DETACHED_PROCESS
                start_new_session=os.name == "posix",
            )
            while process.poll() is None:
                storage.require(
                    time.monotonic() < deadline, "Authoritative reader deadline exceeded"
                )
                storage.require(
                    stdout.stat().st_size <= LOG_LIMIT and stderr.stat().st_size <= LOG_LIMIT,
                    "Reader log byte limit exceeded",
                )
                time.sleep(0.02)
            storage.require(
                stdout.stat().st_size <= LOG_LIMIT and stderr.stat().st_size <= LOG_LIMIT,
                "Reader log byte limit exceeded",
            )
            storage.require(process.returncode == 0, "Fixed authoritative reconstruction failed")
    finally:
        stop()
        if is_main and previous_handler is not None:
            signal.signal(signal.SIGTERM, previous_handler)
    report_raw = storage.read_file(output, "report.json", budget, limit=REPORT_LIMIT)
    report = storage.strict_json(report_raw)
    complete = completeness(task, report)
    files, _ = storage.inventory(output, budget)
    storage.require(set(files["files"]) == set(REPORTS[task]), "Unexpected fixed reader artifacts")
    result = {
        "status": "verified_reconstruction",
        "complete": complete,
        "artifacts": files["files"],
        "reader_command": argv,
        "reader_checkout": str(checkout),
        "reader_executable": argv[0],
        "reader_python": reader_python,
        # Inclusion policy, independent of whether the native route has a flag.
        "allow_failed": True,
        "requested_timeout_seconds": timeout_seconds,
        "effective_timeout_seconds": max(0, deadline - started),
        "exit_code": process.returncode,
    }
    (evidence / "reader-receipt.json").write_bytes(storage.encoded(result))
    return result
