"""Owned GUI admission and fixed CLI dispatch for the synthetic observation task."""

import copy
import re
import uuid

from experiments.observation_analysis.fixtures import CASES, analysis_settings
from experiments.observation_analysis.observations import parse_csv, validate_package
from experiments.observation_analysis.plan import validate_settings
from experiments.platform_files import atomic_write_bytes

from .library_observations import ARTIFACTS, TASK, validate_report
from .service import (
    MAX_REPORT,
    bounded_bytes,
    decode_json,
    digest,
    encode,
    inventory,
    read_json,
    timestamp,
)

OPERATIONS = frozenset(
    "observation_" + name for name in ("example", "freeze", "run", "reconstruct")
)
REQUEST = "opent1d.gui-observation-request/1"
CONFIG = "opent1d.gui-observation-configuration/1"
ENTRY = "opent1d.gui-observation-entry/1"
CASE_LABELS = {
    "increase": "Consistent increase control",
    "assumption-dependent": "Assumption-dependent control",
    "unresolved": "Unresolved change control",
    "censored": "Censored observation control",
}


def require(value, message):
    if not value:
        raise ValueError(message)


def identity(value, kind, prefix="obs"):
    require(
        isinstance(value, str) and re.fullmatch(prefix + "-" + kind + r"-[0-9a-f]{32}", value),
        "Invalid observation " + kind + " identity",
    )
    return value


def validate_request(
    value,
    *,
    task=TASK,
    operations=OPERATIONS,
    request_schema=REQUEST,
    cases=CASES,
    operation_prefix="observation",
    id_prefix="obs",
):
    require(
        isinstance(value, dict)
        and set(value)
        == {
            "schema",
            "task",
            "operation",
            "configuration_id",
            "entry_id",
            "example_id",
            "case",
            "plan_identity",
            "archive_identity",
        }
        and value["schema"] == request_schema
        and value["task"] == task
        and value["operation"] in operations,
        "Unsupported observation operation request",
    )
    example = value["operation"] == operation_prefix + "_example"
    require(
        (value["example_id"] is not None) == example and (value["case"] is not None) == example,
        "Example operation fields differ",
    )
    if example:
        identity(value["example_id"], "input", id_prefix)
        require(value["case"] in cases, "Unknown invented case")
    for key, kind, needed in (
        ("configuration_id", "config", not example),
        (
            "entry_id",
            "study",
            value["operation"] in (operation_prefix + "_run", operation_prefix + "_reconstruct"),
        ),
    ):
        require((value[key] is not None) == needed, "Operation identity fields differ")
        if needed:
            identity(value[key], kind, id_prefix)
    for key in ("plan_identity", "archive_identity"):
        require(
            value[key] is None
            or isinstance(value[key], str)
            and re.fullmatch(r"[0-9a-f]{64}", value[key]),
            "Invalid frozen observation identity",
        )
    require(
        (value["plan_identity"] is not None)
        == (value["operation"] in {operation_prefix + "_run", operation_prefix + "_reconstruct"}),
        "Required plan identity differs",
    )
    require(
        (value["archive_identity"] is not None)
        == (value["operation"] == operation_prefix + "_reconstruct"),
        "Required archive identity differs",
    )
    return value


class Observations:
    task = TASK
    operations = OPERATIONS
    cases = CASES
    config_schema = CONFIG
    entry_schema = ENTRY
    request_schema = REQUEST
    operation_prefix = "observation"
    id_prefix = "obs"
    data_name = "observations"
    native_module = "experiments.observation_analysis"
    validate_report = staticmethod(validate_report)
    case_labels = CASE_LABELS
    default_display_name = "Paired meal-test analysis"

    def identity(self, value, kind):
        return identity(value, kind, self.id_prefix)

    def validate_request(self, value):
        return validate_request(
            value,
            task=self.task,
            operations=self.operations,
            request_schema=self.request_schema,
            cases=self.cases,
            operation_prefix=self.operation_prefix,
            id_prefix=self.id_prefix,
        )

    def op(self, name):
        return self.operation_prefix + "_" + name

    def __init__(self, service):
        self.service = service
        self.data = service.safe_path(service.data / self.data_name, exists=False)
        self.data.mkdir(exist_ok=True)
        for name in ("inputs", "configurations", "archives"):
            service.safe_path(self.data / name, exists=False).mkdir(exist_ok=True)
        self.configs, self.entries = {}, {}
        for kind, target, schema in (
            ("configurations", self.configs, self.config_schema),
            ("archives", self.entries, self.entry_schema),
        ):
            for path in sorted((self.data / kind).glob(self.id_prefix + "-*/*.json")):
                if path.name != "record.json":
                    continue
                try:
                    value = read_json(service.safe_path(path))
                    require(value["schema"] == schema, "Unsupported observation record")
                    self.identity(value["id"], "config" if kind == "configurations" else "study")
                    require(value["id"] == path.parent.name, "Observation record directory differs")
                    if value.get("verification") == "native_reader_verified":
                        value["verification"] = "recorded_verification"
                    if value.get("verification") == "verifying":
                        value["verification"] = "not_requested"
                    if value.get("state") in ("queued", "running"):
                        value["state"] = "interrupted_owner_unavailable"
                    target[value["id"]] = value
                    self.persist(value)
                except (OSError, ValueError, KeyError, TypeError):
                    continue

    def folder(self, record):
        kind = "configurations" if record["schema"] == self.config_schema else "archives"
        return self.service.safe_path(self.data / kind / record["id"])

    def persist(self, record):
        target = self.folder(record) / "record.json"
        temporary = target.with_suffix(".tmp")
        atomic_write_bytes(target, encode(record), temporary=temporary)

    def idle(self):
        require(
            not self.service.closing and self.service.active is None,
            "One active operation is allowed; wait or cancel it",
        )

    def bootstrap(self):
        return {
            "task": self.task,
            "cases": list(self.cases),
            "settings": analysis_settings(),
            "configurations": self.configurations(),
            "entries": self.list(),
        }

    def input_display_name(self, body):
        """Presentation metadata follows an owned input pair, never native evidence."""
        for config in self.configs.values():
            paths = config.get("input_paths", {})
            if all(paths.get(key) == body.get(key) for key in ("package", "csv")):
                return config.get("display_name") or self.default_display_name
        for job in self.service.jobs.values():
            request = job.get("request") or {}
            if request.get("operation") != self.op("example") or job.get("exit_code") != 0:
                continue
            paths = (job.get("result") or {}).get("input_paths", {})
            if all(paths.get(key) == body.get(key) for key in ("package", "csv")):
                return self.case_labels.get(request.get("case"), self.default_display_name)
        return self.default_display_name

    def configuration_display_name(self, body):
        name = body.get("display_name", "")
        require(
            isinstance(name, str)
            and len(name) <= 120
            and all(character.isprintable() for character in name),
            "Analysis name must be at most 120 characters on one line",
        )
        return name.strip() or self.input_display_name(body)

    def browse(self, directory="inputs"):
        path = self.service.safe_path(directory)
        require(path.is_dir(), "Choose a workspace directory")
        items = []
        for child in sorted(path.iterdir()):
            if child.is_symlink() or child.name.startswith("."):
                continue
            if child.is_dir() or child.is_file() and child.suffix in (".json", ".csv"):
                items.append(
                    {
                        "name": child.name,
                        "path": child.relative_to(self.service.root).as_posix(),
                        "directory": child.is_dir(),
                    }
                )
            if len(items) >= 256:
                break
        return {"directory": path.relative_to(self.service.root).as_posix(), "items": items}

    def read_inputs(self, body):
        package_path = self.service.safe_path(body["package"], suffix=".json")
        package_raw = bounded_bytes(package_path, 1024 * 1024)
        package = validate_package(
            decode_json(package_raw)
        )  # Refuse human declaration before CSV access.
        csv_path = self.service.safe_path(body["csv"], suffix=".csv")
        csv_raw = bounded_bytes(csv_path, 16 * 1024 * 1024)
        return package, package_raw, csv_raw

    def inspect(self, body):
        with self.service.lock:
            self.idle()
            require(
                set(body) == {"package", "csv", "settings"},
                "Choose metadata, CSV and settings files",
            )
            package, raw, csv = self.read_inputs(body)
            settings = read_json(
                self.service.safe_path(body["settings"], suffix=".json"), 1024 * 1024
            )
            validate_settings(settings, package)
            require(
                settings["uncertainty"]["seed"] <= 2**53 - 1,
                "Use a seed at most 9007199254740991 in the GUI; larger 64-bit seeds require CLI",
            )
            return {
                "display_name": self.input_display_name(body),
                "settings": copy.deepcopy(settings),
                "input_sha256": {"package.json": digest(raw), "observations.csv": digest(csv)},
                "validation": self.validation_summary(parse_csv(csv, package)),
                "planned_people": len(package["participants"]),
            }

    @staticmethod
    def validation_summary(validation):
        return {
            "valid": validation["valid"],
            "errors": validation["errors"],
            "visits": [
                {
                    "participant_id": visit["participant_id"],
                    "visit_id": visit["visit_id"],
                    "valid": visit["valid"],
                    "rows": len(visit["rows"]),
                    "errors": visit["errors"],
                    "missing_or_censored": sum(
                        row["cpeptide_status"] != "observed" or row["glucose_status"] != "observed"
                        for row in visit["rows"]
                    ),
                }
                for visit in validation["visits"]
            ],
        }

    def configure(self, body):
        with self.service.lock:
            self.idle()
            require(
                set(body) - {"display_name"} == {"package", "csv", "settings", "input_sha256"},
                "Unsupported observation configuration",
            )
            display_name = self.configuration_display_name(body)
            package, package_raw, csv = self.read_inputs(body)
            settings = validate_settings(body["settings"], package)
            require(
                settings["uncertainty"]["seed"] <= 2**53 - 1, "GUI seed exceeds exact integer range"
            )
            hashes = {"package.json": digest(package_raw), "observations.csv": digest(csv)}
            require(hashes == body["input_sha256"], "Input bytes changed; inspect the files again")
            ident = self.id_prefix + "-config-" + uuid.uuid4().hex
            folder = self.service.safe_path(self.data / "configurations" / ident, exists=False)
            folder.mkdir()
            (folder / "inputs").mkdir()
            raw = {
                "package.json": package_raw,
                "observations.csv": csv,
                "settings.json": encode(settings),
            }
            for name, value in raw.items():
                (folder / "inputs" / name).write_bytes(value)
            record = {
                "schema": self.config_schema,
                "id": ident,
                "display_name": display_name,
                "created_at": timestamp(),
                "state": "prepared",
                "source_paths": {"package": body["package"], "csv": body["csv"]},
                "input_paths": {
                    key: (folder / "inputs" / name).relative_to(self.service.root).as_posix()
                    for key, name in (
                        ("package", "package.json"),
                        ("csv", "observations.csv"),
                        ("settings", "settings.json"),
                    )
                },
                "inputs_sha256": {name: digest(value) for name, value in raw.items()},
                "settings": copy.deepcopy(settings),
                "planned_people": len(package["participants"]),
                "validation": self.validation_summary(parse_csv(csv, package)),
                "plan_identity": None,
                "ready": False,
                "error": None,
            }
            self.configs[ident] = record
            self.persist(record)
            return copy.deepcopy(record)

    def configurations(self):
        return [
            self.get_configuration(value["id"])
            for value in sorted(self.configs.values(), key=lambda v: v["created_at"], reverse=True)
        ]

    def list(self):
        return [
            self.get(value["id"])
            for value in sorted(self.entries.values(), key=lambda v: v["created_at"], reverse=True)
        ]

    def get_configuration(self, ident):
        self.identity(ident, "config")
        require(ident in self.configs, "Unknown observation configuration")
        config = copy.deepcopy(self.configs[ident])
        config.setdefault("display_name", self.default_display_name)
        return config

    def get(self, ident):
        self.identity(ident, "study")
        require(ident in self.entries, "Unknown observation analysis")
        entry = copy.deepcopy(self.entries[ident])
        entry.setdefault(
            "display_name",
            self.configs.get(entry.get("configuration_id"), {}).get("display_name")
            or self.default_display_name,
        )
        job = self.service.jobs.get(entry.get("run_job"), {})
        if entry["state"] == "queued" and job.get("state") in ("queued", "running", "cancelling"):
            entry["state"] = job["state"]
        return entry

    def request(self, operation, *, configuration_id=None, entry_id=None, case=None):
        require(operation in self.operations, "Unsupported observation operation")
        request = {
            "schema": self.request_schema,
            "task": self.task,
            "operation": operation,
            "configuration_id": configuration_id,
            "entry_id": entry_id,
            "example_id": None,
            "case": None,
            "plan_identity": None,
            "archive_identity": None,
        }
        if operation == self.op("example"):
            require(case in self.cases, "Choose an invented case")
            request.update(case=case, example_id=self.id_prefix + "-input-" + uuid.uuid4().hex)
        elif operation == self.op("reconstruct"):
            entry = self.get(entry_id)
            require(
                entry.get("archive_identity") is not None, "No sealed analysis archive is available"
            )
            request.update(
                configuration_id=entry["configuration_id"],
                archive_identity=entry["archive_identity"],
                plan_identity=entry["plan_identity"],
            )
        else:
            config = self.get_configuration(configuration_id)
            if operation == self.op("run"):
                require(config["ready"], "Validate and freeze this plan before running")
                request.update(
                    entry_id=self.id_prefix + "-study-" + uuid.uuid4().hex,
                    plan_identity=config["plan_identity"],
                )
            else:
                require(config["state"] == "prepared", "Choose a fresh configuration to freeze")
        return self.validate_request(request)

    def started(self, job):
        request = self.validate_request(job["request"])
        job["task"] = self.task
        if request["configuration_id"]:
            job[self.operation_prefix + "_configuration_id"] = request["configuration_id"]
        if request["entry_id"]:
            job[self.operation_prefix + "_entry_id"] = request["entry_id"]
        if request["operation"] == self.op("run"):
            folder = self.service.safe_path(
                self.data / "archives" / request["entry_id"], exists=False
            )
            folder.mkdir()
            entry = {
                "schema": self.entry_schema,
                "id": request["entry_id"],
                "display_name": self.get_configuration(request["configuration_id"])["display_name"],
                "configuration_id": request["configuration_id"],
                "plan_identity": request["plan_identity"],
                "created_at": timestamp(),
                "state": "queued",
                "run_job": job["id"],
                "verification": "not_requested",
                "archive_identity": None,
                "artifacts_sha256": {},
                "report_completeness": "unavailable",
                "error": None,
            }
            self.entries[entry["id"]] = entry
            self.persist(entry)
        elif request["operation"] == self.op("reconstruct"):
            entry = self.entries[request["entry_id"]]
            entry["verification"] = "verifying"
            self.persist(entry)

    def commands(self, job):
        request = self.validate_request(job["request"])
        base = [self.service.python, "-B", "-E", "-s", "-S", "-m"]
        native = base + [self.native_module]

        def workflow(operation):
            if getattr(self.service, "profile", "checkout") == "desktop":
                return native + [operation]
            return base + ["experiments.workflows", operation, self.task]

        operation = request["operation"]
        if operation == self.op("example"):
            return [
                (
                    native
                    + [
                        "example",
                        "--case",
                        request["case"],
                        "--output",
                        str(self.data / "inputs" / request["example_id"]),
                    ],
                    60,
                )
            ]
        config = self.configs[request["configuration_id"]]
        folder = self.folder(config)
        if operation == self.op("freeze"):
            for name, sha in config["inputs_sha256"].items():
                path = self.service.safe_path(folder / "inputs" / name)
                require(
                    digest(bounded_bytes(path, 16 * 1024 * 1024)) == sha,
                    "GUI input snapshot changed",
                )
            return [
                (
                    native
                    + [
                        "import",
                        "--package",
                        str(folder / "inputs/package.json"),
                        "--csv",
                        str(folder / "inputs/observations.csv"),
                        "--output",
                        str(folder / "validation"),
                    ],
                    60,
                ),
                (
                    native
                    + [
                        "freeze",
                        "--package",
                        str(folder / "inputs/package.json"),
                        "--csv",
                        str(folder / "inputs/observations.csv"),
                        "--settings",
                        str(folder / "inputs/settings.json"),
                        "--output",
                        str(folder / "frozen"),
                    ],
                    60,
                ),
                (
                    workflow("check")
                    + [
                        "--config",
                        str(folder / "frozen"),
                    ],
                    60,
                ),
            ]
        require(
            digest(
                bounded_bytes(self.service.safe_path(folder / "frozen/manifest.json"), MAX_REPORT)
            )
            == request["plan_identity"],
            "Frozen plan identity changed",
        )
        entry = self.entries[request["entry_id"]]
        archive = self.folder(entry) / "archive"
        if operation == self.op("run"):
            return [
                (
                    workflow("run")
                    + [
                        "--config",
                        str(folder / "frozen"),
                        "--output",
                        str(archive),
                    ],
                    180,
                )
            ]
        require(
            inventory(self.service.safe_path(archive)) == request["archive_identity"],
            "Saved analysis changed since execution",
        )
        return [
            (
                workflow("reconstruct")
                + [
                    "--archive",
                    str(archive),
                    "--output",
                    str(self.service.data / job["id"] / "reconstructed"),
                    "--allow-failed",
                ],
                180,
            )
        ]

    def finish(self, job):
        request = self.validate_request(job["request"])
        result = job.get("result") or {}
        operation = request["operation"]
        if operation == self.op("example"):
            if job.get("exit_code") == 0:
                result["display_name"] = self.case_labels[request["case"]]
                folder = self.data / "inputs" / request["example_id"]
                result["input_paths"] = {
                    key: (folder / name).relative_to(self.service.root).as_posix()
                    for key, name in (
                        ("package", "package.json"),
                        ("csv", "observations.csv"),
                        ("settings", "settings.json"),
                    )
                }
        elif operation == self.op("freeze"):
            config = self.configs[request["configuration_id"]]
            validation_path = self.folder(config) / "validation/import.json"
            if validation_path.is_file():
                validation = read_json(validation_path, MAX_REPORT).get("validation")
                if validation is not None:
                    config["validation"] = self.validation_summary(validation)
            checked = (
                result.get("status") == "ready"
                if getattr(self.service, "profile", "checkout") == "desktop"
                else result.get("ready") is True
            )
            config["ready"] = job.get("exit_code") == 0 and checked
            config["state"] = "frozen" if config["ready"] else "invalid_or_interrupted"
            config["error"] = (
                None
                if config["ready"]
                else "Validation/freeze did not complete; inspect the retained validation"
            )
            if config["ready"]:
                config["plan_identity"] = digest(
                    bounded_bytes(self.folder(config) / "frozen/manifest.json", MAX_REPORT)
                )
            self.persist(config)
            result[self.operation_prefix + "_configuration"] = self.get_configuration(config["id"])
        else:
            entry = self.entries[request["entry_id"]]
            archive = self.folder(entry) / "archive"
            if operation == self.op("run"):
                if (archive / "manifest.json").is_file():
                    report = self.validate_report(read_json(archive / "report.json", MAX_REPORT))
                    frozen_plan = read_json(
                        self.folder(self.configs[entry["configuration_id"]]) / "frozen/plan.json"
                    )
                    if report["plan"] is not None:
                        require(
                            report["plan"] == frozen_plan,
                            "Native report plan differs from selected GUI plan",
                        )
                    entry.update(
                        archive_identity=inventory(archive),
                        artifacts_sha256={
                            name: digest(bounded_bytes(archive / name, MAX_REPORT))
                            for name in ARTIFACTS
                        },
                        report_completeness="complete"
                        if report["coverage"]["complete_cohort"]
                        else "incomplete",
                        state=report["execution_status"],
                        error=job.get("error"),
                        coverage=report["coverage"],
                        classifications={
                            person: value["classification"]
                            for person, value in report.get("people", {}).items()
                        },
                    )
                else:
                    entry.update(
                        state="unsealed_or_unavailable",
                        error="No sealed native analysis is available",
                    )
            else:
                rebuilt = self.service.data / job["id"] / "reconstructed"
                if job.get("exit_code") == 0:
                    require(
                        inventory(archive) == request["archive_identity"],
                        "Source archive changed during reconstruction",
                    )
                    require(
                        all(
                            digest(bounded_bytes(rebuilt / name, MAX_REPORT))
                            == entry["artifacts_sha256"][name]
                            for name in ARTIFACTS
                        ),
                        "Reconstructed report bytes differ",
                    )
                    entry["verification"] = "native_reader_verified"
                    entry["verified_at"] = timestamp()
                    job["verification"] = "native_reader_verified"
                else:
                    entry["verification"] = "verification_failed"
            self.persist(entry)
            result.update(
                observation_entry=self.get(entry["id"]),
                report_completeness=entry["report_completeness"],
            )
        job["result"] = result

    def report_bytes(self, ident, name):
        require(name in ARTIFACTS, "Unknown observation report artifact")
        with self.service.lock:
            entry = self.entries[self.identity(ident, "study")]
            require(
                entry["verification"] not in {"changed_since_verification", "verification_failed"},
                "Saved analysis verification failed or bytes changed; check unchanged evidence",
            )
            path = self.service.safe_path(self.folder(entry) / "archive" / name)
            raw = bounded_bytes(path, MAX_REPORT)
            if digest(raw) != entry["artifacts_sha256"].get(name):
                entry["verification"] = "changed_since_verification"
                self.persist(entry)
                raise ValueError("Saved report bytes changed")
            return raw

    def report(self, ident):
        raw = self.report_bytes(ident, "report.json")
        entry = self.get(ident)
        report = self.validate_report(decode_json(raw))
        return {
            "task": self.task,
            "schema": report["schema"],
            "native_report": report,
            "report_sha256": digest(raw),
            "verification": entry["verification"],
            "report_completeness": entry["report_completeness"],
            "verification_scope": "recorded_owned_snapshot",
            "source_freshness": "report_bytes_checked",
        }
