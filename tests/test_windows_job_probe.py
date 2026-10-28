"""Platform-neutral checks for read-only Windows diagnostic identity matching."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from tests.windows_job_probe import inspect_job_processes


class QueryKernel:
    def __init__(self):
        self.creation = 0x1234567890
        self.image = r"C:\private-fixture\conhost.exe"
        self.member = True
        self.times = True
        self.opened, self.closed = [], []

    def OpenProcess(self, access, inherit, pid):
        if (access, inherit, pid) != (0x00101000, False, 42):
            raise AssertionError("Probe exceeded the selected member's query/sync rights")
        self.opened.append(80)
        return 80

    def IsProcessInJob(self, handle, job, member):
        if (handle, job) != (80, 30):
            raise AssertionError("Probe used another process or Job")
        member._obj.value = self.member
        return True

    def GetExitCodeProcess(self, handle, code):
        code._obj.value = 109
        return True

    def WaitForSingleObject(self, handle, timeout):
        if timeout != 0:
            raise AssertionError("Probe must not wait for or change process completion")
        return 0 if handle == 20 else 258

    def GetProcessTimes(self, handle, creation, exited, system, user):
        creation._obj.dwLowDateTime = self.creation & 0xFFFFFFFF
        creation._obj.dwHighDateTime = self.creation >> 32
        return self.times

    def QueryFullProcessImageNameW(self, handle, flags, image, size):
        if self.image is None:
            return False
        image.value = self.image
        return True

    def CloseHandle(self, handle):
        self.closed.append(handle)
        return True


class WindowsJobProbeTests(unittest.TestCase):
    def setUp(self):
        self.api = QueryKernel()
        self.returncode = None
        self.process = SimpleNamespace(
            pid=7,
            process=SimpleNamespace(_handle=20),
            job=SimpleNamespace(handle=30),
            poll=lambda: self.returncode,
        )
        self.cache = {}
        kernel = patch("tests.windows_job_probe.kernel", return_value=self.api)
        kernel.start()
        self.addCleanup(kernel.stop)
        errors = patch("ctypes.get_last_error", return_value=5, create=True)
        errors.start()
        self.addCleanup(errors.stop)
        self.addCleanup(lambda: self.assertEqual(self.api.opened, self.api.closed))

    def inspect(self):
        return inspect_job_processes(self.process, [42], image_cache=self.cache)["processes"][0]

    def test_late_access_denied_matches_only_prior_running_creation_identity(self):
        first = self.inspect()
        self.assertEqual(first["image_basename"], "conhost.exe")
        self.assertNotIn("private-fixture", repr(first))
        self.assertEqual(self.cache, {42: (self.api.creation, "conhost.exe")})
        self.returncode, self.api.image = 0, None
        final = self.inspect()
        self.assertEqual(final["earlier_running_image_basename"], "conhost.exe")
        self.assertEqual(final["image_error"], 5)
        self.assertEqual(final["exit_code"], 109)
        self.assertEqual(final["wait_result"], 258)
        self.assertTrue(final["in_job"])

    def test_reused_pid_and_missing_creation_time_cannot_reuse_cached_name(self):
        self.inspect()
        self.returncode, self.api.image = 0, None
        self.api.creation += 1
        self.assertNotIn("earlier_running_image_basename", self.inspect())
        self.api.creation -= 1
        self.api.times = False
        final = self.inspect()
        self.assertEqual(final["creation_error"], 5)
        self.assertNotIn("earlier_running_image_basename", final)

    def test_nonmember_or_already_completed_or_unknown_image_is_never_cached(self):
        for mode in ("nonmember", "completed", "missing-image"):
            with self.subTest(mode=mode):
                self.api.member = mode != "nonmember"
                self.returncode = 0 if mode == "completed" else None
                self.api.image = None if mode == "missing-image" else r"C:\fixture\python.exe"
                self.inspect()
                self.assertEqual(self.cache, {})

    def test_query_handle_closes_when_later_inspection_raises(self):
        with patch.object(self.api, "GetProcessTimes", side_effect=OSError("fixture query error")):
            with self.assertRaisesRegex(OSError, "fixture query error"):
                self.inspect()


if __name__ == "__main__":
    unittest.main()
