"""Logging configuration for fibermorph package."""

import logging
import sys
from typing import Optional


def setup_logging(level: int = logging.INFO, log_file: Optional[str] = None) -> None:
    """Configure logging for the fibermorph package.

    Parameters
    ----------
    level : int
        Logging level (e.g., logging.INFO, logging.DEBUG).
    log_file : str, optional
        Path to log file. If None, logs only to console.
    """
    handlers = [logging.StreamHandler(sys.stdout)]
    
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module.

    Parameters
    ----------
    name : str
        Name of the module (typically __name__).

    Returns
    -------
    logging.Logger
        Configured logger instance.
    """
    return logging.getLogger(name)
