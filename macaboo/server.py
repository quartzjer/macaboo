from __future__ import annotations

"""Simple HTTP server to display screenshots."""

from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from time import time

from .screenshot import capture_window

__all__ = ["serve_window"]


def serve_window(window_info: dict, port: int = 6222) -> None:
    """Start a blocking HTTP server showing screenshots of ``window_info``."""

    screenshot_path = Path("latest.png")

    class ScreenshotHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: D401
            if self.path.startswith("/screenshot.png"):
                capture_window(window_info, str(screenshot_path))
                try:
                    data = screenshot_path.read_bytes()
                except FileNotFoundError:
                    self.send_error(404)
                    return
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.end_headers()
                self.wfile.write(data)
            else:
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.end_headers()
                ts = int(time())
                html = (
                    f"<html><body>"
                    f"<img src='/screenshot.png?{ts}' alt='screenshot'/>"
                    f"</body></html>"
                )
                self.wfile.write(html.encode("utf-8"))

    server = HTTPServer(("0.0.0.0", port), ScreenshotHandler)
    print(f"Serving on http://localhost:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
