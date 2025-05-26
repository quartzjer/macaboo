"""Logging configuration for macaboo."""

from __future__ import annotations

import logging
import sys
from typing import Optional

# Global logger instance
_logger: Optional[logging.Logger] = None
_verbose_mode = False

def setup_logging(verbose: bool = False) -> None:
    """Set up logging configuration."""
    global _logger, _verbose_mode
    _verbose_mode = verbose
    
    _logger = logging.getLogger("macaboo")
    _logger.setLevel(logging.DEBUG if verbose else logging.ERROR)
    
    # Remove any existing handlers
    for handler in _logger.handlers[:]:
        _logger.removeHandler(handler)
    
    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG if verbose else logging.ERROR)
    
    # Create formatter
    if verbose:
        formatter = logging.Formatter(
            fmt="[%(asctime)s] %(levelname)s: %(message)s",
            datefmt="%H:%M:%S"
        )
    else:
        formatter = logging.Formatter("ERROR: %(message)s")
    
    handler.setFormatter(formatter)
    _logger.addHandler(handler)
    
    # Prevent propagation to root logger
    _logger.propagate = False

def get_logger() -> logging.Logger:
    """Get the configured logger instance."""
    if _logger is None:
        setup_logging()
    return _logger

def is_verbose() -> bool:
    """Check if verbose mode is enabled."""
    return _verbose_mode

def log_error(message: str) -> None:
    """Log an error message (always shown)."""
    get_logger().error(message)

def log_info(message: str) -> None:
    """Log an info message (only in verbose mode)."""
    get_logger().info(message)

def log_debug(message: str) -> None:
    """Log a debug message (only in verbose mode)."""
    get_logger().debug(message)

def log_event(event_type: str, details: str = "") -> None:
    """Log an event (only in verbose mode)."""
    if details:
        get_logger().info(f"Event {event_type}: {details}")
    else:
        get_logger().info(f"Event: {event_type}")

def log_client(action: str, details: str = "") -> None:
    """Log client communication (only in verbose mode)."""
    if details:
        get_logger().info(f"Client {action}: {details}")
    else:
        get_logger().info(f"Client: {action}")
