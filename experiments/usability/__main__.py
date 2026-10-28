"""Prepare, receive, check, explicitly install and start a local GUI test packet."""

import argparse
import json
import os
import signal
import stat
import subprocess
import sys
import threading
import uuid
import webbrowser
from pathlib import Path
from urllib.parse import urlsplit

from .packet import ROOT, clean_revision, digest, prepare, receive, require, verify


def selected(directory):
    record = verify(directory)
    require(clean_revision() == record["commit"], "Use the packet's clean source-bundle checkout")
    require(
        os.name == "posix" and sys.platform in {"darwin", "linux"},
        "Use macOS/Linux; on Windows use the prepared WSL route",
    )
    return record


def setup(directory, install=False):
    from experiments.setup.core import execute, plan

    record = selected(directory)
    output = ROOT / "results/usability/setup" / uuid.uuid4().hex
    plan("m4-study-secure", output / "plan")
    result = execute(output / "plan", output / "receipt", install=install)
    return {"packet_id": record["id"], "receipt": str(output / "receipt"), "setup": result}


def start(directory, port=0, open_browser=True):
    record = selected(directory)
    from experiments.gui.server import Handler, create_server

    directory = Path(directory).absolute()

    class PacketHandler(Handler):
        def do_GET(self):
            target = urlsplit(self.path).path
            mapping = {
                "/test/": "assets/index.html",
                "/test/participant": "assets/participant.html",
                "/test/moderator": "assets/moderator.html",
                "/test/observations": "assets/observations.html",
                "/test/worksheet.js": "assets/worksheet.js",
                "/test/style.css": "assets/style.css",
                "/test/assets/worksheet.js": "assets/worksheet.js",
                "/test/assets/style.css": "assets/style.css",
                "/test/FirstSteps.html": "FirstSteps.html",
                "/test/Observations.html": "Observations.html",
                "/test/guides/local-gui.html": "guides/local-gui.html",
                "/test/guides/gui-test-session.html": "guides/gui-test-session.html",
                "/test/guides/gui-researcher-exercise.html": "guides/gui-researcher-exercise.html",
            }
            for name in (
                "Participant",
                "Moderator",
                "M4-Participant",
                "M4-Moderator",
                "M4-Observations",
            ):
                mapping["/test/" + name + ".html"] = name + ".html"
            for name in ("observation-analysis", "mmtt-sampling"):
                mapping["/test/guides/" + name + ".html"] = "guides/" + name + ".html"
            if target == "/test/packet.json":
                if self.admitted():
                    self.send(
                        200,
                        {
                            key: record[key]
                            for key in (
                                "schema",
                                "id",
                                "commit",
                                "language",
                                "target",
                                "goals",
                                "references",
                            )
                        },
                    )
                return
            if target not in mapping:
                return super().do_GET()
            if not self.admitted():
                return
            try:
                path = directory / mapping[target]
                for parent in (path, path.parent, directory):
                    require(not parent.is_symlink(), "Packet asset was replaced by a link")
                info = path.lstat()
                require(
                    stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_size <= 1048576,
                    "Invalid packet asset",
                )
                raw = path.read_bytes()
                require(
                    digest(raw) == record["inventory"]["files"][mapping[target]]["sha256"],
                    "Packet asset changed; restart with an intact packet",
                )
                kind = (
                    "text/javascript"
                    if path.suffix == ".js"
                    else "text/css"
                    if path.suffix == ".css"
                    else "text/html"
                )
                self.send(200, raw, kind + "; charset=utf-8")
            except (OSError, ValueError) as error:
                self.send(409, {"error": str(error)})

    server = create_server(port, archive_roots=(directory / "references",))
    stopping, serving = threading.Event(), threading.Event()

    def stop(_number, _frame):
        stopping.set()
        action = server.shutdown if serving.is_set() else server.service.close
        threading.Thread(target=action, daemon=True).start()

    previous_handlers = {
        number: signal.signal(number, stop)
        for number in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)
    }
    try:
        server.RequestHandlerClass = PacketHandler
        root_id = next(
            item["id"]
            for item in server.service.library.roots()
            if item["directory"] == str((directory / "references").resolve())
        )
        for kind in ("complete", "interrupted"):
            request = server.service.library.add(
                {
                    "root_id": root_id,
                    "path": kind,
                    "task": "m4-study-secure",
                    "tags": ["session-reference", kind],
                }
            )
            job = server.service.start_owned("library_index", request)
            server.service.thread.join(120)
            if stopping.is_set():
                raise SystemExit(130)
            require(
                not server.service.thread.is_alive()
                and server.service.jobs[job["id"]]["state"] == "completed",
                "Reference indexing did not complete; inspect retained GUI evidence",
            )

        address = f"http://127.0.0.1:{server.server_port}/test/"
        print("OpenT1D session: " + address, flush=True)
        print(
            (
                "Keep this window open. Use Cancel in the GUI, then Ctrl+C here to stop"
                ". Closing a browser tab does not stop a run."
            ),
            flush=True,
        )
        if open_browser:
            webbrowser.open(address)
        if not stopping.is_set():
            serving.set()
            server.serve_forever()
    finally:
        server.server_close()
        server.service.close()
        for number, previous in previous_handlers.items():
            signal.signal(number, previous)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    command = commands.add_parser("prepare")
    command.add_argument("--output", type=Path, required=True)
    command.add_argument("--complete", type=Path, required=True)
    command.add_argument("--interrupted", type=Path, required=True)
    command.add_argument("--session", choices=("m4", "mmtt"), default="m4")
    command.add_argument("--language", choices=("en", "nl"), default="en")
    command.add_argument("--target", choices=("posix", "windows-wsl"), default="posix")
    for action in ("verify", "receive", "check", "install", "start"):
        command = commands.add_parser(action)
        command.add_argument("--packet", type=Path, required=True)
        if action == "receive":
            command.add_argument("--output", type=Path, required=True)
        if action == "start":
            command.add_argument("--port", type=int, default=0)
            command.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    try:
        if args.action == "prepare":
            result = prepare(
                args.output,
                args.complete,
                args.interrupted,
                args.language,
                args.target,
                session=args.session,
            )
        elif args.action == "receive":
            result = receive(args.packet, args.output)
        elif args.action == "verify":
            result = verify(args.packet)
        elif args.action == "start":
            require(0 <= args.port <= 65535, "Choose a port between 0 and 65535")
            start(args.packet, args.port, not args.no_browser)
            return
        else:
            result = setup(args.packet, args.action == "install")
        print(json.dumps(result, indent=2, allow_nan=False))
        if args.action in {"check", "install"} and not result["setup"]["ready"]:
            parser.exit(2, "Setup is not ready. Keep its receipt and follow the recovery guide.\n")
    except subprocess.SubprocessError as error:
        parser.exit(
            1, f"OpenT1D: a fixed Git/native-reader operation failed ({type(error).__name__}).\n"
        )
    except (OSError, ValueError) as error:
        parser.exit(1, f"OpenT1D: {error}\nSee docs/gui-test-session.md for setup and recovery.\n")


if __name__ == "__main__":
    main()
