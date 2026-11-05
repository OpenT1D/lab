"""Portable loader contracts; no compiler, Mac profile or selected candidate run.

Positive addon reports below are invented assessment fixtures, not execution
evidence. Only the explicitly requested Mac experiment builds a valid addon.
"""

import base64
import copy
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path, PurePosixPath
from unittest.mock import patch

from experiments.lt1_diagnostic import native_route_loader_tooling as loader

ACTUAL_NODE_INFO = None


@unittest.skipUnless(shutil.which("node"), "Node required for invented loader controls")
class LT1NativeLoaderTests(unittest.TestCase):
    def test_invented_loader_controls(self):
        node = Path(shutil.which("node")).resolve()
        if loader.digest(node.read_bytes()) == loader.RUNTIME["executable_sha256"]:
            self.skipTest("selected candidate excluded; ordinary Node unavailable")
        result = subprocess.run(
            [str(node), "--test", "tests/lt1_native_loader.test.mjs"],
            cwd=Path(__file__).resolve().parents[1],
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


def snapshot(sha="a" * 64, *, mode=0o400, size=123, uid=501, inode=1):
    return {"identity": [1, inode, uid, mode, 1, size, 1, 1], "sha256": sha}


def outer(argv, *, pid=100, ppid=999):
    return {
        "argv": argv,
        "status": "completed",
        "exit_code": 0,
        "error": None,
        "cleanup_forced": False,
        "owned_processes": [
            {"pid": pid, "ppid": ppid, "pgid": pid, "start": "invented:1", "alive": False}
        ],
        "remaining_owned_processes": [],
        "received_signals": [],
    }


def log_data(raw):
    return {
        "snapshot": snapshot(loader.digest(raw), mode=0o600, size=len(raw)),
        "raw_b64": base64.b64encode(raw).decode(),
    }


def tools_data():
    node, sdk = "/private/tmp/c20-ordinary/bin/node", str(loader.SDK.parent / "MacOSX15.5.sdk")
    files = {
        str(p): snapshot(uid=0, mode=0o755)
        for p in (
            loader.CLANG,
            loader.LINKER,
            loader.SANDBOX,
            loader.DYLD,
            PurePosixPath(sdk) / "SDKSettings.json",
            PurePosixPath(sdk) / "usr/lib/libSystem.B.tbd",
            node,
        )
    }
    headers = {
        str(loader.HEADERS / name): snapshot(uid=0, mode=0o644)
        for name in (
            "node_api.h",
            "node_api_types.h",
            "js_native_api.h",
            "js_native_api_types.h",
            "node_version.h",
        )
    }
    return {
        "schema": "opent1d.lt1-c20-installed-toolchain/1",
        "node": node,
        "sdk": sdk,
        "files": files,
        "headers": headers,
    }


def success(sha=None, value=None):
    return {
        "status": "ok",
        "sha256": sha,
        "value": value,
        "error_code": None,
        "error_message": None,
    }


def failure(code="EPERM"):
    return {
        "status": "error",
        "sha256": None,
        "value": None,
        "error_code": code,
        "error_message": "invented bounded diagnostic",
    }


def changed_runtime(report, values, *, slots=(0, 1, 2)):
    """Alter the declared runtime coherently, including actual retained log pins."""
    for i in slots:
        record = report["records"][i]
        record["probe"]["runtime"].update(values)
        record["log"] = log_data(loader.encoded(record["probe"]) + b"\n")


def changed_processes(report, starts):
    for record, start in zip(report["records"], starts):
        record["outer"]["owned_processes"][0].update(pid=100, pgid=100, start=start)
        record["probe"]["runtime"]["pid"] = 100
        record["log"] = log_data(loader.encoded(record["probe"]) + b"\n")


def witness(source):
    """Closed synthetic full report, deliberately without a real compiled addon."""
    producer_root = PurePosixPath("/private/tmp/c20-reviewed-code")
    parent = PurePosixPath("/private/tmp/c20-invented-retained")
    context = {
        "parent": str(parent),
        "parent_identity": [1, 10, 501, 0o700],
        **{name: str(parent / name) for name in ("targets", "build", "records")},
        "directories": {
            str(parent / name): [1, 20 + i, 501, 0o500 if name == "targets" else 0o700]
            for i, name in enumerate(("targets", "build", "records"))
        },
        "owner_pid": 999,
    }
    tools = tools_data()
    module_sha = source["implementation"][loader.MODULE.relative_to(loader.ROOT).as_posix()]
    artifacts = {"module.mjs": snapshot(module_sha), "addon.node": snapshot("b" * 64, inode=2)}
    records = []
    for i, slot in enumerate(loader.SLOTS):
        entry = {
            "kind": "invented",
            "slot": slot,
            "nonce_sha256": str(i + 1) * 64,
            "owner_pid": 999,
            "targets": context["targets"],
        }
        operations = {
            "module_read": success(module_sha),
            "addon_read": success("b" * 64),
            "module_import": success(value="opent1d-c20-module/1"),
            "addon_load": success(value=51020),
        }
        if slot == "base":
            operations.update(
                module_read=failure(),
                module_import=failure("EACCES"),
                addon_load=failure("ERR_DLOPEN_FAILED"),
            )
        probe = {
            "schema": "opent1d.lt1-c20-loader-operations/1",
            "kind": "invented",
            "slot": slot,
            "nonce_sha256": entry["nonce_sha256"],
            "completed": True,
            "runtime": {
                "pid": 100 + i,
                "ppid": 999,
                "exec_path": tools["node"],
                "node": "v22.22.2",
                "platform": "darwin",
                "arch": "arm64",
                "napi": "10",
            },
            "operations": operations,
            "native_host_qualified": False,
            "native_execution_authorized": False,
        }
        policy = None
        argv = [
            tools["node"],
            str(producer_root / loader.SCRIPT.relative_to(loader.ROOT).as_posix()),
        ]
        if slot != "validity-control":
            policy = loader._profile(
                tools["node"],
                context["targets"],
                slot,
                parent / "records" / (slot + ".log"),
                source_root=producer_root,
            )
            argv = [str(loader.SANDBOX), "-p", policy, *argv]
        records.append(
            {
                "slot": slot,
                "entry": entry,
                "profile": policy,
                "outer": outer(argv, pid=100 + i),
                "log": log_data(loader.encoded(probe) + b"\n"),
                "probe": probe,
                "error": None,
                "status": "completed",
            }
        )
    preparation = []
    for i, scan in enumerate((True, False)):
        argv = loader._compile_argv(
            tools["sdk"], parent / "targets", parent / "build", scan=scan, source_root=producer_root
        )
        preparation.append(
            {
                "phase": "dependency-scan" if scan else "compile",
                "outer": outer(argv, pid=90 + i),
                "log": log_data(b""),
            }
        )
    addon = str(producer_root / loader.ADDON.relative_to(loader.ROOT).as_posix())
    closure = {
        name: copy.deepcopy(value)
        for name, value in tools["headers"].items()
        if not name.endswith("node_version.h")
    }
    closure[addon] = snapshot(
        source["implementation"][loader.ADDON.relative_to(loader.ROOT).as_posix()]
    )
    report = {
        "schema": "opent1d.lt1-c20-loader-witness/1",
        "kind": "invented",
        "scope": "ordinary-tooling-fixed-module-addon-only",
        "source_identity": source,
        "producer_root": str(producer_root),
        "toolchain": tools,
        "context": context,
        "preparation": preparation,
        "header_closure": closure,
        "initial_artifacts": artifacts,
        "final_artifacts": copy.deepcopy(artifacts),
        "records": records,
        "error": None,
        "all_slots_accounted": True,
        "scientific_sessions_run": False,
        "selected_candidate_started": False,
        **loader.AUTHORITY,
    }
    report["assessment"] = loader._assess(records, artifacts, artifacts, None)
    return report


class LoaderContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = loader.source_identity()

    def inspect(self, report, *, current=None):
        raw = loader.encoded(report)
        with patch.object(loader, "source_identity", return_value=current or self.source):
            return loader.inspect(raw, loader.digest(raw), expected_identity=current or self.source)

    def test_source_identity_owns_exact_four_new_sources(self):
        required = {
            "experiments/lt1_diagnostic/" + n
            for n in (
                "native_route_loader_tooling.py",
                "native_route_loader_tooling.mjs",
                "native_route_loader_module.mjs",
                "native_route_loader_addon.c",
            )
        }
        self.assertLessEqual(required, self.source["implementation"].keys())
        self.assertTrue(all(loader.AUTHORITY[k] is False for k in loader.AUTHORITY))

    def test_fixed_profile_delta_cannot_allow_addon_mapping_through_read_wildcard(self):
        root = PurePosixPath("/private/tmp/fresh-targets")
        node, log = "/ordinary/bin/node", "/private/tmp/base.log"
        base = loader._profile(node, root, "base", log)
        twin = loader._profile(node, root, "allow-twin", log)
        deny = '(deny file-map-executable (literal "/private/tmp/fresh-targets/addon.node"))\n'
        self.assertTrue(base.endswith(deny))
        self.assertEqual(
            twin,
            base.removesuffix(deny)
            + '(allow file-read-data (literal "/private/tmp/fresh-targets/module.mjs"))\n'
            '(allow file-map-executable (literal "/private/tmp/fresh-targets/addon.node"))\n',
        )
        self.assertEqual(base.count(str(root / "addon.node")), 2)
        self.assertNotIn(deny, twin)
        self.assertNotIn(
            '(allow file-map-executable (literal "' + str(root / "addon.node") + '"))', base
        )
        self.assertNotIn(str(root / "module.mjs"), base)
        self.assertIn('(allow file-read-data (literal "/ordinary/bin/node")', base)
        self.assertNotIn('(subpath "/private/tmp', base)
        self.assertNotIn("network", twin)
        with self.assertRaises(ValueError):
            loader._profile(node, root, "arbitrary", log)

    def test_compiler_recipe_fixes_compiler_linker_sdk_source_and_NAPI_without_invocation(self):
        sdk, targets, build = (
            PurePosixPath(p) for p in ("/fixed/sdk", "/fresh/targets", "/fresh/build")
        )
        source_root = PurePosixPath("/reviewed/ordinary-tooling-code")
        scan = loader._compile_argv(sdk, targets, build, scan=True, source_root=source_root)
        compile_ = loader._compile_argv(sdk, targets, build, scan=False, source_root=source_root)
        self.assertEqual(scan[0], str(loader.CLANG))
        self.assertIn("-M", scan)
        self.assertIn("-DNAPI_VERSION=8", compile_)
        self.assertIn("-nostdlib", compile_)
        self.assertIn("-fuse-ld=" + str(loader.LINKER), compile_)
        system_stub = str(sdk / "usr/lib/libSystem.B.tbd")
        self.assertIn(system_stub, compile_)
        self.assertNotIn(system_stub, scan)
        self.assertNotIn("-lSystem", compile_)
        self.assertNotIn("-L", compile_)
        self.assertEqual(
            compile_[-1], str(source_root / loader.ADDON.relative_to(loader.ROOT).as_posix())
        )
        self.assertNotIn("npm", compile_)

    def test_typed_probe_and_actual_marker_are_distinct_checks(self):
        report = witness(self.source)
        first = report["records"][0]
        loader._validate_probe(first["probe"], first["entry"], report["toolchain"]["node"])
        for change in (
            lambda p: p.update(completed=1),
            lambda p: p.update(native_host_qualified=True),
            lambda p: p["runtime"].update(ppid=1),
            lambda p: p["operations"]["addon_load"].update(value=True),
            lambda p: p["operations"].update(extra={}),
        ):
            altered = copy.deepcopy(first["probe"])
            change(altered)
            with self.assertRaises(ValueError):
                loader._validate_probe(altered, first["entry"], report["toolchain"]["node"])
        altered = copy.deepcopy(report)
        altered["records"][0]["probe"]["operations"]["addon_load"]["value"] = 0
        self.assertEqual(
            loader._assess(
                altered["records"], altered["initial_artifacts"], altered["final_artifacts"], None
            )["state"],
            "inconclusive",
        )

    def test_matched_assessment_needs_valid_target_twin_parent_and_real_denominators(self):
        report = witness(self.source)
        self.assertEqual(self.inspect(report)["state"], "matched-policy-effect")
        for change in (
            lambda r: r["records"][0].update(probe=None),
            lambda r: r["records"][2]["probe"]["operations"].update(
                addon_load=failure("ERR_DLOPEN_FAILED")
            ),
            lambda r: r["records"][1]["probe"]["operations"].update(module_read=failure("ENOENT")),
            lambda r: r["final_artifacts"]["addon.node"].update(sha256="c" * 64),
            lambda r: r.update(error="incomplete parent cleanup"),
            lambda r: r["records"][0]["outer"].update(remaining_owned_processes=None),
        ):
            altered = copy.deepcopy(report)
            change(altered)
            result = loader._assess(
                altered["records"],
                altered["initial_artifacts"],
                altered["final_artifacts"],
                altered["error"],
            )
            self.assertEqual(result["state"], "inconclusive")
            self.assertTrue(all(result[k] is False for k in loader.AUTHORITY))
        unconfined = copy.deepcopy(report)
        unconfined["records"][1]["probe"]["operations"] = copy.deepcopy(
            unconfined["records"][0]["probe"]["operations"]
        )
        self.assertEqual(
            loader._assess(
                unconfined["records"],
                unconfined["initial_artifacts"],
                unconfined["final_artifacts"],
                None,
            )["state"],
            "base-unconfined",
        )

    def test_cold_reader_rejects_contradictory_slot_status_and_execution_prefixes(self):
        report = witness(self.source)
        for status in ("not-run", "incomplete"):
            changed = copy.deepcopy(report)
            for record in changed["records"]:
                record["status"] = status
            changed["assessment"] = loader._assess(
                changed["records"],
                changed["initial_artifacts"],
                changed["final_artifacts"],
                changed["error"],
            )
            self.assertEqual(changed["assessment"]["state"], "inconclusive")
            self.assertFalse(changed["assessment"]["checks"]["all_owned_slots_complete"])
            with self.subTest(status=status), self.assertRaises(ValueError):
                self.inspect(changed)
        changed = copy.deepcopy(report)
        changed["error"] = "invented failure"
        changed["records"][0].update(status="incomplete", error=changed["error"])
        changed["assessment"] = loader._assess(
            changed["records"],
            changed["initial_artifacts"],
            changed["final_artifacts"],
            changed["error"],
        )
        with self.assertRaisesRegex(ValueError, "sequential loader outcome prefix"):
            self.inspect(changed)

    def test_cold_reader_retains_each_actual_incomplete_loader_prefix(self):
        for index in range(len(loader.SLOTS)):
            for outer_started in (False, True):
                with self.subTest(index=index, outer_started=outer_started):
                    report = witness(self.source)
                    report.update(error="invented loader interruption", final_artifacts={})
                    record = report["records"][index]
                    record.update(
                        status="incomplete" if outer_started else "not-run",
                        error=report["error"],
                    )
                    if not outer_started:
                        record.update(outer=None, log=None, probe=None)
                    for later in report["records"][index + 1 :]:
                        later.update(
                            entry=None,
                            profile=None,
                            outer=None,
                            log=None,
                            probe=None,
                            status="not-run",
                            error=report["error"],
                        )
                    report["assessment"] = loader._assess(
                        report["records"], report["initial_artifacts"], {}, report["error"]
                    )
                    self.assertEqual(self.inspect(report)["state"], "inconclusive")
                    for corrupt in (
                        "missing-parent-error",
                        "mismatched-slot-error",
                        "missing-artifacts",
                    ):
                        altered = copy.deepcopy(report)
                        if corrupt == "missing-parent-error":
                            altered["error"] = None
                        elif corrupt == "mismatched-slot-error":
                            altered["records"][index]["error"] = "other failure"
                        else:
                            altered["initial_artifacts"] = {}
                        altered["assessment"] = loader._assess(
                            altered["records"], altered["initial_artifacts"], {}, altered["error"]
                        )
                        with self.subTest(corrupt=corrupt), self.assertRaises(ValueError):
                            self.inspect(altered)

    def test_cold_reader_consumes_owned_bytes_without_reopening_any_historical_tools(self):
        report = witness(self.source)
        with (
            patch.object(
                loader, "toolchain_identity", side_effect=AssertionError("historical tools")
            ),
            patch.object(loader, "_snapshot", side_effect=AssertionError("historical path")),
            patch.object(loader.subprocess, "Popen", side_effect=AssertionError("cold process")),
        ):
            self.assertEqual(self.inspect(report), report["assessment"])
            partial = copy.deepcopy(report)
            target = partial["context"]["targets"]
            partial["context"]["directories"] = {target: [1, 20, 501, 0o700]}
            partial.update(
                preparation=[],
                header_closure={},
                initial_artifacts={},
                final_artifacts={},
                error="incomplete directory preparation",
            )
            for record in partial["records"]:
                record.update(
                    entry=None,
                    profile=None,
                    outer=None,
                    log=None,
                    probe=None,
                    error=partial["error"],
                    status="not-run",
                )
            partial["assessment"] = loader._assess(partial["records"], {}, {}, partial["error"])
            self.assertEqual(self.inspect(partial)["state"], "inconclusive")
            reuse = copy.deepcopy(report)
            changed_processes(reuse, ("invented:100", "invented:101", "invented:102"))
            self.assertEqual(self.inspect(reuse), report["assessment"])

    def test_cold_reader_rejects_rehashed_context_profile_outer_log_and_source_drift(self):
        report = witness(self.source)
        variants = (
            lambda r: r["toolchain"]["files"].pop(
                str(PurePosixPath(r["toolchain"]["sdk"]) / "usr/lib/libSystem.B.tbd")
            ),
            lambda r: r["context"]["directories"].pop(r["context"]["build"]),
            lambda r: r["context"]["directories"].pop(r["context"]["records"]),
            lambda r: r["context"]["directories"][r["context"]["build"]].__setitem__(
                slice(0, 2), r["context"]["directories"][r["context"]["records"]][:2]
            ),
            lambda r: r["records"][0]["log"]["snapshot"]["identity"].__setitem__(2, 0),
            lambda r: r["preparation"][0]["log"]["snapshot"]["identity"].__setitem__(2, 0),
            lambda r: changed_processes(r, ("invented:1", "invented:1", "invented:1")),
            lambda r: r["preparation"][1]["outer"].update(
                owned_processes=copy.deepcopy(r["preparation"][0]["outer"]["owned_processes"])
            ),
            lambda r: changed_runtime(r, {"platform": "linux"}),
            lambda r: changed_runtime(r, {"arch": "x64"}),
            lambda r: changed_runtime(r, {"napi": "7"}),
            lambda r: changed_runtime(r, {"napi": "08"}),
            lambda r: changed_runtime(r, {"node": "22.22.2"}),
            lambda r: changed_runtime(r, {"node": "v022.22.2"}),
            lambda r: changed_runtime(r, {"node": "v22.22.2\n"}),
            lambda r: changed_runtime(r, {"node": "v22.22.3"}, slots=(2,)),
            lambda r: changed_runtime(r, {"napi": "9"}, slots=(2,)),
            lambda r: r["records"][1].update(profile=r["records"][2]["profile"]),
            lambda r: r["records"][0]["outer"]["argv"].append("foreign"),
            lambda r: r["records"][0]["log"].update(raw_b64="e30K"),
            lambda r: r["records"][2]["entry"].update(
                nonce_sha256=r["records"][0]["entry"]["nonce_sha256"]
            ),
            lambda r: r["context"].update(targets="/usr/lib/targets"),
            lambda r: r["toolchain"]["files"][r["toolchain"]["node"]].update(
                sha256=loader.RUNTIME["executable_sha256"]
            ),
            lambda r: r["source_identity"]["implementation"].update(
                {loader.SOURCE_FILES[0]: "f" * 64}
            ),
            lambda r: r["header_closure"].pop(
                next(k for k in r["header_closure"] if k.endswith(".c"))
            ),
            lambda r: r["header_closure"].pop(str(loader.HEADERS / "js_native_api.h")),
            lambda r: r["initial_artifacts"]["module.mjs"].update(sha256="f" * 64),
        )
        for i, change in enumerate(variants):
            altered = copy.deepcopy(report)
            change(altered)
            with self.subTest(counterexample=i), self.assertRaises(ValueError):
                self.inspect(altered)
        raw = loader.encoded(report)
        with self.assertRaisesRegex(ValueError, "externally pinned"):
            loader.inspect(raw, "f" * 64, expected_identity=self.source)

    def test_historical_full_audit_is_data_and_only_three_authority_fields_can_change(self):
        source = copy.deepcopy(self.source)
        source["implementation"].update({n: "a" * 64 for n in loader.AUTHORITY_FILES})
        report = witness(source)
        current = copy.deepcopy(source)
        for name in loader.AUTHORITY_FILES:
            current["implementation"][name] = "f" * 64
        self.assertEqual(self.inspect(report, current=current), report["assessment"])
        self.assertEqual(report["source_identity"], source)
        bad = copy.deepcopy(current)
        bad["implementation"][loader.SOURCE_FILES[0]] = "e" * 64
        with self.assertRaisesRegex(ValueError, "code/Python"):
            self.inspect(report, current=bad)

    def test_owned_completion_requires_real_nonempty_unique_rooted_unforced_ownership(self):
        report = witness(self.source)
        self.assertEqual(self.inspect(report)["state"], "matched-policy-effect")
        variants = (
            lambda r: r["records"][0]["outer"].update(owned_processes=[]),
            lambda r: r["records"][1]["outer"]["owned_processes"].append(
                copy.deepcopy(r["records"][1]["outer"]["owned_processes"][0])
            ),
            lambda r: r["records"][2]["outer"].update(cleanup_forced=True),
            lambda r: r["records"][0]["outer"]["owned_processes"][0].update(pgid=7),
            lambda r: r["records"][0]["outer"]["owned_processes"][0].update(start=""),
            lambda r: r["records"][0]["outer"]["owned_processes"][0].update(ppid=100),
        )
        for change in variants:
            altered = copy.deepcopy(report)
            change(altered)
            self.assertEqual(
                loader._assess(
                    altered["records"],
                    altered["initial_artifacts"],
                    altered["final_artifacts"],
                    None,
                )["state"],
                "inconclusive",
            )
            with self.assertRaises(ValueError):
                self.inspect(altered)
        for change in (
            lambda r: r["preparation"][0]["outer"].update(owned_processes=[]),
            lambda r: r["preparation"][1]["outer"]["owned_processes"][0].update(ppid=998),
            lambda r: r["records"][2]["entry"].update(owner_pid=998),
        ):
            altered = copy.deepcopy(report)
            change(altered)
            with self.assertRaises(ValueError):
                self.inspect(altered)
        # First-observed alive=True is historical evidence, not final liveness.
        historical = copy.deepcopy(report)
        for item in [*historical["preparation"], *historical["records"]]:
            item["outer"]["owned_processes"][0]["alive"] = True
        self.assertEqual(self.inspect(historical), report["assessment"])


@unittest.skipUnless(os.name == "posix", "private descriptor fixtures require POSIX")
class LoaderPreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = loader.source_identity()

    def test_missing_installed_compiler_retains_three_slots_without_path_or_process_intake(self):
        class Bomb:
            def __fspath__(self):
                raise AssertionError("caller path before tools")

        with (
            patch.object(loader, "source_identity", return_value=self.source),
            patch.object(loader.sys, "platform", "darwin"),
            patch.object(loader.platform, "machine", return_value="arm64"),
            patch.object(
                loader, "toolchain_identity", side_effect=OSError("fixed compiler missing")
            ),
            patch.object(loader, "_owned", side_effect=AssertionError("compiler invoked")),
        ):
            result = loader.capture(Bomb(), expected_identity=self.source, expected_toolchain=None)
        self.assertEqual([r["slot"] for r in result["records"]], list(loader.SLOTS))
        self.assertTrue(result["all_slots_accounted"])
        self.assertTrue(all(r["status"] == "not-run" for r in result["records"]))
        self.assertIsNone(result["parent_witness_sha256"])
        self.assertFalse(result["private_evidence_may_remain"])
        self.assertEqual(result["assessment"]["state"], "inconclusive")

    def test_preparation_and_witness_ENOSPC_keep_partial_bytes_without_a_pin(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary).resolve()
            original_create = loader._create

            def no_space(path, raw):
                original_create(path, b"{")
                raise OSError(28, "invented ENOSPC")

            tools = tools_data()
            with (
                patch.object(loader, "source_identity", return_value=self.source),
                patch.object(loader.sys, "platform", "darwin"),
                patch.object(loader.platform, "machine", return_value="arm64"),
                patch.object(loader, "toolchain_identity", return_value=tools),
                patch.object(loader, "_create", side_effect=no_space),
                patch.object(loader, "_owned", side_effect=AssertionError("compiler invoked")),
            ):
                result = loader.capture(
                    parent, expected_identity=self.source, expected_toolchain=tools
                )
            self.assertTrue(result["all_slots_accounted"])
            self.assertTrue(all(r["outer"] is None for r in result["records"]))
            self.assertIsNone(result["parent_witness_sha256"])
            self.assertIn("ENOSPC", result["parent_witness_error"])
            self.assertTrue(result["private_evidence_may_remain"])
            self.assertEqual((parent / "targets/module.mjs").read_bytes(), b"{")
            self.assertEqual((parent / "loader-result.json").read_bytes(), b"{")

    def test_failed_owned_preparation_retains_real_prefix_and_cold_incomplete_observation(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary).resolve()
            tools = tools_data()

            def failed_scan(argv, log, guard):
                guard()
                loader._create(log, b"invented unavailable compiler diagnostic\n")
                result = outer(argv, ppid=os.getpid())
                result.update(status="failed", exit_code=1, error="invented compiler unavailable")
                return result

            with (
                patch.object(loader, "source_identity", return_value=self.source),
                patch.object(loader.sys, "platform", "darwin"),
                patch.object(loader.platform, "machine", return_value="arm64"),
                patch.object(loader, "toolchain_identity", return_value=tools),
                patch.object(loader, "_owned", side_effect=failed_scan) as owned,
            ):
                result = loader.capture(
                    parent, expected_identity=self.source, expected_toolchain=tools
                )
                self.assertEqual(owned.call_count, 1)
                self.assertEqual([r["slot"] for r in result["records"]], list(loader.SLOTS))
                self.assertTrue(all(r["outer"] is None for r in result["records"]))
                self.assertEqual(result["preparation"][0]["outer"]["exit_code"], 1)
                raw = (parent / "loader-result.json").read_bytes()
                with patch.object(
                    loader, "toolchain_identity", side_effect=AssertionError("old tools")
                ):
                    self.assertEqual(
                        loader.inspect(
                            raw, result["parent_witness_sha256"], expected_identity=self.source
                        )["state"],
                        "inconclusive",
                    )

    def test_changed_toolchain_before_scan_stops_before_any_compiler_process(self):
        with tempfile.TemporaryDirectory() as temporary:
            tools = tools_data()
            changed = copy.deepcopy(tools)
            changed["files"][str(loader.LINKER)]["sha256"] = "f" * 64
            with (
                patch.object(loader, "source_identity", return_value=self.source),
                patch.object(loader.sys, "platform", "darwin"),
                patch.object(loader.platform, "machine", return_value="arm64"),
                patch.object(loader, "toolchain_identity", side_effect=[tools, changed]),
                patch.object(loader, "_owned", side_effect=AssertionError("compiler after drift")),
            ):
                result = loader.capture(
                    Path(temporary).resolve(),
                    expected_identity=self.source,
                    expected_toolchain=tools,
                )
            self.assertIn("source/toolchain drift", result["error"])
            self.assertTrue(result["all_slots_accounted"])
            self.assertTrue(all(r["outer"] is None for r in result["records"]))
            self.assertEqual(result["assessment"]["state"], "inconclusive")

    def test_dependency_closure_reads_actual_fresh_bytes_and_refuses_unknown_or_duplicate_paths(
        self,
    ):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary).resolve()
            headers, resources, sdk = (parent / n for n in ("headers", "resources", "sdk"))
            for path in (headers, resources, sdk):
                path.mkdir()
            source, header = parent / "addon.c", headers / "node_api.h"
            source.write_bytes(b"fresh invented C data")
            header.write_bytes(b"fresh invented header")
            raw = f"c20-addon: {source} {header}\n".encode()
            with (
                patch.object(loader, "ADDON", source),
                patch.object(loader, "HEADERS", headers),
                patch.object(loader, "RESOURCES", resources),
            ):
                before = loader._dependencies(raw, sdk)
                header.write_bytes(b"changed header")
                self.assertNotEqual(loader._dependencies(raw, sdk), before)
                with self.assertRaises(ValueError):
                    loader._dependencies(raw + str(header).encode(), sdk)
                foreign = parent / "foreign.h"
                foreign.write_bytes(b"unknown")
                with self.assertRaisesRegex(ValueError, "fixed header/source"):
                    loader._dependencies(raw.rstrip() + b" " + str(foreign).encode() + b"\n", sdk)


@unittest.skipUnless(
    os.name == "posix" and shutil.which("node"), "ordinary POSIX Node fixture required"
)
class OrdinaryLoaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.node = Path(shutil.which("node")).resolve()
        cls.node_snapshot = loader._snapshot(cls.node)
        if cls.node_snapshot["sha256"] == loader.RUNTIME["executable_sha256"]:
            raise unittest.SkipTest("selected candidate excluded; ordinary Node unavailable")

    def test_real_module_parser_and_invalid_addon_never_substitute_for_a_valid_addon_control(self):
        global ACTUAL_NODE_INFO
        for module_raw, addon_raw in (
            (loader.MODULE.read_bytes(), b"not a Mach-O or ELF addon"),
            (b"export const = broken syntax;", b"not a Mach-O or ELF addon"),
            (loader.MODULE.read_bytes(), None),
        ):
            with self.subTest(
                module_valid=module_raw == loader.MODULE.read_bytes(),
                addon_present=addon_raw is not None,
            ):
                with tempfile.TemporaryDirectory() as temporary:
                    parent = Path(temporary).resolve()
                    targets = parent / "targets"
                    targets.mkdir(mode=0o700)
                    (targets / "module.mjs").write_bytes(module_raw)
                    (targets / "module.mjs").chmod(0o400)
                    if addon_raw is not None:
                        (targets / "addon.node").write_bytes(addon_raw)
                        (targets / "addon.node").chmod(0o400)
                    targets.chmod(0o500)
                    entry = {
                        "kind": "invented",
                        "slot": "validity-control",
                        "nonce_sha256": "a" * 64,
                        "owner_pid": os.getpid(),
                        "targets": str(targets),
                    }

                    def guard():
                        self.assertEqual(loader._snapshot(self.node), self.node_snapshot)

                    actual = loader._owned(
                        [str(self.node), str(loader.SCRIPT)],
                        parent / "actual.log",
                        guard,
                        control=entry,
                        timeout=8,
                    )
                    self.assertTrue(loader._complete(actual), actual)
                    report = loader._validate_probe(
                        json.loads((parent / "actual.log").read_bytes()), entry, str(self.node)
                    )
                    ACTUAL_NODE_INFO = {
                        **report["runtime"],
                        "executable_sha256": self.node_snapshot["sha256"],
                        "historical_owned_processes": actual["owned_processes"],
                        "final_remaining_owned_processes": actual["remaining_owned_processes"],
                    }
                    self.assertEqual(report["operations"]["module_read"]["status"], "ok")
                    self.assertEqual(
                        report["operations"]["module_read"]["sha256"], loader.digest(module_raw)
                    )
                    self.assertEqual(report["operations"]["addon_load"]["status"], "error")
                    if addon_raw is None:
                        self.assertEqual(report["operations"]["addon_read"]["error_code"], "ENOENT")
                    else:
                        self.assertEqual(
                            report["operations"]["addon_read"]["sha256"], loader.digest(addon_raw)
                        )
                    self.assertEqual(
                        report["operations"]["module_import"]["status"],
                        "ok" if module_raw == loader.MODULE.read_bytes() else "error",
                    )
                    partial = [
                        {"probe": report, "outer": actual, "error": None},
                        {"probe": None},
                        {"probe": None},
                    ]
                    self.assertEqual(loader._assess(partial, {}, {}, None)["state"], "inconclusive")
