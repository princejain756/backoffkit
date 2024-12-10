"""The asyncio counterpart of :func:`backoffkit.retry`."""

from __future__ import annotations

import asyncio
import functools
from typing import (
    Any,
    Awaitable,
    Callable,
    Optional,
    TypeVar,
    cast,
)

from .retry import (
    DEFAULT_MAX_ATTEMPTS,
    ErrorTypes,
    RetryError,
    RetryPolicy,
    RetryState,
)
from .strategy import Strategy

__all__ = ["async_retry", "async_retry_call"]

AF = TypeVar("AF", bound=Callable[..., Awaitable[Any]])


def async_retry(
    *,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    strategy: Optional[Strategy] = None,
    retry_on: ErrorTypes = Exception,
    giveup: Optional[Callable[[BaseException], bool]] = None,
    on_retry: Optional[Callable[[RetryState], None]] = None,
    sleep: Optional[Callable[[float], Awaitable[None]]] = None,
) -> Callable[[AF], AF]:
    """Retry an async callable, awaiting ``sleep(delay)`` between attempts.

    Cancellation is never swallowed: :class:`asyncio.CancelledError` derives
    from :class:`BaseException`, so with the default ``retry_on=Exception`` the
    task is cancelled immediately.

    The decorator must be applied to a coroutine function; calling the
    decorated object returns a coroutine.
    """
    policy = RetryPolicy(
        max_attempts=max_attempts,
        strategy=strategy,
        retry_on=retry_on,
        giveup=giveup,
    )
    sleeper = sleep if sleep is not None else asyncio.sleep

    def decorator(func: AF) -> AF:
        if not asyncio.iscoroutinefunction(func) and not asyncio.iscoroutinefunction(
            getattr(func, "__call__", None)
        ):
            raise TypeError(f"async_retry expects a coroutine function, got {func!r}")

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            attempt = 1
            while True:
                try:
                    return await func(*args, **kwargs)
                except BaseException as error:
                    if not policy.accepts(error):
                        raise
                    if attempt >= policy.max_attempts:
                        raise RetryError(
                            f"{func.__name__} failed after {attempt} attempts",
                            attempts=attempt,
                            last_error=error,
                        ) from error
                    delay = policy.delay(attempt)
                    if on_retry is not None:
                        on_retry(RetryState(attempt=attempt, delay=delay, error=error))
                    await sleeper(delay)
                    attempt += 1

        return cast(AF, wrapper)

    return decorator


async def async_retry_call(
    func: Callable[..., Awaitable[Any]],
    *args: Any,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    strategy: Optional[Strategy] = None,
    retry_on: ErrorTypes = Exception,
    giveup: Optional[Callable[[BaseException], bool]] = None,
    on_retry: Optional[Callable[[RetryState], None]] = None,
    sleep: Optional[Callable[[float], Awaitable[None]]] = None,
    **kwargs: Any,
) -> Any:
    """Await ``func`` with retries without decorating it."""
    wrapped = async_retry(
        max_attempts=max_attempts,
        strategy=strategy,
        retry_on=retry_on,
        giveup=giveup,
        on_retry=on_retry,
        sleep=sleep,
    )(func)
    return await wrapped(*args, **kwargs)
