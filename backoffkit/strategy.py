"""Delay strategies.

A strategy answers one question: given that ``attempt`` attempts have already
failed, how many seconds should pass before the next one?  Every strategy
implements the :class:`Strategy` protocol, so they can be wrapped and combined
freely.

All delays are expressed in seconds and never negative.
"""

from __future__ import annotations

import random
from typing import Optional, Protocol, runtime_checkable

__all__ = [
    "Strategy",
    "FixedDelay",
    "ExponentialBackoff",
    "Jittered",
    "EqualJitter",
]


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


class ExponentialBackoff:
    """Multiply the delay by ``factor`` after every failed attempt.

    The delay for attempt *n* is ``base * factor ** (n - 1)``, optionally
    capped at ``max_delay``.  ``base=0`` produces an immediate first retry,
    which is useful together with jitter.
    """

    __slots__ = ("base", "factor", "max_delay")

    def __init__(
        self,
        base: float = 0.5,
        factor: float = 2.0,
        max_delay: Optional[float] = None,
    ) -> None:
        if base < 0:
            raise ValueError(f"base must be >= 0, got {base!r}")
        if factor < 1:
            raise ValueError(f"factor must be >= 1, got {factor!r}")
        if max_delay is not None and max_delay < 0:
            raise ValueError(f"max_delay must be >= 0, got {max_delay!r}")
        self.base = float(base)
        self.factor = float(factor)
        self.max_delay = None if max_delay is None else float(max_delay)

    def delay(self, attempt: int) -> float:
        _check_attempt(attempt)
        value = self.base * self.factor ** (attempt - 1)
        if self.max_delay is not None:
            value = min(value, self.max_delay)
        return value

    def __repr__(self) -> str:
        return (
            f"ExponentialBackoff(base={self.base!r}, factor={self.factor!r}, "
            f"max_delay={self.max_delay!r})"
        )


class Jittered:
    """Full jitter: pick a delay uniformly from ``[0, ceiling]``.

    Retrying on a fixed schedule makes clients that failed together retry
    together.  Sampling the whole interval spreads them out again.
    """

    __slots__ = ("strategy", "_random")

    def __init__(
        self,
        strategy: Strategy,
        rng: Optional[random.Random] = None,
    ) -> None:
        self.strategy = strategy
        self._random = rng if rng is not None else random.Random()

    def delay(self, attempt: int) -> float:
        ceiling = self.strategy.delay(attempt)
        if ceiling <= 0:
            return 0.0
        return self._random.uniform(0.0, ceiling)