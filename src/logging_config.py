# src/logging_config.py
"""Centralized logging configuration for the application."""

import logging
import os
from datetime import datetime
from pathlib import Path




def setup_logging(log_level: str = "INFO", log_file: str = None) -> None:
    """
    Setup application-wide logging configuration.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path. If None, uses default location.
    """
    # Get log directory from constants or use default
    try:
        from core.constants import DATA_DIR
        log_dir = DATA_DIR / "logs"
    except ImportError:
        log_dir = Path("data/logs")

    # Create log directory if it doesn't exist
    log_dir.mkdir(parents=True, exist_ok=True)

    # Set default log file if not provided
    if log_file is None:
        timestamp = datetime.now().strftime("%Y%m%d")
        log_file = log_dir / f"app_{timestamp}.log"

    # Ensure log_file is a Path object
    if isinstance(log_file, str):
        log_file = Path(log_file)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Clear existing handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    root_logger.addHandler(console_handler)

    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)  # Always log DEBUG to file
    file_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_format)
    root_logger.addHandler(file_handler)

    logging.info(f"Logging initialized: level={log_level}, file={log_file}")





def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the given name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)
