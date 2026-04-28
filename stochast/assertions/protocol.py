from __future__ import annotations

from typing import Protocol, runtime_checkable

from stochast._core.types import AssertionResult, EvalContext, Output


@runtime_checkable
class Assertion(Protocol):
    async def evaluate(self, output: Output, context: EvalContext) -> AssertionResult:
        ...
