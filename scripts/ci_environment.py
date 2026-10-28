"""Print selected CI identities and tool versions without dumping the environment."""

import json
import os
import platform
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def command(*args, root=ROOT):
    return subprocess.check_output(args, cwd=root, text=True).strip()


def collect(root=ROOT):
    return {
        "schema": "opent1d.ci-environment/1",
        "source_sha": command("git", "rev-parse", "HEAD", root=root),
        "source_dirty": bool(command("git", "status", "--porcelain", root=root)),
        "event_sha": os.environ.get("GITHUB_SHA"),
        "pull_request_head_sha": os.environ.get("PR_HEAD_SHA") or None,
        "event": os.environ.get("GITHUB_EVENT_NAME"),
        "run_id": os.environ.get("GITHUB_RUN_ID"),
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "runner": {
            "os": platform.system(),
            "architecture": platform.machine(),
            "image": os.environ.get("ImageOS"),
            "image_version": os.environ.get("ImageVersion"),
        },
        "python": platform.python_version(),
        "uv": command("uv", "--version", root=root),
        # Missing Node fails the required job instead of silently skipping its DOM checks.
        "node": command("node", "--version", root=root),
        "actions_cache": "disabled-by-workflow",
    }


if __name__ == "__main__":
    print(json.dumps(collect(), indent=2, sort_keys=True))
