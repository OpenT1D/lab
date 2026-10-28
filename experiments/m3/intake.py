"""Conservative Ohio-style CGM XML conversion; release format remains unverified."""

import datetime as dt
import xml.etree.ElementTree as ET
from pathlib import Path

from .common import ROOT, SCHEMA, Snapshot, digest, finite, provenance, read, require, save
from .data import observations


def local_time(text):
    try:
        return dt.datetime.strptime(text, "%d-%m-%Y %H:%M:%S")
    except (ValueError, TypeError):
        raise ValueError("Invalid native timestamp format") from None


def convert_xml(raw, *, person, source_person, origin_local):
    """No resampling, insulin inference, weight interpretation or censor-bound guessing."""
    require(
        b"<!DOCTYPE" not in raw.upper() and b"<!ENTITY" not in raw.upper(),
        "XML entities are unsupported",
    )
    root = ET.fromstring(raw)
    require(root.tag == "patient" and root.get("id") == source_person, "Source identity mismatch")
    glucose = root.findall("glucose_level")
    require(len(glucose) == 1, "Exactly one CGM section required")
    origin = local_time(origin_local)
    rows = []
    for event in glucose[0]:
        require(
            event.tag == "event" and set(event.attrib) == {"ts", "value"},
            "Unreviewed native CGM fields",
        )
        require(not list(event), "Nested native CGM content unsupported")
        text = event.get("ts")
        time = (local_time(text) - origin).total_seconds() / 60
        finite(time, "local elapsed time", 0)
        raw_value = event.get("value")
        if raw_value == "":
            status, value = "missing", None
        else:
            try:
                value = float(raw_value)
            except (ValueError, TypeError):
                raise ValueError("Nonnumeric native CGM field") from None
            value = finite(value, "parsed native CGM", 0)
            status = "measured" if value > 0 else "invalid"
            if status == "invalid":
                value = None
        rows.append(
            {
                "time": time,
                "available": time,
                "segment": "unadjusted-local",
                "raw_time": text,
                "status": status,
                "value": value,
                "bound": None,
            }
        )
    value = {
        "schema": SCHEMA,
        "person": person,
        "clock": "shifted_local",
        "unit": "mg/dL",
        "rows": rows,
    }
    observations(value, person, "shifted_local", 0, max((r["time"] for r in rows), default=0) + 1)
    return value


def normalize(input_path, intake_path, output):
    intake, intake_sha = read(intake_path)
    require(intake.get("kind") in ("synthetic", "human"), "Explicit input kind required")
    if intake["kind"] == "human":
        require(
            intake.get("authorized_processing") is True and intake.get("authorization_reference"),
            "Authorization record required before reading human input",
        )
        require(
            intake.get("native_cgm_semantics_reviewed") is True,
            "Verify native units/censoring before conversion",
        )
        for path in (input_path, intake_path, output):
            require(
                not Path(path).resolve().is_relative_to(ROOT),
                "Human material must remain outside repository",
            )
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    state = {"schema": SCHEMA, "status": "started", "intake_sha256": intake_sha}
    save(output / "status.json", state)
    try:
        state["provenance"] = provenance()
        snap = Snapshot(Path(input_path).parent)
        raw = snap.read(Path(input_path).name)
        require(digest(raw) == intake.get("source_sha256"), "Native input bytes changed")
        value = convert_xml(
            raw,
            person=intake["person"],
            source_person=intake["source_person"],
            origin_local=intake["origin_local"],
        )
        snap.verify_unchanged()
        save(output / "observations.json", value)
        save(
            output / "conversion.json",
            {
                "schema": SCHEMA,
                "kind": intake["kind"],
                "person": intake["person"],
                "source_person": intake["source_person"],
                "provenance": state["provenance"],
                "source_sha256": digest(raw),
                "intake_sha256": intake_sha,
                "output_sha256": digest((output / "observations.json").read_bytes()),
                "availability_assumption": (
                    "measurement timestamp equals availability; not verified online"
                ),
                "clock": "shifted local elapsed minutes; timezone unknown; no clock repair",
                "native_release_tested": False,
                "excluded_sections": sorted(
                    {c.tag for c in ET.fromstring(raw)} - {"glucose_level"}
                ),
            },
        )
        state["status"] = "completed"
    except BaseException as error:
        from .workflow import failure

        state.update(status="failed", error=failure(error))
        try:
            save(output / "status.json", state)
        except BaseException:
            pass
        raise
    save(output / "status.json", state)
