"""Explicit raw M3 retention: byte copies with no native-reader or package claim."""

import argparse
import copy
import sys
import uuid
from pathlib import Path

from experiments.durable_archives import storage
from experiments.platform_files import atomic_write_bytes

from .library_paths import directory_identity, validate_identity
from .service import digest, encode, read_json, timestamp

ENTRY = "opent1d.gui-forensic-entry/1"
REQUEST = "opent1d.gui-forensic-request/1"
RESULT = "opent1d.gui-forensic-worker/1"
RECEIPT = "opent1d.m3-forensic-retention/1"
TASKS = {"m3-forecast", "m3-compare"}


@storage.cancellable
def retain(request):
    storage.require(
        isinstance(request, dict)
        and set(request)
        == {
            "schema",
            "entry_id",
            "operation",
            "root_identity",
            "path",
            "source",
            "preparation",
            "administration",
            "provenance",
        }
        and request["schema"] == REQUEST
        and request["operation"] == "durable_forensic"
        and isinstance(request["entry_id"], str)
        and request["entry_id"].startswith("forensic-")
        and request["path"] == request["entry_id"]
        and len(request["entry_id"]) == 41
        and all(c in "0123456789abcdef" for c in request["entry_id"][9:])
        and isinstance(request["provenance"], dict)
        and request["provenance"].get("task") in TASKS,
        "Unsupported raw retention request",
    )
    budget = storage.Budget()
    root = validate_identity(request["root_identity"])
    output = root / request["path"]
    sources = {}
    for name in ("source", "preparation", "administration"):
        item = request[name]
        storage.require(
            isinstance(item, dict) and set(item) == {"path", "identity"},
            "Invalid raw retention source",
        )
        path = validate_identity(item["identity"])
        storage.require(str(path) == item["path"], "Frozen raw source differs")
        storage.separate(root, path)
        sources[name] = path
    for name, path in sources.items():
        for other, alternative in sources.items():
            if name != other:
                storage.separate(path, alternative)
    views = {name: storage.inventory(path, budget) for name, path in sources.items()}
    with storage.staging(output, list(sources.values())) as stage:
        for name, path in sources.items():
            target = stage / ("archive" if name == "source" else name)
            target.mkdir()
            view, _ = storage.inventory(path, budget, destination=target)
            storage.require(view == views[name][0], "Raw source changed during copy")
        provenance = encode(request["provenance"])
        storage.require(len(provenance) <= storage.MANIFEST_LIMIT, "Provenance exceeds limit")
        (stage / "provenance.json").write_bytes(provenance)
        inventory, _ = storage.inventory(stage, budget)
        for name, path in sources.items():
            storage.require(storage.inventory(path, budget) == views[name], "Raw source changed")
        receipt = {
            "schema": RECEIPT,
            "task": request["provenance"]["task"],
            "source": {name: str(path) for name, path in sources.items()},
            "retained_at": timestamp(),
            "byte_copy_verified": True,
            "integrity_verified": False,
            "reconstruction_verified": False,
            "complete": None,
            "interpretation": "Raw byte retention only; no verified durable package, native-reader "
            "success, scientific completeness, resume or process authority.",
            **inventory,
        }
        raw = storage.encoded(receipt)
        storage.require(len(raw) <= storage.MANIFEST_LIMIT, "Raw receipt exceeds limit")
        (stage / "retention.json").write_bytes(raw)
        # Exact bound applies to the receipt as well as copied source files.
        storage.inventory(stage, budget)
        validate_identity(request["root_identity"])
    return {
        "schema": RECEIPT,
        "task": receipt["task"],
        "output": str(output),
        "receipt_identity": digest(raw),
        "byte_copy_verified": True,
        "integrity_verified": False,
        "reconstruction_verified": False,
        "complete": None,
        "interpretation": receipt["interpretation"],
    }


class Forensics:
    def __init__(self, durable):
        self.durable = durable
        self.service = durable.service
        self.registered = {}
        for path in sorted(durable.data.glob("forensic-*.json"))[:128]:
            try:
                self.service.safe_path(path)
                entry = read_json(path)
                if entry.get("schema") != ENTRY or entry.get("id") != path.stem:
                    continue
                if entry.get("status") == "checking":
                    entry["status"] = "interrupted"
                self.registered[entry["id"]] = entry
            except (OSError, ValueError, KeyError, TypeError):
                continue

    def persist(self, entry):
        path = self.service.safe_path(self.durable.data / (entry["id"] + ".json"), exists=False)
        temporary = self.service.safe_path(path.with_suffix(".tmp"), exists=False)
        atomic_write_bytes(path, encode(entry), temporary=temporary)

    def prepare(self, identity):
        if not self.durable.bootstrap()["can_export"]:
            raise ValueError("Start the GUI with an existing external --archive-store")
        if len(self.registered) >= 128:
            raise ValueError("At most 128 raw retention entries are supported")
        entry = self.service.m3.get(identity)
        if entry["execution_state"] in {"queued", "running", "cancelling"}:
            raise ValueError("Retain a stopped M3 operation")
        archive = self.service.m3.archive_path(identity)
        preparation = self.service.m3.configuration_path(entry["configuration_id"])
        matching = [
            job
            for job in self.service.jobs.values()
            if job.get("operation") == "m3_run"
            and job.get("request", {}).get("entry_id") == identity
        ]
        if len(matching) != 1:
            raise ValueError("Raw retention requires its unique original owned M3 run receipt")
        source_job = self.service.get_job(matching[0]["id"])
        administration = self.service.safe_path(self.service.data / source_job["id"])
        value = "forensic-" + uuid.uuid4().hex
        request = {
            "schema": REQUEST,
            "operation": "durable_forensic",
            "entry_id": value,
            "root_identity": copy.deepcopy(self.durable.store),
            "path": value,
            "source": {"path": str(archive), "identity": directory_identity(archive)},
            "preparation": {"path": str(preparation), "identity": directory_identity(preparation)},
            "administration": {
                "path": str(administration),
                "identity": directory_identity(administration),
            },
            "provenance": {
                "task": entry["task"],
                "m3_entry": copy.deepcopy(entry),
                "recorded_gui_job": copy.deepcopy(source_job),
                "process_authority": (
                    "Recorded process identities are provenance only; never adopted"
                ),
            },
        }
        record = {
            "schema": ENTRY,
            "id": value,
            "m3_id": identity,
            "created_at": timestamp(),
            "status": "checking",
            "request": request,
            "result": None,
            "error": None,
        }
        self.registered[value] = record
        self.persist(record)
        return copy.deepcopy(request)

    def commands(self, job):
        request = job["request"]
        entry = self.registered.get(request["entry_id"])
        if not entry or request != entry["request"]:
            raise ValueError("Frozen raw retention request changed")
        folder = self.service.safe_path(self.service.data / job["id"])
        path = self.service.safe_path(folder / "worker-request.json", exists=False)
        if path.exists():
            raise ValueError("Raw retention requires a fresh job")
        path.write_bytes(encode(request))
        return [
            (
                [
                    self.service.python,
                    "-B",
                    "-E",
                    "-s",
                    "-S",
                    "-m",
                    "experiments.gui.forensic",
                    "--request",
                    str(path),
                    "--output",
                    str(folder),
                ],
                900,
            )
        ]

    def finish(self, job):
        entry = self.registered[job["request"]["entry_id"]]
        try:
            result = read_json(
                self.service.safe_path(self.service.data / job["id"] / "worker-result.json")
            )
            if (
                result.get("schema") != RESULT
                or result.get("entry_id") != entry["id"]
                or result.get("request_sha256") != digest(encode(job["request"]))
                or result.get("operation") != "durable_forensic"
            ):
                raise ValueError("Raw retention result does not bind its request")
            native = result.get("native") or {}
            clean = (
                not job["cancel_requested"]
                and not job.get("cleanup_forced")
                and not job.get("error")
                and not job.get("remaining_owned_processes")
            )
            if (
                result["status"] == "completed"
                and job["exit_code"] == 0
                and clean
                and native.get("schema") == RECEIPT
                and native.get("byte_copy_verified") is True
                and native.get("integrity_verified") is False
                and native.get("reconstruction_verified") is False
                and native.get("complete") is None
                and native.get("output")
                == str(Path(job["request"]["root_identity"]["path"]) / entry["id"])
            ):
                entry.update(status="retained", result=native, error=None)
            else:
                raise ValueError(result.get("error") or "Raw retention did not complete cleanly")
            job["result"] = result
        except (OSError, ValueError, KeyError, TypeError) as error:
            entry.update(
                status="cancelled" if job["cancel_requested"] else "failed", error=str(error)[:300]
            )
            if not job["cancel_requested"]:
                job["error"] = job.get("error") or str(error)[:300]
        job["report_completeness"] = "unavailable"
        job["verification"] = "not_requested"
        entry["last_job"] = job["id"]
        self.persist(entry)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve(strict=True)
    if args.request.parent.resolve(strict=True) != output:
        raise ValueError("Raw request must be frozen in its owned job folder")
    request = read_json(args.request)
    result = {
        "schema": RESULT,
        "entry_id": request.get("entry_id"),
        "operation": "durable_forensic",
        "request_sha256": digest(encode(request)),
        "status": "failed",
        "native": None,
        "error": None,
    }
    try:
        result.update(status="completed", native=retain(request))
    except (OSError, ValueError, KeyError, TypeError, RecursionError) as error:
        result["error"] = type(error).__name__ + ": " + str(error)[:1000]
    (output / "worker-result.json").write_bytes(encode(result))
    print(encode(result).decode(), end="")
    return 0 if result["status"] == "completed" else 1


if __name__ == "__main__":
    sys.exit(main())
