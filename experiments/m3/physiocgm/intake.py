"""PhysioCGM intake candidate with locally observed format variants.

Original implementation, not copied from the authors' unlicensed code. Supported
field names and EGV selection are documented in the source assessment. Human
conversion uses the separately gated service, never a synthetic declaration.
"""

import csv
import io
import re
from collections import Counter

from experiments.m3.azt1d.common import MINUTE, SCHEMA
from experiments.m3.azt1d.data import validate_observations
from experiments.m3.azt1d.intake import _elapsed_us, _policy, _signal, local_time
from experiments.m3.common import ID, require

CONTRACT = "physiocgm-cgm-candidate/0.2"
RELEASE = "10.6084/m9.figshare.28136294.v1"
AUTHOR_COMMIT = "6940f1d587f8f68b131cf129d5a9f65237f61fcc"
TIME = "Timestamp (YYYY-MM-DDThh:mm:ss)"
GLUCOSE = "Glucose Value (mg/dL)"
EVENT = "Event Type"
REQUIRED = ("Index", TIME, EVENT, GLUCOSE)
_SINGLE_HOUR = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]:[0-9]{2}:[0-9]{2}\Z")
POLICY = {
    "numeric_boundary": "exclude",
    "lower": 40,
    "upper": 400,
    "reference": "Synthetic conservative candidate; native endpoints remain unverified",
}
ASSUMPTIONS = {
    "availability": "measurement time approximates availability; synthetic assumption only",
    "clock": "one naive local segment; no timezone inferred; backward EGV time rejected",
    "censoring": "Low/High retain direction without a verified numerical bound",
    "numeric_limits": "values at or outside 40 and 400 excluded by candidate policy",
    "lineage": "CSV data-record numbers, excluding header; not device Index",
    "end": "last registered EGV time plus 300 seconds is an administrative endpoint",
}


def validate_header(header):
    require(
        isinstance(header, list)
        and all(isinstance(name, str) and (name == "" or name.strip()) for name in header)
        and len(set(header)) == len(header)
        and set(REQUIRED) <= set(header),
        "Explicit unique header with required fields and at most one empty name is required",
    )
    require(
        not any("Glucose Value" in name and name != GLUCOSE for name in header),
        "Conflicting or unreviewed glucose unit column",
    )


def _native_time(text):
    """Interpret the declared local spelling without changing stored source text."""
    single_hour = _SINGLE_HOUR.fullmatch(text) is not None
    parsed = local_time(text[:11] + "0" + text[11:] if single_hour else text)
    return parsed, single_hour


def convert_csv(raw, *, person, expected_header, kind):
    """Convert a declared synthetic CSV, retaining every registered EGV origin.

    Header order/extras must be explicitly declared, not guessed from a specimen.
    A declared unnamed column must be empty in every record, even excluded events.
    Local format inspection informed these variants; human use remains disabled.
    Other events do not contribute glucose, origins or clock assumptions.
    """
    require(kind == "synthetic", "Human PhysioCGM intake is not verified or enabled")
    return _convert_csv(raw, person=person, expected_header=expected_header, kind=kind)


def _convert_csv(raw, *, person, expected_header, kind):
    """Pure conversion core; human callers must use the source-bound human service."""
    require(kind in ("synthetic", "human"), "Explicit conversion kind required")
    require(type(raw) is bytes, "CSV bytes required")
    require(isinstance(person, str) and ID.fullmatch(person) and person != "model", "Invalid alias")
    validate_header(expected_header)
    parsed_policy = _policy(POLICY)
    records, egv, excluded, single_hours = 0, 0, 0, 0
    rows, previous, origin, prior_key = [], None, None, None
    try:
        reader = csv.reader(io.StringIO(raw.decode("utf-8-sig"), newline=""), strict=True)
        header = next(reader, None)
        require(header == expected_header, "CSV header differs from declared candidate layout")
        unnamed_col = header.index("") if "" in header else None
        time_col, glucose_col, event_col = (header.index(key) for key in (TIME, GLUCOSE, EVENT))
        for records, fields in enumerate(reader, 1):
            require(len(fields) == len(header), "Invalid CSV record width")
            require(
                unnamed_col is None or fields[unnamed_col] == "",
                "Declared unnamed column contains data",
            )
            if fields[event_col] != "EGV":
                excluded += 1
                continue
            egv += 1
            timestamp, single_hour = _native_time(fields[time_col])
            single_hours += int(single_hour)
            require(previous is None or timestamp >= previous, "EGV timestamps run backwards")
            previous = timestamp
            if origin is None:
                origin = timestamp
            time_us = _elapsed_us(timestamp, origin)
            text = fields[glucose_col]
            if text.strip() in ("Low", "High"):
                status = "censored_low" if text.strip() == "Low" else "censored_high"
                value, bound, key = None, None, (status,)
            else:
                status, value, bound, key = _signal(text, parsed_policy)
            if rows and rows[-1]["time_us"] == time_us:
                rows[-1]["source_rows"].append(records)
                if key != prior_key:
                    rows[-1].update(status="ambiguous", value=None, bound=None)
            else:
                rows.append(
                    {
                        "time_us": time_us,
                        "available_us": time_us,
                        "segment": "synthetic-local" if kind == "synthetic" else "assumed-local",
                        "raw_time": fields[time_col],
                        "status": status,
                        "value": value,
                        "bound": bound,
                        "source_rows": [records],
                    }
                )
                prior_key = key
    except (csv.Error, UnicodeError):
        raise ValueError("Invalid CSV encoding or structure") from None
    require(rows, "No registered EGV observations")
    document = {
        "schema": SCHEMA,
        "person": person,
        "clock": "local_elapsed",
        "unit": "mg/dL",
        "bounds_us": [0, rows[-1]["time_us"] + 5 * MINUTE],
        "rows": rows,
    }
    validate_observations(document, person, *document["bounds_us"])
    audit = {
        "contract": CONTRACT,
        "kind": kind,
        "release_files_verified": False,
        "source_record_count": records,
        "egv_record_count": egv,
        "excluded_non_egv_records": excluded,
        "registered_origins": len(rows),
        "duplicate_egv_records": egv - len(rows),
        "format_variants": {
            "empty_unnamed_column": unnamed_col is not None,
            "empty_unnamed_records": records if unnamed_col is not None else 0,
            "single_digit_hour_egv_records": single_hours,
        },
        "statuses": dict(sorted(Counter(row["status"] for row in rows).items())),
        "assumptions": dict(ASSUMPTIONS),
    }
    if kind == "human":
        audit["assumptions"]["availability"] = (
            "measurement time approximates availability; conditional retrospective assumption"
        )
    return document, audit
