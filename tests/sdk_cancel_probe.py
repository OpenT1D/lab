"""Controlled live stop/resume around real installed commands; no scientific phase claim."""

import builtins
import json
import os
import signal
import subprocess
import sys
import threading
import time
from unittest.mock import patch


def main(site, project, plan):
    sys.path.insert(0, site)
    import opent1d_lab._client as client

    cancel = threading.Event()
    real_exec = builtins.exec
    stopped = []
    owners = []
    unrelated = subprocess.Popen(
        [sys.executable, "-I", "-S", "-c", "import time;time.sleep(30)"], start_new_session=True
    )

    def controlled_exec(code, namespace):
        real_exec(code, namespace)
        original = namespace["Ownership"]

        class ObserveNative(original):
            def __init__(self, process):
                super().__init__(process)
                owners.append(self)

            def observe(self):
                observed = super().observe()
                if not stopped:
                    for pid, identity in observed.items():
                        if identity["ppid"] != self.process.pid:
                            continue
                        actual = self.table.one(pid)
                        if actual and actual["alive"] and actual["start"] == identity["start"]:
                            os.kill(pid, signal.SIGSTOP)
                            stopped.append((pid, identity["start"], time.monotonic()))
                            cancel.set()
                            break
                elif time.monotonic() - stopped[0][2] > 0.15:
                    resume()
                return observed

        namespace["Ownership"] = ObserveNative

    def resume():
        if stopped and owners:
            pid, start, _ = stopped[0]
            actual = owners[0].table.one(pid)
            if actual and actual["alive"] and actual["start"] == start:
                os.kill(pid, signal.SIGCONT)

    try:
        with patch.object(client, "exec", side_effect=controlled_exec, create=True):
            outcome = client.invoke(
                {
                    "action": "run",
                    "project": project,
                    "plan": plan,
                    "retry_of": None,
                    "timeout": 10,
                },
                cancel=cancel,
            )
        result = {
            "attempt": outcome["attempt"],
            "receipt_status": outcome["receipt"]["status"],
            "remaining_owned_processes": owners[0].cleanup(0)[1],
            "stopped_live_native_child": bool(stopped),
            "unrelated_alive": unrelated.poll() is None,
        }
        assert result["receipt_status"] == "interrupted", result
        assert result["remaining_owned_processes"] == [], result
        assert outcome["receipt"]["remaining_owned_processes"] == [], outcome
        assert stopped and unrelated.poll() is None, result
        print(json.dumps(result, sort_keys=True))
    finally:
        resume()
        for owner in owners:
            owner.cleanup(0)
        unrelated.terminate()
        unrelated.wait(timeout=5)


if __name__ == "__main__":
    main(*sys.argv[1:])
