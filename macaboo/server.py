from __future__ import annotations

"""HTTP server utilities for displaying screenshots."""

from pathlib import Path
from time import time
from typing import Optional
import ssl
from aiohttp import web

from .screenshot import capture_window

__all__ = ["make_server", "serve_window"]

# Path to the HTML template used for the index page
HTML_TEMPLATE = Path(__file__).with_name("templates").joinpath("index.html")


def make_server(
    window_info: dict,
    *,
    tls: bool = False,
    certfile: Optional[str] = None,
    keyfile: Optional[str] = None,
) -> web.Application:
    """Create an aiohttp application serving screenshots of ``window_info``."""

    screenshot_path = Path("latest.png")

    async def screenshot(_: web.Request) -> web.Response:
        capture_window(window_info, str(screenshot_path))
        try:
            data = screenshot_path.read_bytes()
        except FileNotFoundError:
            raise web.HTTPNotFound()
        return web.Response(body=data, content_type="image/png")

    async def index(_: web.Request) -> web.Response:
        ts = int(time())
        html = HTML_TEMPLATE.read_text().replace("{{ts}}", str(ts))
        return web.Response(text=html, content_type="text/html")

    app = web.Application()
    app.router.add_get("/", index)
    app.router.add_get("/screenshot.png", screenshot)
    if tls:
        if certfile is None:
            raise ValueError("certfile is required when tls is True")
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certfile, keyfile)
        app["ssl_context"] = context
    return app


def serve_window(
    window_info: dict,
    port: int = 6222,
    *,
    tls: bool = False,
    certfile: Optional[str] = None,
    keyfile: Optional[str] = None,
) -> None:
    """Start a blocking HTTP server showing screenshots of ``window_info``."""

    app = make_server(
        window_info,
        tls=tls,
        certfile=certfile,
        keyfile=keyfile,
    )
    ssl_context = app.get("ssl_context")
    scheme = "https" if tls else "http"
    print(f"Serving on {scheme}://localhost:{port}")
    web.run_app(app, host="0.0.0.0", port=port, ssl_context=ssl_context)
