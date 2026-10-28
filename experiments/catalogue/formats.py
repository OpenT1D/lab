"""Explicit metadata adapters; archived Python is always opaque bytes."""

import math
from pathlib import PurePosixPath

from .storage import ID, SHA, digest, encoded, read, require

TASKS = (
    "p1-controller",
    "m3-forecast",
    "m3-compare",
    "m4-secretion",
    "m4-compare",
    "m4-study",
    "m4-study-secure",
    "m5-prognosis",
    "mmtt-sensitivity",
    "mmtt-sampling",
)


def normalized(value, location=()):
    """Paths select opaque bytes; their frozen identities carry scientific meaning."""
    if isinstance(value, list):
        return [normalized(item, (*location, "[]")) for item in value]
    if isinstance(value, dict):
        omitted = set()
        if not location:
            omitted = {"model", "declaration", "predictor"}
        elif location in {("sources", "[]"), ("candidates", "[]")}:
            omitted = {"model", "declaration"}
        elif location[-1] in {"source", "settings", "input"}:
            omitted = {"file"}
        return {
            key: normalized(item, (*location, key))
            for key, item in value.items()
            if key not in omitted
        }
    return value


def model(value):
    require(isinstance(value, dict), "Missing model declaration")
    identity = value.get("model_id", value.get("id", value.get("name")))
    source_record = value.get("source", {})
    source = value.get("source_sha256")
    if source is None and isinstance(source_record, dict):
        source = source_record.get("sha256")
    require(isinstance(identity, str) and identity, "Missing declared model identity")
    require(isinstance(source, str) and len(source) == 64, "Missing declared source identity")
    return {"id": identity, "source_sha256": source, "declaration": normalized(value)}


def scientific_files(files):
    def snapshot(name):
        path = PurePosixPath(name)
        # The component immediately after children is a roster ID, which may itself
        # be 'logs'. Every other logs directory is diagnostic storage.
        logged = any(
            part == "logs" and not (index == 1 and path.parts[0] == "children")
            for index, part in enumerate(path.parts[:-1])
        )
        return (
            not logged
            and path.suffix != ".log"
            and (
                path.name.startswith("source-")
                or name.startswith("sources/")
                or path.name
                in {"uv.lock", "pyproject.toml", "protocol.json", "protocol-settings.json"}
            )
        )

    return {name: value["sha256"] for name, value in files.items() if snapshot(name)}


def _p1(path, files):
    marker, study = read(path / "workflow.json"), read(path / "study.json")
    require(marker["schema"] == "opent1d.p1-external-workflow/1", "Wrong P1 marker schema")
    require(study["schema"] == marker["schema"], "Wrong P1 schedule schema")
    config = {"profile": marker["profile"], "seed": marker["seed"], "cases": study["cases"]}
    conditions = {**config, "implementation": marker["implementation_sha256"]}
    return marker["schema"], [model(marker["controller"])], config, conditions, study["status"]


def _m3(path, task):
    plan = read(path / "plan.json")
    expected = "opent1d.m3.researcher/1" if task == "m3-forecast" else "opent1d.m3.comparison/1"
    require(plan["schema"] == expected, "Wrong M3 plan schema")
    config = plan["config"]
    require(config["schema"] == expected, "Wrong M3 configuration schema")
    if task == "m3-forecast":
        models = [model(plan["predictor"])]
    else:
        models = [
            {"roster_id": item["id"], **model(plan["candidates"][item["id"]]["declaration"])}
            for item in config["candidates"]
        ]
    conditions = {
        "config": normalized(config),
        "timeout_seconds": plan.get("timeout_seconds", config.get("timeout_seconds")),
        "implementation": plan["provenance"]["sources"],
        "python": plan["provenance"]["python"],
    }
    report = read(path / "report.json")
    require(report["schema"] == expected, "Wrong M3 report schema")
    complete = (
        report["evaluation"]["complete_cohort"]
        if task == "m3-forecast"
        else report["common"]["complete_cohort"]
    )
    return expected, models, config, conditions, "complete" if complete is True else "incomplete"


def _m4(path, task):
    report = read(path / "report.json")
    if task == "m4-secretion":
        require(report["schema"] == "m4-researcher-workflow/1", "Wrong M4 report schema")
        config, protocol = read(path / "config.json"), read(path / "protocol.json")
        models = [model(read(path / "model.json"))]
        controls = {
            name: values
            for name, values in report.get("trajectories", {}).items()
            if name.endswith(("--host_constant_basal", "--bc008_reference"))
        }
        conditions = {"protocol": protocol, "config": normalized(config), "controls": controls}
    else:
        plan = read(path / "plan.json")
        expected = {
            "m4-compare": "m4-source-comparison/1",
            "m4-study": "m4-initial-load-report/1",
            "m4-study-secure": "m4-secure-study-report/1",
        }[task]
        require(report["schema"] == expected, "Wrong M4 comparison/study report schema")
        config = plan["config"] if task == "m4-compare" else plan["configuration"]
        protocol = plan["protocol"]
        source_names(config)
        models = [
            {"roster_id": item["id"], **model(read(path / "frozen" / item["id"] / "model.json"))}
            for item in config["sources"]
        ]
        conditions = {
            "protocol": protocol,
            "config": normalized(config),
            "controls": report.get("common_controls", {}),
        }
        # Attempt statuses are outcomes, while exact saved control curves are conditions.
        controls = conditions["controls"]
        require(isinstance(controls, dict), "Missing shared control conditions")
        if task in ("m4-study", "m4-study-secure"):
            conditions["controls"] = study_controls(report, config)
        else:
            conditions["controls"] = controls.get("trajectories", {})
        require(
            report["passed"] is not True or bool(conditions["controls"]),
            "Accepted study lacks explicit complete shared control conditions",
        )
    if report["passed"] is True and task not in ("m4-study", "m4-study-secure"):
        expected = {
            f"{scenario}--{mode}"
            for scenario in ("fasting", "gastric_load_30g")
            for mode in ("host_constant_basal", "bc008_reference")
        }
        saved = conditions["controls"]
        require(set(saved) == expected, "Incomplete accepted shared control roster")
        for values in saved.values():
            control_series(
                values, ("times_min", "glucose_mg_dl", "insulin_pmol_l", "cpeptide_pmol_l")
            )
    return (
        report["protocol"],
        models,
        config,
        conditions,
        "complete" if report["passed"] is True else "failed",
    )


def control_series(value, names):
    require(
        isinstance(value, dict) and set(value) == set(names), "Missing control signal or unit key"
    )
    for name in names:
        numbers = value[name]
        require(
            isinstance(numbers, list)
            and len(numbers) == 961
            and all(type(number) in (int, float) and math.isfinite(number) for number in numbers),
            "Incomplete or nonfinite shared control grid/signal",
        )
    require(value[names[0]] == [i / 4 for i in range(961)], "Shared control grid differs")


def study_controls(report, config):
    if report["passed"] is not True:
        return {"available": False, "reason": "whole study failed; controls diagnostic only"}
    require(report["common_controls"]["passed"] is True, "Shared study controls did not pass")
    saved = report["common_controls"].get("trajectories")
    require(isinstance(saved, dict) and bool(saved), "Missing explicit shared study trajectories")
    anchor = None
    for item in config["sources"]:
        source = report["sources"][item["id"]]
        require(source["accepted"] is True, "Accepted study has an unaccepted source")
        curves = {}
        for scenario in config["scenarios"]:
            for mode in ("host_constant_basal", "bc008_reference"):
                curve = source["curves"][scenario][mode]
                control_series(curve, ("times", "glucose", "insulin", "cpeptide"))
                curves[scenario + "--" + mode] = curve
        if anchor is None:
            anchor = curves
        require(curves == anchor, "Source shared control trajectories disagree")
    require(bool(anchor), "Missing accepted study control roster")
    aliases = {
        "times": "times_min",
        "glucose": "glucose_mg_dl",
        "insulin": "insulin_pmol_l",
        "cpeptide": "cpeptide_pmol_l",
    }
    normalized_curves = {
        case: {aliases[name]: value for name, value in curve.items()}
        for case, curve in anchor.items()
    }
    require(saved == normalized_curves, "Saved shared trajectories differ from source controls")
    return {"available": True, "trajectories": saved}


def _m5(path):
    protocol, declaration = read(path / "protocol.json"), read(path / "model.json")
    require(protocol["schema"] == "m5-researcher-workflow/1", "Wrong M5 protocol schema")
    report = read(path / "report.json")
    require(report["schema"] == protocol["schema"], "Wrong M5 report schema")
    config = {"protocol": protocol, "fixture": read(path / "fixture.json")}
    conditions = {
        **config,
        "baseline": read(path / "baseline.json"),
        "runtime": read(path / "provenance.json")["host_runtime"],
    }
    return protocol["schema"], [model(declaration)], config, conditions, report["comparison_status"]


def numerical_runtime(value):
    require(
        isinstance(value, dict)
        and set(value) == {"python", "numpy", "scipy"}
        and all(isinstance(item, str) and item for item in value.values()),
        "Missing exact numerical runtime versions",
    )
    return value


def source_names(config):
    names = [item["id"] for item in config["sources"]]
    require(
        all(isinstance(name, str) and ID.fullmatch(name) for name in names)
        and len(set(names)) == len(names),
        "Unsafe or duplicate saved source roster",
    )
    return names


def native_conditions(value):
    require(
        isinstance(value, dict) and set(value) == {"runtime", "identity", "parameters"},
        "Missing complete native conditions",
    )
    identity = value["identity"]
    require(
        isinstance(identity, dict)
        and set(identity)
        == {
            "body_weight_kg",
            "kinetic_parameters",
            "package_version",
            "parameter_file",
            "parameter_file_sha256",
            "patient_file",
            "patient_file_sha256",
            "profile",
            "upstream_revision",
        },
        "Missing or unsupported native identity fields",
    )
    for name in ("parameter_file", "patient_file"):
        require(
            isinstance(identity[name], str) and identity[name], "Missing native location record"
        )
        require(
            isinstance(identity[name + "_sha256"], str)
            and SHA.fullmatch(identity[name + "_sha256"]),
            "Missing native source/parameter digest",
        )
    require(
        isinstance(value["parameters"], dict) and bool(value["parameters"]),
        "Missing full native parameter table",
    )
    return {
        "runtime": numerical_runtime(value["runtime"]),
        "identity": {
            key: item
            for key, item in identity.items()
            if key not in {"parameter_file", "patient_file"}
        },
        "parameters": value["parameters"],
    }


def worker_conditions(path, schema, native=None):
    worker = read(path)
    require(worker["schema"] == schema and worker["status"] == "completed", "Worker incomplete")
    runtime = numerical_runtime(worker["runtime"])
    if native is not None:
        identity = worker["native_identity"]
        require(
            native_conditions(
                {"runtime": runtime, "identity": identity, "parameters": native["parameters"]}
            )
            == native,
            "Worker native runtime or scientific identity differs",
        )
    return runtime


def secretion_conditions(path):
    native = native_conditions(read(path / "causal/reference/native.json"))
    require(
        native_conditions(read(path / "reference/native.json")) == native,
        "Saved secretion reference/native conditions differ",
    )
    return {
        "parent_python": read(path / "causal/manifest.json")["parent_python"],
        "native": native,
        "workers": {
            label: {
                "native": worker_conditions(
                    path / "causal" / label / "worker.json", "m4-causal-worker/1", native
                ),
                "observer": worker_conditions(
                    path / "observations" / label / "worker.json", "m4-researcher-observer/1"
                ),
            }
            for label in ("primary", "repeat")
        },
    }


def orchestration(provenance):
    value = {key: provenance.get(key) for key in ("python", "platform")}
    require(
        all(isinstance(item, str) and item for item in value.values()),
        "Saved orchestration Python/platform unavailable",
    )
    return value


def m4_runtime_conditions(path, task, config):
    if task == "m4-secretion":
        return {"execution": secretion_conditions(path), "platform": None}
    plan = read(path / "plan.json")
    value = {"orchestration": orchestration(plan["provenance"])}
    if task == "m4-compare":
        value["reference"] = native_conditions(read(path / "reference/native.json"))
        value["sources"] = {
            item["id"]: secretion_conditions(path / "children" / item["id"])
            for item in config["sources"]
        }
        return value
    value["historical_reference"] = native_conditions(read(path / "historical/native.json"))
    value["reference"], value["sources"] = {}, {}
    folders = [("reference", path / "reference", "reference")]
    folders.extend(
        (item["id"], path / "children" / item["id"], "source") for item in config["sources"]
    )
    for name, folder, kind in folders:
        labels = {}
        for label in ("primary", "repeat"):
            native = native_conditions(read(folder / label / "native.json"))
            labels[label] = {
                "native": native,
                "worker_runtime": worker_conditions(
                    folder / label / "worker.json", "m4-initial-load-worker/1", native
                ),
            }
            if kind == "source":
                labels[label]["observer_runtime"] = worker_conditions(
                    folder / "observations" / label / "worker.json", "m4-initial-load-observer/1"
                )
        if kind == "reference":
            value["reference"] = labels
        else:
            value["sources"][name] = labels
    return value


def _observations(path, task="mmtt-sensitivity"):
    execution = read(path / "execution.json")
    report = read(path / "report.json")
    require(
        report["schema"]
        == (
            "opent1d.mmtt-sampling/1"
            if task == "mmtt-sampling"
            else "opent1d.observation-analysis/1"
        )
        and report["kind"] == "synthetic"
        and report["human_evaluation"] is False,
        "Unsupported observation analysis report",
    )
    plan = report["plan"]
    identity = (
        execution["implementation_sha256"]["experiments/observation_analysis/estimator.py"]
        if task == "mmtt-sampling"
        else digest(encoded(execution["implementation_sha256"]))
    )
    declared = {
        "id": "polonsky1986-fixed-kinetic-linear-concentration-exact/1",
        "source_sha256": identity,
        "reference": "Polonsky 1986; BC-003; OT-053 narrow scope",
    }
    config = {"plan": plan}
    conditions = {"plan": plan, "runtime": execution["runtime"]}
    return (
        "OT-055-synthetic-sampling/1" if task == "mmtt-sampling" else "OT-054-synthetic/1",
        [model(declared)],
        config,
        conditions,
        "complete" if report["coverage"]["complete_cohort"] is True else "incomplete",
    )


def repeat_conditions(path, task, config, status):
    """Missing historical provenance permits reading, never repeat eligibility."""
    complete = True
    reasons = []
    try:
        if task.startswith("m4-"):
            runtime = m4_runtime_conditions(path, task, config)
            if task == "m4-secretion":
                complete = False
                reasons.append("legacy secretion archive does not record execution platform")
        elif task.startswith("m3-"):
            runtime = orchestration(read(path / "plan.json")["provenance"])
        elif task == "p1-controller":
            runtime = {}
            fields = {
                "packages",
                "upstream_files_sha256",
                "upstream_revision",
                "numpy_disabled_features",
                "numpy_cpu_features",
                "effective_settings",
            }
            for case in config["cases"]:
                require(case in {"A", "B", "C", "D"}, "Unsafe controller case identifier")
                saved = read(path / case / "manifest.json")
                require(fields <= set(saved), "Missing saved controller runtime/native conditions")
                runtime[case] = {**orchestration(saved), **{key: saved[key] for key in fields}}
        elif task in ("mmtt-sensitivity", "mmtt-sampling"):
            runtime = read(path / "execution.json")["runtime"]
            if config["plan"] is None:
                complete = False
                reasons.append("analysis plan unavailable; scientific repeat conditions unknown")
        else:
            saved = read(path / "provenance.json")
            runtime = {"host_runtime": saved["host_runtime"], "platform": saved.get("platform")}
            if not isinstance(runtime["platform"], str) or not runtime["platform"]:
                complete = False
                reasons.append("legacy prognostic archive does not record execution platform")
    except (OSError, ValueError, KeyError, TypeError) as error:
        if status == "complete" and task in {"m4-compare", "m4-study", "m4-study-secure"}:
            raise
        runtime = {"available": False}
        complete = False
        reasons.append("saved runtime/native conditions unavailable: " + type(error).__name__)
    return runtime, {"complete": complete, "reasons": reasons}


def metadata(path, task, files):
    require(task in TASKS, "Unsupported catalogue task")
    if task == "p1-controller":
        protocol, models, config, conditions, status = _p1(path, files)
    elif task.startswith("m3-"):
        protocol, models, config, conditions, status = _m3(path, task)
    elif task.startswith("m4-"):
        protocol, models, config, conditions, status = _m4(path, task)
    elif task in ("mmtt-sensitivity", "mmtt-sampling"):
        protocol, models, config, conditions, status = _observations(path, task)
    else:
        protocol, models, config, conditions, status = _m5(path)
    runtime, coverage = repeat_conditions(path, task, config, status)
    return {
        "protocol": protocol,
        "models": models,
        "configuration_sha256": digest(encoded(normalized(config))),
        "conditions_sha256": digest(
            encoded(
                {
                    "conditions": conditions,
                    "runtime": runtime,
                    "models": models,
                    "science": scientific_files(files),
                }
            )
        ),
        "repeat_condition_coverage": coverage,
        "recorded_status": status,
        # Preserve the native outcome for presentation; catalogue acceptance and
        # scientific condition identities retain their established meaning.
        **(
            {"native_report_status": read(path / "report.json").get("status")}
            if task == "m4-study-secure"
            else {}
        ),
    }


def reconstruction_args(task, archive, output, allow_failed=False):
    modules = {
        "p1-controller": "experiments.p1_external",
        "m3-forecast": "experiments.m3.researcher",
        "m3-compare": "experiments.m3.comparison",
        "m4-secretion": "experiments.m4.researcher_workflow.report",
        "m4-compare": "experiments.m4.comparison",
        "m4-study": "experiments.m4.initial_load",
        "m4-study-secure": "experiments.m4.secure_study",
        "m5-prognosis": "experiments.m5.researcher_workflow.run",
        "mmtt-sensitivity": "experiments.observation_analysis",
        "mmtt-sampling": "experiments.mmtt_sampling",
    }
    require(task in modules, "Unregistered native reader")
    args = ["-m", modules[task]]
    if task in ("p1-controller", "m3-forecast", "m3-compare"):
        args.extend(["report" if task == "m3-forecast" else "reconstruct", "--study", str(archive)])
    elif task in ("m4-compare", "m4-study", "m4-study-secure", "mmtt-sensitivity", "mmtt-sampling"):
        args.extend(["reconstruct", "--archive", str(archive)])
    elif task == "m4-secretion":
        args.append(str(archive))
    else:
        args.extend(["reconstruct", str(archive)])
    if task != "m5-prognosis":
        args.extend(["--output", str(output)])
    if (task.startswith("m4-") or task in ("mmtt-sensitivity", "mmtt-sampling")) and allow_failed:
        args.append("--allow-failed")
    return args


def report_complete(task, report):
    if task in ("mmtt-sensitivity", "mmtt-sampling"):
        return report["coverage"]["complete_cohort"] is True
    if task == "p1-controller":
        return report["study_status"] == "completed"
    if task == "m3-forecast":
        return report["evaluation"]["complete_cohort"] is True
    if task == "m3-compare":
        return report["common"]["complete_cohort"] is True
    if task.startswith("m4-"):
        return report["passed"] is True
    return (
        report["comparison_status"] == "complete" and report["candidate_execution_complete"] is True
    )
