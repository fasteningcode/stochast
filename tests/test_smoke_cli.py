"""Smoke test for the @stochast.test decorator and CLI runner (no LLM calls)."""
import stochast
from stochast._core.types import Output
from stochast.assertions import All, BehavioralProperty, RegexMatcher


@stochast.test(runs=10, threshold=0.80)
async def test_always_passes(ctx):
    output = Output(text="positive")
    return output, BehavioralProperty(
        fn=lambda out, c: out.text == "positive",
        name="is_positive",
    )


@stochast.test(runs=10, threshold=0.50)
async def test_regex_date_format(ctx):
    output = Output(text="2024-01-15")
    return output, RegexMatcher(pattern=r"^\d{4}-\d{2}-\d{2}$")


@stochast.test(runs=10, threshold=0.90)
async def test_combined_assertions(ctx):
    output = Output(text="The answer is positive and clear.")
    return output, All(
        BehavioralProperty(fn=lambda out, c: "positive" in out.text, name="has_positive"),
        BehavioralProperty(fn=lambda out, c: len(out.text) > 5, name="non_trivial"),
    )
