"""Sampling-specific admission on the shared owned observation GUI lifecycle."""

import copy
import shutil

from experiments.mmtt_sampling.design import validate_design
from experiments.mmtt_sampling.fixtures import CASES
from experiments.mmtt_sampling.intake import development_inventory

from .library_sampling import TASK, validate_report
from .observations import Observations, require
from .service import bounded_bytes, decode_json, digest, inventory


class Sampling(Observations):
    task = TASK
    cases = CASES
    operations = frozenset("sampling_" + n for n in ("example", "freeze", "run", "reconstruct"))
    config_schema = "opent1d.gui-sampling-configuration/1"
    entry_schema = "opent1d.gui-sampling-entry/1"
    request_schema = "opent1d.gui-sampling-request/1"
    operation_prefix = "sampling"
    id_prefix = "sam"
    data_name = "sampling"
    native_module = "experiments.mmtt_sampling"
    validate_report = staticmethod(validate_report)
    case_labels = {
        "information-loss": "Constructed direction reversal",
        "constant": "Constant control",
        "incomplete": "Low / censored control",
        "steep-response": "Boundary failure control",
    }
    default_display_name = "Fewer measurement times"

    def extra(self, body):
        design_path = self.service.safe_path(body["design"], suffix=".json")
        raw = bounded_bytes(design_path, 1024 * 1024)
        design = validate_design(decode_json(raw))
        archive = self.service.safe_path(body["development_import"])
        development_inventory(archive, design)  # Reject evaluation roster before CSV access.
        return (
            raw,
            design,
            archive,
            {"design.json": digest(raw), "development_import": inventory(archive)},
        )

    def inspect(self, body):
        with self.service.lock:
            self.idle()
            require(
                set(body) == {"package", "csv", "settings", "design", "development_import"},
                "Choose observation, settings, design and development-import files",
            )
            _, design, _, hashes = self.extra(body)
            result = super().inspect({k: body[k] for k in ("package", "csv", "settings")})
            require(
                "required_times_min" not in result["settings"],
                "Sampling design owns required times; choose base shared settings",
            )
            result["input_sha256"].update(hashes)
            result["design"] = design
            return result

    def configure(self, body):
        with self.service.lock:
            self.idle()
            require(
                set(body) - {"display_name"}
                == {"package", "csv", "settings", "input_sha256", "design", "development_import"},
                "Unsupported sampling configuration",
            )
            raw, design, archive, hashes = self.extra(body)
            require(
                all(body["input_sha256"].get(k) == v for k, v in hashes.items()),
                "Design or development bytes changed; inspect again",
            )
            require(
                "required_times_min" not in body["settings"], "Sampling design owns required times"
            )
            base = {k: body[k] for k in ("package", "csv", "settings", "input_sha256")}
            if "display_name" in body:
                base["display_name"] = body["display_name"]
            base["input_sha256"] = {
                k: v for k, v in base["input_sha256"].items() if k not in hashes
            }
            value = super().configure(base)
            record = self.configs[value["id"]]
            folder = self.folder(record) / "inputs"
            (folder / "design.json").write_bytes(raw)
            shutil.copytree(archive, folder / "development-import")
            require(
                inventory(folder / "development-import") == hashes["development_import"],
                "Development import changed during snapshot",
            )
            record["inputs_sha256"]["design.json"] = hashes["design.json"]
            record["development_identity"] = hashes["development_import"]
            record["design"] = copy.deepcopy(design)
            for key, name in (
                ("design", "design.json"),
                ("development_import", "development-import"),
            ):
                record["input_paths"][key] = (
                    (folder / name).relative_to(self.service.root).as_posix()
                )
            self.persist(record)
            return copy.deepcopy(record)

    def commands(self, job):
        commands = super().commands(job)
        request = job["request"]
        if request["operation"] == self.op("example"):
            command, budget = commands[0]
            folder = self.data / "inputs" / request["example_id"]
            development = folder / "development"
            commands += [
                (command[:-1] + [str(development), "--development-only"], budget),
                (
                    [
                        self.service.python,
                        "-B",
                        "-E",
                        "-s",
                        "-S",
                        "-m",
                        "experiments.observation_analysis",
                        "import",
                        "--package",
                        str(development / "package.json"),
                        "--csv",
                        str(development / "observations.csv"),
                        "--output",
                        str(folder / "development-import"),
                    ],
                    budget,
                ),
            ]
        elif request["operation"] == self.op("freeze"):
            config = self.configs[request["configuration_id"]]
            folder = self.folder(config) / "inputs"
            require(
                inventory(folder / "development-import") == config["development_identity"],
                "Development snapshot changed",
            )
            command = commands[1][0]
            command[command.index("freeze")] = "freeze-study"
            command += [
                "--design",
                str(folder / "design.json"),
                "--development-import",
                str(folder / "development-import"),
            ]
            commands = commands[1:]  # Invalid full analytes may leave valid reduced children.
        return commands

    def finish(self, job):
        super().finish(job)
        if job["request"]["operation"] == self.op("example") and job.get("exit_code") == 0:
            folder = self.data / "inputs" / job["request"]["example_id"]
            for key, name in (
                ("design", "sampling-design.json"),
                ("development_import", "development-import"),
            ):
                job["result"]["input_paths"][key] = (
                    (folder / name).relative_to(self.service.root).as_posix()
                )
