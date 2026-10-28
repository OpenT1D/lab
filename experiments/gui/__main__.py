"""Start the bounded local synthetic M3, maintained M4 and observation interface."""

import argparse
import signal
import threading
import webbrowser

from experiments.platform_process import handled_signals

from .server import create_server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--archive-root", action="append", default=[])
    parser.add_argument("--archive-store")
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error("Port must be between 0 and 65535")
    options = {}
    if args.archive_root:
        options["archive_roots"] = args.archive_root
    if args.archive_store:
        options["archive_store"] = args.archive_store
    server = create_server(args.port, **options)
    url = f"http://127.0.0.1:{server.server_port}/"

    def stop(_signum, _frame):
        threading.Thread(target=server.shutdown, daemon=True).start()

    for signum in handled_signals():
        signal.signal(signum, stop)
    print("OpenT1D local study interface: " + url, flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    finally:
        server.service.close()
        server.server_close()


if __name__ == "__main__":
    main()
