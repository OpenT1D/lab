"""Desktop packaging and private-owner lifecycle counterexamples, not host QA."""

import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.build_concept_desktop import extract_electron

ROOT = Path(__file__).resolve().parents[1]


class DesktopArchiveTests(unittest.TestCase):
    def test_regular_payload_and_executable_modes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            archive = root / "runtime.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                executable = zipfile.ZipInfo("App/Contents/MacOS/App")
                executable.external_attr = (stat.S_IFREG | 0o755) << 16
                bundle.writestr(executable, b"controlled executable")
                bundle.writestr("App/Contents/Resources/data", b"preserved bytes")
            output = root / "output"
            extract_electron(archive, output)
            self.assertEqual(
                (output / "App/Contents/Resources/data").read_bytes(), b"preserved bytes"
            )
            if os.name == "posix":
                self.assertTrue((output / "App/Contents/MacOS/App").stat().st_mode & 0o111)

    def test_traversal_case_alias_and_framework_escape_refuse(self):
        entries = [
            [("../outside", b"refuse")],
            [("App/A", b"a"), ("app/a", b"b")],
            [("App/alias", "../../outside")],
            [("App/alias", "target"), ("App/alias/child", b"refuse")],
        ]
        for case in entries:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                archive = root / "runtime.zip"
                with zipfile.ZipFile(archive, "w") as bundle:
                    for name, value in case:
                        entry = zipfile.ZipInfo(name)
                        entry.external_attr = (
                            (stat.S_IFLNK | 0o777) << 16
                            if isinstance(value, str)
                            else (stat.S_IFREG | 0o644) << 16
                        )
                        bundle.writestr(entry, value)
                with self.assertRaises(ValueError):
                    extract_electron(archive, root / "output")
                self.assertFalse((root / "outside").exists())

    @unittest.skipUnless(os.name == "posix", "Mac framework aliases require POSIX links")
    def test_internal_framework_alias_is_retained(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            archive = root / "runtime.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr("App/Versions/A/data", b"framework")
                link = zipfile.ZipInfo("App/Versions/Current")
                link.external_attr = (stat.S_IFLNK | 0o777) << 16
                bundle.writestr(link, "A")
            extract_electron(archive, root / "output")
            self.assertTrue((root / "output/App/Versions/Current").is_symlink())
            self.assertEqual((root / "output/App/Versions/Current/data").read_bytes(), b"framework")


IMPORT_DESKTOP = f"""
import importlib,json,os,sys,types
from pathlib import Path
package=types.ModuleType('desktop_lifecycle_fixture')
package.__path__=[{str(ROOT / "packaging/sdk/opent1d_lab")!r}]
sys.modules[package.__name__]=package
desktop=importlib.import_module(package.__name__+'._desktop')
gui=importlib.import_module(package.__name__+'.gui')
transport=importlib.import_module(package.__name__+'._gui_http')
"""


class DesktopOwnerTests(unittest.TestCase):
    def run_child(self, source, *, owner_eof=False):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory).resolve() / "closed"
            code = IMPORT_DESKTOP + f"\nmarker=Path({str(marker)!r})\n" + source
            process = subprocess.Popen(
                [sys.executable, "-I", "-B", "-c", code],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            try:
                if owner_eof:
                    process.stdin.close()
                    process.stdout.close()
                # Keep the owner's pipe open until process exit in the normal
                # case: buffered daemon reads used to abort Python finalisation.
                process.wait(timeout=10)
                stderr = process.stderr.read().decode()
                self.assertEqual(process.returncode, 0, stderr)
                self.assertTrue(marker.is_file(), stderr)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=3)
                for stream in (process.stdin, process.stdout, process.stderr):
                    if stream is not None and not stream.closed:
                        stream.close()

    def test_service_return_with_live_owner_pipe_does_not_abort(self):
        self.run_child("""
class Server:
    origin='http://127.0.0.1:12345'
    token='a'*64
    def request_stop(self): pass
def serve(workspace,ready): ready(Server())
desktop.serve=serve
sys.argv=['desktop','--workspace',str(marker.parent/'workspace')]
desktop.main()
marker.write_text('finished')
""")

    @unittest.skipUnless(os.name == "posix", "The selected SDK lifecycle is POSIX")
    def test_ready_error_stops_started_loop_and_closes_controller(self):
        self.run_child("""
class Controller:
    def __init__(self,*args,**kwargs): pass
    def begin_close(self): pass
    def close(self): marker.write_text('closed')
gui.Controller=Controller
gui.Server=lambda controller,port: transport.Server(controller,port,assets={'index.html':b''})
def ready(server): raise BrokenPipeError('controlled owner loss')
try: gui.serve(str(marker.parent/'workspace'),ready=ready)
except BrokenPipeError: pass
else: raise AssertionError('ready failure was hidden')
""")

    @unittest.skipUnless(os.name == "posix", "The selected SDK lifecycle is POSIX")
    def test_owner_loss_before_ready_has_no_unstarted_shutdown_thread(self):
        self.run_child(
            """
class Controller:
    def __init__(self,*args,**kwargs): pass
    def begin_close(self): pass
    def close(self): marker.write_text('closed')
gui.Controller=Controller
gui.Server=lambda controller,port: transport.Server(controller,port,assets={'index.html':b''})
sys.argv=['desktop','--workspace',str(marker.parent/'workspace')]
try: desktop.main()
except BrokenPipeError:
    descriptor=os.open(os.devnull,os.O_WRONLY)
    os.dup2(descriptor,1)
    os.close(descriptor)
""",
            owner_eof=True,
        )

    def test_locked_target_is_mac_only(self):
        lock = json.loads((ROOT / "packaging/desktop/runtime-lock.json").read_bytes())
        self.assertEqual(set(lock["targets"]), {"darwin-arm64"})
