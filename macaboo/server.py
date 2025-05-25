from __future__ import annotations

"""Async HTTP server to display screenshots."""

import asyncio
import hashlib
import threading
import time
from pathlib import Path
import queue

from aiohttp import web, WSMsgType
import json
import cv2
import numpy as np

from .events import click_at, scroll, key_press, bring_app_to_foreground

from .screenshot import capture_window_bytes

__all__ = ["serve_window"]

TEMPLATE_PATH = Path(__file__).parent / "templates" / "index.html"

class ScreenshotMonitor:
    """Monitors screenshot changes and notifies WebSocket clients."""
    
    def __init__(self, window_info: dict, change_threshold: float = 0.01, debug: bool = False):
        self.window_info = window_info
        self.change_threshold = change_threshold
        self.debug = debug
        self.previous_frame = None
        self.current_screenshot = None
        self.clients = set()
        self.running = False
        self.thread = None
        self.notification_queue = queue.Queue()
        self.event_loop = None
        
    def add_client(self, ws):
        """Add a WebSocket client to receive updates."""
        self.clients.add(ws)
        
    def remove_client(self, ws):
        """Remove a WebSocket client."""
        self.clients.discard(ws)
        
    def _has_significant_change(self, frame1: np.ndarray, frame2: np.ndarray) -> bool:
        """Check if there's a significant change between two frames using OpenCV."""
        if frame1 is None or frame2 is None:
            return True
            
        # Ensure frames have the same shape
        if frame1.shape != frame2.shape:
            return True
            
        # Calculate absolute difference
        diff = cv2.absdiff(frame1, frame2)
        mean_diff = np.mean(diff)
        normalized_diff = mean_diff / 255.0
        
        has_change = normalized_diff > self.change_threshold
        
        if self.debug:
            print(f"Frame diff: {normalized_diff:.4f}, threshold: {self.change_threshold:.4f}, changed: {has_change}")
            
        return has_change
        
    def _bytes_to_frame(self, screenshot_bytes: bytes) -> np.ndarray:
        """Convert PNG bytes to OpenCV frame (numpy array)."""
        # Decode PNG bytes to numpy array
        nparr = np.frombuffer(screenshot_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return frame
        
    def _monitor_loop(self):
        """Background thread loop that checks for screenshot changes."""
        while self.running:
            try:
                screenshot_bytes = capture_window_bytes(self.window_info)
                current_frame = self._bytes_to_frame(screenshot_bytes)
                
                if self.previous_frame is None:
                    if self.debug:
                        print("First screenshot captured")
                elif self._has_significant_change(self.previous_frame, current_frame):
                    self._notify_clients()
                    if self.debug:
                        print("Screenshot change detected, notifying clients")

                # always update the previous frame
                self.previous_frame = current_frame
                self.current_screenshot = screenshot_bytes
                    
            except Exception as e:
                print(f"Screenshot monitoring error: {e}")
                
            time.sleep(0.1)
            
    def _notify_clients(self):
        """Notify all connected WebSocket clients of screenshot update."""
        if not self.clients:
            return
            
        # Put notification in queue to be processed by the main event loop
        self.notification_queue.put("screenshot_update")
        
    def start(self, event_loop):
        """Start the screenshot monitoring thread."""
        if not self.running:
            self.running = True
            self.event_loop = event_loop
            self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.thread.start()
            
    def stop(self):
        """Stop the screenshot monitoring thread."""
        self.running = False
        if self.thread:
            self.thread.join()
            
    def get_current_screenshot(self) -> bytes:
        """Get the current screenshot bytes."""
        return self.current_screenshot or capture_window_bytes(self.window_info)
        
    async def process_notifications(self):
        """Process notifications from the queue and send to WebSocket clients."""
        try:
            # Non-blocking queue check
            while True:
                try:
                    notification = self.notification_queue.get_nowait()
                    if notification == "screenshot_update":
                        await self._send_to_all_clients({"type": "screenshot_update"})
                except queue.Empty:
                    break
        except Exception as e:
            print(f"Error processing notifications: {e}")
            
    async def _send_to_all_clients(self, message_data: dict):
        """Send a message to all connected WebSocket clients."""
        if not self.clients:
            return
            
        message = json.dumps(message_data)
        disconnected_clients = set()
        
        for ws in self.clients:
            try:
                if ws.closed:
                    disconnected_clients.add(ws)
                else:
                    await ws.send_str(message)
            except Exception as e:
                print(f"Error sending to client: {e}")
                disconnected_clients.add(ws)
                
        # Remove disconnected clients
        self.clients -= disconnected_clients


def serve_window(window_info: dict, port: int = 6222, change_threshold: float = 0.01, debug: bool = False) -> None:
    """Start a blocking HTTP server showing screenshots of ``window_info``."""
    
    # Create the screenshot monitor with configurable threshold and debug mode
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
        
        # Add this client to the monitor for screenshot updates
        monitor.add_client(ws)
        
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
                        
                        elif event_type == "focus":
                            bring_app_to_foreground(window_info)
                            await ws.send_str(json.dumps({"status": "ok", "type": "focus"}))
                            
                    except (json.JSONDecodeError, KeyError, ValueError) as e:
                        await ws.send_str(json.dumps({"status": "error", "message": str(e)}))
                elif msg.type == WSMsgType.ERROR:
                    print(f'WebSocket error: {ws.exception()}')
        finally:
            # Remove this client when connection closes
            monitor.remove_client(ws)
        
        return ws
    
    async def notification_processor():
        """Periodic task to process screenshot notifications."""
        while True:
            await monitor.process_notifications()
            await asyncio.sleep(0.05)  # 50ms interval

    app = web.Application()
    app.router.add_get("/", index)
    app.router.add_get("/screenshot.png", screenshot)
    app.router.add_get("/ws", websocket_handler)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Start the screenshot monitor with the event loop
    monitor.start(loop)
    
    # Create the notification processor task
    notification_task = loop.create_task(notification_processor())
    
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
        notification_task.cancel()
        monitor.stop()
        loop.run_until_complete(runner.cleanup())
        loop.close()
