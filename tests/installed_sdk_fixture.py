"""Offline noneditable SDK wheel installed in a fresh environment per test class."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts import build_sdk


class InstalledWheelTestCase(unittest.TestCase):
    """Build the selected wheel, and give each test a fresh CLI working directory."""

    wheel_options = {}

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        temporary = tempfile.TemporaryDirectory(prefix="installed-sampling-")
        cls.addClassCleanup(temporary.cleanup)
        cls.base = Path(temporary.name).resolve()
        cls.env = {**os.environ, "UV_CACHE_DIR": str(cls.base / "cache")}
        cls.env.pop("PYTHONPATH", None)
        receipt = build_sdk.build(
            cls.base / "build", allow_dirty=True, build_label="sampling-test", **cls.wheel_options
        )
        cls.environment = cls.base / "sdk"
        for command in (
            ["uv", "venv", "--offline", "--python", sys.executable, str(cls.environment)],
            [
                "uv",
                "pip",
                "install",
                "--offline",
                "--no-deps",
                "--link-mode=copy",
                "--python",
                str(cls.environment / "bin/python"),
                receipt["wheel"],
            ],
        ):
            subprocess.run(command, env=cls.env, capture_output=True, check=True)
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
