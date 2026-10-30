"""Authenticated loopback transport for fixed installed GUI actions."""

import re
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from ._gui_files import decode, encoded, read, require, sha256
from ._gui_state import Busy
from ._integrity import verify

STATIC = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/drafts.js": ("drafts.js", "text/javascript; charset=utf-8"),
    "/app.css": ("app.css", "text/css; charset=utf-8"),
}
DOWNLOAD_HEADERS = {
    "report.json": 'attachment; filename="report.json"',
    "report.md": 'attachment; filename="report.md"',
    "figure.svg": 'attachment; filename="figure.svg"',
}
CSP = (
    "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' blob:; "
    "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'; "
    "object-src 'none'"
)


class Server(ThreadingHTTPServer):
    daemon_threads = True  # Request threads never own SDK operations.
    allow_reuse_address = False

    def __init__(self, controller, port=0, *, assets=None):
        self.controller = controller
        self.token = secrets.token_hex(32)
        if assets is None:
            package = Path(__file__).resolve().parent
            manifest = verify(package)
            assets = {}
            for name, _ in STATIC.values():
                raw = read(package / "_gui_assets" / name)
                require(
                    manifest["files"]["_gui_assets/" + name]
                    == {"sha256": sha256(raw), "bytes": len(raw)},
                    "GUI asset differs from installed artifact",
                )
                assets[name] = raw
        self.assets = dict(assets)
        self.assets["index.html"] = self.assets["index.html"].replace(
            b"__SESSION_TOKEN__", self.token.encode()
        )
        self.request_slots = threading.BoundedSemaphore(16)
        super().__init__(("127.0.0.1", port), Handler)
        self.origin = f"http://127.0.0.1:{self.server_port}"
        self.stop_lock = threading.RLock()
        self.stopping = False

    def process_request(self, request, client_address):
        if not self.request_slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self.request_slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.request_slots.release()

    def request_stop(self):
        with self.stop_lock:
            if self.stopping:
                return
            self.stopping = True
            self.controller.begin_close()
            threading.Thread(target=self.shutdown, daemon=False).start()


class DeadlineReader:
    """One total request-read deadline, including continuously dripping headers."""

    def __init__(self, connection):
        self.connection = connection
        self.deadline = time.monotonic() + 5
        self.buffer = bytearray()
        self.closed = False

    def receive(self):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Request read deadline exceeded")
        self.connection.settimeout(remaining)
        return self.connection.recv(4096)

    def readline(self, limit):
        while b"\n" not in self.buffer and len(self.buffer) < limit:
            chunk = self.receive()
            if not chunk:
                break
            self.buffer.extend(chunk)
        size = min(self.buffer.find(b"\n") + 1 or len(self.buffer), limit)
        result = bytes(self.buffer[:size])
        del self.buffer[:size]
        return result

    def read(self, size):
        while len(self.buffer) < size:
            chunk = self.receive()
            if not chunk:
                break
            self.buffer.extend(chunk)
        result = bytes(self.buffer[:size])
        del self.buffer[:size]
        return result

    def close(self):
        self.closed = True
        self.buffer.clear()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"

    def setup(self):
        super().setup()
        self.connection.settimeout(5)
        self.rfile.close()
        self.rfile = DeadlineReader(self.connection)

    def log_message(self, *_args):
        pass

    def send(self, status, value, mime="application/json", *, filename=None):
        disposition = None
        if filename is not None:
            require(
                type(filename) is str and filename in DOWNLOAD_HEADERS,
                "Unsupported report download filename",
            )
            disposition = DOWNLOAD_HEADERS[filename]
        raw = encoded(value) if not isinstance(value, bytes) else value
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", CSP)
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        if disposition is not None:
            self.send_header("Content-Disposition", disposition)
        try:
            self.end_headers()
            self.wfile.write(raw)
        except (BrokenPipeError, ConnectionResetError):
            return

    def one(self, name, *, required=False):
        values = self.headers.get_all(name, [])
        require(
            len(values) <= 1 and (not required or len(values) == 1),
            "Exactly one " + name + " header is required",
        )
        return values[0] if values else None

    def authorized(self, mutation=False):
        require(not self.headers.get_all("Transfer-Encoding", []), "Transfer encoding refused")
        if not mutation:
            require(self.one("Content-Length") in {None, "0"}, "GET request bodies are unavailable")
        target = urlsplit(self.path)
        require(
            self.path.startswith("/")
            and not self.path.startswith("//")
            and not target.scheme
            and not target.netloc
            and not target.query
            and not target.fragment,
            "Only fixed origin-form routes are supported",
        )
        require(
            self.one("Host", required=True) == self.server.origin.removeprefix("http://"),
            "Foreign Host refused",
        )
        origin = self.one("Origin", required=mutation)
        require(origin is None or origin == self.server.origin, "Foreign Origin refused")
        require(
            self.one("Sec-Fetch-Site") not in {"cross-site", "same-site"},
            "Cross-site request refused",
        )
        if mutation or target.path.startswith("/api/"):
            token = self.one("X-OpenT1D-Token", required=True)
            require(
                token.isascii() and secrets.compare_digest(token, self.server.token),
                "Current session token required",
            )
        return target.path

    def body(self, maximum=65536):
        require(not self.headers.get_all("Transfer-Encoding", []), "Transfer encoding refused")
        length = self.one("Content-Length", required=True)
        require(
            re.fullmatch(r"0|[1-9][0-9]{0,6}", length) is not None and int(length) <= maximum,
            "Bounded JSON body required",
        )
        content_type = self.one("Content-Type", required=True)
        require(
            content_type.split(";", 1)[0].strip().lower() == "application/json",
            "JSON content type required",
        )
        raw = self.rfile.read(int(length))
        require(len(raw) == int(length), "Incomplete request body")
        return decode(raw)

    def do_GET(self):
        try:
            route = self.authorized()
            if route in STATIC:
                name, mime = STATIC[route]
                self.send(200, self.server.assets[name], mime)
            elif route == "/api/state":
                self.send(200, self.server.controller.state())
            elif match := re.fullmatch(r"/api/drafts/([a-f0-9]{32})", route):
                self.send(200, self.server.controller.get_draft(match[1]))
            elif match := re.fullmatch(r"/api/jobs/([a-f0-9]{32})", route):
                self.send(200, self.server.controller.get_job(match[1]))
            elif match := re.fullmatch(
                r"/api/reports/([a-f0-9]{32})/((?:studies/[a-z][a-z0-9_-]{0,63}/)?report\.(?:json|md)|figure\.svg)",
                route,
            ):
                raw, mime = self.server.controller.report(match[1], match[2])
                self.send(200, raw, mime, filename=match[2].rsplit("/", 1)[-1])
            else:
                self.send(404, {"error": "Unknown route"})
        except (BrokenPipeError, ConnectionResetError):
            return
        except (ValueError, KeyError, TypeError, OSError) as error:
            self.send(
                403
                if "header" in str(error)
                or "token" in str(error)
                or "Host" in str(error)
                or "Origin" in str(error)
                or "site" in str(error)
                else 409,
                {"error": str(error)[:500]},
            )

    def do_POST(self):
        try:
            route = self.authorized(mutation=True)
            body = self.body(2 * 1024 * 1024 if route == "/api/drafts" else 65536)
            if route == "/api/actions":
                self.send(202, self.server.controller.submit(body))
            elif route == "/api/drafts":
                require(
                    isinstance(body, dict)
                    and body.get("operation") in {"draft_create", "draft_save"},
                    "Only bounded concept intake uses this route",
                )
                self.send(202, self.server.controller.submit(body))
            elif match := re.fullmatch(r"/api/jobs/([a-f0-9]{32})/cancel", route):
                require(body == {}, "Empty cancellation body required")
                self.server.controller.cancel(match[1])
                self.send(202, {"stop_requested": True})
            elif route == "/api/shutdown":
                require(body == {}, "Empty shutdown body required")
                self.server.controller.begin_close()
                self.server.request_stop()
                self.send(
                    202,
                    {
                        "closing": True,
                        "message": "Runs stop through the SDK; other project actions "
                        "finish before exit.",
                    },
                )
            else:
                self.send(404, {"error": "Unknown route"})
        except Busy as error:
            self.send(409, {"error": str(error)})
        except (BrokenPipeError, ConnectionResetError):
            return
        except (TimeoutError, ValueError, KeyError, TypeError, OSError, RecursionError) as error:
            self.send(
                403
                if "header" in str(error)
                or "token" in str(error)
                or "Host" in str(error)
                or "Origin" in str(error)
                or "site" in str(error)
                else 400,
                {"error": str(error)[:500]},
            )

    def do_OPTIONS(self):
        self.send(403, {"error": "Cross-origin access is unavailable"})
