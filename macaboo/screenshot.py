"""Core functionality for listing applications and capturing windows."""

from __future__ import annotations

import sys
from typing import List, Optional

import Quartz
from Cocoa import NSURL, NSWorkspace
from Foundation import NSMutableData
from AppKit import NSApplicationActivationPolicyRegular

__all__ = [
    "list_running_apps",
    "choose_app",
    "get_first_window_of_app",
    "capture_window_bytes",
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
