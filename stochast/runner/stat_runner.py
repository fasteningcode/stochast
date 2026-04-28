from __future__ import annotations

import asyncio
import functools
import math
import time
from typing import Any, Callable, Coroutine

from stochast._core.types import AssertionResult, EvalContext, Output, RunResult, StochasticResult

_DEFAULT_PROVIDER_KEY = "_default_provider"


def _wilson_lower_bound(successes: int, n: int, z: float = 1.96) -> float:
    if n == 0:
        return 0.0
    p = successes / n
    return (
        p + z * z / (2 * n) - z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)
    ) / (1 + z * z / n)


@functools.lru_cache(maxsize=64)
def _min_runs(threshold: float, z: float = 1.96) -> int:
    if threshold >= 1.0:
        return 1
    for n in range(1, 500):
        if _wilson_lower_bound(n, n, z) >= threshold:
            return n
    return 500


@functools.lru_cache(maxsize=64)
def _low_sample_warning(runs: int, threshold: float) -> str | None:
    if runs >= _min_runs(threshold):
        return None
    return (
        f"Warning: {runs} runs is statistically insufficient to reliably "
        f"confirm a {threshold:.0%} pass rate. Consider using runs>={_min_runs(threshold)}."
    )


async def _run_once(
    test_fn: Callable,
    index: int,
    default_provider: Any,
    sem: asyncio.Semaphore,
) -> RunResult:
    ctx = EvalContext(run_index=index)
    if default_provider is not None:
        ctx.metadata[_DEFAULT_PROVIDER_KEY] = default_provider

    async with sem:
        start = time.monotonic()
        try:
            returned = await test_fn(ctx)
            latency_ms = (time.monotonic() - start) * 1000
            return await _interpret(returned, index, ctx, latency_ms)
        except Exception as exc:
            latency_ms = (time.monotonic() - start) * 1000
            return RunResult(
                run_index=index,
                passed=False,
                latency_ms=latency_ms,
                error=f"{type(exc).__name__}: {exc}",
            )


async def _interpret(returned: Any, index: int, ctx: EvalContext, latency_ms: float) -> RunResult:
    if returned is None:
        return RunResult(run_index=index, passed=True, latency_ms=latency_ms)

    if isinstance(returned, AssertionResult):
        return RunResult(
            run_index=index,
            passed=returned.passed,
            assertion_results=[returned],
            latency_ms=latency_ms,
        )

    if isinstance(returned, tuple) and len(returned) == 2:
        output, assertion = returned
        result = await assertion.evaluate(output, ctx)
        return RunResult(
            run_index=index,
            passed=result.passed,
            assertion_results=[result],
            latency_ms=latency_ms,
        )

    if isinstance(returned, Output):
        return RunResult(run_index=index, passed=True, latency_ms=latency_ms)

    if isinstance(returned, bool):
        return RunResult(run_index=index, passed=returned, latency_ms=latency_ms)

    # Bare assertion with no output — BehavioralProperty that ignores output.text
    result = await returned.evaluate(Output(text=""), ctx)
    return RunResult(
        run_index=index,
        passed=result.passed,
        assertion_results=[result],
        latency_ms=latency_ms,
    )


class StatRunner:
    def __init__(self, max_concurrency: int = 10) -> None:
        self.max_concurrency = max_concurrency

    async def run(
        self,
        test_name: str,
        test_fn: Callable[[EvalContext], Coroutine[Any, Any, Any]],
        runs: int,
        threshold: float,
        default_provider: Any = None,
    ) -> StochasticResult:
        warning = _low_sample_warning(runs, threshold)
        if warning:
            import warnings
            warnings.warn(warning, stacklevel=4)

        sem = asyncio.Semaphore(self.max_concurrency)
        run_results = await asyncio.gather(
            *[_run_once(test_fn, i, default_provider, sem) for i in range(runs)]
        )
        return StochasticResult(
            test_name=test_name,
            runs=runs,
            threshold=threshold,
            run_results=list(run_results),
        )
