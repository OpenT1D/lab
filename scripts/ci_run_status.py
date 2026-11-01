"""Read exact-run evidence without rewriting checks or hiding earlier failures.

Run this script from the revision whose current public job roster is reviewed.
A successful receipt describes that run, not PR merge eligibility or a clean UI.
"""

import argparse
import json
import re
import subprocess
import sys
from time import monotonic

EXPECTED = frozenset(
    {"Root checks", "Dependency review", "Repository checks"}
    | {f"Root tests ({i}/4)" for i in range(1, 5)}
    | {f"Browser application ({i}/3)" for i in range(1, 4)}
    | {f"Browser checks ({name})" for name in ("chromium", "firefox", "webkit")}
    | {f"Public smoke ({name})" for name in ("ubuntu-24.04", "macos-15", "windows-2025")}
)


def evaluate(run, jobs, checks, *, run_id, head_sha):
    if (
        run.get("id") != run_id
        or run.get("head_sha") != head_sha
        or run.get("path") != ".github/workflows/checks.yml"
        or run.get("event") not in {"pull_request", "push", "workflow_dispatch"}
        or not isinstance(run.get("run_attempt"), int)
        or run["run_attempt"] < 1
    ):
        raise ValueError("Run/source/workflow identity mismatch")
    named = {}
    for job in jobs:
        if job.get("run_id") != run_id or job.get("head_sha") != head_sha:
            raise ValueError("Job belongs to a different run/source")
        if (
            not isinstance(job.get("run_attempt"), int)
            or not 1 <= job["run_attempt"] <= run["run_attempt"]
        ):
            raise ValueError("Invalid retained job attempt")
        if job["name"] in named:
            raise ValueError("Duplicate latest job name: " + job["name"])
        named[job["name"]] = job
    missing = sorted(EXPECTED - named.keys())
    failed = []
    for name in sorted(EXPECTED & named.keys()):
        job = named[name]
        dependency_skip = (
            name == "Dependency review"
            and run["event"] in {"push", "workflow_dispatch"}
            and job.get("conclusion") == "skipped"
        )
        if job.get("status") != "completed" or (
            job.get("conclusion") != "success" and not dependency_skip
        ):
            failed.append(name)
    current_urls = {job["html_url"] for job in jobs}
    prefix = f"https://github.com/{run['repository']['full_name']}/actions/runs/{run_id}/job/"
    earlier = [
        {key: check.get(key) for key in ("id", "name", "status", "conclusion", "details_url")}
        for check in checks
        if check.get("details_url", "").startswith(prefix)
        and check["details_url"] not in current_urls
    ]
    return {
        "schema": "opent1d.ci-run-status/1",
        "run_id": run_id,
        "head_sha": head_sha,
        "run_attempt": run["run_attempt"],
        "workflow": run["path"],
        "run_status": run.get("status"),
        "run_conclusion": run.get("conclusion"),
        "required_jobs_missing": missing,
        "required_jobs_unsuccessful": failed,
        "latest_run_succeeded": not missing
        and not failed
        and run.get("status") == "completed"
        and run.get("conclusion") == "success",
        "latest_jobs": [
            {
                key: job.get(key)
                for key in ("id", "name", "run_attempt", "status", "conclusion", "html_url")
            }
            for job in jobs
        ],
        "superseded_same_run_checks": earlier,
        "scope": (
            "Exact run/latest attempt, including retained successful jobs; "
            "not PR rollup or merge eligibility. Earlier failures remain evidence."
        ),
    }


def collect(repository, run_id, head_sha):
    until = monotonic() + 120

    def api(endpoint):
        remaining = until - monotonic()
        if remaining <= 0:
            raise ValueError("CI diagnostic acquisition exceeded 120 seconds")
        return json.loads(
            subprocess.check_output(["gh", "api", endpoint], text=True, timeout=min(30, remaining))
        )

    def pages(endpoint, key):
        values = []
        seen = set()
        total = None
        for page in range(1, 21):
            data = api(f"{endpoint}&per_page=100&page={page}")
            if total is None:
                total = data["total_count"]
            if data["total_count"] != total:
                raise ValueError("CI job/check inventory changed during pagination")
            for item in data[key]:
                identity = item.get("id")
                if not isinstance(identity, int) or identity in seen:
                    raise ValueError("Invalid or repeated CI job/check ID")
                seen.add(identity)
                values.append(item)
            if len(values) == total:
                return values
            if not data[key] or len(values) > total:
                raise ValueError("Incomplete CI job/check pagination")
        raise ValueError("CI job/check inventory exceeds 20 pages")

    base = f"repos/{repository}"
    run = api(f"{base}/actions/runs/{run_id}")
    jobs = pages(f"{base}/actions/runs/{run_id}/jobs?filter=latest", "jobs")
    checks = pages(f"{base}/commits/{head_sha}/check-runs?filter=all", "check_runs")
    latest = api(f"{base}/actions/runs/{run_id}")
    if any(
        latest.get(key) != run.get(key)
        for key in ("head_sha", "run_attempt", "status", "conclusion")
    ):
        raise ValueError("Workflow attempt changed during acquisition; read again")
    return evaluate(run, jobs, checks, run_id=run_id, head_sha=head_sha)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", default="OpenT1D/lab")
    parser.add_argument("--run", required=True, type=int)
    parser.add_argument("--sha", required=True)
    args = parser.parse_args(argv)
    if (
        not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.repository)
        or not re.fullmatch(r"[0-9a-f]{40}", args.sha)
        or args.run < 1
    ):
        parser.error("Require owner/repository, positive run ID and full lowercase source SHA")
    try:
        receipt = collect(args.repository, args.run, args.sha)
    except (ValueError, KeyError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        return 2
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["latest_run_succeeded"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
