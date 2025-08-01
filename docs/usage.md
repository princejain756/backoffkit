# Usage

This page walks through the three things `backoffkit` does: computing delays,
wrapping a function with retries, and doing the same for coroutines.

## Picking a strategy

A strategy is an object with one method:

```python
class Strategy(Protocol):
    def delay(self, attempt: int) -> float: ...
```

`attempt` is one-based — `1` means one attempt has already failed. Strategies
never sleep and never touch the clock, which makes them trivial to test.

### FixedDelay

Use it when the failure is likely transient and short, such as a lock
contention or a file rename on a networked volume.

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
half fixed and samples the upper half, so retries still space out. Both accept
an optional `random.Random` instance, which is what the test suite uses to make
the sampled values reproducible.

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

### Exception allow-lists

Pass a class or a tuple of classes to `retry_on`. Broad values like `Exception`
are convenient at the top of a new project but hide bugs, because a `TypeError`
from your own code will be retried three times before it is reported.

```python
@retry(max_attempts=3, retry_on=ConnectionError)
def connect(host: str) -> None: ...
```

`giveup` runs before the allow-list and can veto a specific error:

```python
@retry(max_attempts=5, retry_on=OSError, giveup=lambda error: error.errno == 2)
def read_config(path: str) -> str: ...
```

## Retrying a coroutine

```python
from backoffkit import async_retry, ExponentialBackoff

@async_retry(max_attempts=3, strategy=ExponentialBackoff(base=0.1, max_delay=2.0))
async def health() -> str:
    response = await client.get("/health")
    return response.text
```

The async variant uses the same `RetryPolicy` as the sync one, so the
allow-list, `giveup`, and `on_retry` semantics are identical. Two details are
specific to asyncio:

- `asyncio.CancelledError` inherits from `BaseException`, so the default
  `retry_on=Exception` leaves it alone. Cancelling the enclosing task stops the
  loop on the attempt that is in flight.
- The decorated object must be a coroutine function; anything else raises
  `TypeError` when the decorator is applied, not when it is first called.

`async_retry_call` is available when you cannot decorate, for example a method
on a client object you do not own.

## Observing retries

`on_retry` is called after every failure that will be retried, with a frozen
`RetryState(attempt, delay, error)`. Use it for logging or metrics:

```python
import logging
from backoffkit import RetryState

log = logging.getLogger(__name__)

def note_retry(state: RetryState) -> None:
    log.warning(