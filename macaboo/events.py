from __future__ import annotations

import Quartz
from Cocoa import NSWorkspace

import time

__all__ = ["click_at", "scroll"]


def _window_origin(window_info: dict) -> tuple[int, int]:
    """Return the global origin (x, y) of ``window_info`` in screen coordinates."""
    bounds = window_info.get("kCGWindowBounds", {})
    x = int(bounds.get("X", 0))
    y = int(bounds.get("Y", 0))
    height = int(bounds.get("Height", 0))
    
    # Convert from macOS window coordinates (bottom-left origin) to 
    # screen coordinates (top-left origin) for CGEvent
    main_display = Quartz.CGMainDisplayID()
    screen_height = Quartz.CGDisplayPixelsHigh(main_display)
    
    # Window Y is from bottom-left, convert to top-left
    screen_y = screen_height - y - height
    
    return x, screen_y


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
    
    bounds = window_info["kCGWindowBounds"]
    origin_x = int(bounds["X"])                # bottom-left
    origin_y = int(bounds["Y"])
    height   = int(bounds["Height"])

    # Convert y from the webpage (top-left origin)
    y_bottom = height - y                  # <-- single, correct flip

    abs_x = origin_x + x
    abs_y = origin_y + y_bottom                # now in CG global space

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
    
    print(f"Clicked at window coords ({x}, {y}) -> screen ({abs_x}, {abs_y}) in {window_info.get('kCGWindowName', 'Unknown')}")


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

