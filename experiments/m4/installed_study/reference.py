"""Owned maintained execution of inherited BC-008 science, with a distinct receipt."""

import argparse
import shutil
import signal
from contextlib import contextmanager
from pathlib import Path

from experiments.m4.causal_secretion.common import reference as inherited_reference
from experiments.m4.feedback import common as bc
from experiments.m4.feedback import report as scientific
from experiments.platform_process import handled_signals

from . import context, locations, profile
from .common import (
    NATIVE_PROJECT,
    REFERENCE_SCHEMA,
    ROOT,
    digest,
    dump,
    protocol,
    read,
    require,
    sha256,
    source_snapshots,
)
from .process import Control, supervise
from .runtime import validate, validate_numerical_runtime


@contextmanager
def scientific_reader(schema):
    previous = scientific.VERSION
    scientific.VERSION = schema
    try:
        yield
    finally:
        scientific.VERSION = previous


def command(directory):
    return context.command("native", "worker", [str(directory), "--kind", "baseline"])


def descriptor():
    p = protocol()
    return {
        "schema": "m4-installed-reference-execution/1",
        "protocol": p["id"],
        "protocol_sha256": digest((Path(__file__).parent / "protocol.json").read_bytes()),
        "scientific_protocol": "BC-008/2",
        "scientific_protocol_sha256": p["conditions"]["protocol_files_sha256"][
            "experiments/m4/feedback/protocol.json"
        ],
        "execution": p["execution"],
        "implementation_sources_sha256": {
            name: digest(raw) for name, raw in source_snapshots().items()
        },
    }


def verify(directory):
    directory = profile.archive(directory)
    require(not directory.is_symlink(), "Reference cannot be a symlink")
    manifest = read(directory / "manifest.json")
    if manifest.get("schema") != REFERENCE_SCHEMA:
        from experiments.m4.researcher_workflow.common import verify_reference_sources

        require(
            not any(path.is_symlink() for path in directory.rglob("*")),
            "Historical reference contains symlink",
        )
        result = inherited_reference(directory)
        verify_reference_sources(directory)
        return result
    require(
        read(directory / "execution.json") == descriptor(),
        "Maintained reference execution descriptor changed",
    )
    for folder in (directory, directory / "repeat"):
        for name in ("protocol.json", "source-cases.json"):
            require(
                sha256(folder / name) == sha256(bc.HERE / name),
                "Inherited reference scientific bytes changed",
            )
    require(
        sha256(directory / "sources.json") == sha256(bc.HERE / "sources.json"),
        "Inherited reference attribution bytes changed",
    )
    for name, expected in read(directory / "execution.json")[
        "implementation_sources_sha256"
    ].items():
        require(
            sha256(directory / "implementation" / name) == expected,
            "Maintained reference implementation snapshot changed",
        )
    for name in bc.SOURCES:
        require(
            sha256(directory / ("source-" + name)) == sha256(bc.HERE / name),
            "Inherited reference source changed",
        )
    for name in bc.REUSED:
        require(
            sha256(directory / ("source-" + name.replace("/", "__"))) == sha256(ROOT / name),
            "Inherited reference helper changed",
        )
    for name in ("pyproject.toml", "uv.lock"):
        require(
            sha256(directory / name) == sha256(ROOT / NATIVE_PROJECT / name),
            "Maintained reference runtime changed",
        )
    p = protocol()
    attachment = profile.evidence(read(directory / "runtime-context.json"))
    require(
        sha256(directory / "runtime-context.json")
        == manifest["execution_locations"]["attachment_sha256"],
        "Reference attachment snapshot differs",
    )
    for folder in (directory, directory / "repeat"):
        receipt = read(folder / "runtime.json")
        validate(receipt, NATIVE_PROJECT, p, attachment)
        for name in ("native.json", "probe.json"):
            validate_numerical_runtime(receipt, read(folder / name)["runtime"])
    require(
        read(directory / "runtime.json") == read(directory / "repeat/runtime.json"),
        "Reference runtime repeat differs",
    )
    require(manifest.get("files") == bc.file_hashes(directory), "Reference inventory changed")
    attempts = manifest.get("attempts", [])
    require(len(attempts) == 2, "Missing maintained reference repeat ledger")
    original = manifest["archive_original_path"]
    require(
        type(manifest["timeout_seconds"]) is int and 1 <= manifest["timeout_seconds"] <= 1800,
        "Reference budget changed",
    )
    for label, attempt in zip(("primary", "repeat"), attempts, strict=True):
        folder = original if label == "primary" else locations.join_recorded(original, "repeat")
        args = locations.command(manifest, "native", "worker", [str(folder), "--kind", "baseline"])
        require(
            attempt
            == {
                "label": label,
                "argv": args,
                "timeout_seconds": manifest["timeout_seconds"],
                "exit_code": 0,
                "error_type": None,
            },
            "Reference execution command/status changed",
        )
        from .process import validate_receipt

        validate_receipt(
            directory / ("worker.log" if label == "primary" else "repeat.log"),
            args,
            manifest["timeout_seconds"],
            0,
            "completed",
            10,
        )
        relative = Path("runtime.json") if label == "primary" else Path("repeat/runtime.json")
        require(
            read(directory / relative)["executable"] == args[0],
            "Reference actual interpreter differs from command",
        )
        header = read_log_header(directory / ("worker.log" if label == "primary" else "repeat.log"))
        require(
            header == {"argv": args, "timeout_seconds": manifest["timeout_seconds"]},
            "Reference command log changed",
        )
    with scientific_reader(REFERENCE_SCHEMA):
        report = scientific.reconstruct(directory)
    require(report["passed"], "Maintained reference failed inherited scientific gates")
    require(read(directory / "report.json") == report, "Maintained reference report changed")
    return (
        read(directory / "protocol.json"),
        read(directory / "native.json"),
        read(directory / "probe.json"),
        report,
    )


def read_log_header(path):
    from experiments.m1.artifacts import strict_json

    return strict_json(path.read_bytes().splitlines()[0])


def execute(output, timeout=600):
    require(type(timeout) is int and 1 <= timeout <= 1800, "Invalid reference stage budget")
    output = Path(output).absolute()
    require(not output.is_symlink(), "Reference output cannot be a symlink")
    output.mkdir(parents=True, exist_ok=False)
    manifest = {
        "schema": REFERENCE_SCHEMA,
        "status": "started",
        "files": {},
        "attempts": [],
        "archive_original_path": str(output),
        "checkout_path": str(ROOT),
        "timeout_seconds": timeout,
        "execution_locations": locations.capture((NATIVE_PROJECT,)),
    }
    context.snapshot(output / "runtime-context.json")
    for name in ("protocol.json", "source-cases.json", "sources.json"):
        shutil.copyfile(bc.HERE / name, output / name)
    for name in bc.SOURCES:
        shutil.copyfile(bc.HERE / name, output / ("source-" + name))
    for name in bc.REUSED:
        shutil.copyfile(ROOT / name, output / ("source-" + name.replace("/", "__")))
    for name in ("pyproject.toml", "uv.lock"):
        shutil.copyfile(ROOT / NATIVE_PROJECT / name, output / name)
    for name, raw in source_snapshots().items():
        path = output / "implementation" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    dump(output / "execution.json", descriptor())
    dump(output / "manifest.json", manifest)
    control = Control()
    previous = {s: signal.getsignal(s) for s in handled_signals()}
    for s in previous:
        signal.signal(s, control.stop)
    try:
        for label in ("primary", "repeat"):
            if control.signal is not None:
                raise KeyboardInterrupt("Maintained reference interrupted")
            folder = output if label == "primary" else output / "repeat"
            if label == "repeat":
                folder.mkdir()
                for name in ("protocol.json", "source-cases.json"):
                    shutil.copyfile(output / name, folder / name)
            args = command(folder)
            attempt = {
                "label": label,
                "argv": args,
                "timeout_seconds": timeout,
                "exit_code": None,
                "error_type": None,
            }
            manifest["attempts"].append(attempt)
            dump(output / "manifest.json", manifest)
            code, error = supervise(
                args,
                output / ("worker.log" if label == "primary" else "repeat.log"),
                timeout,
                control,
            )
            attempt.update(exit_code=code, error_type=error)
            if error is not None:
                raise RuntimeError(error)
        manifest.update(status="calculated", files=bc.file_hashes(output))
        dump(output / "manifest.json", manifest)
        with scientific_reader(REFERENCE_SCHEMA):
            report = scientific.reconstruct(output, allow_pending=True)
        require(report["passed"], "Maintained reference failed inherited numerical gates")
        dump(output / "report.json", report)
        manifest.update(status="completed", files=bc.file_hashes(output))
        dump(output / "manifest.json", manifest)
        verify(output)
        return report
    except BaseException as exc:
        manifest.update(
            status="failed",
            error={"type": type(exc).__name__, "message": str(exc)[:500]},
            files=bc.file_hashes(output),
        )
        dump(output / "manifest.json", manifest)
        raise
    finally:
        for s, handler in previous.items():
            signal.signal(s, handler)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=int, default=600)
    args = parser.parse_args()
    execute(args.output, args.timeout_seconds)
