from __future__ import annotations

from typing import List

import pytest

from backoffkit import FixedDelay, RetryError, RetryPolicy, retry


class Flaky:
    """Fails ``failures`` times, then returns ``value``."""

    def __init__(self, failures: int, value: str = "ok") -> None:
        self.failures = failures
        self.value = value
        self.calls = 0

    def __call__(self) -> str:
        self.calls += 1
        if self.calls <= self.failures:
            raise ConnectionError(f"boom {self.calls}")
        return self.value


def test_returns_first_successful_result() -> None:
    flaky = Flaky(failures=2)
    sleeps: List[float] = []

    @retry(max_attempts=3, strategy=FixedDelay(0.01), sleep=sleeps.append)
    def call() -> str:
        return flaky()

    assert call() == "ok"
    assert flaky.calls == 3
    assert sleeps == [0.01, 0.01]


def test_gives_up_after_max_attempts() -> None:
    flaky = Flaky(failures=10)

    @retry(max_attempts=3, strategy=FixedDelay(0.0), sleep=lambda _: None)
    def call() -> str:
        return flaky()

    with pytest.raises(RetryError) as excinfo:
        call()
    assert flaky.calls == 3
    assert excinfo.value.attempts == 3
    assert isinstance(excinfo.value.__cause__, ConnectionError)


def test_metadata_is_preserved() -> None:
    @retry(max_attempts=1, sleep=lambda _: None)
    def documented(value: int) -> int:
        """Docstring survives."""
        return value

    assert documented.__name__ == "documented"
    assert documented.__doc__ == "Docstring survives."
    assert documented(7) == 7


def test_max_attempts_below_one_is_rejected() -> None:
    with pytest.raises(ValueError, match="max_attempts must be >= 1"):
        retry(max_attempts=0)


def test_unlisted_exception_propagates_untouched() -> None:
    sleeps: List[float] = []

    @retry(
        max_attempts=4,
        strategy=FixedDelay(1.0),
        retry_on=ConnectionError,
        sleep=sleeps.append,
    )
    def call() -> None:
        raise ValueError("not retryable")

    with pytest.raises(ValueError):
        call()
    assert sleeps == []


def test_giveup_stops_retrying_early() -> None:
    flaky = Flaky(failures=10)

    @retry(
        max_attempts=5,
        strategy=FixedDelay(0.0),
        giveup=lambda error: "boom 2" in str(error),
        sleep=lambda _: None,
    )