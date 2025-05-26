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
    """Capture the target window and any of its child windows (like menus, dialogs)."""
    bounds = window.get("kCGWindowBounds", {})
    x = bounds.get("X", 0)
    y = bounds.get("Y", 0)
    width = bounds.get("Width", 0)
    height = bounds.get("Height", 0)
    
    # Get the target window's PID
    target_pid = window.get("kCGWindowOwnerPID")
    
    # Get all on-screen windows
    all_windows_list = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionOnScreenOnly, Quartz.kCGNullWindowID
    )
    
    # Find all window IDs belonging to the same process that are on-screen
    # and have a layer (i.e., are actual visible windows, not off-screen buffers)
    same_process_window_ids = []
    for win_info in all_windows_list:
        if win_info.get("kCGWindowOwnerPID") == target_pid and \
           win_info.get("kCGWindowLayer", -1) >= 0:
            same_process_window_ids.append(win_info.get("kCGWindowNumber"))

    if not same_process_window_ids:
        target_window_id = window.get("kCGWindowNumber")
        if target_window_id:
            same_process_window_ids.append(target_window_id)
        else:
            print("Error: Target window ID not found.")
            sys.exit(1)

    # Define the capture rectangle based on the main window's bounds
    window_rect = Quartz.CGRectMake(x, y, width, height)
    
    # Capture the specified windows composited together within the given rectangle
    image = Quartz.CGWindowListCreateImageFromArray(
        window_rect,
        same_process_window_ids,
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
