"""Adverse installed-client ownership fixture; only controls live owned processes."""

import builtins
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

from experiments.gui.ownership import Ownership


def main(site):
    sys.path.insert(0, site)
    import opent1d_lab._client as client

    real_popen, real_exec = subprocess.Popen, builtins.exec
    processes, watchers, children = [], [], []
    unrelated = real_popen(
        [sys.executable, "-I", "-S", "-c", "import time;time.sleep(30)"], start_new_session=True
    )
    with tempfile.TemporaryDirectory(prefix="sdk-owned-fixture-") as temporary:
        root = Path(temporary).resolve()
        ready, probe = root / "ready", root / "probe.py"
        probe.write_text(
            "import subprocess,sys,time\nfrom pathlib import Path\n"
            "p=subprocess.Popen([sys.executable,'-I','-S','-c','import time;time.sleep(30)'])\n"
            f"Path({str(ready)!r}).write_text(str(p.pid))\ntime.sleep(30)\n"
        )

        def launch(_argv, **kwargs):
            process = real_popen([sys.executable, "-I", "-B", "-S", str(probe)], **kwargs)
            processes.append(process)
            watchers.append(Ownership(process))
            return process

        def controlled_exec(code, namespace):
            real_exec(code, namespace)

            class ConstructorFailure:
                def __init__(self, _process):
                    deadline = time.monotonic() + 5
                    while not ready.exists() and time.monotonic() < deadline:
                        time.sleep(0.01)
                    child = int(ready.read_text())
                    children.append(child)
                    watcher = watchers[-1]
                    while child not in watcher.observed and time.monotonic() < deadline:
                        watcher.observe()
                        time.sleep(0.01)
                    if child not in watcher.observed:
                        raise RuntimeError("Child observation fixture failed")
                    raise ValueError("controlled constructor failure")

            namespace["Ownership"] = ConstructorFailure

        try:
            with (
                patch.object(client.subprocess, "Popen", side_effect=launch),
                patch.object(client, "exec", side_effect=controlled_exec, create=True),
            ):
                try:
                    client.invoke({"action": "installation"})
                except ValueError as error:
                    if "controlled constructor" not in str(error):
                        raise
                else:
                    raise AssertionError("Constructor failure became success")
            observed = watchers[-1].observe()
            result = {
                "direct_reaped": processes[-1].poll() is not None,
                "child_alive": children[-1] in observed,
                "unrelated_alive": unrelated.poll() is None,
            }
            print(json.dumps(result, sort_keys=True))
            assert result == {"direct_reaped": True, "child_alive": False, "unrelated_alive": True}
        finally:
            for watcher in watchers:
                watcher.cleanup(0)
            for process in processes:
                if process.stdin and not process.stdin.closed:
                    process.stdin.close()
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=5)
            unrelated.terminate()
            unrelated.wait(timeout=5)


if __name__ == "__main__":
    main(sys.argv[1])
