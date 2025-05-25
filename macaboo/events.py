from __future__ import annotations

import Quartz
from Cocoa import NSWorkspace

import time

__all__ = ["click_at", "scroll", "key_press", "bring_app_to_foreground"]

# JS keyCode -> macOS CGKeyCode  (US-QWERTY subset)
JS_TO_MAC = {
    8:   51,   # Backspace -> kVK_Delete
    9:   48,   # Tab
    13:  36,   # Enter/Return
    16:  56,   # Shift (left)
    17:  59,   # Control (left)
    18:  58,   # Option/Alt (left)
    27:  53,   # Escape
    32:  49,   # Space
    37:  123,  # Left Arrow
    38:  126,  # Up Arrow
    39:  124,  # Right Arrow
    40:  125,  # Down Arrow
    # alphanumerics
    **{c: k for (c, k) in zip(range(48, 58),   # '0'–'9'
                              (29, 18,19,20,21,23,22,26,28,25))},
    **{c: k for (c, k) in zip(range(65, 91),   # 'A'–'Z'
                              (0,11,8,2,14,3,5,4,34,38,
                               40,37,46,45,31,35,12,15,
                               1,17,32,9,16,7,6,13))}
}

def bring_app_to_foreground(window_info: dict) -> None:
    """Bring the application to the foreground."""
    pid = int(window_info.get("kCGWindowOwnerPID", 0))
    
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

def click_at(window_info: dict, x: int, y: int, display_width: int, display_height: int) -> None:
    """Post a left mouse click at ``(x, y)`` to ``window_info``'s process."""
    
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


def key_press(window_info: dict, key_code: int) -> None:
    """Post a key press event to ``window_info``'s process."""
    # Convert JS keyCode to macOS CGKeyCode
    mac_key_code = JS_TO_MAC.get(key_code)
    if mac_key_code is None:
        print(f"Warning: Unmapped key code {key_code}, attempting to use as-is")
        mac_key_code = key_code
    
    # Create key down and key up events
    key_down = Quartz.CGEventCreateKeyboardEvent(None, mac_key_code, True)
    key_up = Quartz.CGEventCreateKeyboardEvent(None, mac_key_code, False)
    
    # Post the events
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, key_down)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, key_up)
    
    print(f"Key press: JS code={key_code} -> macOS code={mac_key_code} in window {window_info.get('kCGWindowName', 'Unknown')}")

