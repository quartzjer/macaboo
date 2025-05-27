"""Core functionality for listing applications and capturing windows."""

from __future__ import annotations

import asyncio
import subprocess
from typing import List, Optional

from .logger import log_error

from contextlib import contextmanager

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
    "wake_display",
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


async def wake_display(duration: int = 2) -> None:
    """Wake the display using the ``caffeinate`` command line tool.

    The command is started asynchronously so that it doesn't block the
    event loop. Failures are ignored quietly.
    """
    try:
        await asyncio.create_subprocess_exec(
            "caffeinate", "-u", "-t", str(duration),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        # ``caffeinate`` may not be available or the call might fail.
        pass


def choose_app(apps):
    """Prompt the user to select an app from ``apps``."""
    print("Available Applications:")
    for i, app in enumerate(apps):
        print(f"{i}: {app.localizedName()} (PID: {app.processIdentifier()})")
    try:
        choice = int(input("Choose an application by index: "))
    except ValueError:
        log_error("Invalid input. Please enter a number.")
        return None
    if choice < 0 or choice >= len(apps):
        log_error("Invalid choice. Exiting.")
        return None
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


@contextmanager
def cg_image_resource(create_func, *args, **kwargs):
    """Context manager that releases a Core Graphics resource."""
    resource = create_func(*args, **kwargs)
    if resource is None:
        yield None
        return
    try:
        yield resource
    finally:
        Quartz.CFRelease(resource)


def capture_window_bytes(window: dict) -> Optional[bytes]:
    """Capture the target window and any of its child windows (like menus, dialogs)."""
    bounds = window.get("kCGWindowBounds", {})
    x = bounds.get("X", 0)
    y = bounds.get("Y", 0)
    width = bounds.get("Width", 0)
    height = bounds.get("Height", 0)

    target_pid = window.get("kCGWindowOwnerPID")

    all_windows_list = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionOnScreenOnly, Quartz.kCGNullWindowID
    )

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
            log_error("Error: Target window ID not found.")
            return None

    window_rect = Quartz.CGRectMake(x, y, width, height)

    with cg_image_resource(
        Quartz.CGWindowListCreateImageFromArray,
        window_rect,
        same_process_window_ids,
        Quartz.kCGWindowImageDefault,
    ) as image:
        if image is None:
            log_error("Failed to capture image.")
            return None

        data = NSMutableData.alloc().init()

        with cg_image_resource(
            Quartz.CGImageDestinationCreateWithData,
            data,
            "public.png",
            1,
            None,
        ) as dest:
            if dest is None:
                log_error("Failed to create image destination.")
                return None

            properties = {
                Quartz.kCGImagePropertyDPIWidth: 72,
                Quartz.kCGImagePropertyDPIHeight: 72,
            }
            Quartz.CGImageDestinationAddImage(dest, image, properties)
            if not Quartz.CGImageDestinationFinalize(dest):
                log_error("Failed to finalize image destination.")
                return None
            return bytes(data)
