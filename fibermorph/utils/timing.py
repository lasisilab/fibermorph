"""Timing utility functions for fibermorph package."""

from functools import wraps
from timeit import default_timer as timer
from typing import Callable
import logging

logger = logging.getLogger(__name__)


def convert(seconds: float) -> str:
    """Converts seconds into readable format (hours, mins, seconds).

    Parameters
    ----------
    seconds : float or int
        Number of seconds to convert to final format.

    Returns
    -------
    str
        A string with the input seconds converted to a readable format.
    """
    min, sec = divmod(seconds, 60)
    hour, min = divmod(min, 60)
    return "%dh: %02dm: %02ds" % (hour, min, sec)


def timing(f: Callable) -> Callable:
    """Decorator to time function execution.

    Parameters
    ----------
    f : Callable
        Function to be timed.

    Returns
    -------
    Callable
        Wrapped function with timing.
    """
    @wraps(f)
    def wrap(*args, **kw):
        logger.info(f"The {f.__name__} function is currently running...")
        ts = timer()
        result = f(*args, **kw)
        te = timer()
        total_time = convert(te - ts)
        logger.info(
            f"The function: {f.__name__} with args:[{args}, {kw}] "
            f"and result: {result} Total time: {total_time}"
        )
        return result

    return wrap
