# backoffkit

Small, dependency-free retry and backoff helpers. Pure Python 3.9+, fully
type-annotated, no runtime dependencies.

```python
from backoffkit import ExponentialBackoff, retry

@retry(max_attempts=5, strategy=ExponentialBackoff(base=0.2, max_delay=8.0))
def fetch(url: str) -> bytes:
    return http_get(url)
```

## Install

```console
$ pip install backoffkit
```

## Strategies

A strategy computes the delay for attempt *n*. Strategies never sleep and never
read the clock, which makes them trivial to test.

```python
from backoffkit import ExponentialBackoff, FixedDelay, EqualJitter, Jittered

FixedDelay(0.5)                             # 0.5s every time
ExponentialBackoff(base=0.5, factor=2.0)    # 0.5, 1, 2, 4, 8, ...
ExponentialBackoff(base=0.5, max_delay=10)  # ... capped at 10
Jittered(ExponentialBackoff())              # uniform in [0, ceiling]
EqualJitter(ExponentialBackoff())           # uniform in [ceiling/2, ceiling]
```

`attempt` is one-based, and `attempt=0` raises `ValueError` — a delay is only
meaningful after a failure.

## Retrying a function

```python
from backoffkit import ExponentialBackoff, retry

@retry(
    max_attempts=4,
    strategy=ExponentialBackoff(base=0.2, max_delay=5.0),
    retry_on=ConnectionError,
)
def fetch_user(user_id: int) -> dict:
    ...
```

Errors outside `retry_on` propagate immediately. When the allow-list is
exhausted, `RetryError` is raised with the last error chained as `__cause__`, so
a traceback still shows the original failure.

## asyncio

```python
from backoffkit import async_retry, ExponentialBackoff

@async_retry(max_attempts=3, strategy=ExponentialBackoff(base=0.1))
async def ping() -> str:
    return await client.get("/health")
```

Cancellation is not retried: `asyncio.CancelledError` derives from
`BaseException`, so the default `retry_on=Exception` leaves it alone.

## Testing

Both decorators accept a `sleep` argument, so tests do not have to wait:

```python
delays: list[float] = []

@retry(max_attempts=3, strategy=ExponentialBackoff(), sleep=delays.append)
def flaky() -> str:
    ...

assert delays == [0.5, 1.0]
```

## License

MIT
