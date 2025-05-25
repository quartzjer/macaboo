from __future__ import annotations

"""Async HTTP server to display screenshots."""

import asyncio
from pathlib import Path

from aiohttp import web, WSMsgType
import json

from .events import click_at, scroll, key_press

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

    async def websocket_handler(request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                    event_type = data.get("type")
                    
                    if event_type == "click":
                        x = int(data.get("x", 0))
                        y = int(data.get("y", 0))
                        display_width = int(data.get("displayWidth", 0))
                        display_height = int(data.get("displayHeight", 0))
                        click_at(window_info, x, y, display_width, display_height)
                        await ws.send_str(json.dumps({"status": "ok", "type": "click"}))
                    
                    elif event_type == "scroll":
                        dx = int(data.get("dx", 0))
                        dy = int(data.get("dy", 0))
                        scroll(window_info, dx, dy)
                        await ws.send_str(json.dumps({"status": "ok", "type": "scroll"}))
                    
                    elif event_type == "key":
                        key_code = data.get("keyCode")
                        if key_code is not None:
                            key_press(window_info, int(key_code))
                            await ws.send_str(json.dumps({"status": "ok", "type": "key"}))
                        else:
                            await ws.send_str(json.dumps({"status": "error", "message": "No key code provided"}))
                        
                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    await ws.send_str(json.dumps({"status": "error", "message": str(e)}))
            elif msg.type == WSMsgType.ERROR:
                print(f'WebSocket error: {ws.exception()}')
        
        return ws

    app = web.Application()
    app.router.add_get("/", index)
    app.router.add_get("/screenshot.png", screenshot)
    app.router.add_get("/ws", websocket_handler)

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
