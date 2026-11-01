"""Latest-attempt diagnostics never select a green check by name or maximum ID."""

import copy
import json
import unittest
from unittest.mock import patch

from scripts import ci_run_status as status


class RunStatusTests(unittest.TestCase):
    def setUp(self):
        self.run = {
            "id": 123,
            "head_sha": "a" * 40,
            "run_attempt": 2,
            "path": ".github/workflows/checks.yml",
            "event": "pull_request",
            "status": "completed",
            "conclusion": "success",
            "repository": {"full_name": "OpenT1D/lab"},
        }
        self.jobs = [
            {
                "id": i,
                "run_id": 123,
                "head_sha": "a" * 40,
                "run_attempt": 1 if name == "Dependency review" else 2,
                "name": name,
                "status": "completed",
                "conclusion": "success",
                "html_url": f"https://github.com/OpenT1D/lab/actions/runs/123/job/{i}",
            }
            for i, name in enumerate(sorted(status.EXPECTED), 1)
        ]

    def read(self, jobs=None, checks=()):
        return status.evaluate(
            self.run, self.jobs if jobs is None else jobs, checks, run_id=123, head_sha="a" * 40
        )

    def test_current_success_and_retained_jobs_preserve_earlier_failed_checks(self):
        old = {
            "id": 999999,
            "name": "Repository checks",
            "status": "completed",
            "conclusion": "failure",
            "details_url": "https://github.com/OpenT1D/lab/actions/runs/123/job/999999",
        }
        report = self.read(checks=[old])
        self.assertTrue(report["latest_run_succeeded"])
        self.assertEqual(report["superseded_same_run_checks"], [old])
        self.assertIn("not PR rollup", report["scope"])
        self.assertIn(1, {job["run_attempt"] for job in report["latest_jobs"]})

    def test_failed_cancelled_skipped_missing_and_unfinished_required_jobs_do_not_pass(self):
        for conclusion in ("failure", "cancelled", "skipped", None):
            for name in status.EXPECTED:
                jobs = copy.deepcopy(self.jobs)
                next(job for job in jobs if job["name"] == name)["conclusion"] = conclusion
                with self.subTest(name=name, conclusion=conclusion):
                    self.assertFalse(self.read(jobs)["latest_run_succeeded"])
        self.assertFalse(self.read(self.jobs[:-1])["latest_run_succeeded"])
        self.jobs[0]["status"] = "in_progress"
        self.assertFalse(self.read()["latest_run_succeeded"])

    def test_latest_failure_is_not_replaced_by_older_success_or_larger_check_id(self):
        next(job for job in self.jobs if job["name"] == "Repository checks")["conclusion"] = (
            "failure"
        )
        old = {
            "id": 999999,
            "name": "Repository checks",
            "conclusion": "success",
            "details_url": "https://github.com/OpenT1D/lab/actions/runs/123/job/999999",
        }
        self.assertFalse(self.read(checks=[old])["latest_run_succeeded"])

    def test_wrong_identity_duplicate_name_or_future_job_attempt_is_refused(self):
        for field, value in (
            ("id", 124),
            ("head_sha", "b" * 40),
            ("path", ".github/workflows/other.yml"),
            ("run_attempt", 0),
        ):
            original = copy.deepcopy(self.run)
            self.run[field] = value
            with self.assertRaises(ValueError):
                self.read()
            self.run = original
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.read(self.jobs + self.jobs[:1])
        for field, value in (("run_id", 124), ("head_sha", "b" * 40), ("run_attempt", 3)):
            jobs = copy.deepcopy(self.jobs)
            jobs[0][field] = value
            with self.assertRaises(ValueError):
                self.read(jobs)

    def test_only_the_dependency_review_skip_on_explicit_non_pr_events_is_accepted(self):
        next(job for job in self.jobs if job["name"] == "Dependency review")["conclusion"] = (
            "skipped"
        )
        for event, passed in (("pull_request", False), ("push", True), ("workflow_dispatch", True)):
            self.run["event"] = event
            self.assertEqual(self.read()["latest_run_succeeded"], passed)

    def test_pagination_fetches_latest_jobs_all_checks_and_detects_attempt_change(self):
        calls = []

        def api(command, **kwargs):
            endpoint = command[-1]
            calls.append(endpoint)
            if "/jobs?" in endpoint:
                page = int(endpoint.split("page=")[-1])
                return json.dumps(
                    {
                        "total_count": len(self.jobs),
                        "jobs": self.jobs[:2] if page == 1 else self.jobs[2:],
                    }
                )
            if "/check-runs?" in endpoint:
                return '{"total_count":0,"check_runs":[]}'
            return json.dumps(self.run)

        with patch.object(status.subprocess, "check_output", side_effect=api):
            self.assertTrue(status.collect("OpenT1D/lab", 123, "a" * 40)["latest_run_succeeded"])
        self.assertTrue(any("filter=latest" in call and "page=2" in call for call in calls))
        responses = [
            json.dumps(self.run),
            json.dumps({"total_count": len(self.jobs), "jobs": self.jobs}),
            '{"total_count":0,"check_runs":[]}',
            json.dumps(self.run | {"run_attempt": 3}),
        ]
        with (
            patch.object(status.subprocess, "check_output", side_effect=responses),
            self.assertRaisesRegex(ValueError, "attempt changed"),
        ):
            status.collect("OpenT1D/lab", 123, "a" * 40)

    def test_overlapping_check_pages_are_not_mistaken_for_complete_history(self):
        item = {"id": 999, "name": "old failure", "conclusion": "failure"}
        responses = [
            json.dumps(self.run),
            json.dumps({"total_count": len(self.jobs), "jobs": self.jobs}),
            json.dumps({"total_count": 2, "check_runs": [item]}),
            json.dumps({"total_count": 2, "check_runs": [item]}),
        ]
        with (
            patch.object(status.subprocess, "check_output", side_effect=responses),
            self.assertRaisesRegex(ValueError, "repeated"),
        ):
            status.collect("OpenT1D/lab", 123, "a" * 40)


if __name__ == "__main__":
    unittest.main()
