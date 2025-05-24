"""Utilities for dispatching mouse events to a window."""

from __future__ import annotations

import Quartz

__all__ = ["click_at", "scroll"]


def _window_origin(window_info: dict) -> tuple[int, int]:
    """Return the global origin (x, y) of ``window_info``."""
    bounds = window_info.get("kCGWindowBounds", {})
    return int(bounds.get("X", 0)), int(bounds.get("Y", 0))


def click_at(window_info: dict, x: int, y: int) -> None:
    """Post a left mouse click at ``(x, y)`` relative to ``window_info``."""
    origin_x, origin_y = _window_origin(window_info)
    abs_x = origin_x + x
    abs_y = origin_y + y

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
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, down)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, up)


def scroll(window_info: dict, delta_x: int, delta_y: int) -> None:
    """Post a scroll event relative to ``window_info``."""
    # ``window_info`` is unused but kept for symmetry and future use
    event = Quartz.CGEventCreateScrollWheelEvent(
        None,
        Quartz.kCGScrollEventUnitPixel,
        2,
        int(delta_y),
        int(delta_x),
    )
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, event)

