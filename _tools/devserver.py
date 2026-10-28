#!/usr/bin/env python3
"""A local stand-in for GitHub Pages, used by the browser tests and review screenshots.

Serves the site folder like Pages does: folder/ -> folder/index.html, /folder -> redirect to
/folder/, unknown paths -> 404.html with status 404. Quiet (no request logging).

Preview by hand: python3 _tools/devserver.py 8000   then open http://localhost:8000/
(plain `python3 -m http.server 8000` works too; it just doesn't show the custom 404 page).
"""
import functools
import http.server
import os
import sys
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map,
                      ".avif": "image/avif", ".webp": "image/webp", ".mp4": "video/mp4",
                      ".js": "text/javascript", ".svg": "image/svg+xml"}

    def log_message(self, *args):
        pass

    def send_error(self, code, message=None, explain=None):
        if code == 404:
            body = open(os.path.join(ROOT, "404.html"), "rb").read()
            self.send_response(404)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)
            return
        super().send_error(code, message, explain)


class Server:
    """Context manager: with Server() as base_url: ..."""

    def __init__(self, port=0):
        handler = functools.partial(Handler, directory=ROOT)
        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    @property
    def url(self):
        return f"http://127.0.0.1:{self.httpd.server_address[1]}"

    def __enter__(self):
        self.thread.start()
        return self.url

    def __exit__(self, *exc):
        self.httpd.shutdown()
        self.httpd.server_close()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    srv = Server(port)
    print(f"Serving {ROOT} at http://localhost:{port}/  (Ctrl+C to stop)")
    try:
        srv.httpd.serve_forever()
    except KeyboardInterrupt:
        pass
