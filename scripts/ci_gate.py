"""Require every explicitly named public family to finish successfully."""

import json
import os
import sys

REQUIRED = frozenset({"repository-checks", "public-smoke", "browser"})


def validate(results):
    if not isinstance(results, dict) or set(results) != REQUIRED:
        raise ValueError("Missing or unexpected public check families")
    failed = [
        name
        for name in sorted(REQUIRED)
        if not isinstance(results[name], dict) or results[name].get("result") != "success"
    ]
    if failed:
        raise ValueError("Public check families did not succeed: " + ", ".join(failed))


def main():
    try:
        validate(json.loads(os.environ["PUBLIC_CHECK_RESULTS"]))
    except (KeyError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    print("All required public check families succeeded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
