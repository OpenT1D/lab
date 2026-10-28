"""Synthetic native-format preparation and verification; no download or evaluation."""

import os
from pathlib import Path

from experiments.m3.azt1d.analysis import _equal, _hashes, _Snapshot
from experiments.m3.azt1d.study import private_directory
from experiments.m3.common import ID, ROOT, SHA, digest, read, require, save, sources
from experiments.m3.external.common import FORMAT
from experiments.m3.external.common import SCHEMA as EXTERNAL_SCHEMA
from experiments.m3.external.study import registry_check
from experiments.m3.workflow import failure

from .intake import AUTHOR_COMMIT, CONTRACT, POLICY, RELEASE, convert_csv, validate_header

SCHEMA = "opent1d.physiocgm.preparation/1"


def provenance():
    paths = list((ROOT / "experiments/m3/physiocgm").glob("*.py"))
    paths += [
        ROOT / "experiments/m3/azt1d" / name
        for name in ("intake.py", "data.py", "common.py", "analysis.py", "study.py")
    ]
    paths += [ROOT / "experiments/m3/external" / name for name in ("common.py", "study.py")]
    return {
        "contract": CONTRACT,
        "candidate_release": RELEASE,
        "author_code_commit": AUTHOR_COMMIT,
        "policy": POLICY,
        "sources": sources() | {str(p.relative_to(ROOT)): digest(p.read_bytes()) for p in paths},
        "native_release_verified": False,
    }


def validate_request(request):
    require(
        isinstance(request, dict)
        and set(request) == {"schema", "kind", "people"}
        and request["schema"] == SCHEMA,
        "Invalid preparation request",
    )
    # This check precedes any source path inspection or source read.
    require(request["kind"] == "synthetic", "Human PhysioCGM intake is not verified or enabled")
    people = request["people"]
    require(isinstance(people, list) and people, "Complete planned synthetic cohort required")
    aliases, paths, hashes = set(), set(), set()
    for person in people:
        require(
            isinstance(person, dict) and set(person) == {"id", "input", "header"},
            "Invalid planned person",
        )
        pid = person["id"]
        require(
            isinstance(pid, str) and ID.fullmatch(pid) and pid != "model" and pid not in aliases,
            "Repeated or invalid alias",
        )
        aliases.add(pid)
        validate_header(person["header"])
        ref = person["input"]
        require(
            isinstance(ref, dict) and set(ref) == {"file", "sha256"},
            "Native input reference required",
        )
        require(
            isinstance(ref["file"], str) and Path(ref["file"]).is_absolute(),
            "Absolute native path required",
        )
        path = os.path.normpath(ref["file"])
        require(path not in paths, "Repeated native path")
        paths.add(path)
        require(
            isinstance(ref["sha256"], str)
            and SHA.fullmatch(ref["sha256"])
            and ref["sha256"] not in hashes,
            "Repeated or invalid native identity",
        )
        hashes.add(ref["sha256"])


def registry(request, documents, output, request_sha):
    value = {
        "schema": EXTERNAL_SCHEMA,
        "kind": "synthetic",
        "source": {
            "id": "invented-physiocgm-format",
            "format": FORMAT,
            "reference": (
                f"Self-authored fixtures; {CONTRACT}; request SHA-256 {request_sha}; "
                f"conversion evidence {output}/manifest.json"
            ),
        },
        "ledger": str(output.parent / f"{output.name}-evaluation-access.jsonl"),
        "prior_access": {
            "reviewed": True,
            "status": "present",
            "reference": (
                "Synthetic generation and native-format conversion preceded this registry; "
                "no human release inspected"
            ),
        },
        "people": [],
    }
    for person in request["people"]:
        pid = person["id"]
        document, sha = documents[pid]
        value["people"].append(
            {
                "id": pid,
                "input": {"file": str(output / pid / "observations.json"), "sha256": sha},
                "bounds_us": document["bounds_us"],
                "origins_us": [r["time_us"] for r in document["rows"]],
            }
        )
    registry_check(value)
    return value


def _seal(folder):
    with _Snapshot(folder) as snapshot:
        files = {
            name: digest(snapshot.read(name))
            for name in sorted(snapshot.names)
            if name != "manifest.json"
        }
        snapshot.verify()
    save(folder / "manifest.json", {"schema": SCHEMA, "files": files})


def prepare(request_path, output):
    request, request_sha = read(request_path)
    validate_request(request)
    output = Path(output).absolute()
    with private_directory(output):
        with _Snapshot(Path(request_path).parent, only={Path(request_path).name}) as snapshot:
            raw_request = snapshot.read(Path(request_path).name)
            require(digest(raw_request) == request_sha, "Request changed before preparation")
            (output / "request.json").write_bytes(raw_request)
            snapshot.verify()
        state = {
            "schema": SCHEMA,
            "kind": "synthetic",
            "status": "started",
            "submitted_request_sha256": request_sha,
            "output_directory": str(output),
            "provenance": provenance(),
            "model_fit_or_evaluation": False,
            "cases": [{"id": p["id"], "status": "not_attempted"} for p in request["people"]],
        }
        save(output / "state.json", state)
        documents = {}
        try:
            for person, case in zip(request["people"], state["cases"], strict=True):
                folder = output / person["id"]
                try:
                    folder.mkdir(mode=0o700)
                    # Evidence of intended synthetic read, not a human first-access ledger.
                    save(
                        folder / "read-attempt.json",
                        {
                            "schema": SCHEMA,
                            "kind": "synthetic",
                            "person": person["id"],
                            "source_sha256": person["input"]["sha256"],
                            "request_sha256": request_sha,
                        },
                    )
                    source = Path(person["input"]["file"])
                    with _Snapshot(source.parent, only={source.name}) as snapshot:
                        raw = snapshot.read(source.name)
                        require(
                            digest(raw) == person["input"]["sha256"], "Native source bytes changed"
                        )
                        snapshot.verify()
                    (folder / "native.csv").write_bytes(raw)
                    document, audit = convert_csv(
                        raw,
                        person=person["id"],
                        expected_header=person["header"],
                        kind=request["kind"],
                    )
                    save(folder / "observations.json", document)
                    save(folder / "audit.json", audit)
                    documents[person["id"]] = (
                        document,
                        digest((folder / "observations.json").read_bytes()),
                    )
                    case["status"] = "completed"
                except BaseException as error:
                    case.update(status="failed", error=failure(error))
                    if not isinstance(error, Exception):
                        raise
                finally:
                    save(output / "state.json", state)
            require(
                all(c["status"] == "completed" for c in state["cases"]),
                "Preparation incomplete; no partial-cohort registry created",
            )
            save(output / "registry.json", registry(request, documents, output, request_sha))
            state["status"] = "completed"
        except BaseException as error:
            state.update(status="failed", error=failure(error))
            raise
        finally:
            save(output / "state.json", state)
            _seal(output)
    return verify(output)


def verify(folder):
    """Recheck a complete conversion from its saved native bytes, without original paths."""
    folder = Path(folder)
    with _Snapshot(folder) as snapshot:
        # Refuse a human bundle before hashing (and thus reading) native snapshots.
        request = snapshot.parsed("request.json")
        validate_request(request)
        state = snapshot.parsed("state.json")
        require(state.get("kind") == "synthetic", "Human PhysioCGM verification is not enabled")
        manifest = snapshot.parsed("manifest.json")
        require(
            set(manifest) == {"schema", "files"} and manifest["schema"] == SCHEMA,
            "Invalid conversion manifest",
        )
        hashes = _hashes(manifest["files"])
        require(
            set(hashes) == snapshot.names - {"manifest.json"},
            "Conversion inventory membership changed",
        )
        for name, sha in hashes.items():
            require(digest(snapshot.read(name)) == sha, "Conversion artifact bytes changed")
        require(
            state.get("schema") == SCHEMA
            and state.get("kind") == "synthetic"
            and state.get("status") == "completed"
            and state.get("model_fit_or_evaluation") is False,
            "Only complete synthetic conversions may verify",
        )
        require(
            _equal(state["provenance"], provenance()), "Conversion implementation or policy changed"
        )
        expected_cases = [{"id": p["id"], "status": "completed"} for p in request["people"]]
        require(state["cases"] == expected_cases, "Planned conversion cohort changed")
        request_sha = state["submitted_request_sha256"]
        require(
            isinstance(request_sha, str) and SHA.fullmatch(request_sha),
            "Invalid original request identity",
        )
        require(
            digest(snapshot.read("request.json")) == request_sha, "Original request bytes changed"
        )
        output = Path(state["output_directory"])
        require(output.is_absolute(), "Original output location required")
        expected_files = {"request.json", "state.json", "registry.json"}
        documents, total = {}, 0
        for person in request["people"]:
            pid = person["id"]
            prefix = pid + "/"
            expected_files |= {
                prefix + name
                for name in ("read-attempt.json", "native.csv", "observations.json", "audit.json")
            }
            require(
                snapshot.parsed(prefix + "read-attempt.json")
                == {
                    "schema": SCHEMA,
                    "kind": "synthetic",
                    "person": pid,
                    "source_sha256": person["input"]["sha256"],
                    "request_sha256": request_sha,
                },
                "Native read attempt changed",
            )
            raw = snapshot.read(prefix + "native.csv")
            require(digest(raw) == person["input"]["sha256"], "Saved native source differs")
            document, audit = convert_csv(
                raw, person=pid, expected_header=person["header"], kind=request["kind"]
            )
            require(
                _equal(document, snapshot.parsed(prefix + "observations.json")),
                "Normalized observations differ from native conversion",
            )
            require(
                _equal(audit, snapshot.parsed(prefix + "audit.json")), "Conversion audit differs"
            )
            documents[pid] = document, digest(snapshot.read(prefix + "observations.json"))
            total += len(document["rows"])
        require(expected_files == set(hashes), "Unexpected conversion files")
        require(
            _equal(
                snapshot.parsed("registry.json"), registry(request, documents, output, request_sha)
            ),
            "Normalized registry differs",
        )
        snapshot.verify()
    return {
        "kind": "synthetic",
        "conversion_verified": True,
        "planned_people": len(request["people"]),
        "registered_origins": total,
        "release_files_verified": False,
        "model_fit_or_evaluation": False,
    }
