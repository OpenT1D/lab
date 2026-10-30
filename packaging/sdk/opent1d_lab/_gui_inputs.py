"""Named UTF-8 concept files and SDK-owned development preparation."""

import uuid

from ._gui_drafts import FILES, LIMITS, raw_files
from ._gui_files import path, read, require


def texts(task, inputs):
    if task == "m4-study-installed":
        locations = {"config.json": inputs["config.json"]}
    else:
        locations = {
            name: inputs[name] for name in FILES[task] if not name.startswith("development-")
        }
        if task == "mmtt-sampling":
            development = path(inputs["development"], directory=True)
            locations.update(
                {
                    "development-package.json": development / "package.json",
                    "development-observations.csv": development / "observations.csv",
                }
            )
    return {
        name: read(filename, LIMITS[name]).decode("utf-8", errors="strict")
        for name, filename in locations.items()
    }


def materialize(sdk, task, files, inputs_root):
    raw = raw_files(task, files)
    folder = inputs_root / uuid.uuid4().hex
    folder.mkdir()
    if task == "m4-study-installed":
        inputs = sdk.example(task, folder / "bundle", case="fasting")["inputs"]
        filename = path(inputs["config.json"])
        require(filename.is_relative_to(folder), "SDK input export escaped its destination")
        filename.write_bytes(raw["config.json"])
        return inputs
    inputs = {}
    for name, value in raw.items():
        filename = folder / name
        filename.write_bytes(value)
        if not name.startswith("development-"):
            inputs[name] = str(filename)
    if task == "mmtt-sampling":
        result = sdk.prepare_development(
            folder / "development-package.json",
            folder / "development-observations.csv",
            folder / "design.json",
            folder / "development",
        )
        inputs["development"] = result["development"]
    return inputs
