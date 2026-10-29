"""Inject a real early TERM at installed begin(), retaining original source/commands."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch


def main(site, project, plan):
    sys.path.insert(0, site)
    import opent1d_lab._client as client

    real_popen = subprocess.Popen
    with tempfile.TemporaryDirectory(prefix="sdk-early-cancel-") as temporary:
        root = Path(temporary).resolve()
        marker = root / "early-term"
        harness = root / "controlled-bootstrap.py"
        harness.write_text(
            "import os,runpy,signal,sys\nfrom pathlib import Path\n"
            "bootstrap=sys.argv[1];sys.argv=[bootstrap]\n"
            "namespace=runpy.run_path(bootstrap,run_name='_controlled_installed_bootstrap')\n"
            "def trace(frame,event,arg):\n"
            " if event=='call' and frame.f_code.co_name=='begin' and "
            "frame.f_globals.get('__name__')=='experiments.shared_services.execution':\n"
            f"  Path({str(marker)!r}).touch()\n"
            "  sys.settrace(None)\n  os.kill(os.getpid(),signal.SIGTERM)\n"
            " return trace\n"
            "sys.settrace(trace)\nnamespace['main']()\n"
        )

        def launch(argv, **kwargs):
            assert argv[-1].endswith("/_bootstrap.py"), argv
            return real_popen([*argv[:-1], str(harness), argv[-1]], **kwargs)

        with patch.object(client.subprocess, "Popen", side_effect=launch):
            result = client.invoke(
                {
                    "action": "run",
                    "project": project,
                    "plan": plan,
                    "retry_of": None,
                    "timeout": 10,
                }
            )
        assert marker.exists(), "Early phase signal fixture was not reached"
        assert result["receipt"]["status"] == "interrupted", result
        assert result["receipt"]["error"] == "Cancelled before worker launch", result
        assert result["receipt"]["remaining_owned_processes"] == [], result
        assert result["result"]["payload"] == "forensic", result
        assert set(result["result"]["slot_statuses"].values()) == {"unavailable"}, result
        print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main(*sys.argv[1:])
