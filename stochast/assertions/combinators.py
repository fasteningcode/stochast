from __future__ import annotations

import asyncio
import builtins

from stochast._core.types import AssertionResult, EvalContext, Output
from stochast.assertions.protocol import Assertion


def _aggregate_cost(results: list[AssertionResult]) -> float | None:
    total = sum(r.cost_usd for r in results if r.cost_usd is not None)
    return total if total else None


class All:
    """All assertions must pass for the run to pass."""

    def __init__(self, *assertions: Assertion) -> None:
        self.assertions = assertions

    async def evaluate(self, output: Output, context: EvalContext) -> AssertionResult:
        results = await asyncio.gather(
            *(a.evaluate(output, context) for a in self.assertions)
        )
        passed = builtins.all(r.passed for r in results)
        failed = [r for r in results if not r.passed]
        return AssertionResult(
            passed=passed,
            name="all",
            score=sum(r.score for r in results) / len(results) if results else 1.0,
            reason="; ".join(r.reason for r in failed if r.reason),
            cost_usd=_aggregate_cost(results),
        )


class Any:
    """At least one assertion must pass for the run to pass."""

    def __init__(self, *assertions: Assertion) -> None:
        self.assertions = assertions

    async def evaluate(self, output: Output, context: EvalContext) -> AssertionResult:
        results = await asyncio.gather(
            *(a.evaluate(output, context) for a in self.assertions)
        )
        passed = builtins.any(r.passed for r in results)
        return AssertionResult(
            passed=passed,
            name="any",
            score=max((r.score for r in results), default=0.0),
            reason="" if passed else "No assertions passed: " + "; ".join(
                r.reason for r in results if r.reason
            ),
            cost_usd=_aggregate_cost(results),
        )
