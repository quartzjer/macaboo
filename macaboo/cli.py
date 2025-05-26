"""Command line interface for macaboo."""

from __future__ import annotations

import argparse

from .logger import setup_logging, log_error, log_info
from .screenshot import (
    list_running_apps,
    choose_app,
    get_first_window_of_app,
    find_app_by_name,
)
from .server import serve_window


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Capture a screenshot of a running application window and serve it on the web."
    )
    parser.add_argument(
        "app_name",
        nargs="?",
        help="Name of the application to capture (case-insensitive). If not provided, shows a list to choose from.",
    )
    parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=6222,
        help="Port to serve the web page on (default: 6222)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging (shows all events and debugging info)",
    )
    args = parser.parse_args(argv)

    # Set up logging based on verbose flag
    setup_logging(verbose=args.verbose)

    apps = list_running_apps()
    if not apps:
        log_error("No regular applications found.")
        return 1
    
    if args.app_name:
        chosen_app = find_app_by_name(apps, args.app_name)
        if not chosen_app:
            log_error(f"No application found matching '{args.app_name}'.")
            print("Available applications:")
            for app in apps:
                print(f"  {app.localizedName()}")
            return 1
    else:
        chosen_app = choose_app(apps)
    pid = chosen_app.processIdentifier()
    log_info(f"Selected app: {chosen_app.localizedName()} (PID: {pid})")
    print(f"Selected app: {chosen_app.localizedName()} (PID: {pid})")
    window_info = get_first_window_of_app(pid)
    if not window_info:
        log_error(f"No on-screen window found for {chosen_app.localizedName()}.")
        return 1

    print("Starting web server. Press Ctrl+C to stop.")
    serve_window(window_info, args.port, verbose=args.verbose)
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
