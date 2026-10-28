"""Serve the real checkout UI and workers with a disposable synthetic workspace."""

import argparse
import signal
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from experiments.gui.server import Server  # noqa: E402
from experiments.gui.service import Service  # noqa: E402
from experiments.platform_process import handled_signals  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    args = parser.parse_args()
    workspace = args.workspace.resolve(strict=True)
    if workspace == ROOT or ROOT in workspace.parents or workspace in ROOT.parents:
        parser.error("Browser checks require a separate temporary workspace")
    service = Service(workspace, source_root=ROOT, python=sys.executable)
    try:
        server = Server(service)
    except BaseException:
        service.close()
        raise

    def stop(_signum, _frame):
        threading.Thread(target=server.shutdown, daemon=True).start()

    for signum in handled_signals():
        signal.signal(signum, stop)
    print(f"OPENT1D_BROWSER_URL=http://127.0.0.1:{server.server_port}/", flush=True)
    try:
        server.serve_forever()
    finally:
        service.close()
        server.server_close()


if __name__ == "__main__":
    main()
