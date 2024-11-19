"""backoffkit — small, dependency-free retry and backoff helpers.

Quick start::

    from backoffkit import retry, ExponentialBackoff

    @retry(max_attempts=5, strategy=ExponentialBackoff(base=0.2))
    def fetch(url: str) -> bytes:
        ...
"""

from __future__ import annotations

from .async_retry import async_retry, async_retry_call
from .retry import RetryError, RetryPolicy, RetryState, retry, retry_call
from .strategy import (
    EqualJitter,
    ExponentialBackoff,
    FixedDelay,
    Jittered,
    Strategy,
)

__version__ = "0.3.0"

__all__ = [
    "EqualJitter",
    "ExponentialBackoff",
    "FixedDelay",
    "Jittered",
    "RetryError",
    "RetryPolicy",
    "RetryState",
    "Strategy",
    "__version__",
    "async_retry",
    "async_retry_call",
    "retry",
    "retry_call",
]
