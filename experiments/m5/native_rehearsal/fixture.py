"""Write clearly invented CIT-07-shaped CSVs for OT-027 structural checks."""

import argparse
import csv
import json
from pathlib import Path

from experiments.m5.native_rehearsal.run import MANIFEST, TABLES


def generate(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    manifest = json.loads(MANIFEST.read_text())
    study = "CIT07-SYNTHETIC"
    records = {name: [] for name in TABLES.values()}
    for alias, n_tx, second in (("SYN001", 1, ""), ("SYN002", 2, "150"), ("SYN003", 1, "")):
        records["patient_status.csv"].append(
            {
                "ACCESSION": alias,
                "StudyID": study,
                "NumTX": n_tx,
                "Numdays2ndTX": second,
                "Numdays3rdTX": "",
            }
        )
        for order in range(1, n_tx + 1):
            records["ieq_infused.csv"].append(
                {
                    "ACCESSION": alias,
                    "StudyID": study,
                    "LotID": f"LOT-{alias}-{order}",
                    "TX": order,
                    "PostTransplantIEQ": "100000",
                }
            )
        records["cpeptide.csv"].append(
            {
                "ACCESSION": alias,
                "StudyID": study,
                "NumDaysInitial": 75,
                "Flag08": "0",
                "pstintvst": "",
                "pstfinvst": "",
                "Fasting_cpeptide": "0.5",
                "Stimulated_cpeptide_90": "1.2",
                "Fasting_glucose": "110",
                "Stimulated_glucose_90": "140",
            }
        )
    for alias, start, end in (("SYN001", 359, 365), ("SYN002", 360, 366), ("SYN003", 358, 364)):
        for day in range(start, end + 1):
            if alias == "SYN003" and day == 361:
                continue
            records["insulin.csv"].append(
                {
                    "ACCESSION": alias,
                    "StudyID": study,
                    "NumDaysInitial": day,
                    "Flag08": "0",
                    "pstintvst": "",
                    "pstfinvst": "",
                    "Insulin": "10",
                }
            )
        records["mean_insulin.csv"].append(
            {
                "ACCESSION": alias,
                "StudyID": study,
                "NumDaysInitial": start,
                "EndDay": end,
                "pstintvst": "",
                "pstfinvst": "",
                "Mean_Insulin": "10",
                "Weight": "50",
                "Ins_kg": "0.2",
            }
        )
    for dictionary, filename in TABLES.items():
        with (directory / filename).open("w", newline="") as stream:
            writer = csv.DictWriter(
                stream, fieldnames=manifest["files"][dictionary]["required_variables"]
            )
            writer.writeheader()
            writer.writerows(records[filename])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    generate(parser.parse_args().output)
