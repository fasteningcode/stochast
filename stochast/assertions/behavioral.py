from __future__ import annotations

from typing import Callable

from stochast._core.types import AssertionResult, EvalContext, Output


class BehavioralProperty:
    def __init__(
        self,
        fn: Callable[[Output, EvalContext], bool],
        name: str = "behavioral_property",
    ) -> None:
        self.fn = fn
        self.name = name

    async def evaluate(self, output: Output, context: EvalContext) -> AssertionResult:
        try:
            passed = bool(self.fn(output, context))
            return AssertionResult(
                passed=passed,
                name=self.name,
                score=1.0 if passed else 0.0,
                reason="" if passed else f"Property '{self.name}' returned False",
            )
        except Exception as exc:
            return AssertionResult(
                passed=False,
                name=self.name,
                score=0.0,
                reason=f"Property '{self.name}' raised {type(exc).__name__}: {exc}",
            )
