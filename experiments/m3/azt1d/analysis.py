"""Offline, standard-library reconstruction of sealed AZT1D study artifacts."""

import json
import os
import stat
import tomllib
from collections import Counter
from pathlib import Path, PurePosixPath

from experiments.m1.artifacts import strict_json
from experiments.m3.common import ID, SHA

from .common import (
    METRIC,
    MINUTE,
    PHASES,
    PROTOCOL,
    ROOT,
    SCHEMA,
    digest,
    finite,
    outside_repository,
    require,
    validate_provenance,
)
from .data import eligibility, history, origins, target, training_windows, validate_observations
from .ledger import verify_snapshot
from .metrics import summarize_case, summarize_study


def _json(raw):
    try:
        return strict_json(raw)
    except (ValueError, TypeError, UnicodeError, OverflowError, RecursionError):
        raise ValueError("Invalid saved JSON artifact") from None


def _saved(value):
    # save() preserves mapping order; source snapshots retain that order after parsing.
    return (json.dumps(value, indent=2, allow_nan=False) + "\n").encode()


def _equal(first, second):
    # Python equality would accept True as integer 1 inside nested saved records.
    return json.dumps(first, sort_keys=True, allow_nan=False) == json.dumps(
        second, sort_keys=True, allow_nan=False
    )


def _name(name):
    require(
        isinstance(name, str)
        and name
        and "\\" not in name
        and not PurePosixPath(name).is_absolute()
        and all(part not in ("", ".", "..") for part in name.split("/")),
        "Unsafe artifact path",
    )
    return name


def _hashes(value):
    require(isinstance(value, dict), "Artifact inventory required")
    for name, sha in value.items():
        _name(name)
        require(isinstance(sha, str) and SHA.fullmatch(sha), "Invalid artifact hash")
    return value


class _Snapshot:
    """Open descendants through non-symlink directory descriptors and verify stability."""

    def __init__(self, folder, *, only=None):
        try:
            self.fd = os.open(folder, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        except OSError:
            raise ValueError("Invalid artifact directory") from None
        self.cache, self.signatures, self.only = {}, {}, only
        try:
            self.names = self._names(self.fd) if only is None else {_name(name) for name in only}
        except BaseException:
            os.close(self.fd)
            raise

    def _names(self, directory, prefix=""):
        output = set()
        for name in sorted(os.listdir(directory)):
            item = os.stat(name, dir_fd=directory, follow_symlinks=False)
            relative = prefix + name
            _name(relative)
            require(not stat.S_ISLNK(item.st_mode), "Symlink in saved artifacts")
            if stat.S_ISDIR(item.st_mode):
                child = os.open(
                    name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory
                )
                try:
                    output.update(self._names(child, relative + "/"))
                finally:
                    os.close(child)
            else:
                require(stat.S_ISREG(item.st_mode), "Nonregular saved artifact")
                output.add(relative)
        return output

    def _open(self, name):
        parts = _name(name).split("/")
        directory = os.dup(self.fd)
        try:
            for part in parts[:-1]:
                child = os.open(
                    part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory
                )
                os.close(directory)
                directory = child
            return os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory)
        finally:
            os.close(directory)

    @staticmethod
    def _signature(fd):
        value = os.fstat(fd)
        require(stat.S_ISREG(value.st_mode), "Nonregular saved artifact")
        return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns

    def read(self, name):
        if name not in self.cache:
            try:
                fd = self._open(name)
                try:
                    before = self._signature(fd)
                    chunks = []
                    while chunk := os.read(fd, 64 * 1024):
                        chunks.append(chunk)
                    require(before == self._signature(fd), "Artifact changed while reading")
                    self.cache[name] = b"".join(chunks)
                    self.signatures[name] = before
                finally:
                    os.close(fd)
            except OSError:
                raise ValueError("Missing or invalid saved artifact") from None
        return self.cache[name]

    def parsed(self, name):
        return _json(self.read(name))

    def verify(self):
        if self.only is None:
            require(self._names(self.fd) == self.names, "Artifact inventory changed during reading")
        for name, expected in self.signatures.items():
            try:
                fd = self._open(name)
                try:
                    require(
                        self._signature(fd) == expected, "Artifact changed during reconstruction"
                    )
                finally:
                    os.close(fd)
            except OSError:
                raise ValueError("Artifact changed during reconstruction") from None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        os.close(self.fd)


def _state(snapshot, state_name="state.json", prefix="", *, flat=False):
    state = snapshot.parsed(state_name)
    require(
        isinstance(state, dict)
        and state.get("schema") == SCHEMA
        and state.get("status") in ("started", "completed", "failed", "interrupted"),
        "Invalid saved execution state",
    )
    validate_provenance(state.get("provenance"))
    files = _hashes(state.get("files"))
    require("trace.jsonl" in files, "Missing trace inventory")
    if state["status"] == "completed":
        require({"result.json", "worker.log"} <= files.keys(), "Incomplete completed inventory")
    if state["status"] in ("failed", "interrupted"):
        require(
            isinstance(state.get("error"), dict)
            and isinstance(state["error"].get("type"), str)
            and state["error"]["type"],
            "Missing original failure",
        )
    finite(state.get("elapsed_seconds"), "execution elapsed seconds", 0)
    for name, sha in files.items():
        require(not flat or "/" not in name, "Nested fit artifact is unsupported")
        require(name != "state.json" and not name.endswith(".tmp"), "Invalid sealed inventory")
        require(digest(snapshot.read(prefix + name)) == sha, "Sealed artifact bytes changed")
    actual = {
        name[len(prefix) :]
        for name in snapshot.names
        if name.startswith(prefix) and name != state_name and not name.endswith(".tmp")
    }
    require(actual == set(files), "Uninventoried sealed artifact")
    return state


def verify_inventory(folder):
    """Verify a sealed fit/run folder recursively without following links."""
    with _Snapshot(folder) as snapshot:
        state = _state(snapshot)
        snapshot.verify()
        return state


def _model(model):
    fields = {
        "method",
        "settings",
        "mean",
        "scale",
        "coef",
        "intercept",
        "feature_rank",
        "singular_values",
        "training_counts",
        "packages",
    }
    require(isinstance(model, dict) and set(model) == fields, "Invalid saved model fields")
    require(
        model["method"] == "sklearn-ridge"
        and _equal(model["settings"], {"alpha": 1.0, "fit_intercept": True, "solver": "svd"}),
        "Model settings changed",
    )
    for key in ("mean", "scale", "coef"):
        require(isinstance(model[key], list) and len(model[key]) == 6, "Invalid model dimensions")
        for number in model[key]:
            finite(number, "saved model number")
    require(all(number > 0 for number in model["scale"]), "Invalid model scale")
    finite(model["intercept"], "saved intercept")
    require(type(model["feature_rank"]) is int and 0 <= model["feature_rank"] <= 6, "Invalid rank")
    require(
        isinstance(model["singular_values"], list) and model["singular_values"],
        "Missing rank diagnostic",
    )
    for number in model["singular_values"]:
        finite(number, "singular value", 0)
    counts = model["training_counts"]
    require(
        isinstance(counts, dict)
        and counts
        and all(
            isinstance(pid, str) and type(count) is int and count > 0
            for pid, count in counts.items()
        ),
        "Invalid model training counts",
    )
    lock = tomllib.loads((ROOT / "experiments/m3/runtime/uv.lock").read_text())
    expected = {p["name"]: p["version"] for p in lock["package"] if "registry" in p["source"]}
    require(model["packages"] == expected, "Estimator package identity changed")


def _predict(model, features):
    return finite(
        model["intercept"]
        + sum(
            coefficient * ((value - mean) / scale)
            for coefficient, value, mean, scale in zip(
                model["coef"], features, model["mean"], model["scale"], strict=True
            )
        ),
        "reconstructed forecast",
    )


def _plan(plan, raw):
    require(
        isinstance(plan, dict)
        and plan.get("schema") == SCHEMA
        and plan.get("kind") in ("synthetic", "human"),
        "Invalid saved plan",
    )
    validate_provenance(plan.get("provenance"))
    source = plan.get("registry_source_utf8")
    require(isinstance(source, str), "Original registry bytes required")
    require(
        digest(source.encode("utf-8")) == plan.get("registry_sha256")
        and _equal(_json(source.encode("utf-8")), plan.get("registry")),
        "Registry byte identity differs",
    )
    registry, identity = plan["registry"], plan.get("identity")
    require(
        registry.get("schema") == SCHEMA
        and registry.get("kind") == plan["kind"]
        and isinstance(identity, dict)
        and identity.get("schema") == SCHEMA
        and identity.get("kind") == plan["kind"],
        "Plan identity differs",
    )
    people = registry.get("people")
    require(isinstance(people, list) and people, "Empty planned cohort")
    ids = [person.get("id") for person in people]
    require(
        all(isinstance(pid, str) and ID.fullmatch(pid) for pid in ids), "Invalid participant alias"
    )
    require(len(ids) == len(set(ids)), "Repeated planned participant")
    require(
        isinstance(identity.get("people"), list)
        and [person.get("id") for person in identity["people"]] == ids,
        "Frozen identity roster changed",
    )
    if plan["kind"] == "human":
        require(len(people) == 20 and plan["provenance"]["dirty"] is False, "Invalid human freeze")
        reviews = registry.get("reviews", {})
        require(
            all(
                reviews.get(key) is True
                for key in (
                    "authorized_fitting",
                    "authorized_evaluation",
                    "overlap_reviewed",
                    "prior_access_disclosed",
                )
            )
            and isinstance(reviews.get("reference"), str)
            and reviews["reference"].strip(),
            "Human study review missing",
        )
    require(
        isinstance(registry.get("ledger"), str) and Path(registry["ledger"]).is_absolute(),
        "Invalid ledger identity",
    )
    return digest(raw)


def _conversion(value, person, phase, kind, frozen_identity, expected_sha=None):
    require(
        isinstance(value, dict)
        and set(value) == {"intake", "conversion", "observations", "status"},
        "Incomplete normalized source snapshot",
    )
    intake, receipt, document, state = (
        value[key] for key in ("intake", "conversion", "observations", "status")
    )
    require(
        all(isinstance(item, dict) for item in (intake, receipt, document, state)),
        "Invalid normalized snapshot",
    )
    for item in (intake, receipt):
        require(
            item.get("schema") == SCHEMA
            and item.get("person") == person
            and item.get("phase") == phase
            and item.get("kind") == kind
            and item.get("source_sha256") == frozen_identity["source_sha256"],
            "Normalized source identity changed",
        )
    require(
        state.get("schema") == SCHEMA
        and state.get("kind") == kind
        and state.get("status") == "completed",
        "Incomplete source conversion",
    )
    require(
        digest(_saved(intake)) == receipt.get("intake_sha256")
        and digest(_saved(document)) == receipt.get("observations_sha256"),
        "Normalized snapshot bytes differ",
    )
    receipt_sha = digest(_saved(receipt))
    if expected_sha is not None:
        require(receipt_sha == expected_sha, "Consumed conversion identity differs")
    validate_provenance(receipt.get("provenance"))
    require(receipt.get("model_fit_or_evaluation") is False, "Invalid conversion stage")
    bounds = frozen_identity["phases"][phase]
    require(
        all(
            type(intake.get(key)) is int and intake[key] == bounds[key]
            for key in ("start_us", "end_us", "row_start", "row_stop")
        ),
        "Frozen phase bounds changed",
    )
    require(
        intake["row_stop"] > intake["row_start"] >= 1
        and _equal(intake.get("policy"), frozen_identity["policy"])
        and _equal(intake.get("allocation_reference"), frozen_identity.get("allocation")),
        "Frozen source convention changed",
    )
    rows = validate_observations(document, person, intake["start_us"], intake["end_us"])
    require(
        [index for row in rows.values() for index in row["source_rows"]]
        == list(range(intake["row_start"], intake["row_stop"]))
        and receipt.get("source_rows") == intake["row_stop"] - intake["row_start"]
        and receipt.get("registered_origins") == len(rows)
        and receipt.get("statuses") == dict(Counter(row["status"] for row in rows.values())),
        "Source row accounting changed",
    )
    if kind == "human":
        reviews = intake.get("reviews", {})
        require(
            all(
                reviews.get(key) is True
                for key in (
                    "authorized_processing",
                    "derived_retention",
                    "release_reviewed",
                    "units_reviewed",
                    "status_policy_reviewed",
                    "availability_reviewed",
                    "clock_reviewed",
                )
            ),
            "Human intake review missing",
        )
    return intake, rows, receipt_sha


def _expected(rows, person, phase, bounds, model, origin):
    features, reason = history(rows, origin, bounds[0], phase)
    point = rows[origin]
    if point["status"] != "measured" or point["available_us"] > origin:
        stratum = "unknown"
    else:
        stratum = "low" if point["value"] < 70 else "high" if point["value"] > 180 else "in_range"
    return {
        "person": person,
        "phase": phase,
        "origin_us": origin,
        "history_rows": [rows.get(origin - offset * MINUTE) for offset in (25, 20, 15, 10, 5, 0)],
        "features": features,
        "forecasts": None
        if features is None
        else {"ridge": _predict(model, features), "persistence": features[-1]},
        "target": target(rows, origin, bounds[1]),
        "reason": reason,
        "origin_stratum": stratum,
    }


def _trace(raw, expected, *, completed):
    rows, fragment = [], 0
    for line in raw.splitlines(keepends=True):
        if not line.endswith(b"\n"):
            require(not completed, "Truncated completed forecast trace")
            fragment = len(line)
            break
        require(len(rows) < len(expected), "Unexpected forecast origin")
        row = _json(line)
        require(
            _equal(row, expected[len(rows)]), "Forecast differs from frozen causal inputs or model"
        )
        rows.append(row)
    require(not completed or len(rows) == len(expected), "Incomplete completed forecast schedule")
    return rows, fragment


def _fit(snapshot, plan, plan_sha, prefix="fit-"):
    state_name = prefix + "state.json"
    state = _state(snapshot, state_name, prefix, flat=True)
    require(state["status"] == "completed", "Learned model fit did not complete")
    frozen = snapshot.parsed(prefix + "freeze.json")
    validate_provenance(frozen.get("provenance"))
    require(
        frozen.get("schema") == SCHEMA
        and frozen.get("stage") == "learned"
        and frozen.get("plan_sha256") == plan_sha,
        "Learned freeze differs from plan",
    )
    for name, key in (
        ("model.json", "model_sha256"),
        ("trace.jsonl", "validation_sha256"),
        ("result.json", "result_sha256"),
        ("inputs.json", "inputs_sha256"),
    ):
        require(
            digest(snapshot.read(prefix + name)) == frozen.get(key),
            "Learned artifact bytes changed",
        )
    model, result, inputs = (
        snapshot.parsed(prefix + name + ".json") for name in ("model", "result", "inputs")
    )
    _model(model)
    require(
        result.get("schema") == SCHEMA
        and result.get("status") == "completed"
        and result.get("plan_sha256") == plan_sha,
        "Fit result identity changed",
    )
    people = plan["registry"]["people"]
    require(
        isinstance(inputs, dict) and set(inputs) == {p["id"] for p in people},
        "Fit input roster changed",
    )
    counts, validation, expected_validation, conventions = {}, {}, [], {}
    expected_identity = []
    source_hashes = set()
    for person, identity in zip(people, plan["identity"]["people"], strict=True):
        pid = person["id"]
        require(
            set(inputs[pid]) == {"development", "validation"},
            "Fit includes missing or forbidden phase",
        )
        require(
            isinstance(identity.get("source_sha256"), str)
            and SHA.fullmatch(identity["source_sha256"])
            and identity["source_sha256"] not in source_hashes,
            "Repeated or invalid native source",
        )
        source_hashes.add(identity["source_sha256"])
        require(set(identity.get("phases", {})) == set(PHASES), "Incomplete frozen phases")
        requests, phase_rows = {}, {}
        for phase in PHASES[:2]:
            intake, rows, _ = _conversion(
                inputs[pid][phase], pid, phase, plan["kind"], identity, person[phase]["sha256"]
            )
            requests[phase], phase_rows[phase] = intake, rows
        first, middle, last = (identity["phases"][phase] for phase in PHASES)
        require(
            all(
                isinstance(block, dict)
                and set(block) == {"start_us", "end_us", "row_start", "row_stop"}
                and all(type(v) is int and v >= 0 for v in block.values())
                for block in (first, middle, last)
            ),
            "Invalid frozen phase boundaries",
        )
        require(
            first["start_us"] == 0
            and first["end_us"] == middle["start_us"]
            and middle["end_us"] == last["start_us"]
            and first["end_us"] == (3 * last["end_us"] + 4) // 5
            and middle["end_us"] == (4 * last["end_us"] + 4) // 5,
            "Frozen elapsed split differs",
        )
        require(
            first["row_start"] == 1
            and first["row_stop"] == middle["row_start"]
            and middle["row_stop"] == last["row_start"]
            and last["row_stop"] > last["row_start"],
            "Frozen native slices differ",
        )
        require(
            requests["development"]["origin_local"] == requests["validation"]["origin_local"],
            "Cross-phase origin changed",
        )
        require(
            origins(phase_rows["development"])[0] == 0,
            "Development does not begin at native origin",
        )
        evaluation = person["evaluation"]
        schedule = evaluation["origins_us"]
        require(
            isinstance(schedule, list)
            and schedule
            and all(type(t) is int and last["start_us"] <= t < last["end_us"] for t in schedule)
            and schedule == sorted(set(schedule)),
            "Invalid planned evaluation schedule",
        )
        require(
            schedule[-1] + 5 * MINUTE == last["end_us"], "Administrative final boundary changed"
        )
        expected_identity.append(
            {
                "id": pid,
                "source_sha256": requests["development"]["source_sha256"],
                "phases": {
                    phase: {
                        key: requests[phase][key]
                        for key in ("start_us", "end_us", "row_start", "row_stop")
                    }
                    if phase in requests
                    else last
                    for phase in PHASES
                },
                "policy": requests["development"]["policy"],
                "allocation": requests["development"].get("allocation_reference"),
                "evaluation_origins_us": schedule,
            }
        )
        windows = training_windows(phase_rows["development"], first["start_us"], first["end_us"])
        window_origins = [window[0] for window in windows]
        counts[pid] = {
            "eligible": eligibility(window_origins),
            "origins_us": window_origins,
            "registered_origins_us": origins(phase_rows["development"]),
        }
        bounds = [middle["start_us"], middle["end_us"]]
        val_expected = [
            _expected(phase_rows["validation"], pid, "validation", bounds, model, origin)
            for origin in origins(phase_rows["validation"])
        ]
        validation[pid] = (origins(phase_rows["validation"]), val_expected, bounds)
        expected_validation.extend(val_expected)
        conventions[pid] = requests["development"]
    require(
        _equal(
            plan["identity"], {"schema": SCHEMA, "kind": plan["kind"], "people": expected_identity}
        ),
        "Frozen source identities changed",
    )
    require(
        _equal(result.get("development"), counts)
        and _equal(snapshot.parsed(prefix + "development.json"), counts),
        "Development counts or eligibility changed",
    )
    training = {pid: len(value["origins_us"]) for pid, value in counts.items() if value["eligible"]}
    require(
        training
        and _equal(model["training_counts"], training)
        and result.get("training_people") == list(training),
        "Training cohort differs from development eligibility",
    )
    schedules = {pid: value[0] for pid, value in validation.items()}
    require(
        _equal(result.get("validation_origins"), schedules)
        and _equal(snapshot.parsed(prefix + "validation-schedule.json"), schedules),
        "Validation schedule changed",
    )
    traces, fragment = _trace(
        snapshot.read(prefix + "trace.jsonl"), expected_validation, completed=True
    )
    require(not fragment, "Partial validation trace in completed fit")
    diagnostics = {}
    offset = 0
    for pid, (schedule, _, bounds) in validation.items():
        subset = traces[offset : offset + len(schedule)]
        diagnostics[pid] = summarize_case(
            schedule,
            subset,
            development_eligible=counts[pid]["eligible"],
            execution_status="completed",
            bounds_us=bounds,
        )
        offset += len(schedule)
    return frozen, model, counts, diagnostics, conventions


def verify_learned(plan_path, fit_path):
    """Semantic preflight before evaluation access; only saved plan/fit files are opened."""
    plan_path = Path(plan_path)
    with (
        _Snapshot(plan_path.parent, only={plan_path.name}) as source,
        _Snapshot(fit_path) as snapshot,
    ):
        raw = source.read(plan_path.name)
        plan = _json(raw)
        plan_sha = _plan(plan, raw)
        if plan["kind"] == "human":
            outside_repository(plan_path, fit_path)
        frozen, _, _, _, _ = _fit(snapshot, plan, plan_sha, prefix="")
        source.verify()
        snapshot.verify()
        return plan, frozen, digest(snapshot.read("freeze.json"))


def _access(snapshot, name, ledger, plan, freeze_sha, person, event):
    evidence = snapshot.parsed(name)
    context = verify_snapshot(ledger, plan["identity"], evidence)
    require(
        evidence["event"] == event
        and evidence["person"] == person
        and evidence["phase"] == "evaluation"
        and evidence["freeze_sha256"] == freeze_sha
        and context["kind"] == plan["kind"],
        "Evaluation access evidence differs",
    )
    return evidence


def reconstruct(study_folder):
    """Rebuild a private report without original sources, live ledger or model packages."""
    with _Snapshot(study_folder) as snapshot:
        inventory = _hashes(snapshot.parsed("inventory.json"))
        require(
            set(inventory) == snapshot.names - {"inventory.json", "report.json"},
            "Study inventory is incomplete",
        )
        for name, sha in inventory.items():
            require(digest(snapshot.read(name)) == sha, "Study artifact bytes changed")
        raw_plan = snapshot.read("plan.json")
        plan = _json(raw_plan)
        plan_sha = _plan(plan, raw_plan)
        if plan["kind"] == "human":
            outside_repository(study_folder)
        study = snapshot.parsed("study.json")
        validate_provenance(study.get("provenance"))
        require(
            study.get("schema") == SCHEMA
            and study.get("kind") == plan["kind"]
            and study.get("status")
            in ("started", "completed", "finished_with_failures", "failed", "interrupted"),
            "Invalid study lifecycle",
        )
        frozen, model, development, validation, conventions = _fit(snapshot, plan, plan_sha)
        freeze_sha = digest(snapshot.read("fit-freeze.json"))
        require(study.get("freeze_sha256") == freeze_sha, "Study learned freeze differs")
        ledger = snapshot.read("ledger.jsonl")
        context = verify_snapshot(ledger, plan["identity"], frozen["ledger_anchor"])
        require(
            context["kind"] == plan["kind"]
            and context["prior_access"] == plan["registry"]["prior_access"]
            and frozen["ledger_anchor"]["event"] == "created"
            and frozen["ledger_anchor"]["sequence"] == 0,
            "Study access history differs",
        )
        people = plan["registry"]["people"]
        cases = study.get("cases")
        require(
            isinstance(cases, list)
            and [case.get("id") for case in cases] == [p["id"] for p in people],
            "Study case roster or order differs",
        )
        summaries = {}
        for person, identity, case in zip(people, plan["identity"]["people"], cases, strict=True):
            pid, status = person["id"], case.get("status")
            planned = person["evaluation"]["origins_us"]
            require(
                case.get("origins_us") == planned
                and status in ("not_attempted", "started", "completed", "failed", "interrupted"),
                "Case schedule or lifecycle changed",
            )
            prefix = pid + "/"
            names = {name for name in snapshot.names if name.startswith(prefix)}
            if status == "not_attempted":
                require(not names, "Unattempted case has saved execution artifacts")
            if status in ("failed", "interrupted"):
                require(
                    isinstance(case.get("error"), dict)
                    and isinstance(case["error"].get("type"), str),
                    "Case failure not retained",
                )
            block = identity["phases"]["evaluation"]
            bounds = [block["start_us"], block["end_us"]]
            traces, fragment, access = [], 0, {}
            for filename, event in (
                ("normalization-access.json", "before_normalization"),
                ("execution-access.json", "before_execution"),
            ):
                if prefix + filename in names:
                    access[event] = _access(
                        snapshot, prefix + filename, ledger, plan, freeze_sha, pid, event
                    )
            if "before_execution" in access:
                require(
                    "before_normalization" in access
                    and access["before_normalization"]["sequence"]
                    < access["before_execution"]["sequence"],
                    "Execution precedes normalization access record",
                )
            run_state_name = prefix + "run/state.json"
            if run_state_name in names:
                require(
                    set(access) == {"before_normalization", "before_execution"},
                    "Missing evaluation access receipts",
                )
                normalized = {
                    name: snapshot.parsed(prefix + "conversion/" + name + ".json")
                    for name in ("intake", "conversion", "observations", "status")
                }
                intake, rows, conversion_sha = _conversion(
                    normalized, pid, "evaluation", plan["kind"], identity
                )
                require(
                    intake["origin_local"] == conventions[pid]["origin_local"]
                    and origins(rows) == planned,
                    "Evaluation source clock or registered schedule changed",
                )
                pointer = person["evaluation"]["intake_reference"]
                require(
                    normalized["conversion"].get("submitted_intake_sha256") == pointer["sha256"],
                    "Consumed evaluation request differs",
                )
                if plan["kind"] == "human":
                    require(
                        _equal(
                            normalized["conversion"].get("evaluation_access"),
                            access["before_normalization"],
                        ),
                        "Normalization access receipt differs",
                    )
                run_state = _state(snapshot, run_state_name, prefix + "run/")
                require(run_state["status"] == status, "Case state disagrees with study")
                expected = [
                    _expected(rows, pid, "evaluation", bounds, model, origin) for origin in planned
                ]
                traces, fragment = _trace(
                    snapshot.read(prefix + "run/trace.jsonl"),
                    expected,
                    completed=status == "completed",
                )
                claim = prefix + "run/worker-access.json"
                if claim in names:
                    require(
                        _equal(
                            snapshot.parsed(claim),
                            {"execution_event_sha256": access["before_execution"]["event_sha256"]},
                        ),
                        "Worker access claim differs",
                    )
                else:
                    require(not traces and status != "completed", "Missing worker access claim")
                if prefix + "run/schedule.json" in names:
                    require(
                        _equal(
                            snapshot.parsed(prefix + "run/schedule.json"),
                            {
                                "person": pid,
                                "origins_us": planned,
                                "conversion_sha256": conversion_sha,
                            },
                        ),
                        "Consumed evaluation schedule differs",
                    )
                if status == "completed":
                    require(prefix + "run/schedule.json" in names, "Missing completed schedule")
                    require(
                        _equal(
                            snapshot.parsed(prefix + "run/result.json"),
                            {
                                "schema": SCHEMA,
                                "status": "completed",
                                "person": pid,
                                "rows": len(planned),
                                "conversion_sha256": conversion_sha,
                            },
                        ),
                        "False case completion",
                    )
            else:
                require(status != "completed", "Completed case has no sealed execution")
                require(
                    not any(name.startswith(prefix + "run/") for name in names),
                    "Unsealed execution artifacts",
                )
            result = summarize_case(
                planned,
                traces,
                development_eligible=development[pid]["eligible"],
                execution_status=status,
                bounds_us=bounds,
            )
            result.update(
                partial_fragment=bool(fragment), partial_fragment_bytes=fragment, access=access
            )
            summaries[pid] = result
        statuses = [case["status"] for case in cases]
        if study["status"] == "completed":
            require(all(status == "completed" for status in statuses), "False study completion")
        if study["status"] == "finished_with_failures":
            require(
                all(status in ("completed", "failed", "interrupted") for status in statuses)
                and any(status != "completed" for status in statuses),
                "False finished-study failure accounting",
            )
        report = {
            "schema": "opent1d.m3.azt1d.report/1",
            "protocol": PROTOCOL,
            "metric": METRIC,
            "kind": plan["kind"],
            "study_status": study["status"],
            "evidence_scope": "synthetic software mechanics only"
            if plan["kind"] == "synthetic"
            else "retrospective CGM forecasts under observed treatment",
            "evaluation": summarize_study(summaries),
            "validation_diagnostic": validation,
            "evaluation_access": {
                "prior_access": context["prior_access"],
                "snapshot_event_count": context["event_count"],
                "snapshot_head_sha256": context["head_sha256"],
                "live_ledger_head_verified": False,
            },
            "artifacts_sha256": {
                "inventory.json": digest(snapshot.read("inventory.json")),
                "plan.json": plan_sha,
                "learned_freeze": freeze_sha,
                "ledger.jsonl": digest(ledger),
            },
        }
        snapshot.verify()
        return report
