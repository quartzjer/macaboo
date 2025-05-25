from __future__ import annotations

"""Async HTTP server to display screenshots."""

import asyncio
import hashlib
import threading
import time
from pathlib import Path

from aiohttp import web, WSMsgType
import json
import cv2
import numpy as np

from .events import click_at, scroll, key_press, bring_app_to_foreground
from .screenshot import capture_window_bytes

__all__ = ["serve_window"]

TEMPLATE_PATH = Path(__file__).parent / "templates" / "index.html"

class ScreenshotMonitor:
    """Monitors screenshot changes and notifies WebSocket client."""
    
    def __init__(self, window_info: dict, change_threshold: float = 0.01, debug: bool = False):
        self.window_info = window_info
        self.change_threshold = change_threshold
        self.debug = debug
        self.previous_frame = None
        self.current_screenshot = None
        self.client_ws = None
        self.monitor_task = None
        
    def set_client(self, ws):
        """Set the WebSocket client to receive updates."""
        self.client_ws = ws
        
    def remove_client(self):
        """Remove the WebSocket client."""
        self.client_ws = None
        
    def _has_significant_change(self, frame1: np.ndarray, frame2: np.ndarray) -> bool:
        """Check if there's a significant change between two frames using OpenCV."""
        if frame1 is None or frame2 is None:
            return True
            
        if frame1.shape != frame2.shape:
            return True
            
        diff = cv2.absdiff(frame1, frame2)
        mean_diff = np.mean(diff)
        normalized_diff = mean_diff / 255.0
        
        has_change = normalized_diff > self.change_threshold
        
        if self.debug:
            print(f"Frame diff: {normalized_diff:.4f}, threshold: {self.change_threshold:.4f}, changed: {has_change}")
            
        return has_change
        
    def _bytes_to_frame(self, screenshot_bytes: bytes) -> np.ndarray:
        """Convert PNG bytes to OpenCV frame (numpy array)."""
        nparr = np.frombuffer(screenshot_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return frame
        
    async def _monitor_loop(self):
        """Async loop that checks for screenshot changes."""
        while True:
            try:
                screenshot_bytes = capture_window_bytes(self.window_info)
                current_frame = self._bytes_to_frame(screenshot_bytes)
                
                if self.previous_frame is None:
                    if self.debug:
                        print("First screenshot captured")
                elif self._has_significant_change(self.previous_frame, current_frame):
                    await self._notify_client()
                    if self.debug:
                        print("Screenshot change detected, notifying client")

                self.previous_frame = current_frame
                self.current_screenshot = screenshot_bytes
                    
            except Exception as e:
                print(f"Screenshot monitoring error: {e}")
                
            await asyncio.sleep(0.1)
            
    async def _notify_client(self):
        """Notify the connected WebSocket client of screenshot update."""
        if self.client_ws and not self.client_ws.closed:
            try:
                message = json.dumps({"type": "screenshot_update"})
                await self.client_ws.send_str(message)
            except Exception as e:
                print(f"Error sending to client: {e}")
                self.client_ws = None
                
    async def force_screenshot_update(self):
        """Force capture and send screenshot update to client."""
        try:
            screenshot_bytes = capture_window_bytes(self.window_info)
            current_frame = self._bytes_to_frame(screenshot_bytes)
            self.previous_frame = current_frame
            self.current_screenshot = screenshot_bytes
            await self._notify_client()
        except Exception as e:
            print(f"Error in force screenshot update: {e}")
            
    def start_monitoring(self):
        """Start the screenshot monitoring task."""
        if self.monitor_task is None:
            self.monitor_task = asyncio.create_task(self._monitor_loop())
            
    async def stop_monitoring(self):
        """Stop the screenshot monitoring task."""
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
            self.monitor_task = None
            
    def get_current_screenshot(self) -> bytes:
        """Get the current screenshot bytes."""
        return self.current_screenshot or capture_window_bytes(self.window_info)


def serve_window(window_info: dict, port: int = 6222, change_threshold: float = 0.01, debug: bool = False) -> None:
    """Start a blocking HTTP server showing screenshots of ``window_info``."""
    
    monitor = ScreenshotMonitor(window_info, change_threshold=change_threshold, debug=debug)

    async def index(_: web.Request) -> web.Response:
        html = TEMPLATE_PATH.read_text()
        return web.Response(text=html, content_type="text/html")

    async def screenshot(_: web.Request) -> web.Response:
        data = monitor.get_current_screenshot()
        headers = {"Cache-Control": "no-cache, no-store, must-revalidate"}
        return web.Response(body=data, content_type="image/png", headers=headers)

    async def websocket_handler(request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        monitor.set_client(ws)
        
        try:
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
                            await monitor.force_screenshot_update()
                            await ws.send_str(json.dumps({"status": "ok", "type": "click"}))
                        
                        elif event_type == "scroll":
                            dx = int(data.get("dx", 0))
                            dy = int(data.get("dy", 0))
                            scroll(window_info, dx, dy)
                            await monitor.force_screenshot_update()
                            await ws.send_str(json.dumps({"status": "ok", "type": "scroll"}))
                        
                        elif event_type == "key":
                            key_code = data.get("keyCode")
                            if key_code is not None:
                                key_press(window_info, int(key_code))
                                await monitor.force_screenshot_update()
                                await ws.send_str(json.dumps({"status": "ok", "type": "key"}))
                            else:
                                await ws.send_str(json.dumps({"status": "error", "message": "No key code provided"}))
                        
                        elif event_type == "focus":
                            bring_app_to_foreground(window_info)
                            await monitor.force_screenshot_update()
                            await ws.send_str(json.dumps({"status": "ok", "type": "focus"}))
                            
                    except (json.JSONDecodeError, KeyError, ValueError) as e:
                        await ws.send_str(json.dumps({"status": "error", "message": str(e)}))
                elif msg.type == WSMsgType.ERROR:
                    print(f'WebSocket error: {ws.exception()}')
        finally:
            monitor.remove_client()
        
        return ws
    
    async def startup_handler(app):
        """Start monitoring when the app starts."""
        monitor.start_monitoring()
        
    async def cleanup_handler(app):
        """Stop monitoring when the app shuts down."""
        await monitor.stop_monitoring()

    app = web.Application()
    app.router.add_get("/", index)
    app.router.add_get("/screenshot.png", screenshot)
    app.router.add_get("/ws", websocket_handler)
    
    app.on_startup.append(startup_handler)
    app.on_cleanup.append(cleanup_handler)

    print(f"Serving on http://localhost:{port}")
    web.run_app(app, host="0.0.0.0", port=port)
