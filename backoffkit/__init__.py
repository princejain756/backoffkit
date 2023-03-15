"""backoffkit — small, dependency-free retry and backoff helpers."""

from __future__ import annotations

from .strategy import ExponentialBackoff, FixedDelay, Strategy

__version__ = "0.1.0"

__all__ = [
    "ExponentialBackoff",
    "FixedDelay",
    "Strategy",
    "__version__",
]
