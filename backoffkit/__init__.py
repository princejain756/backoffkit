"""backoffkit — small, dependency-free retry and backoff helpers."""

from __future__ import annotations

from .strategy import (
    EqualJitter,
    ExponentialBackoff,
    FixedDelay,
    Jittered,
    Strategy,
)

__version__ = "0.1.0"

__all__ = [
    "EqualJitter",
    "ExponentialBackoff",
    "FixedDelay",
    "Jittered",
    "Strategy",
    "__version__",
]
