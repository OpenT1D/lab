"""Open the installed local workspace without Git, uv or environment setup."""

import argparse
import json
import os
import signal
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from urllib.parse import urlsplit

from experiments.desktop.installation_gate import InstallationGate
from experiments.desktop.runtime import packaged_capabilities
from experiments.gui.locking import WorkspaceLock
from experiments.gui.server import Server
from experiments.gui.service import Service, bounded_bytes
from experiments.platform_files import is_link, native_absolute, open_regular

SOURCE = Path(__file__).resolve().parents[2]


def default_workspace():
    if os.name == "nt":
        local = os.environ.get("LOCALAPPDATA")
        if not local:
            raise ValueError("Windows did not provide a local application-data folder")
        return Path(local) / "OpenT1D" / "workspace"
    if sys.platform == "darwin" and packaged_capabilities(SOURCE) is not None:
        return Path.home() / "Library" / "Application Support" / "OpenT1D" / "MMTT"
    return Path.home() / ".local" / "share" / "opent1d-desktop" / "workspace"


def directory(path):
    path = native_absolute(path)
    for item in (path, *path.parents):
        if is_link(item):
            raise ValueError("Application workspace must not contain linked directories")
    source = native_absolute(SOURCE)
    if path == source or path.is_relative_to(source) or source.is_relative_to(path):
        raise ValueError("Keep analysis data separate from the installed application")
    if packaged_capabilities(SOURCE) is not None:
        application = source.parents[3]
        if path == application or path.is_relative_to(application):
            raise ValueError("Keep analysis data outside the Mac application bundle")
    path.mkdir(parents=True, exist_ok=True)
    return path.resolve(strict=True)


def save_state(path, value):
    # Session token stays in a bounded local file, never in the browser URL/log.
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = open_regular(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True)
        stream.write("\n")


def read_state(path, workspace):
    value = json.loads(bounded_bytes(path, 16384))
    parsed = urlsplit(value["url"])
    if (
        parsed.scheme != "http"
        or parsed.hostname != "127.0.0.1"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
        or not parsed.port
        or value.get("workspace") != str(workspace)
        or not isinstance(value.get("token"), str)
        or len(value["token"]) != 64
    ):
        raise ValueError("Unsupported saved local application endpoint")
    return value


def request(state, route, body=None):
    base = state["url"].rstrip("/")
    headers = {"X-OpenT1D-Token": state["token"], "Origin": base}
    if body is not None:
        headers["Content-Type"] = "application/json"
    call = urllib.request.Request(
        base + route,
        headers=headers,
        data=None if body is None else json.dumps(body).encode(),
    )
    # A machine-wide proxy must not receive the local session token.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(call, timeout=5) as response:
        return json.loads(response.read(1024 * 1024))


def stop_existing(path, workspace):
    if not path.exists():
        # A manager lock without its endpoint is not evidence that shutdown is safe.
        manager = (
            WorkspaceLock(workspace / "results/gui/.manager.lock")
            if (workspace / "results/gui").exists()
            else None
        )
        if manager is not None:
            manager.close()
        return
    state = read_state(path, workspace)
    try:
        request(state, "/api/desktop/shutdown", {})
    except (OSError, urllib.error.URLError):
        pass
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        try:
            manager = WorkspaceLock(workspace / "results/gui/.manager.lock")
        except ValueError:
            time.sleep(0.1)
            continue
        manager.close()
        return
    raise ValueError("OpenT1D has not finished stopping; installation must wait")


def startup_lock(workspace):
    deadline = time.monotonic() + 10
    while True:
        try:
            return WorkspaceLock(workspace / "application-start.lock")
        except ValueError:
            if time.monotonic() >= deadline:
                raise ValueError(
                    "Another OpenT1D launch is still starting; try again shortly"
                ) from None
            time.sleep(0.1)


def run(args):
    workspace = directory(args.data_dir or default_workspace())
    state_path = workspace / "application-session.json"
    if args.stop:
        # The installer already owns the installation mutex while its private
        # maintenance child requests shutdown. Never recursively wait on it.
        stop_existing(state_path, workspace)
        return 0
    gate = InstallationGate()
    try:
        startup = startup_lock(workspace)
    except BaseException:
        gate.close()
        raise
    server = None
    state = None
    try:
        if state_path.exists():
            try:
                existing = read_state(state_path, workspace)
                current = request(existing, "/api/v1/bootstrap")
                if current.get("profile") == "desktop":
                    if existing.get("source_root") != str(SOURCE):
                        raise RuntimeError(
                            "Another OpenT1D version is open. Exit it before starting this version."
                        )
                    if args.state_file:
                        save_state(args.state_file, existing)
                    if not args.no_browser:
                        webbrowser.open(existing["url"])
                    return 0
            except (OSError, ValueError, KeyError, urllib.error.URLError):
                pass
        interpreter = Path(sys.executable)
        if os.name == "nt" and interpreter.name.lower() == "pythonw.exe":
            interpreter = interpreter.with_name("python.exe")
        archive_store = (
            None
            if packaged_capabilities(SOURCE) is not None
            else directory(args.archive_dir or workspace.with_name(workspace.name + "-archives"))
        )
        service = Service(
            workspace,
            python=interpreter,
            profile="desktop",
            source_root=SOURCE,
            archive_store=archive_store,
        )
        try:
            server = Server(service, args.port)
        except BaseException:
            service.close()
            raise
        state = {
            "schema": "opent1d.desktop-session/1",
            "profile": "desktop",
            "url": f"http://127.0.0.1:{server.server_port}/",
            "token": server.token,
            "pid": os.getpid(),
            "workspace": str(workspace),
            "source_root": str(SOURCE),
            "build_id": SOURCE.parent.name,
        }
        save_state(state_path, state)
        if args.state_file:
            save_state(args.state_file, state)
    except BaseException:
        if server is not None:
            server.service.close()
            server.server_close()
        raise
    finally:
        startup.close()
        gate.close()
    if server is None:
        return 0

    def stop(_number, _frame):
        threading.Thread(target=server.shutdown, daemon=True).start()

    previous = {}
    for name in ("SIGINT", "SIGTERM", "SIGHUP"):
        number = getattr(signal, name, None)
        if number is not None:
            previous[number] = signal.signal(number, stop)
    try:
        if not args.no_browser:
            webbrowser.open(state["url"])
        server.serve_forever(poll_interval=0.1)
    finally:
        service.close()
        server.server_close()
        if state_path.exists() and read_state(state_path, workspace).get("token") == state["token"]:
            state_path.unlink()
        for number, handler in previous.items():
            signal.signal(number, handler)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--state-file", type=Path)
    parser.add_argument("--archive-dir", type=Path)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--stop", action="store_true")
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error("Choose a port from 0 to 65535")
    try:
        return run(args)
    except (OSError, ValueError, KeyError, RuntimeError) as error:
        message = "OpenT1D could not start or stop. " + str(error)
        if os.name == "nt" and not (args.no_browser or args.stop):
            import ctypes

            ctypes.windll.user32.MessageBoxW(None, message, "OpenT1D", 0x10)
        elif sys.stderr is not None:
            print(message, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
