"""Delay strategies.

A strategy answers one question: given that ``attempt`` attempts have already
failed, how many seconds should pass before the next one?  Every strategy
implements the :class:`Strategy` protocol, so they can be wrapped and combined
freely.

All delays are expressed in seconds and never negative.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

__all__ = ["Strategy", "FixedDelay"]


@runtime_checkable
class Strategy(Protocol):
    """Structural type for anything that can compute a delay."""

    def delay(self, attempt: int) -> float:
        """Return the delay in seconds to apply before the next attempt.

        ``attempt`` is one-based: ``1`` means a single attempt has already
        failed.
        """
        ...


def _check_attempt(attempt: int) -> None:
    if attempt < 1:
        raise ValueError(f"attempt must be >= 1, got {attempt}")


class FixedDelay:
    """Wait the same amount of time between every attempt."""

    __slots__ = ("seconds",)

    def __init__(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError(f"seconds must be >= 0, got {seconds!r}")
        self.seconds = float(seconds)

    def delay(self, attempt: int) -> float:
        _check_attempt(attempt)
        return self.seconds

    def __repr__(self) -> str:
        return f"FixedDelay(seconds={self.seconds!r})"
