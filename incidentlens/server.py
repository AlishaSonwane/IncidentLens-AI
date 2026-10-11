"""Loopback workspace: explicit local imports/saves; evidence tools remain read-only."""
import argparse
import json
import threading
import uuid
from collections import OrderedDict
from .workspace import Store, WorkspaceTools
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .engine import investigate, to_markdown
from .tools import SampleTools
from .ollama import OllamaPlanner

STATIC = Path(__file__).resolve().parent / "static"
STATIC_FILES = {"/": ("index.html", "text/html; charset=utf-8"),
                "/ui.css": ("ui.css", "text/css; charset=utf-8"),
                "/ui.js": ("ui.js", "text/javascript; charset=utf-8")}


def make_handler(tools, port, store=None):
    store = store or Store()
    snapshots = OrderedDict()
    cache_lock = threading.Lock()
    def snapshot(report):
        report["snapshot_id"] = uuid.uuid4().hex
        report["markdown"] = to_markdown(report)
        with cache_lock:
            snapshots[report["snapshot_id"]] = json.loads(json.dumps(report))
            while len(snapshots) > 64: snapshots.popitem(last=False)
        return report
    ai_lock = threading.Lock()
    allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
    allowed_origins = {f"http://127.0.0.1:{port}", f"http://localhost:{port}"}

    class Handler(BaseHTTPRequestHandler):
        server_version = "IncidentLens/0.1"

        def log_message(self, fmt, *args):
            pass

        def reply(self, status, body, content_type="application/json; charset=utf-8"):
            if isinstance(body, (dict, list)):
                body = json.dumps(body, ensure_ascii=False).encode("utf-8")
            elif isinstance(body, str):
                body = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy",
                             "default-src 'self'; script-src 'self'; style-src 'self'; "
                             "connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; "
                             "base-uri 'none'; object-src 'none'; form-action 'none'")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            # Validate Host/Origin to reject DNS-rebinding and cross-origin requests.
            if self.headers.get("Host") not in allowed_hosts:
                return self.reply(403, {"error": "Only the loopback host is permitted."})
            origin = self.headers.get("Origin")
            if origin and origin not in allowed_origins:
                return self.reply(403, {"error": "Cross-origin requests are forbidden."})
            if self.headers.get("Sec-Fetch-Site") == "cross-site":
                return self.reply(403, {"error": "Cross-site requests are forbidden."})
            if len(self.path) > 2048:
                return self.reply(414, {"error": "Request URL too long."})
            path = urlsplit(self.path)
            query = parse_qs(path.query)
            try:
                if path.path in STATIC_FILES:
                    filename, mime = STATIC_FILES[path.path]
                    return self.reply(200, (STATIC / filename).read_bytes(), mime)
                if path.path == "/health":
                    return self.reply(200, {"status": "ok", "project": "IncidentLens AI",
                                           "mode": "local-evidence", "remediation_enabled": False})
                if path.path == "/api/history":
                    return self.reply(200, store.history())
                if path.path == "/api/history/report":
                    return self.reply(200, store.report(query["id"][0]))
                if path.path == "/api/runbooks":
                    return self.reply(200, tools.search_runbooks(query["incident_id"][0], query.get("q", [""])[0]))
                if path.path == "/api/incidents":
                    return self.reply(200, tools.catalog())
                if path.path == "/api/ai-report":
                    # Explicit browser action only: cross-origin pages cannot supply this header.
                    if self.headers.get("X-IncidentLens-AI") != "1":
                        return self.reply(403, {"error": "Use the explicit Local AI investigation button."})
                    if set(query) != {"incident_id"} or len(query["incident_id"]) != 1:
                        raise ValueError("Supply exactly one incident_id.")
                    incident_id = query["incident_id"][0]
                    if incident_id not in {item["id"] for item in tools.catalog()}:
                        raise ValueError("Unknown sample incident.")
                    if not ai_lock.acquire(blocking=False):
                        return self.reply(429, {"error": "A local AI investigation is already running."})
                    try:
                        report = investigate(incident_id, tools,
                            OllamaPlanner("llama3.2:1b", strategy="structured"))
                        snapshot(report)
                        return self.reply(200, report)
                    finally:
                        ai_lock.release()
                if path.path in ("/api/report", "/api/report.md"):
                    if set(query) != {"incident_id"} or len(query["incident_id"]) != 1:
                        raise ValueError("Supply exactly one incident_id.")
                    report = investigate(query["incident_id"][0], tools)
                    if path.path.endswith(".md"):
                        return self.reply(200, to_markdown(report), "text/markdown; charset=utf-8")
                    snapshot(report)
                    return self.reply(200, report)
                return self.reply(404, {"error": "Endpoint not found."})
            except (ValueError, KeyError, TypeError):
                return self.reply(400, {"error": "Invalid sample request."})
            except Exception:
                return self.reply(500, {"error": "Local report could not be generated."})

        def do_POST(self):
            if self.path not in ('/api/import', '/api/history/save'):
                return self.disabled()
            if (self.headers.get('Host') not in allowed_hosts or
                self.headers.get('Origin', next(iter(allowed_origins))) not in allowed_origins or
                self.headers.get('Sec-Fetch-Site') == 'cross-site' or
                self.headers.get('X-IncidentLens-Action') != '1'):
                return self.reply(403, {'error':'Explicit local action required.'})
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 600000 or self.headers.get('Transfer-Encoding'):
                    raise ValueError('Request size must be 1–600000 bytes.')
                if self.headers.get('Content-Type','').split(';')[0] != 'application/json':
                    raise ValueError('JSON request required.')
                self.connection.settimeout(10)
                data = json.loads(self.rfile.read(size).decode('utf-8'))
                if not isinstance(data,dict): raise ValueError('Invalid request.')
                if self.path == '/api/import':
                    if set(data) != {'title','content'}: raise ValueError('Supply title and content only.')
                    if not isinstance(tools,WorkspaceTools): raise ValueError('Imports unavailable in sample-only mode.')
                    incident = store.add_import(data['title'],data['content'])
                    return self.reply(201, {'incident_id':incident['id'], 'events':len(incident['events'])})
                if set(data) != {'snapshot_id'} or not isinstance(data['snapshot_id'],str):
                    raise ValueError('Supply the displayed snapshot ID only.')
                with cache_lock:
                    report = snapshots.get(data['snapshot_id'])
                if report is None:
                    report = store.report(data['snapshot_id'])
                return self.reply(200, {'id':store.save(data['snapshot_id'],report)})
            except (ValueError, KeyError, TypeError, UnicodeError):
                return self.reply(400, {'error':'Invalid input, exceeded limits, or expired snapshot. Check the input format or reload the report.'})
            except Exception:
                return self.reply(500, {'error':'Local workspace action failed.'})

        def disabled(self):
            self.reply(405, {'error':'Method disabled. No remediation endpoints exist.'})
        do_DELETE = disabled
        do_PUT = disabled
        do_PATCH = disabled
        do_OPTIONS = disabled

    return Handler


def main():
    parser = argparse.ArgumentParser(description="Start the IncidentLens AI local sample UI")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("Use a port between 1024 and 65535.")
    store = Store()
    tools = WorkspaceTools(store)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(tools, args.port, store))
    print(f"IncidentLens AI: http://127.0.0.1:{args.port} — local evidence / no remediation", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
