# backoffkit

Small, dependency-free retry and backoff helpers for synchronous and asyncio
code. Pure Python 3.9+, fully type-annotated, no runtime dependencies.

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

## Why another retry library?

Because most retry loops want the same four things and nothing else: a delay
policy, a bounded number of attempts, a list of errors that are worth retrying,
and a way to see what happened. `backoffkit` keeps those four things separate
and small, so the whole behaviour fits in your head:

| Piece | What it does |
| --- | --- |
| `strategy.py` | Computes the delay for attempt *n*. No I/O, no sleeping. |
| `retry.py` | The `RetryPolicy` plus the `@retry` decorator. |
| `async_retry.py` | The same policy, awaited. |

Strategies are plain objects with a single `delay(attempt)` method, which means
you can compose them (jitter wraps any other strategy), swap them in tests, or
write your own in a few lines.

## Strategies

```python
from backoffkit import ExponentialBackoff, FixedDelay, Jittered, EqualJitter

FixedDelay(0.5)                                    # 0.5s every time
ExponentialBackoff(base=0.5, factor=2.0)           # 0.5, 1, 2, 4, 8, ...
ExponentialBackoff(base=0.5, max_delay=10.0)       # ... capped at 10
Jittered(ExponentialBackoff())                     # uniform in [0, ceiling]
EqualJitter(ExponentialBackoff())                  # uniform in [ceiling/2, ceiling]
```

Delays are in seconds and always non-negative. `attempt` is one-based, and
`attempt=0` raises `ValueError` — a delay is only meaningful after a failure.

## Retrying a function

```python
import httpx
from backoffkit import RetryState, retry, ExponentialBackoff

def log_retry(state: RetryState) -> None:
    print(f"attempt {state.attempt} failed ({state.error!r}), waiting {state.delay:.2f}s")

@retry(
    max_attempts=4,
    strategy=ExponentialBackoff(base=0.1, max_delay=5.0),
    retry_on=(httpx.TimeoutException, httpx.ConnectError),
    on_retry=log_retry,
)
def get_user(user_id: int) -> dict:
    return httpx.get(f"https://api.example.com/users/{user_id}").json()
```

When every attempt fails, `RetryError` is raised with the last error chained as
`__cause__`, so a traceback still shows the original failure:

```python
from backoffkit import RetryError

try:
    get_user(42)
except RetryError as error:
    print(error.attempts, error.last_error)
```

`retry_on` defaults to `Exception`. Anything outside the allow-list propagates
immediately without consuming an attempt, and `giveup` gets a veto over
individual errors:

```python
@retry(max_attempts=5, retry_on=OSError, giveup=lambda error: error.errno == 2)
def read_config(path: str) -> str:
    ...
```

## Retrying without a decorator

```python
from backoffkit import retry_call

result = retry_call(parse_line, line, max_attempts=3)
```

`retry_call` accepts the same options as `retry`; any other keyword argument is
forwarded to the wrapped callable.

## asyncio

```python
from backoffkit import async_retry, ExponentialBackoff

@async_retry(max_attempts=3, strategy=ExponentialBackoff(base=0.1))
async def ping() -> str:
    return await client.get("/health")
```

`async_retry` awaits `asyncio.sleep` between attempts and never retries
`asyncio.CancelledError`, so cancelling the surrounding task takes effect on the
first attempt. It requires a coroutine function and raises `TypeError`
otherwise. `async_retry_call` is the non-decorator form.

## Testing

Both decorators accept a `sleep` argument, so tests do not have to wait:

```python
delays: list[float] = []

@retry(max_attempts=3, strategy=ExponentialBackoff(), sleep=delays.append)
def flaky() -> str:
    ...

assert delays == [0.5, 1.0]
```

For async code pass an `async def` sleeper. Run the suite with:

```console
$ python -m pytest
```

## Limits

- Retries are in-process only; nothing is shared between workers.
- Delays are not persisted, so a restart starts from the first attempt again.
- Only attempts are bounded, not total elapsed time — wrap slow calls with your
  own deadline if you need one.

## License

MIT
