"""Bind Dependency Review's scanned changes to a complete GitHub API comparison."""

import base64
import binascii
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.github.com"
WARNING = "x-github-dependency-graph-snapshot-warnings"
MAX_BYTES = 8 * 1024 * 1024
MAX_PAGES = 100
# Match the pinned official Action: GitHub projects manifest rows per page.
PER_PAGE = 5
WAIT_SECONDS = 120


def decode(raw):
    def unique(pairs):
        result = {}
        for name, value in pairs:
            if name in result:
                raise ValueError("Duplicate dependency comparison field")
            result[name] = value
        return result

    def nonfinite(_value):
        raise ValueError("Nonfinite dependency comparison field")

    return json.loads(raw, object_pairs_hook=unique, parse_constant=nonfinite)


def fingerprint(changes):
    """Compare v5's full ChangeSchema without depending on response ordering."""
    if not isinstance(changes, list) or len(changes) > 10000:
        raise ValueError("Invalid or oversized dependency change inventory")
    records = []
    for change in changes:
        if (
            not isinstance(change, dict)
            or not isinstance(change.get("change_type"), str)
            or change["change_type"] not in {"added", "removed"}
        ):
            raise ValueError("Invalid dependency change")
        record = {"change_type": change["change_type"]}
        for key in ("manifest", "ecosystem", "name", "version", "package_url"):
            if not isinstance(change.get(key), str):
                raise ValueError("Invalid dependency identity field")
            record[key] = change[key]
        for key in ("license", "source_repository_url"):
            if key not in change or change[key] is not None and not isinstance(change[key], str):
                raise ValueError("Invalid nullable dependency identity field")
            record[key] = change[key]
        record["scope"] = change.get("scope", "unknown")
        if not isinstance(record["scope"], str) or record["scope"] not in {
            "runtime",
            "development",
            "unknown",
        }:
            raise ValueError("Invalid dependency scope")
        vulnerabilities = change.get("vulnerabilities", [])
        if not isinstance(vulnerabilities, list):
            raise ValueError("Invalid dependency vulnerability inventory")
        normalized = []
        for vulnerability in vulnerabilities:
            if not isinstance(vulnerability, dict):
                raise ValueError("Invalid dependency vulnerability")
            severity = vulnerability.get("severity", "low")
            if not isinstance(severity, str) or severity not in {
                "low",
                "moderate",
                "high",
                "critical",
            }:
                raise ValueError("Invalid dependency vulnerability severity")
            item = {"severity": severity}
            for key in ("advisory_ghsa_id", "advisory_summary", "advisory_url"):
                if not isinstance(vulnerability.get(key), str):
                    raise ValueError("Invalid dependency advisory identity")
                item[key] = vulnerability[key]
            normalized.append(json.dumps(item, sort_keys=True))
        record["vulnerabilities"] = sorted(normalized)
        records.append(json.dumps(record, sort_keys=True))
    return hashlib.sha256("\n".join(sorted(records)).encode()).hexdigest()


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        raise ValueError("Dependency API redirect refused")


def fetch_page(url, token, timeout):
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer " + token,
            "X-GitHub-Api-Version": "2026-03-10",
            "User-Agent": "OpenT1D-dependency-snapshot",
        },
    )
    with urllib.request.build_opener(NoRedirect()).open(request, timeout=timeout) as response:
        if response.status != 200:
            raise ValueError("Dependency API did not return HTTP 200")
        raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError("Dependency API response exceeds its byte limit")
        return decode(raw), response.headers


def pagination(header, endpoint, current, announced_last=None):
    if header is None:
        if announced_last is not None and current != announced_last:
            raise ValueError("Dependency pagination ended before its announced last page")
        return None, announced_last
    links = {}
    for part in header.split(","):
        match = re.fullmatch(r'\s*<([^<>]+)>;\s*rel="(next|prev|first|last)"\s*', part)
        if match is None or match[2] in links:
            raise ValueError("Invalid or duplicate dependency pagination link")
        url = urllib.parse.urlsplit(match[1])
        target = urllib.parse.urlsplit(endpoint)
        query = urllib.parse.parse_qs(url.query, strict_parsing=True)
        if (
            (url.scheme, url.netloc, url.path) != (target.scheme, target.netloc, target.path)
            or url.fragment
            or set(query) != {"page", "per_page"}
            or query["per_page"] != [str(PER_PAGE)]
            or len(query["page"]) != 1
            or not re.fullmatch(r"[1-9][0-9]*", query["page"][0])
        ):
            raise ValueError("Dependency pagination escaped its exact comparison")
        links[match[2]] = int(query["page"][0])
    if announced_last is not None and (
        "last" in links
        and links["last"] != announced_last
        or current < announced_last
        and "last" not in links
    ):
        raise ValueError("Dependency pagination changed or lost its announced last page")
    announced_last = links.get("last", announced_last)
    following = links.get("next")
    if following is not None and following != current + 1:
        raise ValueError("Dependency pagination skipped or repeated a page")
    if (
        "first" in links
        and links["first"] != 1
        or "prev" in links
        and links["prev"] != current - 1
        or "last" in links
        and links["last"] < (following or current)
    ):
        raise ValueError("Dependency pagination bounds are inconsistent")
    if following is None and links.get("last", current) > current:
        raise ValueError("Dependency pagination omitted a required next page")
    if announced_last is not None and (
        current > announced_last
        or following is None
        and current != announced_last
        or following is not None
        and following > announced_last
    ):
        raise ValueError("Dependency pagination ended outside its announced last page")
    return following, announced_last


def comparison(endpoint, token, deadline, *, fetch=fetch_page):
    changes, warned = [], False
    page, announced_last = 1, None
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0 or page > MAX_PAGES:
            raise ValueError("Dependency comparison exceeded its time or page limit")
        data, headers = fetch(
            endpoint + f"?per_page={PER_PAGE}&page={page}", token, min(30, remaining)
        )
        fingerprint(data)  # Validate every page, including pages that report warnings.
        changes.extend(data)
        values = headers.get_all(WARNING, [])
        if len(values) > 1:
            raise ValueError("Duplicate dependency snapshot warning header")
        if values:
            if len(values[0]) > 16384:
                raise ValueError("Dependency snapshot warning header is too large")
            warning = base64.b64decode(values[0], validate=True).decode("utf-8")
            warned |= bool(warning.strip())
        links = headers.get_all("Link", [])
        if len(links) > 1:
            raise ValueError("Duplicate dependency pagination header")
        following, announced_last = pagination(
            links[0] if links else None, endpoint, page, announced_last
        )
        if time.monotonic() >= deadline:
            raise ValueError("Dependency comparison exceeded its time deadline")
        if following is None:
            return changes, warned, page
        page = following


def verify(
    repository,
    base,
    head,
    token,
    scanned,
    *,
    repository_id,
    fetch=fetch_page,
    wait=WAIT_SECONDS,
):
    if not re.fullmatch(r"[A-Za-z0-9_-]+/[A-Za-z0-9_.-]+", repository) or repository.split("/")[
        -1
    ] in {".", ".."}:
        raise ValueError("Invalid dependency review repository")
    if not isinstance(repository_id, str) or not re.fullmatch(r"[1-9][0-9]{0,19}", repository_id):
        raise ValueError("Invalid dependency review repository ID")
    if not all(re.fullmatch(r"[0-9a-f]{40}", value) for value in (base, head)):
        raise ValueError("Dependency review requires exact commit SHAs")
    if not token or not token.isascii() or any(ord(character) < 33 for character in token):
        raise ValueError("Invalid or absent dependency API token")
    expected = fingerprint(scanned)
    endpoint = f"{API}/repositories/{repository_id}/dependency-graph/compare/{base}...{head}"
    started = time.monotonic()
    deadline, attempts = started + wait, 0
    while True:
        attempts += 1
        changes, warned, pages = comparison(endpoint, token, deadline, fetch=fetch)
        if not warned:
            actual = fingerprint(changes)
            finished = time.monotonic()
            if finished >= deadline:
                raise ValueError("Dependency comparison exceeded its validation deadline")
            if actual != expected:
                raise ValueError("Dependency Review did not scan the complete current comparison")
            return {
                "schema": "opent1d.dependency-snapshot/1",
                "base_sha": base,
                "head_sha": head,
                "changes_sha256": expected,
                "change_count": len(changes),
                "pages": pages,
                "attempts": attempts,
                "elapsed_seconds": finished - started,
                "snapshot_warnings": False,
            }
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ValueError("Dependency snapshots remained incomplete at the deadline")
        time.sleep(min(5, remaining))


def main():
    try:
        raw = os.environ["DEPENDENCY_CHANGES"]
        if len(raw.encode()) > MAX_BYTES:
            raise ValueError("Dependency Review output exceeds its byte limit")
        result = verify(
            os.environ["GITHUB_REPOSITORY"],
            os.environ["PR_BASE_SHA"],
            os.environ["PR_HEAD_SHA"],
            os.environ["GITHUB_TOKEN"],
            decode(raw),
            repository_id=os.environ["GITHUB_REPOSITORY_ID"],
        )
        print(json.dumps(result, sort_keys=True))
        return 0
    except urllib.error.HTTPError as error:
        print(f"Dependency API failed with HTTP {error.code}", file=sys.stderr)
    except (ValueError, binascii.Error) as error:
        print("Dependency snapshot verification failed: " + str(error), file=sys.stderr)
    except (KeyError, OSError, RecursionError):
        print(
            "Dependency snapshot verification failed; inspect the comparison or retry",
            file=sys.stderr,
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
