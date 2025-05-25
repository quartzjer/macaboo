from __future__ import annotations

import Quartz
from Cocoa import NSWorkspace

import time

__all__ = ["click_at", "scroll"]

def click_at(window_info: dict, x: int, y: int) -> None:
    """Post a left mouse click at ``(x, y)`` to ``window_info``'s process."""
    pid = int(window_info.get("kCGWindowOwnerPID", 0))
    
    # Activate the target application first
    workspace = NSWorkspace.sharedWorkspace()
    running_apps = workspace.runningApplications()
    target_app = None
    
    for app in running_apps:
        if app.processIdentifier() == pid:
            target_app = app
            break
    
    if target_app:
        # Bring app to foreground
        target_app.activateWithOptions_(0)  # NSApplicationActivateIgnoringOtherApps = 0
        print(f"Activated app: {target_app.localizedName()}")
        
        # Small delay to ensure activation
        time.sleep(0.1)
    
    # Get window bounds and add incoming coordinates
    bounds = window_info.get("kCGWindowBounds", {})
    window_x = int(bounds.get("X", 0))
    window_y = int(bounds.get("Y", 0))
    
    # Incoming x/y are relative to window's top-left, so just add them
    abs_x = window_x + x
    abs_y = window_y + y

    point = Quartz.CGPoint(abs_x, abs_y)

    move  = Quartz.CGEventCreateMouseEvent(None,
                                           Quartz.kCGEventMouseMoved,
                                           point,
                                           Quartz.kCGMouseButtonLeft)
    down  = Quartz.CGEventCreateMouseEvent(None,
                                           Quartz.kCGEventLeftMouseDown,
                                           point,
                                           Quartz.kCGMouseButtonLeft)
    up    = Quartz.CGEventCreateMouseEvent(None,
                                           Quartz.kCGEventLeftMouseUp,
                                           point,
                                           Quartz.kCGMouseButtonLeft)

    Quartz.CGEventPost(Quartz.kCGHIDEventTap, move)
    time.sleep(0.01)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, down)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, up)
    
    print(f"Incoming ({x}, {y}) window ({window_x}, {window_y}) -> screen ({abs_x}, {abs_y}) in {window_info.get('kCGWindowName', 'Unknown')}")


def scroll(window_info: dict, delta_x: int, delta_y: int) -> None:
    """Post a scroll event to ``window_info``'s process."""
    # ``window_info`` is unused but kept for symmetry and future use
    event = Quartz.CGEventCreateScrollWheelEvent(
        None,
        Quartz.kCGScrollEventUnitPixel,
        2,
        int(delta_y),
        int(delta_x),
    )
    pid = int(window_info.get("kCGWindowOwnerPID", 0))
    Quartz.CGEventPostToPid(pid, event)
    print(f"Scrolled by ({delta_x}, {delta_y}) in window {window_info.get('kCGWindowName', 'Unknown')}")

