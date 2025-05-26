"""Core functionality for listing applications and capturing windows."""

from __future__ import annotations

import sys
from typing import List, Optional

import Quartz
from Cocoa import NSWorkspace
from Foundation import NSMutableData
from AppKit import NSApplicationActivationPolicyRegular

__all__ = [
    "list_running_apps",
    "choose_app",
    "get_first_window_of_app",
    "capture_window_bytes",
    "capture_window_with_menus_bytes",
    "find_app_by_name",
]


def list_running_apps():
    """Return a list of regular GUI applications currently running."""
    apps = NSWorkspace.sharedWorkspace().runningApplications()
    regular_apps = [
        app
        for app in apps
        if app.localizedName()
        and app.activationPolicy() == NSApplicationActivationPolicyRegular
    ]
    regular_apps.sort(key=lambda app: app.localizedName())
    return regular_apps


def choose_app(apps):
    """Prompt the user to select an app from ``apps``."""
    print("Available Applications:")
    for i, app in enumerate(apps):
        print(f"{i}: {app.localizedName()} (PID: {app.processIdentifier()})")
    try:
        choice = int(input("Choose an application by index: "))
    except ValueError:
        print("Invalid input. Please enter a number.")
        sys.exit(1)
    if choice < 0 or choice >= len(apps):
        print("Invalid choice. Exiting.")
        sys.exit(1)
    return apps[choice]


def find_app_by_name(apps, app_name: str):
    """Find an app by name (case-insensitive). Returns the app if found, None otherwise."""
    app_name_lower = app_name.lower()
    for app in apps:
        if app.localizedName().lower() == app_name_lower:
            return app
    return None


def get_first_window_of_app(pid: int) -> Optional[dict]:
    """Return the first on-screen window for a given process id."""
    window_list = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionOnScreenOnly, Quartz.kCGNullWindowID
    )
    for window in window_list:
        if (
            window.get("kCGWindowOwnerPID") == pid
            and window.get("kCGWindowLayer") == 0
        ):
            return window
    return None

def capture_window_bytes(window: dict) -> bytes:
    """Capture ``window`` and return PNG bytes."""
    window_id = window.get("kCGWindowNumber")
    
    # Get window bounds
    bounds = window.get("kCGWindowBounds", {})
    x = bounds.get("X", 0)
    y = bounds.get("Y", 0)
    width = bounds.get("Width", 0)
    height = bounds.get("Height", 0)
    window_rect = Quartz.CGRectMake(x, y, width, height)
    
    image = Quartz.CGWindowListCreateImage(
        window_rect,
        Quartz.kCGWindowListOptionIncludingWindow,
        window_id,
        Quartz.kCGWindowImageDefault,
    )
    if image is None:
        print("Failed to capture image.")
        sys.exit(1)

    data = NSMutableData.alloc().init()
    dest = Quartz.CGImageDestinationCreateWithData(
        data, "public.png", 1, None
    )
    properties = {
        Quartz.kCGImagePropertyDPIWidth: 72,
        Quartz.kCGImagePropertyDPIHeight: 72,
    }
    Quartz.CGImageDestinationAddImage(dest, image, properties)
    if not Quartz.CGImageDestinationFinalize(dest):
        print("Failed to finalize image destination.")
        sys.exit(1)
    return bytes(data)


def list_windows_for_pid(pid: int) -> List[dict]:
    """Return all on-screen windows belonging to ``pid``."""
    window_list = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionOnScreenOnly,
        Quartz.kCGNullWindowID,
    )
    return [w for w in window_list if w.get("kCGWindowOwnerPID") == pid]


def _rect_contains(outer: dict, inner: dict) -> bool:
    """Check if ``inner`` bounds are fully inside ``outer`` bounds."""
    ob = outer.get("kCGWindowBounds", {})
    ib = inner.get("kCGWindowBounds", {})

    return (
        ib.get("X", 0) >= ob.get("X", 0)
        and ib.get("Y", 0) >= ob.get("Y", 0)
        and ib.get("X", 0) + ib.get("Width", 0)
        <= ob.get("X", 0) + ob.get("Width", 0)
        and ib.get("Y", 0) + ib.get("Height", 0)
        <= ob.get("Y", 0) + ob.get("Height", 0)
    )


def capture_window_with_menus_bytes(window: dict) -> bytes:
    """Capture ``window`` plus any of its child windows that fall within it."""
    pid = window.get("kCGWindowOwnerPID")
    menu_windows = [w for w in list_windows_for_pid(pid) if _rect_contains(window, w) and w != window]

    bounds = window.get("kCGWindowBounds", {})
    union_x = bounds.get("X", 0)
    union_y = bounds.get("Y", 0)
    union_w = bounds.get("Width", 0)
    union_h = bounds.get("Height", 0)

    window_ids = [window.get("kCGWindowNumber")]

    for w in menu_windows:
        window_ids.append(w.get("kCGWindowNumber"))
        b = w.get("kCGWindowBounds", {})
        x1 = min(union_x, b.get("X", 0))
        y1 = min(union_y, b.get("Y", 0))
        x2 = max(union_x + union_w, b.get("X", 0) + b.get("Width", 0))
        y2 = max(union_y + union_h, b.get("Y", 0) + b.get("Height", 0))
        union_x, union_y = x1, y1
        union_w, union_h = x2 - x1, y2 - y1

    rect = Quartz.CGRectMake(union_x, union_y, union_w, union_h)
    image = Quartz.CGWindowListCreateImageFromArray(
        rect,
        window_ids,
        Quartz.kCGWindowImageDefault,
    )
    if image is None:
        print("Failed to capture image.")
        sys.exit(1)

    data = NSMutableData.alloc().init()
    dest = Quartz.CGImageDestinationCreateWithData(
        data, "public.png", 1, None
    )
    properties = {
        Quartz.kCGImagePropertyDPIWidth: 72,
        Quartz.kCGImagePropertyDPIHeight: 72,
    }
    Quartz.CGImageDestinationAddImage(dest, image, properties)
    if not Quartz.CGImageDestinationFinalize(dest):
        print("Failed to finalize image destination.")
        sys.exit(1)
    return bytes(data)
