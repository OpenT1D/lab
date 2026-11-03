"""Fake capture controls only; never invokes the OS collector or sysctl."""

import copy
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from experiments.lt1_diagnostic import host_context as context


def invented_context():
    values = (
        "11111111-1111-1111-1111-111111111111",
        "22222222-2222-2222-2222-222222222222",
        "26Z999",
        "26.9.0",
    )
    return {
        "schema": context.SCHEMA,
        "kind": "read-only-observation",
        "host": {"platform": "darwin", "machine": "arm64", "hostname": "invented-host", "uid": 123},
        "observer": {"pid": 123, "ppid": 122, "posix_session": 120, "start": "darwin:123:456"},
        "collector_identity": {
            "implementation": {"experiments/lt1_diagnostic/host_context.py": "a" * 64},
            "python": "3.12.0",
            "executable_sha256": "b" * 64,
        },
        "sysctl_sha256": "c" * 64,
        "queries": {
            k: {"returncode": 0, "value": v, "error": None} for k, v in zip(context.KEYS, values)
        },
        "observed_from": "2026-01-01T00:00:00Z",
        "observed_to": "2026-01-01T00:00:01Z",
        "status": "observed",
        "unknown": [],
    }


class HostContextTests(unittest.TestCase):
    def fake_capture(self, query=None, tool=None, observers=None, sources=None):
        fake = invented_context()
        with (
            patch.object(context, "ROOT", Path("/invented/repo")),
            patch.object(
                context, "__file__", "/invented/repo/experiments/lt1_diagnostic/host_context.py"
            ),
            patch.object(
                context, "_source_identity", side_effect=sources or [fake["collector_identity"]] * 2
            ),
            patch.object(context, "_observer", side_effect=observers or [fake["observer"]] * 2),
            patch.object(context, "_tool_digest", side_effect=tool or ["c" * 64] * 2),
            patch.object(
                context, "_query", side_effect=query or (lambda k: fake["queries"][k])
            ) as queries,
            patch.object(context.sys, "platform", "darwin"),
            patch.object(context.platform, "machine", return_value="arm64"),
            patch.object(context.socket, "gethostname", return_value="invented-host"),
            patch.object(context.os, "getuid", return_value=123),
        ):
            result = context.capture()
            self.assertEqual([c.args[0] for c in queries.call_args_list], list(context.KEYS))
            return result

    def test_complete_fake_capture_has_fixed_keys_and_no_login_claim(self):
        report = self.fake_capture()
        self.assertEqual(report["status"], "observed")
        self.assertEqual(report["unknown"], [])
        self.assertNotIn("login", report)
        self.assertNotIn("authorizations", report)
        self.assertEqual(set(report["observer"]), {"pid", "ppid", "posix_session", "start"})

    def test_unavailable_queries_remain_explicit_unknown(self):
        report = self.fake_capture(
            query=lambda _k: {"returncode": 1, "value": None, "error": "denied"}
        )
        self.assertEqual(report["status"], "unavailable")
        self.assertEqual(report["unknown"], sorted("query:" + k for k in context.KEYS))
        self.assertTrue(all(v["value"] is None for v in report["queries"].values()))

    def test_observer_or_tool_change_refuses(self):
        fake = invented_context()
        for kwargs in (
            {"observers": [fake["observer"], {**fake["observer"], "start": "different"}]},
            {"tool": ["c" * 64, "d" * 64]},
            {
                "sources": [
                    fake["collector_identity"],
                    {**fake["collector_identity"], "python": "changed"},
                ]
            },
        ):
            with self.assertRaisesRegex(ValueError, "changed"):
                self.fake_capture(**kwargs)

    def test_offtree_collector_cannot_make_any_query(self):
        with (
            patch.object(context, "__file__", "/invented/offtree.py"),
            patch.object(context, "_query") as query,
            patch.object(context, "_observer") as observer,
        ):
            with self.assertRaisesRegex(ValueError, "canonical"):
                context.capture()
            query.assert_not_called()
            observer.assert_not_called()

    def test_query_is_fixed_and_nonzero_or_malformed_is_not_a_value(self):
        key = context.KEYS[0]
        completed = SimpleNamespace(
            returncode=0, stdout=b"11111111-1111-1111-1111-111111111111\n", stderr=b""
        )
        with patch.object(context.subprocess, "run", return_value=completed) as run:
            self.assertIsNone(context._query(key)["error"])
            self.assertEqual(run.call_args.args[0], ["/usr/sbin/sysctl", "-n", key])
            self.assertEqual(run.call_args.kwargs["env"], context.ENVIRONMENT)
            with self.assertRaisesRegex(ValueError, "fixed query"):
                context._query("caller-selected-key")
            self.assertEqual(run.call_count, 1)
        for code, raw in ((1, completed.stdout), (0, b"not-a-UUID"), (0, b"0" * 5000)):
            with patch.object(
                context.subprocess,
                "run",
                return_value=SimpleNamespace(returncode=code, stdout=raw, stderr=b""),
            ):
                self.assertIsNone(context._query(key)["value"])

    def test_zero_uuid_forged_observed_state_and_boolean_pid_refuse(self):
        fake = invented_context()
        fake["queries"][context.KEYS[0]]["value"] = "00000000-0000-0000-0000-000000000000"
        with self.assertRaisesRegex(ValueError, "unknown state"):
            context.validate(fake)
        fake["unknown"] = context.unknown_fields(fake)
        fake["status"] = "unavailable"
        self.assertEqual(context.validate(fake)["status"], "unavailable")
        fake["observer"]["pid"] = True
        with self.assertRaisesRegex(ValueError, "process identity"):
            context.validate(fake)

    def test_observer_reads_only_own_pid_and_missing_start_is_unknown(self):
        with (
            patch.object(context.os, "getpid", return_value=123),
            patch.object(context.os, "getppid", return_value=122),
            patch.object(context.os, "getsid", return_value=120),
            patch.object(context, "ProcessTable") as table,
        ):
            table.return_value.one.return_value = None
            self.assertIsNone(context._observer()["start"])
            table.return_value.one.assert_called_once_with(123)

    def test_observation_schema_and_interval_are_strict(self):
        for mutate in (
            lambda v: v.update(login_session="claimed"),
            lambda v: v.update(observed_to="2025-01-01T00:00:00Z"),
            lambda v: v.update(observed_from="2026-01-01T00:00:00"),
            lambda v: v["queries"][context.KEYS[0]].update(returncode=False),
        ):
            fake = copy.deepcopy(invented_context())
            mutate(fake)
            with self.assertRaises(ValueError):
                context.validate(fake)


if __name__ == "__main__":
    unittest.main()
