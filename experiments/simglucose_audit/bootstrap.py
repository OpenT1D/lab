"""Closed native entry and a fixed, data-only invented fixture bootstrap."""

from datetime import UTC


def run_native(*_args, **_kwargs):
    """Refuse before decoding, private-path/source intake, imports or constructors."""
    raise PermissionError("native execution deferred; setup and execution gates remain closed")


def run_fixture(raw=None):
    from .contract import (
        decode,
        default_config,
        digest,
        encode,
        require,
        source_identity,
        validate_config,
    )

    raw = encode(default_config()) if raw is None else raw
    config = validate_config(decode(raw))
    identity = source_identity()
    # Only after exact invented data intake. No factory/import path is accepted.
    from .consumer import run_invented

    result = run_invented(config, identity, digest(raw))
    require(source_identity() == identity, "source-changed-during-fixture")
    return result


def inspect_proposals(asset_raw, bootstrap_raw, consumer_raw, index_raw, expected_index_sha256):
    """Inspect opaque proposal bytes; never follow their source/resource path strings."""
    from .contract import (
        AUTHORITY,
        RESOURCES,
        decode,
        digest,
        encode,
        fields,
        require,
        source_contract,
    )

    require(digest(index_raw) == expected_index_sha256, "external-proposal-index-pin")
    contract = source_contract()
    documents = [decode(raw) for raw in (asset_raw, bootstrap_raw, consumer_raw)]
    schemas = (
        "opent1d.private-simglucose-audit1-assets-proposal/1",
        "opent1d.private-simglucose-audit1-bootstrap-proposal/1",
        "opent1d.private-simglucose-audit1-consumer-proposal/1",
    )
    for label, value, schema in zip(
        ("asset", "bootstrap", "consumer"), documents, schemas, strict=True
    ):
        require(type(value) is dict and value.get("schema") == schema, "proposal-schema")
        require(set(value) == set(contract["proposal_top_fields"][label]), "proposal-fields")
        require(
            value.get("kind") == "proposal-only"
            and value.get("eligible_for_admission_registry") is False
            and value.get("implementation_exists") is False
            and value.get("runtime_observation") is False
            and value.get("approval_requested") is False
            and value.get("activation_command") is None,
            "unadmitted-proposal-only",
        )
        authority = value.get("authority")
        require(
            type(authority) is dict
            and set(authority) == set(AUTHORITY)
            and all(type(authority[k]) is bool and authority[k] is v for k, v in AUTHORITY.items()),
            "no-proposal-authority",
        )
        retention = value.get("retention")
        fields(
            retention,
            "private_outside_git max_days_new_technical_facts not_after_UTC earlier_limits_win "
            "old_origins_reset unknown_old_origins_timely_retention_not_proven "
            "automatic_cleanup_or_extension",
            "retention-fields",
        )
        require(
            retention["private_outside_git"] is True
            and type(retention["max_days_new_technical_facts"]) is int
            and retention["max_days_new_technical_facts"] == 30
            and type(retention["not_after_UTC"]) is str
            and retention["earlier_limits_win"] is True
            and retention["old_origins_reset"] is False
            and retention["unknown_old_origins_timely_retention_not_proven"] is True
            and retention["automatic_cleanup_or_extension"] is False,
            "inherited-retention-limits",
        )
        from datetime import datetime

        deadline = retention["not_after_UTC"]
        require(deadline.endswith("Z"), "retention-UTC-deadline")
        parsed = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
        require(parsed.utcoffset() == UTC.utcoffset(parsed), "retention-UTC-deadline")
    assets, bootstrap, consumer = documents
    require(assets["upstream_revision"] == contract["upstream_revision"], "upstream-revision")
    supplied_code = assets["selected_code"]
    require(type(supplied_code) is list and len(supplied_code) == 17, "exact-source-scope")
    projected = []
    for row in supplied_code:
        fields(
            row,
            "module upstream_path source_file bytes sha256 git_blob_sha1 package_initializer",
            "source-fields",
        )
        require(type(row["source_file"]) is str, "opaque-source-label")
        require(
            type(row["package_initializer"]) is bool and type(row["bytes"]) is int, "source-types"
        )
        projected.append({k: v for k, v in row.items() if k != "source_file"})
    require(encode(projected) == encode(contract["code"]), "exact-source-pins")
    asset_semantics = {k: assets[k] for k in contract["asset_semantics"]}
    for key in ("selected_code", "notices"):
        require(type(asset_semantics[key]) is list, "asset-metadata-list")
        for row in asset_semantics[key]:
            require(
                type(row) is dict and type(row.get("source_file")) is str, "opaque-source-label"
            )
        asset_semantics[key] = [
            {k: v for k, v in row.items() if k != "source_file"} for row in asset_semantics[key]
        ]
    require(
        encode(asset_semantics) == encode(contract["asset_semantics"]), "asset-proposal-contract"
    )
    require(
        encode(assets["retention"])
        == encode(bootstrap["retention"])
        == encode(consumer["retention"]),
        "same-retention-context",
    )
    for label, document in (("bootstrap", bootstrap), ("consumer", consumer)):
        for key, expected in contract[label + "_semantics"].items():
            require(
                encode(document[key]) == encode(expected), "proposal-scientific-bootstrap-contract"
            )
    resources = assets.get("required_resources")
    require(
        type(resources) is list
        and len(resources) == 3
        and {row.get("resource_argument") for row in resources if type(row) is dict} == RESOURCES,
        "exact-resource-scope",
    )
    require(
        all(
            row.get("package") == "simglucose"
            and row.get("payload_sha256") is None
            and row.get("rights_use_decision_sha256") is None
            and row.get("whole_file_read_required") is True
            for row in resources
        ),
        "metadata-only-resource-proposal",
    )
    projected_resources = [{k: v for k, v in row.items() if k != "consumer"} for row in resources]
    require(encode(projected_resources) == encode(contract["resources"]), "exact-resource-pins")
    asset_pin, bootstrap_pin = digest(asset_raw), digest(bootstrap_raw)
    require(
        bootstrap.get("asset_manifest_sha256") == consumer.get("asset_manifest_sha256") == asset_pin
        and consumer.get("bootstrap_manifest_sha256") == bootstrap_pin,
        "proposal-hash-DAG",
    )
    index = decode(index_raw)
    require(
        type(index) is dict
        and index.get("schema") == "opent1d.private-simglucose-audit1-manifest-bundle/1"
        and index.get("kind") == "proposal-only"
        and index.get("operational_approvals_requested") is False
        and index.get("new_authority_granted") is False
        and index.get("native_execution_deferred") is True,
        "proposal-index",
    )
    actual = index.get("files")
    supplied = dict(
        zip(
            (
                "asset-manifest.private.json",
                "bootstrap-manifest.private.json",
                "consumer-manifest.private.json",
            ),
            (asset_raw, bootstrap_raw, consumer_raw),
            strict=True,
        )
    )
    require(type(actual) is dict and set(actual) == set(supplied), "proposal-index-files")
    for name, raw in supplied.items():
        require(actual[name] == {"sha256": digest(raw), "bytes": len(raw)}, "proposal-index-pin")
    return {
        "kind": "proposal-only",
        "status": "blocked",
        "inspection": (
            "data-only identity/authority/resource-boundary checks; not full runtime qualification"
        ),
        "missing": [
            "native consumer/bootstrap implementation",
            "runtime/import closure",
            "asset hashes and rights",
            "setup",
            "host",
            "execution release",
        ],
        "source_paths_opened": False,
        "native_execution_authorized": False,
        "native_execution_deferred": True,
    }


def main(argv=None):
    import sys

    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "native":
        try:
            run_native()
        except PermissionError as error:
            raise SystemExit(str(error)) from None
    if argv != ["fixture"]:
        raise SystemExit("usage: python -m experiments.simglucose_audit fixture | native")
    from .contract import encode

    print(encode(run_fixture()).decode())


if __name__ == "__main__":
    main()
