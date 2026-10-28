"""Run the actual NSIS ancestor check against native Windows filesystem cases."""

import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build_path_probe(destination, compiler):
    """Extract production logic; suppress only its modal error-message presentation."""
    from scripts.build_windows_installer import nsis_literal

    template = (ROOT / "packaging/windows/opent1d.nsi").read_text(encoding="utf-8")
    function = re.search(
        r"^Function VerifyInstallationPath\n.*?^FunctionEnd$", template, re.M | re.S
    ).group()
    function = re.sub(r"^(\s*)MessageBox MB_ICONSTOP ", r"\1DetailPrint ", function, flags=re.M)
    destination = Path(destination).resolve()
    script = destination.with_suffix(".nsi")
    script.write_text(
        f'Unicode true\nRequestExecutionLevel user\nOutFile "{nsis_literal(destination)}"\n'
        + r"""Name "OpenT1D installer path regression"
SilentInstall silent
AutoCloseWindow true
!include "LogicLib.nsh"
!include "FileFunc.nsh"
Var PathProbe
Var PathParent
Var InputPath
Function .onInstFailed
  SetErrorLevel 71
FunctionEnd
"""
        + function
        + r"""
Section
  ReadEnvStr $InputPath "OPENT1D_TEST_INSTALLATION_PATH"
  ${If} $InputPath == ""
    SetErrorLevel 73
    Quit
  ${EndIf}
  StrCpy $PathProbe "caller-path-sentinel"
  Push "caller-stack-sentinel"
  Push $InputPath
  Call VerifyInstallationPath
  Pop $4
  ${If} $PathProbe != "caller-path-sentinel"
  ${OrIf} $4 != "caller-stack-sentinel"
    SetErrorLevel 72
    Quit
  ${EndIf}
  SetErrorLevel 0
SectionEnd
""",
        encoding="utf-8",
    )
    subprocess.run([str(compiler), "-V2", str(script)], check=True, timeout=60)
    return destination


def run_path_probe(executable, path):
    environment = os.environ.copy()
    environment["OPENT1D_TEST_INSTALLATION_PATH"] = str(path)
    return subprocess.run(
        [str(executable)], env=environment, capture_output=True, timeout=30
    ).returncode


@unittest.skipUnless(os.name == "nt", "Actual Windows NSIS and filesystem required")
class WindowsInstallerPathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.root = Path(cls.temporary.name)
        prepared = os.environ.get("OPENT1D_NSIS_PATH_PROBE")
        if prepared:
            cls.probe = Path(prepared).resolve(strict=True)
        else:
            compiler = shutil.which("makensis")
            if not compiler:
                raise unittest.SkipTest("NSIS compiler or prebuilt path probe required")
            cls.probe = build_path_probe(cls.root / "path-probe.exe", compiler)

    def test_existing_and_missing_directories_preserve_the_callers_stack(self):
        existing = self.root / "existing directory with spaces"
        existing.mkdir()
        unicode_directory = self.root / "één map 日本語"
        unicode_directory.mkdir()
        for path in (
            existing,
            existing / "missing",
            existing / "absent" / "missing",
            unicode_directory,
            unicode_directory / "ontbrekende map 日本語",
        ):
            with self.subTest(path=path):
                self.assertEqual(run_path_probe(self.probe, path), 0)

    def test_existing_file_and_other_attribute_errors_are_refused(self):
        ordinary = self.root / "ordinary-file"
        ordinary.write_bytes(b"preserve")
        for path in (ordinary, self.root / "invalid|name"):
            with self.subTest(path=path):
                self.assertEqual(run_path_probe(self.probe, path), 71)
        self.assertEqual(ordinary.read_bytes(), b"preserve")

    def test_junction_and_missing_child_below_junction_are_refused(self):
        target = self.root / "junction-target"
        target.mkdir()
        junction = self.root / "junction"
        subprocess.run(
            ["cmd.exe", "/d", "/c", "mklink", "/J", str(junction), str(target)],
            capture_output=True,
            check=True,
            timeout=10,
        )
        try:
            for path in (junction, junction / "missing-child"):
                with self.subTest(path=path):
                    self.assertEqual(run_path_probe(self.probe, path), 71)
            self.assertTrue(target.is_dir())
        finally:
            junction.rmdir()


if __name__ == "__main__":
    unittest.main()
