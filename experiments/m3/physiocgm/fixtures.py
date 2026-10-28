"""Self-authored native-layout examples, never samples from the human release."""

import csv
import datetime as dt
import io
import math
from pathlib import Path

from experiments.m3.azt1d.study import private_directory
from experiments.m3.common import digest, require, save

from .intake import REQUIRED
from .service import SCHEMA


def generate(output, *, people=2):
    require(type(people) is int and people > 0, "Positive invented cohort required")
    output = Path(output).absolute()
    request = {"schema": SCHEMA, "kind": "synthetic", "people": []}
    with private_directory(output):
        for index in range(people):
            padding = [""] if index % 2 else []
            header = list(REQUIRED) + ["Invented ignored field"] + padding
            pid = f"invented-cgm-{index + 1}"
            stream = io.StringIO(newline="")
            writer = csv.writer(stream)
            writer.writerow(header)
            writer.writerow(
                [0, "not a glucose timestamp", "Calibration", "900", "Invented event"] + padding
            )
            for point in range(577):
                if point == 73:
                    continue
                timestamp = dt.datetime(2040, 1, 1) + dt.timedelta(minutes=point * 5)
                native_time = (
                    f"{timestamp:%Y-%m-%d} {timestamp.hour}:{timestamp:%M:%S}"
                    if padding
                    else timestamp.isoformat()
                )
                glucose = f"{120 + 20 * math.sin(point / 25) + index * 7:.6f}"
                glucose = {48: "", 134: "Low", 224: "High", 313: "400"}.get(point, glucose)
                record = [point + 1, native_time, "EGV", glucose, "Invented"] + padding
                writer.writerow(record)
                if point == 107:
                    writer.writerow(record)
                if point == 177:
                    writer.writerow(record[:3] + ["180", "Invented conflict"] + padding)
            raw = stream.getvalue().encode()
            source = output / f"{pid}.csv"
            source.write_bytes(raw)
            request["people"].append(
                {"id": pid, "input": {"file": str(source), "sha256": digest(raw)}, "header": header}
            )
        save(output / "request.json", request)
    return request
