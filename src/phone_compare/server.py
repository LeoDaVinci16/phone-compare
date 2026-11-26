"""App mode: serve the report from your own PC so the page can edit the data.

    phone-compare --serve            (or double-click run_app.bat)

It uses Python's built-in web server and only listens on 127.0.0.1 (this computer), so nothing
is exposed to the network. Every page load re-reads the CSV files, so edits made in a
spreadsheet app show up after a refresh. Stop it with Ctrl+C (or by closing the window).
"""

from __future__ import annotations

import json
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .data import DataFileError, apply_selection, load_dataset, load_selection, save_selection
from .editing import AddPhoneError, save_phone, update_phone
from .report import render_html
from .validate import find_issues

MAX_BODY = 1_000_000  # 1 MB is plenty for a form


class App:
    def __init__(self, data_dir: Path, out_dir: Path, base: str | None = None):
        self.data_dir = Path(data_dir)
        self.out_dir = Path(out_dir)
        self.base = base
        self.lock = threading.Lock()  # one write at a time

    def page(self) -> str:
        ds = load_dataset(self.data_dir)
        sel = load_selection(self.data_dir)
        issues = find_issues(apply_selection(ds, sel))
        base = self.base if self.base in ds.names else next(
            (n for n in ds.names if n not in sel["phones_off"]), ds.names[0])
        return render_html(ds, base, issues, selection=sel, server_mode=True)

    def add(self, body: dict) -> dict:
        with self.lock:
            messages = save_phone(self.data_dir, body.get("values", {}), body.get("ranks", {}))
        return {"ok": True, "messages": messages}

    def update(self, body: dict) -> dict:
        with self.lock:
            messages = update_phone(self.data_dir, body.get("original", ""), body.get("values", {}), body.get("ranks", {}))
        return {"ok": True, "messages": messages}

    def save_selection(self, body: dict) -> dict:
        with self.lock:
            path = save_selection(self.data_dir, body)
        return {"ok": True, "path": str(path)}


def make_handler(app: App):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):  # keep the console quiet, except errors
            if args and str(args[1]).startswith(("4", "5")):
                super().log_message(fmt, *args)

        def _send(self, status: int, body: bytes, ctype: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, status: int, obj: dict) -> None:
            self._send(status, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

        def do_GET(self):
            path = self.path.split("?")[0].split("#")[0]
            if path in ("/", "/index.html", "/report.html"):
                try:
                    html = app.page()
                except (DataFileError, FileNotFoundError) as e:
                    html = f"<h1>Problem in the data</h1><p>{e}</p><p>Fix the file and refresh this page.</p>"
                    return self._send(500, html.encode("utf-8"), "text/html; charset=utf-8")
                return self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")
            if path == "/favicon.ico":
                return self._send(204, b"", "image/x-icon")
            self._send(404, b"Not found", "text/plain")

        def do_POST(self):
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY:
                return self._json(413, {"ok": False, "error": "Request too large."})
            try:
                body = json.loads(self.rfile.read(length) or b"{}")
            except json.JSONDecodeError:
                return self._json(400, {"ok": False, "error": "Bad request."})
            routes = {"/api/phones": app.add, "/api/phones/update": app.update, "/api/selection": app.save_selection}
            handler = routes.get(self.path.split("?")[0])
            if handler is None:
                return self._json(404, {"ok": False, "error": "Unknown action."})
            try:
                self._json(200, handler(body))
            except AddPhoneError as e:
                self._json(400, {"ok": False, "error": str(e)})
            except (DataFileError, OSError) as e:
                self._json(500, {"ok": False, "error": f"Could not write the file: {e}. "
                                                       "Is it open in Excel? Close it and try again."})

    return Handler


def serve(data_dir: Path, out_dir: Path, base: str | None = None, port: int = 8765, open_browser: bool = True) -> int:
    app = App(data_dir, out_dir, base)
    app.page()  # fail early (and clearly) if the data can't be read
    server = None
    for p in range(port, port + 20):  # if the port is busy, try the next ones
        try:
            server = ThreadingHTTPServer(("127.0.0.1", p), make_handler(app))
            break
        except OSError:
            continue
    if server is None:
        print(f"Could not find a free port between {port} and {port + 19}.")
        return 2
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    print(f"\nPhone comparison app running at {url}")
    print(f"Data: {Path(data_dir).resolve()}")
    print("Keep this window open while you use it. Press Ctrl+C (or close the window) to stop.\n")
    if open_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()
    return 0

