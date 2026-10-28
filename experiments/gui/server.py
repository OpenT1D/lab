"""Loopback-only HTTP transport with fixed routes and same-origin mutation checks."""

import json
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .service import MAX_JSON, Service, decode_json

ASSETS = Path(__file__).resolve().parent / "static"
CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; "
    "img-src 'self' blob:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
)


class Server(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, service, port=0):
        self.service = service
        self.token = secrets.token_hex(32)
        super().__init__(("127.0.0.1", port), Handler)
        self.origins = {
            f"http://127.0.0.1:{self.server_port}",
            f"http://localhost:{self.server_port}",
        }
        self.hosts = {urlsplit(value).netloc for value in self.origins}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        # Request paths and bodies can identify local research material.
        pass

    def send(self, status, body, content_type="application/json; charset=utf-8", filename=None):
        if isinstance(body, dict):
            body = json.dumps(body, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", CSP)
        self.send_header("Referrer-Policy", "no-referrer")
        if filename:
            self.send_header("Content-Disposition", 'attachment; filename="' + filename + '"')
        self.end_headers()
        self.wfile.write(body)

    def admitted(self, *, api=False, mutation=False):
        if self.headers.get("Host") not in self.server.hosts:
            self.send(403, {"error": "Foreign Host refused"})
            return False
        origin = self.headers.get("Origin")
        if origin is not None and origin not in self.server.origins:
            self.send(403, {"error": "Foreign Origin refused"})
            return False
        if mutation and origin not in self.server.origins:
            self.send(403, {"error": "Same-origin request required"})
            return False
        token = self.headers.get("X-OpenT1D-Token", "")
        if api and (not token.isascii() or not secrets.compare_digest(token, self.server.token)):
            self.send(403, {"error": "Session token required; reload this page"})
            return False
        return True

    def do_GET(self):
        target = urlsplit(self.path)
        api = target.path.startswith("/api/v1/")
        if not self.admitted(api=api):
            return
        try:
            if target.path in {
                "/",
                "/app.js",
                "/draft.js",
                "/app.css",
                "/workspace.js",
                "/workspace.css",
                "/ux.js",
                "/icon.svg",
                "/observations.js",
                "/sampling.js",
            }:
                name = "index.html" if target.path == "/" else target.path[1:]
                raw = (ASSETS / name).read_bytes()
                if name == "index.html":
                    raw = raw.replace(b"__SESSION_TOKEN__", self.server.token.encode())
                    raw = raw.replace(
                        b"__APPLICATION_PROFILE__", self.server.service.profile.encode()
                    )
                    if self.server.service.profile == "desktop":
                        raw = raw.replace(b"this checkout", b"your OpenT1D workspace")
                        raw = raw.replace(
                            b"Reconstruction uses this interface's current clean checkout. "
                            b"A different recorded revision needs an explicitly trusted compatible "
                            b"checkout through the CLI.",
                            b"Reconstruction uses this version's verified installed reader. "
                            b"For an older recorded version, exit OpenT1D and open its matching "
                            b"shortcut under Start menu / OpenT1D / Saved readers.",
                        )
                kind = {
                    "index.html": "text/html",
                    "app.js": "text/javascript",
                    "draft.js": "text/javascript",
                    "app.css": "text/css",
                    "workspace.js": "text/javascript",
                    "workspace.css": "text/css",
                    "ux.js": "text/javascript",
                    "icon.svg": "image/svg+xml",
                    "observations.js": "text/javascript",
                    "sampling.js": "text/javascript",
                }[name]
                self.send(200, raw, kind + "; charset=utf-8")
            elif target.path == "/api/v1/bootstrap":
                self.send(200, self.server.service.bootstrap())
            elif len(target.path.split("/")) == 5 and target.path.split("/")[1:4] == [
                "api",
                "v1",
                "configurations",
            ]:
                self.send(
                    200,
                    self.server.service.resolve_configuration(target.path.split("/")[4]),
                )
            elif target.path == "/api/v1/files":
                query = parse_qs(target.query, strict_parsing=True)
                self.send(
                    200,
                    self.server.service.browse(
                        query.get("directory", ["experiments/m4"])[0],
                        query.get("kind", ["model"])[0],
                    ),
                )
            elif target.path.startswith(("/api/v1/observations/", "/api/v1/sampling/")):
                controller = (
                    self.server.service.sampling
                    if target.path.startswith("/api/v1/sampling/")
                    else self.server.service.observations
                )
                route = target.path.replace("/sampling/", "/observations/", 1)
                parts = target.path.split("/")
                if route == "/api/v1/observations/bootstrap":
                    self.send(200, controller.bootstrap())
                elif route == "/api/v1/observations/files":
                    query = parse_qs(target.query, strict_parsing=True)
                    self.send(200, controller.browse(query.get("directory", ["."])[0]))
                elif route == "/api/v1/observations/configurations":
                    self.send(200, {"configurations": controller.configurations()})
                elif route == "/api/v1/observations/entries":
                    self.send(200, {"entries": controller.list()})
                elif len(parts) == 6 and parts[4] == "configurations":
                    self.send(200, controller.get_configuration(parts[5]))
                elif len(parts) == 6 and parts[4] == "entries":
                    self.send(200, controller.get(parts[5]))
                elif len(parts) == 7 and parts[4] == "entries" and parts[6] == "report":
                    self.send(200, controller.report(parts[5]))
                elif len(parts) == 8 and parts[4] == "entries" and parts[6] == "artifacts":
                    kind = "application/json" if parts[7] == "report.json" else "text/plain"
                    self.send(200, controller.report_bytes(parts[5], parts[7]), kind, parts[7])
                else:
                    self.send(404, {"error": "Unknown observation route"})
            elif target.path.startswith("/api/v1/m3/"):
                controller = self.server.service.m3
                parts = target.path.split("/")
                if target.path == "/api/v1/m3/bootstrap":
                    self.send(200, controller.bootstrap())
                elif target.path == "/api/v1/m3/inputs":
                    self.send(200, {"inputs": controller.input_list()})
                elif target.path == "/api/v1/m3/inputs/browse":
                    query = parse_qs(target.query, strict_parsing=True)
                    self.send(
                        200,
                        controller.browse(
                            query.get("root_id", [""])[0], query.get("directory", [""])[0]
                        ),
                    )
                elif target.path == "/api/v1/m3/configurations":
                    self.send(200, {"configurations": controller.configurations()})
                elif target.path == "/api/v1/m3/entries":
                    self.send(200, {"entries": controller.list()})
                elif len(parts) == 6 and parts[4] == "configurations":
                    self.send(200, controller.get_configuration(parts[5]))
                elif len(parts) == 6 and parts[4] == "entries":
                    self.send(200, controller.get(parts[5]))
                elif len(parts) == 7 and parts[4] == "entries" and parts[6] == "report":
                    self.send(200, controller.report(parts[5]))
                elif (
                    len(parts) == 8
                    and parts[4] == "entries"
                    and parts[6] == "artifacts"
                    and parts[7] in {"report.json", "report.md"}
                ):
                    kind = "application/json" if parts[7] == "report.json" else "text/plain"
                    self.send(200, controller.report_bytes(parts[5], parts[7]), kind, parts[7])
                else:
                    self.send(404, {"error": "Unknown M3 route"})
            elif target.path == "/api/v1/durable/bootstrap":
                self.send(200, self.server.service.durable.bootstrap())
            elif target.path == "/api/v1/durable/sources":
                self.send(200, {"sources": self.server.service.durable.sources()})
            elif target.path == "/api/v1/durable/entries":
                self.send(200, {"entries": self.server.service.durable.entries()})
            elif target.path.startswith("/api/v1/durable/entries/"):
                parts = target.path.split("/")
                controller = self.server.service.durable
                if len(parts) == 6:
                    self.send(200, controller.get(parts[5]))
                elif len(parts) == 7 and parts[6] == "report":
                    self.send(200, controller.report(parts[5]))
                elif (
                    len(parts) == 8
                    and parts[6] == "artifacts"
                    and parts[7] in {"report.json", "report.md", "figure.svg"}
                ):
                    kind = {
                        "report.json": "application/json",
                        "report.md": "text/plain",
                        "figure.svg": "image/svg+xml",
                    }[parts[7]]
                    self.send(200, controller.report_bytes(parts[5], parts[7]), kind, parts[7])
                else:
                    self.send(404, {"error": "Unknown durable route"})
            elif target.path == "/api/v1/library/roots":
                self.send(200, {"roots": self.server.service.library.roots()})
            elif target.path == "/api/v1/library/files":
                query = parse_qs(target.query, strict_parsing=True)
                self.send(
                    200,
                    self.server.service.library.browse(
                        query.get("root_id", [""])[0], query.get("directory", [""])[0]
                    ),
                )
            elif target.path == "/api/v1/library/entries":
                query = parse_qs(target.query, strict_parsing=True) if target.query else {}
                self.send(
                    200,
                    {
                        "entries": self.server.service.library.entries(
                            {key: values[0] for key, values in query.items()}
                        )
                    },
                )
            elif target.path.startswith("/api/v1/library/entries/"):
                parts = target.path.split("/")
                if len(parts) == 6:
                    self.send(200, self.server.service.library.get(parts[5]))
                elif len(parts) == 7 and parts[6] == "report":
                    self.send(200, self.server.service.library.report(parts[5]))
                elif len(parts) == 8 and parts[6] == "artifacts":
                    kind = {
                        "report.json": "application/json",
                        "report.md": "text/plain",
                        "figure.svg": "image/svg+xml",
                    }.get(parts[7])
                    if kind is None:
                        raise ValueError("Unknown report artifact")
                    self.send(
                        200,
                        self.server.service.library.report_bytes(parts[5], parts[7]),
                        kind,
                        None if parts[7] == "figure.svg" else parts[7],
                    )
                else:
                    self.send(404, {"error": "Unknown route"})
            elif target.path == "/api/v1/campaigns/configurations":
                self.send(200, {"configurations": self.server.service.campaigns.configurations()})
            elif target.path == "/api/v1/campaigns":
                self.send(200, {"campaigns": self.server.service.campaigns.entries()})
            elif target.path.startswith("/api/v1/campaigns/"):
                parts = target.path.split("/")
                controller = self.server.service.campaigns
                if len(parts) == 6 and parts[4] == "configurations":
                    self.send(200, controller.get_configuration(parts[5]))
                elif len(parts) == 5:
                    self.send(200, controller.get(parts[4]))
                elif len(parts) == 6 and parts[5] == "report":
                    self.send(200, controller.report(parts[4]))
                elif len(parts) == 7 and parts[5] == "artifacts":
                    kind = {"report.json": "application/json", "report.md": "text/plain"}.get(
                        parts[6]
                    )
                    if kind is None:
                        raise ValueError("Unknown campaign report artifact")
                    self.send(200, controller.report_bytes(parts[4], parts[6]), kind, parts[6])
                else:
                    self.send(404, {"error": "Unknown route"})
            elif target.path == "/api/v1/jobs":
                self.send(200, {"jobs": self.server.service.list_jobs()})
            else:
                parts = target.path.split("/")
                if len(parts) == 5 and parts[1:4] == ["api", "v1", "jobs"]:
                    self.send(200, self.server.service.get_job(parts[4], validate=True))
                elif len(parts) == 6 and parts[1:4] == ["api", "v1", "jobs"]:
                    if parts[5] == "report":
                        self.send(200, self.server.service.report(parts[4]))
                    elif parts[5] in {"report.json", "report.md", "figure.svg"}:
                        path = self.server.service.report_file(parts[4], parts[5])
                        kinds = {
                            "report.json": "application/json",
                            "report.md": "text/plain",
                            "figure.svg": "image/svg+xml",
                        }
                        self.send(
                            200,
                            self.server.service.report_bytes(parts[4], parts[5]),
                            kinds[path.name],
                            None if path.name == "figure.svg" else path.name,
                        )
                    else:
                        self.send(404, {"error": "Unknown route"})
                else:
                    self.send(404, {"error": "Unknown route"})
        except (OSError, ValueError, KeyError, TypeError, RecursionError) as error:
            self.send(400, {"error": str(error)})

    def do_POST(self):
        if not self.admitted(api=True, mutation=True):
            return
        try:
            if self.headers.get_content_type() != "application/json" or self.headers.get(
                "Transfer-Encoding"
            ):
                raise ValueError("Bounded JSON body required")
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= MAX_JSON:
                raise ValueError("Request byte limit exceeded")
            self.connection.settimeout(10)
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise ValueError("Incomplete request body")
            body = decode_json(raw)
            if not isinstance(body, dict):
                raise ValueError("JSON object required")
            target = urlsplit(self.path).path
            if target == "/api/desktop/shutdown" and self.server.service.profile == "desktop":
                if body:
                    raise ValueError("Shutdown request body must be empty")
                self.send(202, {"status": "stopping"})
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return
            if target.startswith(("/api/v1/observations/", "/api/v1/sampling/")):
                parts = target.split("/")
                service = self.server.service
                controller = (
                    service.sampling
                    if target.startswith("/api/v1/sampling/")
                    else service.observations
                )
                target = target.replace("/sampling/", "/observations/", 1)
                if target == "/api/v1/observations/example":
                    if set(body) != {"case"}:
                        raise ValueError("Choose one invented case")
                    self.send(
                        202, service.start_observations(controller.op("example"), case=body["case"])
                    )
                elif target == "/api/v1/observations/inspect":
                    self.send(201, controller.inspect(body))
                elif target == "/api/v1/observations/configurations":
                    self.send(201, controller.configure(body))
                elif (
                    len(parts) == 7
                    and parts[4] == "configurations"
                    and parts[6] in {"freeze", "run"}
                ):
                    if body:
                        raise ValueError("Observation operation body must be empty")
                    self.send(
                        202,
                        service.start_observations(
                            controller.op(parts[6]), configuration_id=parts[5]
                        ),
                    )
                elif len(parts) == 7 and parts[4] == "entries" and parts[6] == "reconstruct":
                    if body:
                        raise ValueError("Observation operation body must be empty")
                    self.send(
                        202,
                        service.start_observations(controller.op("reconstruct"), entry_id=parts[5]),
                    )
                else:
                    self.send(404, {"error": "Unknown observation route"})
                return
            if target.startswith("/api/v1/m3/"):
                parts = target.split("/")
                service = self.server.service
                if target == "/api/v1/m3/fixture":
                    if body:
                        raise ValueError("Fixture operation body must be empty")
                    self.send(202, service.start_m3("m3_fixture"))
                elif target == "/api/v1/m3/inspect":
                    self.send(201, service.m3.inspect(body))
                elif target == "/api/v1/m3/configurations":
                    self.send(201, service.configure_m3(body))
                elif (
                    len(parts) == 7
                    and parts[4] == "configurations"
                    and parts[6] in {"check", "run"}
                ):
                    if body:
                        raise ValueError("M3 operation body must be empty")
                    self.send(202, service.start_m3("m3_" + parts[6], configuration_id=parts[5]))
                elif (
                    len(parts) == 7
                    and parts[4] == "entries"
                    and parts[6] in {"reconstruct", "retain"}
                ):
                    if body:
                        raise ValueError("M3 operation body must be empty")
                    self.send(
                        202,
                        service.start_m3("m3_reconstruct", entry_id=parts[5])
                        if parts[6] == "reconstruct"
                        else service.start_durable("durable_forensic", identity=parts[5]),
                    )
                else:
                    self.send(404, {"error": "Unknown M3 route"})
                return
            if target in {"/api/v1/durable/export", "/api/v1/durable/register"}:
                self.send(
                    202,
                    self.server.service.start_durable(
                        "durable_" + target.rsplit("/", 1)[1], body=body
                    ),
                )
                return
            durable_parts = target.split("/")
            if (
                len(durable_parts) == 7
                and durable_parts[1:5] == ["api", "v1", "durable", "entries"]
                and durable_parts[6] in {"verify", "reconstruct"}
            ):
                if body:
                    raise ValueError("Operation body must be empty")
                self.send(
                    202,
                    self.server.service.start_durable(
                        "durable_" + durable_parts[6], identity=durable_parts[5]
                    ),
                )
                return
            if target == "/api/v1/configurations":
                self.send(201, self.server.service.configure(body))
                return
            if target == "/api/v1/campaigns/configurations":
                self.send(201, self.server.service.configure_campaign(body))
                return
            campaign_parts = target.split("/")
            if (
                len(campaign_parts) == 7
                and campaign_parts[1:5] == ["api", "v1", "campaigns", "configurations"]
                and campaign_parts[6] in {"check", "install", "run"}
            ):
                if body:
                    raise ValueError("Operation body must be empty")
                self.send(
                    202,
                    self.server.service.start_campaign(
                        "campaign_" + campaign_parts[6], configuration_id=campaign_parts[5]
                    ),
                )
                return
            if (
                len(campaign_parts) == 6
                and campaign_parts[1:4] == ["api", "v1", "campaigns"]
                and campaign_parts[5] in {"resume", "reconstruct"}
            ):
                if body:
                    raise ValueError("Operation body must be empty")
                self.send(
                    202,
                    self.server.service.start_campaign(
                        "campaign_" + campaign_parts[5], campaign_id=campaign_parts[4]
                    ),
                )
                return
            if target == "/api/v1/library/entries":
                self.send(202, self.server.service.add_archive(body))
                return
            parts = target.split("/")
            if (
                len(parts) == 7
                and parts[1:5] == ["api", "v1", "library", "entries"]
                and parts[6] == "visibility"
            ):
                if not isinstance(body, dict) or set(body) != {"hidden"}:
                    raise ValueError("Choose whether to hide this local reference")
                self.send(200, self.server.service.library.set_hidden(parts[5], body["hidden"]))
                return
            if (
                len(parts) == 7
                and parts[1:5] == ["api", "v1", "library", "entries"]
                and parts[6] == "verify"
            ):
                if body:
                    raise ValueError("Operation body must be empty")
                self.send(202, self.server.service.verify_archive(parts[5]))
                return
            if (
                len(parts) == 6
                and parts[1:4] == ["api", "v1", "configurations"]
                and parts[5] in {"check", "install", "run"}
            ):
                if body:
                    raise ValueError("Operation body must be empty")
                self.send(202, self.server.service.start(parts[5], configuration_id=parts[4]))
            elif (
                len(parts) == 6
                and parts[1:4] == ["api", "v1", "jobs"]
                and parts[5] in {"cancel", "reconstruct"}
            ):
                if body:
                    raise ValueError("Operation body must be empty")
                if parts[5] == "cancel":
                    self.send(202, self.server.service.cancel(parts[4]))
                else:
                    self.send(202, self.server.service.start("reconstruct", archive_job=parts[4]))
            else:
                self.send(404, {"error": "Unknown route"})
        except (OSError, ValueError, KeyError, TypeError, RecursionError) as error:
            self.send(400, {"error": str(error)})


def create_server(port=0, *, archive_roots=(), archive_store=None):
    options = {}
    if archive_roots:
        options["archive_roots"] = archive_roots
    if archive_store is not None:
        options["archive_store"] = archive_store
    service = Service(**options)
    try:
        return Server(service, port)
    except BaseException:
        service.close()
        raise
