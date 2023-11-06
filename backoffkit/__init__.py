"""backoffkit — small, dependency-free retry and backoff helpers.

Quick start::

    from backoffkit import retry, ExponentialBackoff

    @retry(max_attempts=5, strategy=ExponentialBackoff(base=0.2))
    def fetch(url: str) -> bytes:
        ...
"""

from __future__ import annotations

from .retry import RetryError, retry
from .strategy import (
    EqualJitter,
    ExponentialBackoff,
    FixedDelay,
    Jittered,
    Strategy,
)

__version__ = "0.2.0"

__all__ = [
    "EqualJitter",
    "ExponentialBackoff",
    "FixedDelay",
    "Jittered",
    "RetryError",
    "Strategy",
    "__version__",
    "retry",
]
