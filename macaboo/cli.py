"""Command line interface for macaboo."""

from __future__ import annotations

import argparse

from .screenshot import (
    list_running_apps,
    choose_app,
    get_first_window_of_app,
    capture_window,
)
from .server import serve_window


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Capture a screenshot of a running application window and serve it on the web."
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Output PNG file (default: '<AppName>.png')",
    )
    parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=6222,
        help="Port to serve the web page on (default: 6222)",
    )
    args = parser.parse_args(argv)

    apps = list_running_apps()
    if not apps:
        print("No regular applications found.")
        return 1
    chosen_app = choose_app(apps)
    pid = chosen_app.processIdentifier()
    print(f"Selected app: {chosen_app.localizedName()} (PID: {pid})")
    window_info = get_first_window_of_app(pid)
    if not window_info:
        print(f"No on-screen window found for {chosen_app.localizedName()}.")
        return 1

    if args.output is not None:
        output_path = args.output
        capture_window(window_info, output_path)
        print(f"Screenshot saved to {output_path}")

    print("Starting web server. Press Ctrl+C to stop.")
    serve_window(window_info, args.port)
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
