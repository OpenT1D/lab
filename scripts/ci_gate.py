"""Require every explicitly named public family to finish successfully."""

import json
import os
import sys

REQUIRED = frozenset(
    {
        "repository-checks",
        "root-tests",
        "public-smoke",
        "browser",
        "browser-apps",
        "dependency-review",
    }
)
EVENTS = frozenset({"pull_request", "push", "workflow_dispatch"})


def validate(results, event="pull_request"):
    if event not in EVENTS:
        raise ValueError("Missing or unsupported public check event")
    if not isinstance(results, dict) or set(results) != REQUIRED:
        raise ValueError("Missing or unexpected public check families")
    failed = [
        name
        for name in sorted(REQUIRED)
        if not isinstance(results[name], dict)
        or results[name].get("result") != "success"
        and not (
            name == "dependency-review"
            and event in {"push", "workflow_dispatch"}
            and results[name].get("result") == "skipped"
        )
    ]
    if failed:
        raise ValueError("Public check families did not succeed: " + ", ".join(failed))


def main():
    try:
        validate(json.loads(os.environ["PUBLIC_CHECK_RESULTS"]), os.environ["PUBLIC_CHECK_EVENT"])
    except (KeyError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    print("All required public check families succeeded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
