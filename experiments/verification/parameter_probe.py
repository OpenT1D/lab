"""Read native development parameters without executing a trajectory."""

import importlib.metadata
import json
import sys
from pathlib import Path

from simglucose.patient.t1dpatient import T1DPatient

from experiments.m1.artifacts import digest

package = importlib.metadata.distribution("simglucose")
source = json.loads(package.read_text("direct_url.json"))
if source["vcs_info"]["commit_id"] != "a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc":
    raise ValueError("Unexpected native source")
print(
    json.dumps(
        {
            "upstream": source,
            "python": sys.version,
            "parameters": {
                p: {
                    k: str(v) if isinstance(v, str) else float(v)
                    for k, v in T1DPatient.withName(p)._params.items()
                }
                for p in ("adult#001", "adult#002")
            },
            "parameter_table_sha256": digest(
                Path(package.locate_file("simglucose/params/vpatient_params.csv"))
            ),
        },
        allow_nan=False,
    )
)
