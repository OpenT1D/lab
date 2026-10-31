"""Counterexamples for shared stdout offsets and failed fixture-start ownership."""

import itertools
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from tests import test_workbench_installed as workbench


class WorkbenchFixtureStartup(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="fixture-startup-")
        self.addCleanup(temp.cleanup)
        self.host = unittest.TestCase()
        self.host.root = Path(temp.name).resolve()
        self.host.cli = self.host.root / "owned-candidate"
        self.host.env = {}
        self.logs = []
        self.process = Mock()
        self.process.poll.return_value = None
        self.process.wait.return_value = 0

    def popen(self, _command, **kwargs):
        log = kwargs["stdout"]
        self.logs.append(log)
        self.addCleanup(log.close)
        if self.ready:
            log.write("OpenT1D project GUI: http://127.0.0.1:34567\n")
            log.flush()
        return self.process

    def test_child_second_line_cannot_overwrite_ready_url_during_parent_poll(self):
        self.ready = True
        original_open = Path.open

        class InterleavedLog:
            def __init__(self, stream):
                self.stream = stream
                self.injected = False

            def __getattr__(self, name):
                return getattr(self.stream, name)

            def seek(self, offset):
                result = self.stream.seek(offset)
                if offset == 0 and not self.injected:
                    # The child's next flushed write shares the inherited stdout
                    # file offset. Reproduce the scheduler interleaving exactly.
                    self.stream.write("Closing a browser tab keeps work running.\n")
                    self.stream.flush()
                    self.injected = True
                return result

        def opened(path, mode="r", *args, **kwargs):
            stream = original_open(path, mode, *args, **kwargs)
            return InterleavedLog(stream) if mode.startswith("w") else stream

        response = Mock(status=200)
        response.read.return_value = b'<meta name="opent1d-token" content="' + b"a" * 64 + b'">'
        connection = Mock()
        connection.getresponse.return_value = response
        with (
            patch.object(Path, "open", opened),
            patch.object(workbench.subprocess, "Popen", side_effect=self.popen),
            patch.object(workbench.http.client, "HTTPConnection", return_value=connection),
            patch.object(workbench.time, "monotonic", side_effect=itertools.count()),
            patch.object(workbench.time, "sleep"),
        ):
            with workbench.EditableWorkbench.server(self.host) as app:
                self.assertEqual(app.port, 34567)
                self.assertEqual(app.token, "a" * 64)
        self.process.terminate.assert_called_once()
        self.assertTrue(all(log.closed for log in self.logs))

    def test_startup_timeout_stops_owned_process_and_closes_every_log(self):
        self.ready = False
        with (
            patch.object(workbench.subprocess, "Popen", side_effect=self.popen),
            patch.object(workbench.time, "monotonic", side_effect=[0, 1, 21]),
            patch.object(workbench.time, "sleep"),
        ):
            with self.assertRaisesRegex(AssertionError, "Installed server not ready"):
                with workbench.EditableWorkbench.server(self.host):
                    self.fail("No ready URL was emitted")
        self.process.terminate.assert_called_once()
        self.process.wait.assert_called_once_with(timeout=20)
        self.assertTrue(all(log.closed for log in self.logs))


if __name__ == "__main__":
    unittest.main()
