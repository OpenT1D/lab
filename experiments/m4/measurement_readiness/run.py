"""Metadata-only BC-015 preflight; it never opens participant observations."""

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
PROTOCOL_SHA256 = "0a99401d6b2c17bd6295f3004b584a470f156f3b45fdeec7d1b48133b6d44c67"
FILES = {"protocol.json", "candidate.json", "source-run.py", "report.json"}
FINDINGS = {"supported", "partial", "unknown", "contradicted"}
ACCESS = {"request_required", "unknown", "synthetic"}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def read(path):
    path = Path(path)
    if path.stat().st_size > 50_000:
        raise ValueError("Metadata file exceeds the 50 kB limit")
    return json.loads(path.read_text())


def source_url(value):
    if not isinstance(value, str) or len(value) > 400:
        raise ValueError("A short public HTTPS source URL is required")
    if value != value.strip() or any(ord(char) < 33 for char in value):
        raise ValueError("Source URLs cannot contain whitespace or control characters")
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Source URLs must be public HTTPS URLs without credentials or query")


def protocol():
    path = HERE / "protocol.json"
    if digest(path) != PROTOCOL_SHA256:
        raise ValueError("Frozen BC-015 metadata protocol changed")
    result = read(path)
    if result.get("schema") != "bc015-metadata-protocol/1":
        raise ValueError("Wrong metadata protocol")
    return result


def validate(candidate, design):
    if set(candidate) != {
        "schema",
        "id",
        "population",
        "release",
        "access",
        "source_url",
        "evidence",
    }:
        raise ValueError("Candidate must contain only source-level metadata fields")
    if candidate["schema"] != "bc015-candidate/1":
        raise ValueError("Wrong candidate schema")
    for name in ("id", "population", "release"):
        value = candidate[name]
        if not isinstance(value, str) or not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9._/-]{0,79}", value
        ):
            raise ValueError(f"Invalid public {name}")
    if candidate["access"] not in ACCESS:
        raise ValueError("This preflight cannot record or grant human-data authorization")
    source_url(candidate["source_url"])
    if not isinstance(candidate["evidence"], dict) or set(candidate["evidence"]) != set(
        design["requirements"]
    ):
        raise ValueError("Missing or extra measurement requirement")
    for name, evidence in candidate["evidence"].items():
        if not isinstance(evidence, dict) or set(evidence) != {"finding", "basis", "url"}:
            raise ValueError(f"Invalid evidence fields for {name}")
        if evidence["finding"] not in FINDINGS or evidence["basis"] not in design["evidence_rank"]:
            raise ValueError(f"Invalid evidence status for {name}")
        source_url(evidence["url"])


def assess(candidate, design):
    validate(candidate, design)
    ranked = {name: rank for rank, name in enumerate(design["evidence_rank"])}
    decisions = {}
    for name, minimum in design["requirements"].items():
        evidence = candidate["evidence"][name]
        finding = evidence["finding"]
        if finding == "contradicted":
            decision = "contradicted"
        elif finding == "supported" and ranked[evidence["basis"]] >= ranked[minimum]:
            decision = "supported"
        else:
            decision = "unverified"
        decisions[name] = {
            "decision": decision,
            "finding": finding,
            "basis": evidence["basis"],
            "minimum_basis": minimum,
            "source_url": evidence["url"],
        }
    return {
        "schema": "bc015-metadata-report/1",
        "protocol": design["id"],
        "candidate": candidate["id"],
        "population": candidate["population"],
        "release": candidate["release"],
        "catalogue_access": candidate["access"],
        "requirements": decisions,
        "counts": {
            outcome: sum(d["decision"] == outcome for d in decisions.values())
            for outcome in ("supported", "unverified", "contradicted")
        },
        "metadata_packet_for_design_review": all(
            d["decision"] == "supported" for d in decisions.values()
        ),
        "human_execution_authorized": False,
        "claim": "source_metadata_feasibility_only",
    }


def execute(candidate_path, output):
    design = protocol()
    if Path(candidate_path).is_symlink():
        raise ValueError("A metadata candidate cannot be a symlink")
    candidate = read(candidate_path)
    report = assess(candidate, design)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    try:
        shutil.copyfile(HERE / "protocol.json", output / "protocol.json")
        shutil.copyfile(HERE / "run.py", output / "source-run.py")
        write(output / "candidate.json", candidate)
        write(output / "report.json", report)
        write(
            output / "manifest.json",
            {
                "schema": "bc015-metadata-archive/1",
                "status": "completed",
                "files": {name: digest(output / name) for name in sorted(FILES)},
            },
        )
        if reconstruct(output) != report:
            raise ValueError("Metadata archive failed reconstruction")
    except BaseException:
        write(
            output / "manifest.json",
            {
                "schema": "bc015-metadata-archive/1",
                "status": "failed",
                "files": {
                    name: digest(output / name)
                    for name in sorted(FILES)
                    if (output / name).is_file()
                },
            },
        )
        raise
    return report


def reconstruct(directory):
    directory = Path(directory)
    if directory.is_symlink() or (directory / "manifest.json").is_symlink():
        raise ValueError("Metadata archives cannot contain symlink paths")
    manifest = read(directory / "manifest.json")
    if (
        manifest.get("schema") != "bc015-metadata-archive/1"
        or manifest.get("status") != "completed"
        or set(manifest.get("files", {})) != FILES
        or {p.name for p in directory.iterdir()} != FILES | {"manifest.json"}
    ):
        raise ValueError("Incomplete or altered metadata archive")
    for name, expected in manifest["files"].items():
        path = directory / name
        if path.is_symlink() or not path.is_file() or digest(path) != expected:
            raise ValueError(f"Changed metadata artifact: {name}")
    if digest(directory / "protocol.json") != PROTOCOL_SHA256:
        raise ValueError("Changed frozen protocol")
    design = read(directory / "protocol.json")
    candidate = read(directory / "candidate.json")
    result = assess(candidate, design)
    if result != read(directory / "report.json"):
        raise ValueError("Report differs from metadata reconstruction")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reconstruct", type=Path)
    args = parser.parse_args()
    if (args.candidate is None) == (args.reconstruct is None):
        parser.error("Choose exactly one of --candidate or --reconstruct")
    if args.reconstruct is not None:
        report = reconstruct(args.reconstruct)
        if args.output.exists():
            raise ValueError("Choose a new reconstruction output file")
        write(args.output, report)
    else:
        report = execute(args.candidate, args.output)
    print(
        json.dumps(
            {"counts": report["counts"], "reviewable": report["metadata_packet_for_design_review"]}
        )
    )
