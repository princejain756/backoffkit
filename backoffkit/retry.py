"""The synchronous retry decorator and its policy."""

from __future__ import annotations

import functools
import time
from typing import Any, Callable, Optional, Tuple, Type, TypeVar, Union, cast

from .strategy import ExponentialBackoff, Strategy

__all__ = [
    "DEFAULT_MAX_ATTEMPTS",
    "ErrorTypes",
    "RetryError",
    "RetryPolicy",
    "retry",
]

F = TypeVar("F", bound=Callable[..., Any])

DEFAULT_MAX_ATTEMPTS = 3

ErrorTypes = Union[Type[BaseException], Tuple[Type[BaseException], ...]]
"""An exception class, or a tuple of them, that is safe to retry."""


class RetryError(Exception):
    """Raised when a call failed on every allowed attempt."""

    def __init__(self, message: str, attempts: int, last_error: BaseException) -> None:
        super().__init__(message)
        self.attempts = attempts
        self.last_error = last_error

    def __str__(self) -> str:
        return f"{super().__str__()} (last error: {self.last_error!r})"


class RetryPolicy:
    """Decides whether an error is retried and how long to wait.

    The policy is deliberately separate from the decorators: the sync and
    async variants share it, so both behave identically.
    """

    __slots__ = ("max_attempts", "strategy", "retry_on", "giveup")

    def __init__(
        self,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        strategy: Optional[Strategy] = None,
        retry_on: ErrorTypes = Exception,
        giveup: Optional[Callable[[BaseException], bool]] = None,
    ) -> None:
        if max_attempts < 1:
            raise ValueError(f"max_attempts must be >= 1, got {max_attempts}")
        self.max_attempts = max_attempts
        self.strategy: Strategy = (
            strategy if strategy is not None else ExponentialBackoff()
        )
        self.retry_on = retry_on
        self.giveup = giveup

    def accepts(self, error: BaseException) -> bool:
        """Return whether ``error`` may be retried."""
        if self.giveup is not None and self.giveup(error):
            return False
        return isinstance(error, self.retry_on)

    def delay(self, attempt: int) -> float:
        """Return the delay before the next attempt, clamped to ``>= 0``."""
        return max(0.0, float(self.strategy.delay(attempt)))

    def __repr__(self) -> str:
        return (
            f"RetryPolicy(max_attempts={self.max_attempts!r}, "
            f"strategy={self.strategy!r}, retry_on={self.retry_on!r})"
        )


def retry(
    *,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    strategy: Optional[Strategy] = None,
    retry_on: ErrorTypes = Exception,
    giveup: Optional[Callable[[BaseException], bool]] = None,
    sleep: Callable[[float], None] = time.sleep,
) -> Callable[[F], F]:
    """Retry the decorated callable, sleeping according to ``strategy``.

    Exceptions that do not match ``retry_on`` propagate untouched.  When the
    allow-list is exhausted, :class:`RetryError` is raised with the last error
    attached as ``__cause__``.

    ``sleep`` is injectable so tests can run without waiting.
    """
    policy = RetryPolicy(
        max_attempts=max_attempts,
        strategy=strategy,
        retry_on=retry_on,
        giveup=giveup,
    )

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            attempt = 1
            while True:
                try:
                    return func(*args, **kwargs)
                except BaseException as error: