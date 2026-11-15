"""Private-pipe lifecycle around the existing GUI controller and transport."""

import argparse
import json
import os
import sys
import threading

from .gui import serve


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    args = parser.parse_args()

    def ready(server):
        def disconnected():
            # EOF means the live native owner exited, including an app crash.
            while os.read(sys.stdin.fileno(), 1):
                pass
            server.request_stop()

        print(
            json.dumps(
                {
                    "schema": "opent1d.desktop-ready/1",
                    "origin": server.origin,
                    "token": server.token,
                }
            ),
            flush=True,
        )
        threading.Thread(target=disconnected, daemon=True).start()

    serve(args.workspace, ready=ready)
