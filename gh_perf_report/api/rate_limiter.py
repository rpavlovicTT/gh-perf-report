"""Rate limiter for GitHub API calls."""

import time
from typing import Optional

from ..config import DEFAULT_API_RATE_LIMIT


class RateLimiter:
    """Simple rate limiter for GitHub API calls."""

    def __init__(self, calls_per_second: float = DEFAULT_API_RATE_LIMIT):
        """
        Initialize rate limiter.

        Args:
            calls_per_second: Maximum number of API calls per second
        """
        self.min_interval = 1.0 / calls_per_second
        self.last_call_time: Optional[float] = None

    def wait_if_needed(self) -> None:
        """Wait if necessary to respect rate limit."""
        if self.last_call_time is None:
            self.last_call_time = time.time()
            return

        elapsed = time.time() - self.last_call_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)

        self.last_call_time = time.time()
