"""Actual noneditable M3 SDK/CLI, frozen failure and owned cancellation checks."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from experiments.catalogue.storage import encoded
from experiments.m3.comparison import study
from experiments.m3.researcher.fixtures import write_predictor
from experiments.shared_services.store import opened
from scripts import build_sdk


@unittest.skipUnless(
    os.name == "posix" and sys.version_info[:2] == (3, 12), "POSIX CPython 3.12 SDK"
)
class InstalledM3(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="installed-m3-")
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.base = Path(cls.temporary.name).resolve()
        cls.env = {k: v for k, v in os.environ.items() if k not in {"PYTHONPATH", "PYTHONHOME"}}
        cls.env["UV_CACHE_DIR"] = str(cls.base / "cache")
        cls.receipt = build_sdk.build(
            cls.base / "build", allow_dirty=True, build_label="m3-regression", m3_workbench=True
        )
        cls.environment = cls.base / "sdk"
        cls.python = cls.environment / "bin/python"
        for argv in (
            ["uv", "venv", "--offline", "--python", sys.executable, str(cls.environment)],
            [
                "uv",
                "pip",
                "install",
                "--offline",
                "--no-deps",
                "--link-mode=copy",
                "--python",
                str(cls.python),
                cls.receipt["wheel"],
            ],
        ):
            subprocess.run(argv, env=cls.env, capture_output=True, check=True)
        cls.cli = cls.environment / "bin/opent1d-lab"

    def setUp(self):
        self.root = self.base / self._testMethodName
        self.root.mkdir()

    def call(self, *args, expected=0):
        result = subprocess.run(
            [str(self.cli), *map(str, args)],
            cwd=self.root,
            env=self.env,
            capture_output=True,
            text=True,
            timeout=120,
        )
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def prepare(self, mutate=None):
        inputs = self.call("example", "--task", "m3-compare", "--output", self.root / "inputs")[
            "inputs"
        ]
        filename = Path(inputs["config.json"])
        config = json.loads(filename.read_bytes())
        if mutate:
            mutate(config)
            filename.write_bytes(encoded(config))
        project = self.root / "project"
        self.call("create", "--project", project, "--name", "Synthetic CGM comparison")
        plan = self.call(
            "freeze", "--project", project, "--task", "m3-compare", "--config", filename
        )["plan"]
        return project, plan, config, filename

    def test_installed_direct_parity_retry_derivation_and_relocated_report(self):
        project, plan, config, filename = self.prepare()
        self.assertTrue(self.call("check", "--project", project, "--plan", plan)["runtimes_ready"])
        direct = study.run_study(filename, self.root / "direct")
        installed = self.call("run", "--project", project, "--plan", plan)
        self.assertEqual(installed["result"]["completeness"], "complete")
        with opened(project) as ledger:
            _, evidence = ledger.finishes[installed["attempt"]]
            archive = evidence / "native"
            saved = json.loads((archive / "report.json").read_bytes())
            self.assertEqual(saved["common"], direct["common"])
            for candidate in config["candidates"]:
                for person in config["people"]:
                    relative = f"children/{candidate['id']}/cases/{person['id']}/trace.jsonl"
                    self.assertEqual(
                        (archive / relative).read_bytes(),
                        (self.root / "direct" / relative).read_bytes(),
                    )
            expected = {
                name: (archive / name).read_bytes() for name in ("report.json", "report.md")
            }
        first_head = self.call("info", "--project", project)["head"]
        # Derivation uses exact retained bytes and a fresh location, without source execution.
        derived = self.call(
            "export-inputs",
            "--project",
            project,
            "--plan",
            plan,
            "--output",
            self.root / "derived-inputs",
        )
        child = self.call(
            "freeze",
            "--project",
            project,
            "--task",
            "m3-compare",
            "--parent",
            plan,
            "--config",
            derived["inputs"]["config.json"],
        )["plan"]
        self.assertEqual(self.call("plan", "--project", project, "--plan", child)["parent"], plan)
        retry = self.call(
            "run", "--project", project, "--plan", plan, "--retry-of", installed["attempt"]
        )
        self.assertNotEqual(retry["attempt"], installed["attempt"])
        self.assertNotEqual(first_head, self.call("info", "--project", project)["head"])
        destination = self.root / "moved"
        self.call("relocate", "--project", project, "--output", destination)
        shutil.rmtree(project)
        shutil.rmtree(self.root / "inputs")
        shutil.rmtree(self.root / "derived-inputs")
        result = self.call(
            "reconstruct",
            "--project",
            destination,
            "--attempt",
            installed["attempt"],
            "--output",
            self.root / "reconstructed",
        )
        self.assertEqual(result["reconstruction"], "verified")
        for name, raw in expected.items():
            self.assertEqual((self.root / "reconstructed" / name).read_bytes(), raw)
        # Python facade and CLI share exactly the same project and attempt identities.
        probe = subprocess.run(
            [
                str(self.python),
                "-I",
                "-c",
                "import opent1d_lab as s,sys,json; "
                "print(json.dumps(s.open_project(sys.argv[1]).info()))",
                str(destination),
            ],
            cwd=self.root,
            env=self.env,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(json.loads(probe.stdout), self.call("info", "--project", destination))

    def test_missing_input_and_nonfinite_predictor_keep_native_failed_evidence(self):
        def mutate(config):
            Path(config["people"][0]["input"]["file"]).unlink()
            declaration = write_predictor(
                self.root / "nonfinite",
                "def predict(request, settings): return float('nan')\n",
                {},
                name="nonfinite",
                reference="Invented failure control",
            )
            config["candidates"][0] = {"id": "nonfinite", "declaration": str(declaration)}

        project, plan, config, _ = self.prepare(mutate)
        result = self.call("run", "--project", project, "--plan", plan, expected=1)
        self.assertEqual(result["result"]["payload"], "native")
        self.assertEqual(result["result"]["completeness"], "incomplete")
        self.assertEqual(len(result["result"]["slot_statuses"]), 4)
        refusal = self.call(
            "reconstruct",
            "--project",
            project,
            "--attempt",
            result["attempt"],
            "--output",
            self.root / "refused",
            expected=2,
        )
        self.assertIn("allow_failed", refusal["error"])
        moved = self.root / "moved"
        self.call("relocate", "--project", project, "--output", moved)
        shutil.rmtree(project)
        shutil.rmtree(self.root / "inputs")
        shutil.rmtree(self.root / "nonfinite")
        self.call(
            "reconstruct",
            "--project",
            moved,
            "--attempt",
            result["attempt"],
            "--allow-failed",
            "--output",
            self.root / "report",
        )
        report = json.loads((self.root / "report/report.json").read_bytes())
        self.assertEqual(report["common"]["planned_people"], 2)
        self.assertEqual(report["common"]["contributing_people"], 0)
        self.assertEqual(set(report["common"]["people"]), {p["id"] for p in config["people"]})

    def test_cancel_slow_predictor_cleans_owned_tree_and_preserves_unrelated_process(self):
        marker = self.root / "predictor-started"

        def mutate(config):
            source = (
                "import time\nfrom pathlib import Path\ndef predict(request, settings):\n"
                f"    Path({str(marker)!r}).touch()\n    time.sleep(120)\n    return 1.0\n"
            )
            declaration = write_predictor(
                self.root / "slow",
                source,
                {},
                name="slow",
                reference="Invented cancellation control",
            )
            config["candidates"][0] = {"id": "slow", "declaration": str(declaration)}

        project, plan, _, _ = self.prepare(mutate)
        script = """import json,sys,threading,time
from pathlib import Path
import opent1d_lab as sdk
cancel=threading.Event()
def watch():
    deadline=time.monotonic()+30
    while not Path(sys.argv[3]).exists() and time.monotonic()<deadline: time.sleep(.02)
    cancel.set()
thread=threading.Thread(target=watch);thread.start()
result=sdk.open_project(sys.argv[1]).run(sys.argv[2],cancel=cancel)
thread.join();print(json.dumps(result))
"""
        unrelated = subprocess.Popen(
            [sys.executable, "-c", "import time;time.sleep(120)"], start_new_session=True
        )
        try:
            result = subprocess.run(
                [str(self.python), "-I", "-c", script, str(project), plan, str(marker)],
                cwd=self.root,
                env=self.env,
                capture_output=True,
                text=True,
                timeout=75,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            data = json.loads(result.stdout)
            self.assertTrue(marker.exists())
            self.assertEqual(data["receipt"]["remaining_owned_processes"], [])
            self.assertEqual(data["result"]["completeness"], "incomplete")
            self.assertEqual(data["result"]["payload"], "native")
            self.assertIsNone(unrelated.poll())
            self.call(
                "reconstruct",
                "--project",
                project,
                "--attempt",
                data["attempt"],
                "--allow-failed",
                "--output",
                self.root / "report",
            )
            report = json.loads((self.root / "report/report.json").read_bytes())
            self.assertEqual(report["candidate_order"], ["slow", "ridge-coefficient-fixture"])
            self.assertEqual(
                report["candidates"]["ridge-coefficient-fixture"]["coordinator"]["status"],
                "not_attempted",
            )
        finally:
            unrelated.terminate()
            unrelated.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
