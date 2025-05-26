from __future__ import annotations

import time

import Quartz
from Cocoa import NSWorkspace, NSPasteboard, NSStringPboardType

from .logger import log_error, log_info, log_debug

__all__ = ["click_at", "move_pointer", "scroll", "key_press", "bring_app_to_foreground", "paste_text"]

# JS KeyboardEvent.code -> macOS CGKeyCode mapping
CODE_TO_MAC = {
    "ArrowLeft": 123,
    "ArrowUp":   126,
    "ArrowRight":124,
    "ArrowDown": 125,
    "Backspace": 51,
    "Tab":       48,
    "Enter":     36,
    "Escape":    53,
    "Space":     49,
    "ShiftLeft": 56,   
    "ShiftRight": 60,
    # Numbers
    "Digit0": 29, "Digit1": 18, "Digit2": 19, "Digit3": 20, "Digit4": 21,
    "Digit5": 23, "Digit6": 22, "Digit7": 26, "Digit8": 28, "Digit9": 25,
    # Letters
    "KeyA": 0,  "KeyB": 11, "KeyC": 8,  "KeyD": 2,  "KeyE": 14,
    "KeyF": 3,  "KeyG": 5,  "KeyH": 4,  "KeyI": 34, "KeyJ": 38,
    "KeyK": 40, "KeyL": 37, "KeyM": 46, "KeyN": 45, "KeyO": 31,
    "KeyP": 35, "KeyQ": 12, "KeyR": 15, "KeyS": 1,  "KeyT": 17,
    "KeyU": 32, "KeyV": 9,  "KeyW": 13, "KeyX": 7,  "KeyY": 16, "KeyZ": 6,
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
        log_info(f"Activated app: {target_app.localizedName()}")
        
        # Small delay to ensure activation
        time.sleep(0.1)
    else:
        log_error(f"Could not find app with PID {pid} to bring to foreground")

def move_pointer(window_info: dict, x: int, y: int, display_width: int, display_height: int) -> Quartz.CGPoint:
    """Move the mouse pointer to the specified coordinates in the window."""
    
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
        log_error("Invalid display dimensions, using original coordinates.")
    
    # Add window position to get absolute screen coordinates
    abs_x = window_x + scaled_x
    abs_y = window_y + scaled_y

    point = Quartz.CGPoint(abs_x, abs_y)

    move = Quartz.CGEventCreateMouseEvent(None,
                                          Quartz.kCGEventMouseMoved,
                                          point,
                                          Quartz.kCGMouseButtonLeft)
    
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, move)
    
    window_name = window_info.get('kCGWindowName', 'Unknown')
    log_info(f"Move pointer: display ({x}, {y}) in {display_width}x{display_height} -> window ({scaled_x}, {scaled_y}) in {window_width}x{window_height} -> screen ({abs_x}, {abs_y}) in {window_name}")
    
    return point


def click_at(window_info: dict, point: Quartz.CGPoint, button: str = "left") -> None:
    """Post a mouse click at the specified point.
    
    Args:
        window_info: Window information dictionary
        point: Point to click at
        button: Mouse button to click ("left" or "right")
    """
    
    if button == "right":
        down_event = Quartz.kCGEventRightMouseDown
        up_event = Quartz.kCGEventRightMouseUp
        button_type = Quartz.kCGMouseButtonRight
        button_name = "right"
    else:
        down_event = Quartz.kCGEventLeftMouseDown
        up_event = Quartz.kCGEventLeftMouseUp
        button_type = Quartz.kCGMouseButtonLeft
        button_name = "left"
    
    down = Quartz.CGEventCreateMouseEvent(None,
                                          down_event,
                                          point,
                                          button_type)
    up = Quartz.CGEventCreateMouseEvent(None,
                                        up_event,
                                        point,
                                        button_type)

    Quartz.CGEventPost(Quartz.kCGHIDEventTap, down)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, up)
    
    window_name = window_info.get('kCGWindowName', 'Unknown')
    log_info(f"{button_name.capitalize()} click at ({point.x}, {point.y}) in {window_name}")


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
    window_name = window_info.get('kCGWindowName', 'Unknown')
    log_info(f"Scroll: delta ({delta_x}, {delta_y}) in window {window_name}")


def _unicode_event(char: str, key_down: bool, flags: int = 0):
    """Create a unicode keyboard event for a printable character."""
    ev = Quartz.CGEventCreateKeyboardEvent(None, 0, key_down)          # vKey 0
    Quartz.CGEventKeyboardSetUnicodeString(ev, len(char), char)        # embed char
    Quartz.CGEventSetFlags(ev, flags)
    return ev


def key_press(window_info: dict, data: dict) -> None:
    """
    Post a key press described by the original JS `KeyboardEvent`.
    `data` should expose at least: key, code, shiftKey, ctrlKey, altKey, metaKey.
    """
    # Build modifier mask ----------------------------------------------------
    mods = 0
    if data.get("shiftKey"): mods |= Quartz.kCGEventFlagMaskShift
    if data.get("ctrlKey"):  mods |= Quartz.kCGEventFlagMaskControl
    if data.get("altKey"):   mods |= Quartz.kCGEventFlagMaskAlternate
    if data.get("metaKey"):  mods |= Quartz.kCGEventFlagMaskCommand

    # Fast path: printable character ----------------------------------------
    char = data.get("key", "")
    if len(char) == 1 and ord(char) >= 0x20:
        down = _unicode_event(char, True,  mods)
        up   = _unicode_event(char, False, mods)
    else:
        # Fallback: physical key mapping ------------------------------------
        mac_code = CODE_TO_MAC.get(data.get("code"))
        if mac_code is None:
            log_error(f"Unmapped JS code {data.get('code')}")
            return
        down = Quartz.CGEventCreateKeyboardEvent(None, mac_code, True)
        up   = Quartz.CGEventCreateKeyboardEvent(None, mac_code, False)
        Quartz.CGEventSetFlags(down, mods)
        Quartz.CGEventSetFlags(up,   mods)
    
    # Post the events
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, down)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, up)
    
    window_name = window_info.get('kCGWindowName', 'Unknown')
    log_info(f"Key press: {data.get('key', 'unknown')} (code: {data.get('code', 'unknown')}) in window {window_name}")

def paste_text(window_info: dict, text: str) -> None:
    """Send text to the application using pasteboard and paste command."""
    if not text:
        return
    
    # Save current pasteboard contents
    pasteboard = NSPasteboard.generalPasteboard()
    old_contents = pasteboard.stringForType_(NSStringPboardType)
    
    # Set new text to pasteboard
    pasteboard.clearContents()
    pasteboard.setString_forType_(text, NSStringPboardType)
    
    # Send Cmd+V (paste)
    cmd_down = Quartz.CGEventCreateKeyboardEvent(None, 55, True)   # Cmd key down
    v_down = Quartz.CGEventCreateKeyboardEvent(None, 9, True)     # V key down  
    v_up = Quartz.CGEventCreateKeyboardEvent(None, 9, False)      # V key up
    cmd_up = Quartz.CGEventCreateKeyboardEvent(None, 55, False)   # Cmd key up
    
    # Set Cmd modifier for V key events
    Quartz.CGEventSetFlags(v_down, Quartz.kCGEventFlagMaskCommand)
    Quartz.CGEventSetFlags(v_up, Quartz.kCGEventFlagMaskCommand)
    
    # Post the key sequence
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, cmd_down)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, v_down)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, v_up)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, cmd_up)
    
    # Restore original pasteboard contents after a short delay
    time.sleep(0.1)
    if old_contents:
        pasteboard.clearContents()
        pasteboard.setString_forType_(old_contents, NSStringPboardType)
    
    window_name = window_info.get('kCGWindowName', 'Unknown')
    log_info(f"Pasted text: '{text}' in window {window_name}")

