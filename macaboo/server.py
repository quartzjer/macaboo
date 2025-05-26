from __future__ import annotations

"""Async HTTP server to display screenshots."""

import asyncio
import json
from pathlib import Path

import cv2
import numpy as np
from aiohttp import web, WSMsgType

from .events import click_at, move_pointer, scroll, key_press, bring_app_to_foreground, paste_text
from .logger import log_error, log_info, log_debug, log_event, log_client
from .screenshot import capture_window_bytes

__all__ = ["serve_window"]

TEMPLATE_PATH = Path(__file__).parent / "templates" / "index.html"

class ScreenshotMonitor:
    """Monitors screenshot changes and notifies WebSocket client."""
    
    def __init__(self, window_info: dict, change_threshold: float = 0.01, verbose: bool = False):
        self.window_info = window_info
        self.change_threshold = change_threshold
        self.verbose = verbose
        self.previous_frame = None
        self.cached_comparison_frame = None
        self.client_ws = None
        self.monitor_task = None
        
    def set_client(self, ws):
        """Set the WebSocket client to receive updates."""
        self.client_ws = ws
        log_client("connected", f"WebSocket client connected")
        
    def remove_client(self, ws):
        """Remove the WebSocket client."""
        if self.client_ws == ws:
            self.client_ws = None
            log_client("disconnected", f"WebSocket client disconnected")
        
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
        
        if self.verbose and has_change:
            log_debug(f"Frame diff: {normalized_diff:.4f}, threshold: {self.change_threshold:.4f}, changed: {has_change}")
            
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
                if self.cached_comparison_frame is not None:
                    screenshot_bytes = capture_window_bytes(self.window_info)
                    current_frame = self._bytes_to_frame(screenshot_bytes)
                    
                    if self._has_significant_change(self.cached_comparison_frame, current_frame):
                        await self._notify_client()
                        log_debug("Screenshot change detected, notifying client")
                    
            except Exception as e:
                log_error(f"Screenshot monitoring error: {e}")
                
            await asyncio.sleep(0.1)
            
    async def _notify_client(self):
        """Notify the connected WebSocket client of screenshot update."""
        if self.client_ws is not None:
            try:
                message = json.dumps({"type": "screenshot_update"})
                await self.client_ws.send_str(message)
                log_client("notified", "screenshot update sent")
            except Exception as e:
                log_error(f"Error sending to client: {e}")
                self.client_ws = None
        else:
            log_debug(f"No active WebSocket client to notify")
                
    def start_monitoring(self):
        """Start the screenshot monitoring task."""
        if self.monitor_task is None:
            self.monitor_task = asyncio.create_task(self._monitor_loop())
            log_info("Screenshot monitoring started")
            
    async def stop_monitoring(self):
        """Stop the screenshot monitoring task."""
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
            self.monitor_task = None
            log_info("Screenshot monitoring stopped")
            
    def get_current_screenshot(self) -> bytes:
        """Get the current screenshot bytes and cache them as served."""
        screenshot_bytes = capture_window_bytes(self.window_info)
        self.cached_comparison_frame = self._bytes_to_frame(screenshot_bytes)
        log_debug(f"Screenshot captured: {len(screenshot_bytes)} bytes")
        return screenshot_bytes


def serve_window(window_info: dict, port: int = 6222, change_threshold: float = 0.01, verbose: bool = False) -> None:
    """Start a blocking HTTP server showing screenshots of ``window_info``."""
    
    monitor = ScreenshotMonitor(window_info, change_threshold=change_threshold, verbose=verbose)

    async def index(_: web.Request) -> web.Response:
        html = TEMPLATE_PATH.read_text()
        log_client("request", "index page served")
        return web.Response(text=html, content_type="text/html")

    async def screenshot(_: web.Request) -> web.Response:
        data = monitor.get_current_screenshot()
        headers = {"Cache-Control": "no-cache, no-store, must-revalidate"}
        log_client("request", f"screenshot served ({len(data)} bytes)")
        return web.Response(body=data, content_type="image/png", headers=headers)

    async def websocket_handler(request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        monitor.set_client(ws)
        bring_app_to_foreground(window_info)
        
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
                            button = data.get("button", "left")  # Default to left click
                            log_event("click", f"{button} click at ({x}, {y}) in {display_width}x{display_height}")
                            point = move_pointer(window_info, x, y, display_width, display_height)
                            await asyncio.sleep(0.01)  # Small delay between move and click
                            click_at(window_info, point, button)
                            await ws.send_str(json.dumps({"status": "ok", "type": "click"}))
                        
                        elif event_type == "scroll":
                            dx = int(data.get("dx", 0))
                            dy = int(data.get("dy", 0))
                            log_event("scroll", f"delta ({dx}, {dy})")
                            scroll(window_info, dx, dy)
                            await ws.send_str(json.dumps({"status": "ok", "type": "scroll"}))
                        
                        elif event_type == "key":
                            key_press(window_info, data)
                            await ws.send_str(json.dumps({"status": "ok", "type": "key"}))
                        
                        elif event_type == "focus":
                            log_event("focus", "bringing app to foreground")
                            bring_app_to_foreground(window_info)
                            await ws.send_str(json.dumps({"status": "ok", "type": "focus"}))
                        
                        elif event_type == "paste":
                            text = data.get("text", "")
                            if text:
                                log_event("paste", f"text: '{text[:50]}{'...' if len(text) > 50 else ''}'")
                                paste_text(window_info, text)
                                await ws.send_str(json.dumps({"status": "ok", "type": "paste"}))
                            else:
                                log_error("No text provided in paste event")
                                await ws.send_str(json.dumps({"status": "error", "message": "No text provided"}))
                            
                    except (json.JSONDecodeError, KeyError, ValueError) as e:
                        log_error(f"WebSocket message parsing error: {e}")
                        await ws.send_str(json.dumps({"status": "error", "message": str(e)}))
                elif msg.type == WSMsgType.ERROR:
                    log_error(f'WebSocket error: {ws.exception()}')
        finally:
            monitor.remove_client(ws)
        
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

    log_info(f"Starting server on http://localhost:{port}")
    print(f"Serving on http://localhost:{port}")
    web.run_app(app, host="0.0.0.0", port=port)
