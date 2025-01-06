# Usage

This page walks through the two things `backoffkit` does: computing delays and
wrapping a function with retries.

## Picking a strategy

A strategy is an object with one method:

```python
class Strategy(Protocol):
    def delay(self, attempt: int) -> float: ...
```

`attempt` is one-based — `1` means one attempt has already failed. Strategies
never sleep and never touch the clock, which makes them trivial to test.

### FixedDelay

Use it when the failure is likely transient and short, such as lock contention
or a file rename on a networked volume.

```python
from backoffkit import FixedDelay

delay = FixedDelay(0.25)
delay.delay(1), delay.delay(2)   # (0.25, 0.25)
```

### ExponentialBackoff

Use it when the remote side needs time to recover: rate limits, queue
saturation, a database failover. Attempt *n* waits `base * factor ** (n - 1)`
seconds, clamped by `max_delay`.

```python
from backoffkit import ExponentialBackoff

strategy = ExponentialBackoff(base=0.1, factor=2.0, max_delay=2.0)
[strategy.delay(n) for n in range(1, 7)]
# [0.1, 0.2, 0.4, 0.8, 1.6, 2.0]
```

Always set `max_delay` for user-facing paths. Without it, attempt 20 at
`base=1, factor=2` waits twelve days.

### Jitter

Clients that failed together retry together, which turns a recovering service
back into a queue. Jitter spreads the retries out.

```python
from backoffkit import EqualJitter, ExponentialBackoff, Jittered

full = Jittered(ExponentialBackoff(base=0.5, max_delay=30.0))
half = EqualJitter(ExponentialBackoff(base=0.5, max_delay=30.0))
```

`Jittered` samples uniformly from `[0, ceiling]`; `EqualJitter` keeps the lower
half fixed and samples the upper half, so retries still space out.

## Retrying a function

```python
import httpx
from backoffkit import ExponentialBackoff, retry

@retry(
    max_attempts=4,
    strategy=ExponentialBackoff(base=0.2, max_delay=5.0),
    retry_on=(httpx.TimeoutException, httpx.ConnectError),
)
def fetch_user(user_id: int) -> dict:
    response = httpx.get(f"https://api.example.com/users/{user_id}", timeout=2.0)
    response.raise_for_status()
    return response.json()
```

What happens on each call:

1. The function runs. A return value is passed straight through.
2. If it raises something listed in `retry_on`, the policy asks the strategy
   for a delay, calls `sleep(delay)`, and runs the function again.
3. If it raises anything else, the exception propagates untouched — no sleep,
   no wrapped error.
4. After `max_attempts` failures, `RetryError` is raised from the last error.

`RetryError` exposes `attempts` and `last_error`, and the original exception is
available through `__cause__` for logging.

## Testing code that retries

Inject a sleeper instead of patching `time.sleep`:

```python
delays: list[float] = []

@retry(max_attempts=3, strategy=ExponentialBackoff(base=0.5), sleep=delays.append)
def flaky() -> str:
    """Fails twice, then succeeds."""

assert flaky() == "done"
assert delays == [0.5, 1.0]
```
