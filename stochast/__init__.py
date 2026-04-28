"""
Stochast — statistical testing framework for non-deterministic AI systems.

Quick start:

    import stochast
    from stochast.providers import LiteLLMAdapter
    from stochast.assertions import LLMJudge, BehavioralProperty, All

    llm = LiteLLMAdapter("gemini/gemini-2.5-flash")

    @stochast.test(runs=20, threshold=0.90)
    async def test_my_feature(ctx):
        output = await llm("Your prompt here")
        return BehavioralProperty(
            fn=lambda out, c: "expected" in out.text.lower(),
            name="contains_expected"
        )
"""
from __future__ import annotations

from typing import Callable

from stochast._core.types import EvalContext, Output
from stochast._registry import register


def test(
    fn: Callable | None = None,
    *,
    runs: int = 10,
    threshold: float = 0.80,
    provider=None,
    concurrency: int = 10,
):
    """Decorator that marks an async function as a stochastic test.

    Args:
        runs: Number of times to execute the test function.
        threshold: Fraction of runs that must pass (0.0–1.0).
        provider: Default LLM provider made available via ctx.metadata['_default_provider'].
        concurrency: Max parallel LLM calls.

    Example:
        @stochast.test(runs=20, threshold=0.90)
        async def test_sentiment(ctx):
            output = await llm("Classify sentiment of: 'Amazing product!'")
            return BehavioralProperty(
                fn=lambda out, c: out.text.strip().lower() in {"positive", "negative", "neutral"},
                name="valid_sentiment_label"
            )
    """
    def decorator(f: Callable) -> Callable:
        return register(f, runs=runs, threshold=threshold, provider=provider, concurrency=concurrency)

    if fn is not None:
        # Called as @stochast.test without parentheses
        return decorator(fn)

    return decorator


# Convenience re-exports so users can do: from stochast import BehavioralProperty etc.
from stochast.assertions import (  # noqa: E402
    All,
    Any,
    BehavioralProperty,
    ContainsMatcher,
    ExactMatcher,
    LLMJudge,
    RegexMatcher,
    SchemaValidator,
    SemanticSimilarity,
)
from stochast._core import (  # noqa: E402
    AssertionResult,
    EvalContext,
    Output,
    StochasticResult,
)

__version__ = "0.1.0"
__all__ = [
    "test",
    "All",
    "Any",
    "AssertionResult",
    "BehavioralProperty",
    "ContainsMatcher",
    "EvalContext",
    "ExactMatcher",
    "LLMJudge",
    "Output",
    "RegexMatcher",
    "SchemaValidator",
    "SemanticSimilarity",
    "StochasticResult",
]
