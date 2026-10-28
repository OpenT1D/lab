"""Incomplete dependency snapshots and optional PR checks cannot become green."""

import base64
import io
import os
import unittest
import urllib.error
from contextlib import redirect_stderr, redirect_stdout
from email.message import Message
from pathlib import Path
from unittest.mock import Mock, patch

import yaml

from scripts import dependency_snapshot as snapshot

ROOT = Path(__file__).resolve().parents[1]
BASE, HEAD = "a" * 40, "b" * 40
ENDPOINT = f"{snapshot.API}/repos/OpenT1D/lab/dependency-graph/compare/{BASE}...{HEAD}"
TOKEN = "synthetic-not-a-credential"


def change(name="tool", **values):
    return {
        "change_type": "added",
        "manifest": "uv.lock",
        "ecosystem": "pip",
        "name": name,
        "version": "1.0",
        "package_url": "pkg:pypi/" + name + "@1.0",
        "license": None,
        "source_repository_url": None,
        "scope": "development",
        "vulnerabilities": [],
        **values,
    }


def headers(*, warning=None, following=None):
    result = Message()
    if warning is not None:
        result[snapshot.WARNING] = base64.b64encode(warning.encode()).decode()
    if following is not None:
        result["Link"] = f'<{ENDPOINT}?per_page=100&page={following}>; rel="next"'
    return result


class SnapshotTests(unittest.TestCase):
    def verify(self, scanned, fetch, **kwargs):
        return snapshot.verify("OpenT1D/lab", BASE, HEAD, TOKEN, scanned, fetch=fetch, **kwargs)

    def test_complete_empty_and_reordered_comparisons_bind_the_full_scanned_inventory(self):
        for records in ([], [change(), change("other")]):
            with self.subTest(records=records):
                result = self.verify(records, Mock(return_value=(records[::-1], headers())))
                self.assertEqual(result["change_count"], len(records))
                self.assertEqual(result["changes_sha256"], snapshot.fingerprint(records))
                self.assertFalse(result["snapshot_warnings"])
                self.assertEqual(result["attempts"], 1)

    def test_all_page_warnings_survive_later_clean_pages_and_retry_the_whole_comparison(self):
        fetch = Mock(
            side_effect=[
                ([change()], headers(warning="Snapshot pending", following=2)),
                ([change("other")], headers(warning=" ")),
                ([change()], headers(following=2)),
                ([change("other")], headers()),
            ]
        )
        with patch.object(snapshot.time, "sleep"):
            result = self.verify([change(), change("other")], fetch)
        self.assertEqual(result["attempts"], 2)
        self.assertEqual(result["pages"], 2)
        self.assertEqual(
            [call.args[0] for call in fetch.call_args_list],
            [ENDPOINT + f"?per_page=100&page={page}" for page in (1, 2, 1, 2)],
        )

    def test_persistent_snapshot_warnings_stop_at_a_bounded_deadline(self):
        clock = [0.0]
        fetch = Mock(return_value=([], headers(warning="Still incomplete")))
        with (
            patch.object(snapshot.time, "monotonic", side_effect=lambda: clock[0]),
            patch.object(
                snapshot.time,
                "sleep",
                side_effect=lambda seconds: clock.__setitem__(0, clock[0] + seconds),
            ),
            self.assertRaisesRegex(ValueError, "time or page limit"),
        ):
            self.verify([], fetch, wait=11)
        self.assertEqual(clock[0], 11)
        self.assertEqual(fetch.call_count, 3)

    def test_action_partial_output_or_later_advisory_changes_cannot_pass_complete_api_data(self):
        advisory = {
            "severity": "high",
            "advisory_ghsa_id": "GHSA-synthetic",
            "advisory_summary": "Synthetic vulnerability",
            "advisory_url": "https://github.com/advisories/GHSA-synthetic",
        }
        for scanned, actual in (
            ([], [change()]),
            ([change()], [change(), change("missing")]),
            ([change()], [change(vulnerabilities=[advisory])]),
        ):
            with self.subTest(scanned=scanned), self.assertRaisesRegex(ValueError, "did not scan"):
                self.verify(scanned, Mock(return_value=(actual, headers())))

    def test_later_page_http_or_parse_failures_are_never_ignored(self):
        for error in (
            urllib.error.HTTPError(ENDPOINT, 503, "Unavailable", {}, None),
            ValueError("Bad JSON"),
        ):
            fetch = Mock(side_effect=[([change()], headers(following=2)), error])
            with self.subTest(error=error), self.assertRaises(type(error)):
                self.verify([change()], fetch)
            self.assertEqual(fetch.call_count, 2)

    def test_announced_last_page_cannot_disappear_or_change_between_responses(self):
        for mode in ("missing-link", "missing-last", "changed-last"):
            first = headers(following=2)
            first.replace_header(
                "Link", first["Link"] + f', <{ENDPOINT}?per_page=100&page=3>; rel="last"'
            )
            second = headers() if mode == "missing-link" else headers(following=3)
            third = [] if mode == "missing-link" else [change("third")]
            scanned = [change(), change("second"), *third]
            if mode == "changed-last":
                second.replace_header(
                    "Link", second["Link"] + f', <{ENDPOINT}?per_page=100&page=4>; rel="last"'
                )
            fetch = Mock(
                side_effect=[([change()], first), ([change("second")], second), (third, headers())]
            )
            with self.subTest(mode=mode), self.assertRaisesRegex(ValueError, "pagination"):
                self.verify(scanned, fetch)

        first = headers(following=2)
        first.replace_header(
            "Link", first["Link"] + f', <{ENDPOINT}?per_page=100&page=2>; rel="last"'
        )
        result = self.verify(
            [change(), change("second")],
            Mock(side_effect=[([change()], first), ([change("second")], headers())]),
        )
        self.assertEqual(result["pages"], 2)
        first = headers(following=2)
        first.replace_header(
            "Link", first["Link"] + f', <{ENDPOINT}?per_page=100&page=3>; rel="last"'
        )
        middle = headers(following=3)
        middle.replace_header(
            "Link", middle["Link"] + f', <{ENDPOINT}?per_page=100&page=3>; rel="last"'
        )
        fetch = Mock(
            side_effect=[([change()], first), ([change("second")], middle), ([], headers())]
        )
        self.assertEqual(self.verify([change(), change("second")], fetch)["pages"], 3)

    def test_deadline_expiring_during_fetch_or_final_validation_cannot_publish_success(self):
        original = snapshot.fingerprint
        for slow in ("fetch", "validation"):
            clock, calls = [0.0], [0]

            def fetch(*_args):
                if slow == "fetch":
                    clock[0] = 121.0
                return [], headers()

            def fingerprint(value):
                calls[0] += 1
                result = original(value)
                if slow == "validation" and calls[0] == 3:
                    clock[0] = 121.0
                return result

            with (
                self.subTest(slow=slow),
                patch.object(snapshot.time, "monotonic", side_effect=lambda: clock[0]),
                patch.object(snapshot, "fingerprint", side_effect=fingerprint),
                self.assertRaisesRegex(ValueError, "deadline|time"),
            ):
                self.verify([], fetch, wait=120)

    def test_pagination_refuses_foreign_targets_skips_cycles_duplicates_and_lost_next(self):
        for link in (
            '<https://attacker.invalid/path?per_page=100&page=2>; rel="next"',
            f'<{ENDPOINT}/other?per_page=100&page=2>; rel="next"',
            f'<{ENDPOINT}?per_page=100&page=1>; rel="next"',
            f'<{ENDPOINT}?per_page=100&page=3>; rel="next"',
            f'<{ENDPOINT}?per_page=100&page=2&page=3>; rel="next"',
            f'<{ENDPOINT}?per_page=100&page=2#fragment>; rel="next"',
            f'<{ENDPOINT}?per_page=100&page=2>; rel="last"',
            f'<{ENDPOINT}?per_page=100&page=2>; rel="next", '
            f'<{ENDPOINT}?per_page=100&page=1>; rel="last"',
            f'<{ENDPOINT}?per_page=100&page=1>; rel="prev"',
            f'<{ENDPOINT}?per_page=100&page=2>; rel="next", '
            f'<{ENDPOINT}?per_page=100&page=2>; rel="next"',
            "not-a-link",
        ):
            with self.subTest(link=link), self.assertRaises(ValueError):
                snapshot.pagination(link, ENDPOINT, 1)
        with (
            patch.object(snapshot, "MAX_PAGES", 1),
            self.assertRaisesRegex(ValueError, "page limit"),
        ):
            self.verify([], Mock(return_value=([], headers(following=2))))

    def test_malformed_or_duplicate_headers_are_not_warning_free(self):
        values = []
        for raw in ("not-base64!", base64.b64encode(b"\xff").decode()):
            item = Message()
            item[snapshot.WARNING] = raw
            values.append(item)
        warning = headers(warning="")
        warning[snapshot.WARNING] = ""
        values.append(warning)
        links = headers(following=2)
        links["Link"] = links["Link"]
        values.append(links)
        for item in values:
            with self.subTest(headers=item), self.assertRaises(ValueError):
                self.verify([], Mock(return_value=([], item)))

    def test_json_and_v5_schema_errors_fail_and_optional_fields_normalize(self):
        for raw in ('{"duplicate":1,"duplicate":2}', "[NaN]", "not-json"):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                snapshot.decode(raw)
        for value in (
            {},
            [None],
            [change(scope=[])],
            [change(change_type=[])],
            [change(vulnerabilities=None)],
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                snapshot.fingerprint(value)
        optional = change()
        optional.pop("scope")
        optional.pop("vulnerabilities")
        self.assertEqual(
            snapshot.fingerprint([optional]), snapshot.fingerprint([change(scope="unknown")])
        )
        self.assertNotEqual(
            snapshot.fingerprint([change()]), snapshot.fingerprint([change(), change()])
        )

    def test_bad_sha_repository_or_token_never_starts_a_request(self):
        for repository, base, head, token in (
            ("OpenT1D/lab", "main", HEAD, TOKEN),
            ("OpenT1D/lab", BASE, HEAD + ";echo bad", TOKEN),
            ("OpenT1D/../lab", BASE, HEAD, TOKEN),
            ("OpenT1D/..", BASE, HEAD, TOKEN),
            ("OpenT1D/lab", BASE, HEAD, ""),
            ("OpenT1D/lab", BASE, HEAD, "header\ninjection"),
        ):
            fetch = Mock()
            with self.subTest(repository=repository), self.assertRaises(ValueError):
                snapshot.verify(repository, base, head, token, [], fetch=fetch)
            fetch.assert_not_called()


class SnapshotTransportTests(unittest.TestCase):
    def test_transport_bounds_payload_pins_api_version_and_refuses_redirects(self):
        response = Mock(status=200, headers=Message())
        response.read.return_value = b"[]"
        opened = Mock()
        opened.__enter__ = Mock(return_value=response)
        opened.__exit__ = Mock(return_value=False)
        opener = Mock()
        opener.open.return_value = opened
        with patch.object(snapshot.urllib.request, "build_opener", return_value=opener):
            self.assertEqual(snapshot.fetch_page(ENDPOINT, TOKEN, 7), ([], response.headers))
            request = opener.open.call_args.args[0]
            self.assertEqual(request.full_url, ENDPOINT)
            self.assertEqual(request.get_header("Authorization"), "Bearer " + TOKEN)
            self.assertEqual(request.get_header("X-github-api-version"), "2026-03-10")
            response.read.assert_called_once_with(snapshot.MAX_BYTES + 1)
            response.status = 503
            with self.assertRaisesRegex(ValueError, "HTTP 200"):
                snapshot.fetch_page(ENDPOINT, TOKEN, 7)
            response.status = 200
            response.read.return_value = b"x" * (snapshot.MAX_BYTES + 1)
            with self.assertRaisesRegex(ValueError, "byte limit"):
                snapshot.fetch_page(ENDPOINT, TOKEN, 7)
        with self.assertRaisesRegex(ValueError, "redirect refused"):
            snapshot.NoRedirect().redirect_request(
                None, None, 302, None, None, "https://attacker.invalid"
            )

    def test_cli_errors_fail_without_a_success_receipt_or_token_disclosure(self):
        env = {
            "GITHUB_REPOSITORY": "OpenT1D/lab",
            "GITHUB_TOKEN": TOKEN,
            "PR_BASE_SHA": BASE,
            "PR_HEAD_SHA": HEAD,
            "DEPENDENCY_CHANGES": "[]",
        }
        for error in (
            urllib.error.HTTPError(ENDPOINT, 403, "Denied", {}, None),
            urllib.error.URLError("unavailable"),
            ValueError("comparison incomplete"),
        ):
            output, errors = io.StringIO(), io.StringIO()
            with (
                patch.dict(os.environ, env, clear=True),
                patch.object(snapshot, "verify", side_effect=error),
                redirect_stdout(output),
                redirect_stderr(errors),
            ):
                self.assertEqual(snapshot.main(), 1)
            self.assertEqual(output.getvalue(), "")
            self.assertNotIn(TOKEN, errors.getvalue())


class DependencyPolicyTests(unittest.TestCase):
    def test_review_is_read_only_pr_only_and_snapshot_proof_follows_the_full_action(self):
        workflow = yaml.safe_load((ROOT / ".github/workflows/checks.yml").read_text())
        job = workflow["jobs"]["dependency-review"]
        self.assertEqual(job["if"], "github.event_name == 'pull_request'")
        self.assertEqual(job["permissions"], {"contents": "read"})
        self.assertNotIn("continue-on-error", job)
        action, guard = job["steps"][1:3]
        self.assertEqual(action["id"], "review")
        self.assertEqual(
            action["uses"],
            "actions/dependency-review-action@a1d282b36b6f3519aa1f3fc636f609c47dddb294",
        )
        self.assertEqual(
            action["with"],
            {
                "base-ref": "${{ github.event.pull_request.base.sha }}",
                "head-ref": "${{ github.event.pull_request.head.sha }}",
                "fail-on-severity": "high",
                "fail-on-scopes": "runtime, development, unknown",
                "vulnerability-check": True,
                "license-check": False,
                "warn-only": False,
                "comment-summary-in-pr": "never",
                "show-openssf-scorecard": False,
                "retry-on-snapshot-warnings": True,
                "retry-on-snapshot-warnings-timeout": 120,
            },
        )
        self.assertNotIn("if", guard)
        self.assertEqual(
            guard["env"]["DEPENDENCY_CHANGES"], "${{ steps.review.outputs.dependency-changes }}"
        )
        self.assertIn("python3 scripts/dependency_snapshot.py", guard["run"])
        for step in job["steps"]:
            self.assertNotIn("continue-on-error", step)

    def test_monthly_updates_are_only_root_uv_and_actions_with_native_and_asset_exclusions(self):
        data = yaml.safe_load((ROOT / ".github/dependabot.yml").read_text())
        self.assertEqual(data["version"], 2)
        updates = {value["package-ecosystem"]: value for value in data["updates"]}
        self.assertEqual(set(updates), {"uv", "github-actions"})
        self.assertEqual(len(data["updates"]), 2)
        for config in updates.values():
            self.assertEqual(
                set(config),
                {
                    "package-ecosystem",
                    "directory",
                    "schedule",
                    "open-pull-requests-limit",
                    "groups",
                    "ignore",
                }
                | ({"exclude-paths"} if config["package-ecosystem"] == "uv" else set()),
            )
            self.assertEqual(config["directory"], "/")
            self.assertEqual(config["schedule"], {"interval": "monthly"})
            self.assertEqual(config["open-pull-requests-limit"], 3)
        self.assertEqual(
            updates["uv"]["exclude-paths"], ["experiments/**", "packaging/**", "tests/**"]
        )
        self.assertFalse((ROOT / ".github/dependabot.example.yml").exists())

    def test_group_filter_and_global_major_ignore_both_require_manual_major_proposals(self):
        data = yaml.safe_load((ROOT / ".github/dependabot.yml").read_text())
        groups = {"github-actions": "actions", "uv": "repository-tooling"}
        for config in data["updates"]:
            ecosystem = config["package-ecosystem"]
            with self.subTest(ecosystem=ecosystem, layer="group"):
                self.assertEqual(
                    config["groups"],
                    {groups[ecosystem]: {"patterns": ["*"], "update-types": ["minor", "patch"]}},
                )
            # Unmatched major updates otherwise become individual PRs. Group
            # filtering alone does not disable that independent update path.
            with self.subTest(ecosystem=ecosystem, layer="global-major-ignore"):
                self.assertEqual(
                    config.get("ignore"),
                    [{"dependency-name": "*", "update-types": ["version-update:semver-major"]}],
                )


if __name__ == "__main__":
    unittest.main()
