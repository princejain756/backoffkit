from __future__ import annotations

import pytest

from backoffkit.strategy import ExponentialBackoff, FixedDelay, Strategy


def test_fixed_delay_is_constant() -> None:
    strategy = FixedDelay(0.25)
    assert [strategy.delay(n) for n in range(1, 5)] == [0.25, 0.25, 0.25, 0.25]


def test_fixed_delay_rejects_negative_seconds() -> None:
    with pytest.raises(ValueError, match="seconds must be >= 0"):
        FixedDelay(-1)


def test_exponential_doubles_each_attempt() -> None:
    strategy = ExponentialBackoff(base=1.0, factor=2.0)
    assert [strategy.delay(n) for n in range(1, 5)] == [1.0, 2.0, 4.0, 8.0]


def test_exponential_respects_max_delay() -> None:
    strategy = ExponentialBackoff(base=1.0, factor=3.0, max_delay=10.0)
    assert [strategy.delay(n) for n in range(1, 5)] == [1.0, 3.0, 9.0, 10.0]


def test_exponential_rejects_factor_below_one() -> None:
    with pytest.raises(ValueError, match="factor must be >= 1"):
        ExponentialBackoff(factor=0.5)


@pytest.mark.parametrize("strategy", [FixedDelay(1.0), ExponentialBackoff()])
def test_attempts_below_one_are_rejected(strategy: Strategy) -> None:
    with pytest.raises(ValueError, match="attempt must be >= 1"):
        strategy.delay(0)


def test_strategy_protocol_is_runtime_checkable() -> None:
    assert isinstance(FixedDelay(0.1), Strategy)
    assert not isinstance(object(), Strategy)
