"""The synchronous retry decorator."""

from __future__ import annotations

import functools
import time
from typing import Any, Callable, Optional, TypeVar, cast

from .strategy import ExponentialBackoff, Strategy

__all__ = ["DEFAULT_MAX_ATTEMPTS", "RetryError", "retry"]

F = TypeVar("F", bound=Callable[..., Any])

DEFAULT_MAX_ATTEMPTS = 3


class RetryError(Exception):
    """Raised when a call failed on every attempt."""

    def __init__(self, message: str, attempts: int, last_error: BaseException) -> None:
        super().__init__(message)
        self.attempts = attempts
        self.last_error = last_error

    def __str__(self) -> str:
        return f"{super().__str__()} (last error: {self.last_error!r})"


def retry(
    *,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    strategy: Optional[Strategy] = None,
    sleep: Callable[[float], None] = time.sleep,
) -> Callable[[F], F]:
    """Retry the decorated callable, sleeping according to ``strategy``.

    The function is called until it returns, or until ``max_attempts`` attempts
    have failed, in which case :class:`RetryError` is raised with the last
    error attached as ``__cause__``.

    ``sleep`` is injectable so tests can run without waiting.
    """
    if max_attempts < 1:
        raise ValueError(f"max_attempts must be >= 1, got {max_attempts}")
    chosen: Strategy = strategy if strategy is not None else ExponentialBackoff()

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            attempt = 1
            while True:
                try:
                    return func(*args, **kwargs)
                except Exception as error:
                    if attempt >= max_attempts:
                        raise RetryError(
                            f"{func.__name__} failed after {attempt} attempts",
                            attempts=attempt,
                            last_error=error,
                        ) from error
                    sleep(max(0.0, float(chosen.delay(attempt))))
                    attempt += 1

        return cast(F, wrapper)

    return decorator
