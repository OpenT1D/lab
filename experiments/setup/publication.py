"""Limit automatic installation in the independent public source snapshot."""

import json


def check_install(root, projects):
    if not (root / "publication-snapshot.json").exists():
        return
    try:
        policy = json.loads((root / "publication-security.json").read_text())
        if policy["schema"] != "opent1d.publication-security/1":
            raise ValueError("Unsupported publication policy")
        allowed = set(policy["allowed_install_projects"])
        if "." not in allowed or not all(isinstance(item, str) for item in allowed):
            raise ValueError("Invalid publication allowlist")
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise ValueError(
            "Public installation requires a valid publication-security.json"
        ) from error
    refused = sorted(set(projects) - allowed)
    if refused:
        raise ValueError(
            "Public automatic installation excludes historical runtimes: "
            + ", ".join(refused)
            + ". See docs/publication-security.md; use the supported synthetic MMTT tasks."
        )
