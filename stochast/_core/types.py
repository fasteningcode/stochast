from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Output:
    text: str
    raw: Any = None
    usage: TokenUsage | None = None


@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass
class EvalContext:
    run_index: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AssertionResult:
    passed: bool
    name: str = ""
    score: float = 1.0
    reason: str = ""
    cost_usd: float | None = None


@dataclass
class RunResult:
    run_index: int
    passed: bool
    assertion_results: list[AssertionResult] = field(default_factory=list)
    latency_ms: float = 0.0
    error: str | None = None


@dataclass
class StochasticResult:
    test_name: str
    runs: int
    threshold: float
    run_results: list[RunResult] = field(default_factory=list)

    @property
    def passed_count(self) -> int:
        return sum(1 for r in self.run_results if r.passed)

    @property
    def pass_rate(self) -> float:
        if not self.run_results:
            return 0.0
        return self.passed_count / len(self.run_results)

    @property
    def passed(self) -> bool:
        return self.pass_rate >= self.threshold

    @property
    def total_cost_usd(self) -> float:
        total = 0.0
        for run in self.run_results:
            for ar in run.assertion_results:
                if ar.cost_usd is not None:
                    total += ar.cost_usd
        return total

    @property
    def mean_latency_ms(self) -> float:
        if not self.run_results:
            return 0.0
        return sum(r.latency_ms for r in self.run_results) / len(self.run_results)
