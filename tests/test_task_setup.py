"""Explicit locked task setup, missing environments and identity preservation."""

import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.catalogue.storage import ROOT
from experiments.platform_files import native_absolute
from experiments.setup import core


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.checkout = self.base / "checkout"
        for project in (".", core.NATIVE, core.OBSERVER):
            destination = self.checkout / project
            destination.mkdir(parents=True, exist_ok=True)
            for name in ("uv.lock", "pyproject.toml"):
                shutil.copy2(ROOT / project / name, destination / name)
        shutil.copy2(ROOT / ".python-version", self.checkout / ".python-version")
        self.addCleanup(patch.stopall)
        patch("experiments.setup.core.ROOT", self.checkout).start()
        patch("experiments.setup.core.uv_identity", return_value=None).start()

    def test_task_requirements_keep_root_and_native_isolated(self):
        self.assertEqual(list(core.requirements("m3-forecast")), ["."])
        self.assertEqual(list(core.requirements("m4-study")), [".", core.NATIVE, core.OBSERVER])
        self.assertEqual(list(core.requirements("m4-study", reconstruction=True)), ["."])
        maintained = core.requirements("m4-study-secure")
        self.assertEqual(list(maintained), [".", core.SECURE_NATIVE, core.OBSERVER])
        self.assertEqual(maintained[core.SECURE_NATIVE]["urllib3"], "2.8.0")
        self.assertEqual(maintained[core.SECURE_NATIVE]["setuptools"], "84.0.0")
        self.assertNotIn("urllib3", core.requirements("m4-study")[core.NATIVE])
        self.assertEqual(list(core.requirements("m4-study-secure", reconstruction=True)), ["."])
        with self.assertRaises(ValueError):
            core.requirements("arbitrary-archive-module")

    def test_missing_environment_check_never_installs(self):
        expected = {
            project: core.selectors(project) for project in (".", core.NATIVE, core.OBSERVER)
        }
        for project in (core.NATIVE, core.OBSERVER):
            self.assertFalse((self.checkout / project / ".python-version").exists())
            self.assertNotIn(".python-version", expected[project])
        # Real extended paths must resolve the root-level selector's parent components.
        extended_root = native_absolute(self.checkout)
        if os.name == "nt":
            self.assertTrue(str(extended_root).startswith("\\\\?\\"))
        patch.object(core, "ROOT", extended_root).start()
        plan = self.base / "plan"
        data = core.plan("m4-study", plan)
        self.assertEqual({item["project"]: item["files"] for item in data["projects"]}, expected)
        report = (plan / "report.md").read_bytes()
        self.assertEqual(report, core.markdown(data).encode("utf-8"))
        self.assertIn(b"\n", report)
        self.assertNotIn(b"\r", report)
        loaded_path, loaded = core.load(plan)
        self.assertEqual(loaded_path, plan)
        self.assertEqual(loaded, data)
        self.assertEqual((plan / "report.md").read_bytes(), report)
        with patch(
            "experiments.setup.core.install_project",
            side_effect=AssertionError("implicit installation"),
        ):
            result = core.execute(plan, self.base / "checked")
        self.assertFalse(result["ready"])
        self.assertEqual(len(result["projects"]), 3)
        self.assertTrue(
            all(item["reason"] == "missing_or_aliased_environment" for item in result["projects"])
        )
        self.assertFalse(
            any(
                (self.checkout / project / ".venv").exists()
                for project in (".", core.NATIVE, core.OBSERVER)
            )
        )

    def test_modified_lock_refused_before_installation(self):
        plan = self.base / "plan"
        core.plan("m4-study", plan)
        with (self.checkout / core.NATIVE / "uv.lock").open("a") as stream:
            stream.write("\n# changed\n")
        with patch(
            "experiments.setup.core.install_project",
            side_effect=AssertionError("install must not launch"),
        ):
            with self.assertRaisesRegex(ValueError, "lock"):
                core.execute(plan, self.base / "install", install=True)

    def test_plan_and_receipt_bind_runtime_inventory_implementation(self):
        for name in core.SOURCES:
            destination = self.checkout / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, destination)
        helper = "experiments/durable_archives/storage.py"
        plan = self.base / "plan"
        with patch("experiments.catalogue.storage.ROOT", self.checkout):
            data = core.plan("m3-forecast", plan)
            self.assertIn(helper, data["source_sha256"])
            self.assertIn("experiments/durable_archives/__init__.py", data["source_sha256"])
            result = core.execute(plan, self.base / "checked")
            self.assertEqual(result["plan_sha256"], core.digest(core.encoded(data)))
            path = self.checkout / helper
            path.write_bytes(path.read_bytes() + b"\n# changed runtime admission\n")
            with (
                patch.object(core, "install_project") as install,
                self.assertRaisesRegex(ValueError, "Setup implementation changed"),
            ):
                core.execute(plan, self.base / "refused", install=True)
            install.assert_not_called()
        self.assertFalse((self.base / "refused").exists())

    def test_public_install_refused_before_any_installer_or_output(self):
        (self.checkout / "publication-snapshot.json").write_text("{}")
        shutil.copy2(
            ROOT / "publication-security.json", self.checkout / "publication-security.json"
        )
        plan = self.base / "public-plan"
        core.plan("m4-study", plan)
        with patch("experiments.setup.core.install_project") as installer:
            with self.assertRaisesRegex(ValueError, "excludes historical"):
                core.execute(plan, self.base / "refused-install", install=True)
            installer.assert_not_called()
        self.assertFalse((self.base / "refused-install").exists())
        # Read-only inspection remains available and does not claim readiness.
        result = core.execute(plan, self.base / "read-only")
        self.assertFalse(result["ready"])

    def test_public_native_setup_cannot_bypass_policy_with_packaged_manifest(self):
        (self.checkout / "publication-snapshot.json").write_text("{}")
        shutil.copy2(
            ROOT / "publication-security.json", self.checkout / "publication-security.json"
        )
        plan = self.base / "public-bundled-plan"
        core.plan("m4-study", plan)
        with (
            patch.object(core, "packaged_manifest", return_value={"schema": "test"}),
            patch.object(
                core,
                "install_argv",
                side_effect=lambda project: [
                    "uv",
                    "sync",
                    "--locked",
                    *([] if project == "." else ["--project", project]),
                ],
            ),
            patch.object(core, "install_project") as installer,
            patch.object(core, "check_project") as runtime_check,
            self.assertRaisesRegex(ValueError, "excludes historical runtimes"),
        ):
            core.execute(plan, self.base / "refused-public-bundled", install=True)
        installer.assert_not_called()
        runtime_check.assert_not_called()
        self.assertFalse((self.base / "refused-public-bundled").exists())

    def test_unlocked_controller_dependency_refused(self):
        with self.assertRaisesRegex(ValueError, "absent"):
            core.requirements(
                "p1-controller", controller={"dependencies": {"unlocked-dependency": "1.2.3"}}
            )

    def test_environment_selectors_do_not_redirect_install(self):
        with patch.dict(
            "os.environ",
            {
                "UV_PROJECT": "/foreign",
                "UV_INDEX": "https://invalid",
                "PYTHONPATH": "/foreign",
                "VIRTUAL_ENV": "/foreign",
                "UV_NO_SYNC": "1",
            },
        ):
            env = core.environment("/local-cache", False)
        for name in ("UV_PROJECT", "UV_INDEX", "PYTHONPATH", "VIRTUAL_ENV", "UV_NO_SYNC"):
            self.assertNotIn(name, env)
        self.assertEqual(env["UV_NO_CONFIG"], "1")
        self.assertNotIn("UV_OFFLINE", env)
        self.assertEqual(core.environment("/local-cache", True)["UV_OFFLINE"], "1")

    def test_offline_installer_uses_sanitized_default_uv_cache(self):
        cache = str(self.base / "normal-cache")
        with patch.dict("os.environ", {"UV_PROJECT": "/foreign", "UV_CACHE_DIR": "/foreign-cache"}):
            with patch(
                "experiments.setup.core.subprocess.run",
                return_value=subprocess.CompletedProcess([], 0, cache + "\n"),
            ) as call:
                self.assertEqual(core.offline_cache({"path": "/declared/uv"}), cache)
        self.assertEqual(call.call_args.args[0], ["/declared/uv", "cache", "dir"])
        self.assertNotIn("UV_CACHE_DIR", call.call_args.kwargs["env"])
        self.assertNotIn("UV_PROJECT", call.call_args.kwargs["env"])
        self.assertEqual(call.call_args.kwargs["env"]["UV_OFFLINE"], "1")

    def test_existing_output_and_venv_overlap_refused(self):
        with self.assertRaisesRegex(ValueError, "fresh"):
            core.plan("m3-forecast", self.checkout)
        with self.assertRaisesRegex(ValueError, "overlaps"):
            core.plan("m3-forecast", self.checkout / ".venv/new-output")

    @unittest.skipIf(os.name == "nt", "POSIX SIGTERM and process-group semantics required")
    def test_sigterm_reaps_blocking_installer_and_owned_child(self):
        pidfile = self.base / "pids.json"
        installer = self.base / "blocking-uv.py"
        installer.write_text(
            "import json,os,signal,subprocess,sys,time\n"
            "from pathlib import Path\n"
            "child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'])\n"
            "def stop(signum,frame):\n child.terminate();child.wait();sys.exit(1)\n"
            "signal.signal(signal.SIGTERM,stop)\n"
            f"Path({str(pidfile)!r}).write_text(json.dumps([os.getpid(),child.pid]))\n"
            "time.sleep(60)\n"
        )
        resultfile = self.base / "result.json"
        script = (
            "import json,sys;from pathlib import Path;"
            "from experiments.setup.core import install_project;"
            f"result=install_project([sys.executable,{str(installer)!r}],"
            f"Path({str(self.base / 'installer.log')!r}),{str(self.base / 'cache')!r},True);"
            f"Path({str(resultfile)!r}).write_text(json.dumps(result))"
        )
        process = subprocess.Popen([sys.executable, "-B", "-S", "-c", script], cwd=ROOT)
        try:
            deadline = time.monotonic() + 10
            while not pidfile.exists() and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertTrue(pidfile.exists(), "Blocking installer did not start")
            pids = json.loads(pidfile.read_bytes())
            process.send_signal(signal.SIGTERM)
            self.assertEqual(process.wait(timeout=10), 0)
            result = json.loads(resultfile.read_bytes())
            self.assertEqual(result["status"], "interrupted")
            self.assertEqual(result["signal"], signal.SIGTERM)
            for pid in pids:
                with self.assertRaises(ProcessLookupError):
                    os.kill(pid, 0)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            if pidfile.exists():
                for pid in json.loads(pidfile.read_bytes()):
                    try:
                        os.kill(pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass


if __name__ == "__main__":
    unittest.main()
