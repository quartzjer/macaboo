"""Utilities for dispatching mouse events to a window."""

from __future__ import annotations

import Quartz

__all__ = ["click_at", "scroll"]


def _window_bounds(window_info: dict) -> tuple[int, int, int]:
    """Return the global origin ``(x, y)`` and height of ``window_info``."""
    bounds = window_info.get("kCGWindowBounds", {})
    origin_x = int(bounds.get("X", 0))
    origin_y = int(bounds.get("Y", 0))
    height = int(bounds.get("Height", 0))
    return origin_x, origin_y, height


def click_at(window_info: dict, x: int, y: int) -> None:
    """Post a left mouse click at ``(x, y)`` to ``window_info``'s process."""
    origin_x, origin_y, height = _window_bounds(window_info)
    abs_x = origin_x + x
    # ``CGEventCreateMouseEvent`` expects global coordinates with the origin at
    # the bottom-left of the main display.  The screenshot shown in the browser
    # has ``y`` measured from the top of the window, so we need to flip it.
    abs_y = origin_y + (height - y)

    point = Quartz.CGPoint(abs_x, abs_y)
    down = Quartz.CGEventCreateMouseEvent(
        None,
        Quartz.kCGEventLeftMouseDown,
        point,
        Quartz.kCGMouseButtonLeft,
    )
    up = Quartz.CGEventCreateMouseEvent(
        None,
        Quartz.kCGEventLeftMouseUp,
        point,
        Quartz.kCGMouseButtonLeft,
    )
    pid = int(window_info.get("kCGWindowOwnerPID", 0))
    Quartz.CGEventPostToPid(pid, down)
    Quartz.CGEventPostToPid(pid, up)
    print(f"Clicked at ({abs_x}, {abs_y}) in window {window_info.get('kCGWindowName', 'Unknown')}")


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

