from __future__ import annotations

import functools
from typing import Any, Callable

_TEST_REGISTRY: list[dict] = []


def register(fn: Callable, runs: int, threshold: float, provider: Any, concurrency: int) -> Callable:
    _TEST_REGISTRY.append({
        "name": fn.__name__,
        "fn": fn,
        "runs": runs,
        "threshold": threshold,
        "provider": provider,
        "concurrency": concurrency,
    })

    @functools.wraps(fn)
    async def wrapper(*args, **kwargs):
        return await fn(*args, **kwargs)

    return wrapper


def get_registered() -> list[dict]:
    return list(_TEST_REGISTRY)


def clear() -> None:
    _TEST_REGISTRY.clear()
