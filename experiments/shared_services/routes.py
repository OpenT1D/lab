"""Two explicit task bindings; archived snapshots are data, never import paths."""

import copy
from pathlib import Path

from experiments.catalogue.storage import decode, digest, encoded, load_sealed
from experiments.m3.researcher.intake import read_regular
from experiments.m4.initial_load.common import inventory as m4_inventory
from experiments.m4.secure_study import common as m4
from experiments.m4.secure_study.report import validate_frozen as validate_m4_frozen
from experiments.observation_analysis import plan as mmtt
from experiments.shared_contracts.inventory import reader_source_inventory
from experiments.shared_contracts.selected import boundary, outcome, reader

from .store import Budget, inventory, read, require, safe_path, snapshot, write

ROOT = Path(__file__).resolve().parents[2]
TASKS = {
    "mmtt-sensitivity": "experiments.observation_analysis",
    "m4-study-secure": "experiments.m4.secure_study",
}


def runtime_paths(binding):
    return {
        (ROOT / project / name).resolve().relative_to(ROOT).as_posix()
        for project, files in binding["runtime_files_sha256"].items()
        for name in files
    }


def reader_identity(task):
    require(task in TASKS, "Unselected task")
    return {
        **reader(task),
        **reader_source_inventory(TASKS[task]),
        "compatibility": "exact-trusted-reader/1",
    }


def capture(task, inputs, target):
    """Freeze originals separately from effective relocatable M4 path spelling."""
    require(task in TASKS, "Unselected task")
    target.mkdir()
    original = target / "original"
    original.mkdir()
    payload = {}
    expected = (
        {"config.json"}
        if task == "m4-study-secure"
        else {"package.json", "observations.csv", "settings.json"}
    )
    require(set(inputs) == expected, "Explicit native input roster required")
    for name, path in inputs.items():
        raw = read_regular(path, 4 * 1024 * 1024, "scientific input")
        (original / name).write_bytes(raw)
        payload[name] = raw
    metadata = boundary(task, payload)
    effective = target / "input"
    if task == "mmtt-sensitivity":
        mmtt.freeze(
            original / "package.json",
            original / "observations.csv",
            original / "settings.json",
            effective,
        )
    else:
        config, bundles = m4.intake(inputs["config.json"])
        require(
            payload["config.json"] == next(iter(bundles.values()))["config_raw"],
            "M4 input changed during capture",
        )
        effective.mkdir()
        config = copy.deepcopy(config)
        for item in config["sources"]:
            name, bundle = item["id"], bundles[item["id"]]
            folder = effective / name
            folder.mkdir()
            for field, basename in (("model", "model.py"), ("declaration", "model.json")):
                (folder / basename).write_bytes(bundle[field + "_raw"])
                item[field] = name + "/" + basename
        (effective / "config.json").write_bytes(encoded(config))
    trusted = reader_identity(task)
    names = set(trusted["trusted_sources_sha256"]) | set(
        trusted["reader_static_dependencies_sha256"]
    )
    names.update(mmtt.ANCESTRY if task == "mmtt-sensitivity" else ())
    names.update(runtime_paths(metadata["binding"]))
    # Native locks/selectors are already captured by the identity provider;
    # selectors returns path->hash records (not runtime installation receipts).
    snapshots = {}
    for name in sorted(names):
        raw = read_regular(ROOT / name, 4 * 1024 * 1024, "trusted snapshot")
        path = target / "trusted" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        snapshots[name] = digest(raw)
    descriptor = {
        "schema": "opent1d.service-freeze/1",
        "task": task,
        "boundary": metadata,
        "reader": trusted,
        "original_sha256": {name: digest(raw) for name, raw in payload.items()},
        "trusted_sha256": snapshots,
    }
    write(target / "descriptor.json", descriptor)
    validate_freeze(target, descriptor, current=True)
    return descriptor


def validate_freeze(folder, descriptor, *, current):
    require(
        isinstance(descriptor, dict)
        and set(descriptor)
        == {"schema", "task", "boundary", "reader", "original_sha256", "trusted_sha256"}
        and descriptor["schema"] == "opent1d.service-freeze/1"
        and descriptor["task"] in TASKS
        and read(folder / "descriptor.json") == descriptor,
        "Unsupported or changed freeze identity",
    )
    task = descriptor["task"]
    require(
        set(descriptor["original_sha256"])
        == (
            {"config.json"}
            if task == "m4-study-secure"
            else {"package.json", "observations.csv", "settings.json"}
        ),
        "Original input roster differs",
    )
    payload = {
        name: read_regular(folder / "original" / name, 4 * 1024 * 1024, "original input")
        for name in descriptor["original_sha256"]
    }
    require(
        {name: digest(raw) for name, raw in payload.items()} == descriptor["original_sha256"],
        "Original input identity differs",
    )
    require(
        boundary(task, payload) == descriptor["boundary"],
        "Frozen task/source/runtime identity differs",
    )
    trusted = descriptor["reader"]
    require(
        trusted == reader_identity(task),
        "Unsupported trusted reader version; archived code stays opaque",
    )
    expected = set(trusted["trusted_sources_sha256"]) | set(
        trusted["reader_static_dependencies_sha256"]
    )
    expected.update(mmtt.ANCESTRY if task == "mmtt-sensitivity" else ())
    expected.update(runtime_paths(descriptor["boundary"]["binding"]))
    require(set(descriptor["trusted_sha256"]) == expected, "Missing source/reader/runtime snapshot")
    for name, sha in descriptor["trusted_sha256"].items():
        require(
            digest(
                read_regular(folder / "trusted" / name, 4 * 1024 * 1024, "opaque trusted snapshot")
            )
            == sha,
            "Trusted snapshot differs",
        )
        require(
            digest(read_regular(ROOT / name, 4 * 1024 * 1024, "current trusted source")) == sha,
            "Current implementation/runtime/source differs",
        )
    if task == "mmtt-sensitivity":
        mmtt.load_plan(folder / "input", check_runtime=current)
        for name, raw in payload.items():
            require((folder / "input" / name).read_bytes() == raw, "Effective MMTT input differs")
    else:
        effective = copy.deepcopy(decode(payload["config.json"]))
        for item in effective["sources"]:
            name = item["id"]
            for field, basename in (("model", "model.py"), ("declaration", "model.json")):
                item[field] = name + "/" + basename
            identity = descriptor["boundary"]["binding"]["source_sha256"][name]
            require(
                digest((folder / "input" / name / "model.py").read_bytes())
                == identity["source_sha256"],
                "Frozen supplied source differs",
            )
            require(
                digest((folder / "input" / name / "model.json").read_bytes())
                == identity["declaration_sha256"],
                "Frozen source declaration differs",
            )
        require(
            read(folder / "input/config.json") == effective,
            "Effective configuration differs from original",
        )


def native_result(archive, descriptor, plan):
    archive = safe_path(archive)
    inventory(archive, Budget())
    task = descriptor["task"]
    report = read(archive / "report.json")
    execution = read(archive / ("execution.json" if task == "mmtt-sensitivity" else "state.json"))
    if task == "mmtt-sensitivity":
        load_sealed(archive)
        require(
            report["plan"] == read(plan / "input/plan.json"),
            "Native archive belongs to another frozen plan",
        )
        payload = {
            name: (plan / "original" / name).read_bytes() for name in descriptor["original_sha256"]
        }
    else:
        files = m4_inventory(archive)
        manifest = read(archive / "manifest.json")
        require(
            manifest.get("schema") == m4.VERSION
            and manifest.get("files") == {name: digest(raw) for name, raw in files.items()},
            "Native M4 archive inventory differs from manifest",
        )
        # This helper is passive and does not activate inherited module
        # bindings. Full assessment/reconstruction stays in an isolated reader.
        native_plan = validate_m4_frozen(archive, files)
        require(
            native_plan["configuration"] == read(plan / "input/config.json"),
            "Native archive belongs to another frozen plan",
        )
        require(
            native_plan["provenance"]["sources"]
            == descriptor["boundary"]["binding"]["implementation_sha256"],
            "Native implementation differs",
        )
        payload = {"config.json": (plan / "input/config.json").read_bytes()}
    status, complete, slots = outcome(
        task, report, execution, payload, descriptor["boundary"]["binding"]
    )
    names = (
        ("report.json", "report.md", "figure.svg")
        if task == "m4-study-secure"
        else ("report.json", "report.md")
    )
    return {
        "payload": "native",
        "execution_status": status,
        "completeness": "complete" if complete else "incomplete",
        "slot_statuses": slots,
        "reconstruction": "unchecked",
        "scientific_evidence": "synthetic-only",
        "report_sha256": {
            name: digest(read_regular(archive / name, 128 * 1024 * 1024, "native report"))
            for name in names
        },
    }


def forensic_result(descriptor, status):
    return {
        "payload": "forensic",
        "execution_status": status,
        "completeness": "incomplete",
        "slot_statuses": dict.fromkeys(descriptor["boundary"]["planned_slots"], "unavailable"),
        "reconstruction": "unavailable",
        "scientific_evidence": "synthetic-only",
        "report_sha256": {},
    }


def validate_finish(evidence, data, descriptor, plan):
    receipt = data["receipt"]
    require(read(evidence / "receipt.json") == receipt, "Attempt receipt differs")
    require(
        isinstance(receipt, dict)
        and receipt.get("status") in {"completed", "failed", "interrupted"}
        and receipt.get("remaining_owned_processes") == [],
        "Unfinished process cleanup cannot be sealed as terminal",
    )
    result = data["result"]
    if result.get("payload") == "native":
        require(
            result == native_result(evidence / "native", descriptor, plan),
            "Native result/status/slots differ",
        )
        if receipt["status"] == "completed":
            require(result["execution_status"] == "completed", "Process/native status differs")
    else:
        require(receipt["status"] != "completed", "Forensic evidence cannot claim completion")
        require(
            result == forensic_result(descriptor, receipt["status"]),
            "Forensic evidence cannot promote slots",
        )


def freeze(store, task, inputs, *, parent=None):
    import tempfile

    require(parent is None or parent in store.plans, "Missing parent plan")
    with tempfile.TemporaryDirectory(prefix="opent1d-freeze-") as staging:
        captured = Path(staging).resolve() / "plan"
        descriptor = capture(task, inputs, captured)
        if parent is not None:
            require(store.plans[parent][0]["task"] == task, "Derived task differs")
        identity = store.append(
            "freeze",
            {"parent": parent, "descriptor": descriptor},
            lambda folder: snapshot(captured, folder / "plan"),
        )
    store.inspect()
    return identity


def import_attempt(store, plan_id, archive, *, retry_of=None):
    """Explicit passive intake of existing native evidence, including failed archives."""
    from .execution import begin, finish

    descriptor, plan = store.plans[plan_id]
    native_result(Path(archive), descriptor, plan)
    attempt, work = begin(store, plan_id, retry_of=retry_of, mode="import")
    snapshot(archive, work / "native")
    result = native_result(work / "native", descriptor, plan)
    receipt = {
        "status": result["execution_status"],
        "mode": "import",
        "remaining_owned_processes": [],
        "owned_processes": [],
        "native_reader": "unchecked",
    }
    return finish(store, attempt, work, receipt)
