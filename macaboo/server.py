from __future__ import annotations

"""Async HTTP server to display screenshots."""

import asyncio
from pathlib import Path

from aiohttp import web

from .screenshot import capture_window_bytes

__all__ = ["serve_window"]

TEMPLATE_PATH = Path(__file__).parent / "templates" / "index.html"


def serve_window(window_info: dict, port: int = 6222) -> None:
    """Start a blocking HTTP server showing screenshots of ``window_info``."""

    async def index(_: web.Request) -> web.Response:
        html = TEMPLATE_PATH.read_text()
        return web.Response(text=html, content_type="text/html")

    async def screenshot(_: web.Request) -> web.Response:
        data = capture_window_bytes(window_info)
        headers = {"Cache-Control": "no-cache, no-store, must-revalidate"}
        return web.Response(body=data, content_type="image/png", headers=headers)

    app = web.Application()
    app.router.add_get("/", index)
    app.router.add_get("/screenshot.png", screenshot)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    runner = web.AppRunner(app)
    loop.run_until_complete(runner.setup())
    site = web.TCPSite(runner, "0.0.0.0", port)
    loop.run_until_complete(site.start())
    print(f"Serving on http://localhost:{port}")
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(runner.cleanup())
        loop.close()
