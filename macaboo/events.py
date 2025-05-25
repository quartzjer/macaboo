from __future__ import annotations

import Quartz
from Cocoa import NSWorkspace

import time

__all__ = ["click_at", "scroll"]

def click_at(window_info: dict, x: int, y: int, display_width: int, display_height: int) -> None:
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
    
    # Get window bounds
    bounds = window_info.get("kCGWindowBounds", {})
    window_x = int(bounds.get("X", 0))
    window_y = int(bounds.get("Y", 0))
    window_width = int(bounds.get("Width", 0))
    window_height = int(bounds.get("Height", 0))
    
    # Scale coordinates from display dimensions to actual window dimensions
    if display_width > 0 and display_height > 0:
        scaled_x = int(x * window_width / display_width)
        scaled_y = int(y * window_height / display_height)
    else:
        # Fallback to original coordinates if display dimensions are invalid
        scaled_x = x
        scaled_y = y
        print("Warning: Invalid display dimensions, using original coordinates.")
    
    # Add window position to get absolute screen coordinates
    abs_x = window_x + scaled_x
    abs_y = window_y + scaled_y

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
    
    print(f"Display ({x}, {y}) in {display_width}x{display_height} -> window ({scaled_x}, {scaled_y}) in {window_width}x{window_height} -> screen ({abs_x}, {abs_y}) in {window_info.get('kCGWindowName', 'Unknown')}")


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
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, event)
    print(f"Scrolled by ({delta_x}, {delta_y}) in window {window_info.get('kCGWindowName', 'Unknown')}")

