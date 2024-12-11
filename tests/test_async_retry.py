from __future__ import annotations

import asyncio
from typing import List

import pytest

from backoffkit import FixedDelay, RetryError, async_retry, async_retry_call

pytestmark = pytest.mark.asyncio


class AsyncFlaky:
    def __init__(self, failures: int, value: str = "ok") -> None:
        self.failures = failures
        self.value = value
        self.calls = 0

    async def __call__(self) -> str:
        self.calls += 1
        if self.calls <= self.failures:
            raise TimeoutError(f"slow {self.calls}")
        return self.value


async def test_retries_until_success() -> None:
    flaky = AsyncFlaky(failures=2)
    sleeps: List[float] = []

    async def fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    @async_retry(max_attempts=3, strategy=FixedDelay(0.01), sleep=fake_sleep)
    async def call() -> str:
        return await flaky()

    assert await call() == "ok"
    assert flaky.calls == 3
    assert sleeps == [0.01, 0.01]


async def test_raises_retry_error_when_exhausted() -> None:
    flaky = AsyncFlaky(failures=10)

    @async_retry(
        max_attempts=2,
        strategy=FixedDelay(0.0),
        sleep=_no_sleep,
    )
    async def call() -> str:
        return await flaky()

    with pytest.raises(RetryError) as excinfo:
        await call()
    assert flaky.calls == 2
    assert isinstance(excinfo.value.__cause__, TimeoutError)


async def test_unlisted_exception_is_not_retried() -> None:
    calls = 0

    @async_retry(max_attempts=3, retry_on=TimeoutError, sleep=_no_sleep)
    async def call() -> None:
        nonlocal calls
        calls += 1
        raise ValueError("nope")

    with pytest.raises(ValueError):
        await call()
    assert calls == 1


async def test_cancellation_is_never_retried() -> None:
    calls = 0

    @async_retry(max_attempts=5, sleep=_no_sleep)
    async def call() -> None:
        nonlocal calls
        calls += 1
        raise asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        await call()
    assert calls == 1


async def test_concurrent_calls_keep_separate_attempt_counts() -> None:
    flakies = [AsyncFlaky(failures=1) for _ in range(5)]

    @async_retry(max_attempts=2, strategy=FixedDelay(0.0), sleep=_no_sleep)
    async def call(flaky: AsyncFlaky) -> str:
        return await flaky()

    results = await asyncio.gather(*(call(flaky) for flaky in flakies))
    assert results == ["ok"] * 5
    assert [flaky.calls for flaky in flakies] == [2] * 5


async def test_decorator_rejects_sync_functions() -> None:
    def not_async() -> None:
        return None

    with pytest.raises(TypeError, match="coroutine function"):
        async_retry(max_attempts=2)(not_async)  # type: ignore[type-var]


async def test_async_retry_call_wraps_an_existing_coroutine_function() -> None:
    flaky = AsyncFlaky(failures=1)
    result = await async_retry_call(
        flaky,
        max_attempts=2,
        strategy=FixedDelay(0.0),
        sleep=_no_sleep,
    )
    assert result == "ok"
    assert flaky.calls == 2


async def _no_sleep(delay: float) -> None:
    return None
