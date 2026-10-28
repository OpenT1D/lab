"""Keep the prepared, currently inactive branch policy valid and aligned with CI."""

import json
import unittest
from pathlib import Path

import yaml


class BranchPolicyTests(unittest.TestCase):
    def test_prepared_required_checks_cover_actual_workflow_jobs(self):
        root = Path(__file__).resolve().parents[1]
        policy = json.loads((root / ".github/main-branch-protection.json").read_text())
        workflow = yaml.safe_load((root / ".github/workflows/checks.yml").read_text())
        checks = policy["required_status_checks"]["checks"]
        self.assertEqual(
            {c["context"] for c in checks}, {j["name"] for j in workflow["jobs"].values()}
        )
        self.assertEqual(len(checks), len(workflow["jobs"]))
        self.assertTrue(all(c["app_id"] == 15368 for c in checks))

    def workflow(self):
        root = Path(__file__).resolve().parents[1]
        return yaml.safe_load((root / ".github/workflows/checks.yml").read_text())

    def test_maintained_jobs_use_unprivileged_pinned_actions_and_retain_failed_evidence(self):
        workflow = self.workflow()
        self.assertEqual(workflow["permissions"], {"contents": "read"})
        self.assertEqual(set(workflow["on"]), {"push", "pull_request", "workflow_dispatch"})
        for name in ("maintained-m4-study", "c1-patched-checkpoint-boundary"):
            job = workflow["jobs"][name]
            with self.subTest(job=name):
                self.assertEqual(job["runs-on"], "ubuntu-24.04")
                self.assertEqual(job["timeout-minutes"], 30)
                self.assertEqual(job["needs"], "repository-checks")
                self.assertEqual(
                    job["if"],
                    "github.event.repository.private && github.event_name == 'workflow_dispatch' "
                    "&& inputs.historical_native "
                    "&& needs.repository-checks.outputs.native_enabled == 'true'",
                )
                self.assertNotIn("continue-on-error", job)
                for step in job["steps"]:
                    self.assertNotIn("continue-on-error", step)
                    if "uses" in step:
                        self.assertRegex(step["uses"], r"^[^@]+@[a-f0-9]{40}$")
                checkout = job["steps"][0]
                self.assertFalse(checkout["with"]["persist-credentials"])
                self.assertEqual(
                    checkout["with"]["ref"],
                    "${{ github.event.pull_request.head.sha || github.sha }}",
                )
                upload = job["steps"][-1]
                self.assertEqual(upload["if"], "always()")
                self.assertTrue(upload["uses"].startswith("actions/upload-artifact@"))
                self.assertEqual(upload["with"]["retention-days"], 14)

    def test_maintained_study_uses_own_runtime_and_complete_stdlib_reconstruction(self):
        jobs = self.workflow()["jobs"]
        commands = "\n".join(step.get("run", "") for step in jobs["maintained-m4-study"]["steps"])
        self.assertIn("experiments.setup plan m4-study-secure", commands)
        self.assertIn("--project experiments/m0/simglucose_secure", commands)
        self.assertIn("python -B -m experiments.m4.secure_study.test_numerical", commands)
        self.assertIn("python -S -m experiments.workflows run m4-study-secure", commands)
        self.assertIn("--config experiments/m4/secure_study/example.json", commands)
        self.assertIn("python -S -m experiments.workflows reconstruct m4-study-secure", commands)
        self.assertNotIn("--reference", commands)
        for filename in ("report.json", "report.md", "figure.svg"):
            self.assertIn(
                f"cmp results/m4-maintained-ci/study/{filename} "
                f"results/m4-maintained-ci/reconstructed/{filename}",
                commands,
            )
        self.assertIn('["fasting", "gastric_load_15g", "gastric_load_30g"]', commands)
        self.assertIn('"accepted_source_scenarios": 6', commands)
        historical = "\n".join(
            step.get("run", "") for step in jobs["configurable-study-tools"]["steps"]
        )
        self.assertIn("experiments.setup plan m4-study ", historical)
        self.assertIn("--project experiments/m0/simglucose python", historical)
        self.assertNotIn("m4-study-secure", historical)

    def test_c1_job_checks_both_locks_and_synthetic_replay_without_retraining(self):
        job = self.workflow()["jobs"]["c1-patched-checkpoint-boundary"]
        commands = "\n".join(step.get("run", "") for step in job["steps"])
        self.assertEqual(job["defaults"]["run"]["shell"], "bash")
        self.assertIn("37f7b7e161e9c1e7b702c8eebdc5cc7eb4f81d70", commands)
        for runtime in ("policy", "training"):
            self.assertIn(
                f"uv sync --locked --project experiments/c1/g2p2c_{runtime}_source", commands
            )
            self.assertIn(f"tee results/c1-checkpoint-ci/{runtime}-checkpoint.log", commands)
            self.assertIn(
                f"cmp results/c1-checkpoint-ci/{runtime}-primary.json "
                f"results/c1-checkpoint-ci/{runtime}-repeat.json",
                commands,
            )
        self.assertEqual(commands.count("-m unittest tests.test_c1_g2p2c_checkpoint -v"), 2)
        self.assertEqual(commands.count("-m experiments.c1.g2p2c_actor_source_probe"), 4)
        self.assertNotIn("g2p2c_training_run", commands)
        self.assertNotIn("g2p2c_security_runtime run", commands)
        self.assertNotIn("--historical-root", commands)
