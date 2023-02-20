from __future__ import annotations

import pytest

from backoffkit.strategy import FixedDelay, Strategy


def test_fixed_delay_is_constant() -> None:
    strategy = FixedDelay(0.25)
    assert [strategy.delay(n) for n in range(1, 5)] == [0.25, 0.25, 0.25, 0.25]


def test_fixed_delay_rejects_negative_seconds() -> None:
    with pytest.raises(ValueError, match="seconds must be >= 0"):
        FixedDelay(-1)


def test_attempts_below_one_are_rejected() -> None:
    with pytest.raises(ValueError, match="attempt must be >= 1"):
        FixedDelay(1.0).delay(0)


def test_strategy_protocol_is_runtime_checkable() -> None:
    assert isinstance(FixedDelay(0.1), Strategy)
    assert not isinstance(object(), Strategy)
