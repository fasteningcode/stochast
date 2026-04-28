"""Unit tests for core types and the statistical runner (no LLM calls)."""
import pytest
import asyncio

import stochast
from stochast._core.types import AssertionResult, EvalContext, Output, RunResult, StochasticResult
from stochast.assertions import All, Any, BehavioralProperty, RegexMatcher, ExactMatcher, ContainsMatcher
from stochast.runner.stat_runner import StatRunner, _wilson_lower_bound, _min_runs


# --- Core types ---

def test_stochastic_result_pass_rate():
    r = StochasticResult(test_name="t", runs=10, threshold=0.8)
    r.run_results = [RunResult(run_index=i, passed=i < 9) for i in range(10)]
    assert r.pass_rate == 0.9
    assert r.passed_count == 9
    assert r.passed  # 0.9 >= 0.8


def test_stochastic_result_fails_below_threshold():
    r = StochasticResult(test_name="t", runs=10, threshold=0.9)
    r.run_results = [RunResult(run_index=i, passed=i < 8) for i in range(10)]
    assert r.pass_rate == 0.8
    assert not r.passed  # 0.8 < 0.9


def test_stochastic_result_cost_aggregation():
    r = StochasticResult(test_name="t", runs=2, threshold=0.5)
    r.run_results = [
        RunResult(run_index=0, passed=True, assertion_results=[
            AssertionResult(passed=True, name="j", cost_usd=0.001)
        ]),
        RunResult(run_index=1, passed=True, assertion_results=[
            AssertionResult(passed=True, name="j", cost_usd=0.002)
        ]),
    ]
    assert abs(r.total_cost_usd - 0.003) < 1e-9


# --- Wilson CI ---

def test_wilson_lower_bound_all_pass():
    lb = _wilson_lower_bound(10, 10)
    assert lb > 0.7  # 10/10 with z=1.96 → lower bound ~0.72


def test_min_runs_threshold():
    n = _min_runs(0.9)
    assert n > 0
    lb = _wilson_lower_bound(n, n)
    assert lb >= 0.9


# --- Assertions ---

@pytest.mark.asyncio
async def test_behavioral_property_pass():
    bp = BehavioralProperty(fn=lambda out, ctx: "hello" in out.text, name="has_hello")
    result = await bp.evaluate(Output(text="hello world"), EvalContext(run_index=0))
    assert result.passed
    assert result.name == "has_hello"


@pytest.mark.asyncio
async def test_behavioral_property_fail():
    bp = BehavioralProperty(fn=lambda out, ctx: False, name="always_fail")
    result = await bp.evaluate(Output(text="anything"), EvalContext(run_index=0))
    assert not result.passed
    assert "always_fail" in result.reason


@pytest.mark.asyncio
async def test_behavioral_property_exception_becomes_fail():
    bp = BehavioralProperty(fn=lambda out, ctx: 1 / 0, name="explodes")
    result = await bp.evaluate(Output(text="x"), EvalContext(run_index=0))
    assert not result.passed
    assert "ZeroDivisionError" in result.reason


@pytest.mark.asyncio
async def test_regex_matcher_pass():
    rm = RegexMatcher(pattern=r"^\d{4}$")
    result = await rm.evaluate(Output(text="1234"), EvalContext(run_index=0))
    assert result.passed


@pytest.mark.asyncio
async def test_regex_matcher_fail():
    rm = RegexMatcher(pattern=r"^\d{4}$")
    result = await rm.evaluate(Output(text="abcd"), EvalContext(run_index=0))
    assert not result.passed


@pytest.mark.asyncio
async def test_exact_matcher():
    em = ExactMatcher(expected="hello")
    assert (await em.evaluate(Output(text="hello"), EvalContext(run_index=0))).passed
    assert not (await em.evaluate(Output(text="HELLO"), EvalContext(run_index=0))).passed


@pytest.mark.asyncio
async def test_contains_matcher_case_insensitive():
    cm = ContainsMatcher(substring="WORLD")
    result = await cm.evaluate(Output(text="hello world"), EvalContext(run_index=0))
    assert result.passed


@pytest.mark.asyncio
async def test_all_combinator_all_pass():
    a = All(
        BehavioralProperty(fn=lambda o, c: True, name="a"),
        BehavioralProperty(fn=lambda o, c: True, name="b"),
    )
    result = await a.evaluate(Output(text="x"), EvalContext(run_index=0))
    assert result.passed


@pytest.mark.asyncio
async def test_all_combinator_one_fails():
    a = All(
        BehavioralProperty(fn=lambda o, c: True, name="a"),
        BehavioralProperty(fn=lambda o, c: False, name="b"),
    )
    result = await a.evaluate(Output(text="x"), EvalContext(run_index=0))
    assert not result.passed


@pytest.mark.asyncio
async def test_any_combinator_one_passes():
    a = Any(
        BehavioralProperty(fn=lambda o, c: False, name="a"),
        BehavioralProperty(fn=lambda o, c: True, name="b"),
    )
    result = await a.evaluate(Output(text="x"), EvalContext(run_index=0))
    assert result.passed


@pytest.mark.asyncio
async def test_any_combinator_all_fail():
    a = Any(
        BehavioralProperty(fn=lambda o, c: False, name="a"),
        BehavioralProperty(fn=lambda o, c: False, name="b"),
    )
    result = await a.evaluate(Output(text="x"), EvalContext(run_index=0))
    assert not result.passed


# --- StatRunner (no LLM) ---

@pytest.mark.asyncio
async def test_stat_runner_all_pass():
    runner = StatRunner(max_concurrency=5)

    async def always_pass(ctx: EvalContext):
        output = Output(text="ok")
        return output, BehavioralProperty(fn=lambda o, c: True, name="ok")

    result = await runner.run("test_all_pass", always_pass, runs=10, threshold=0.9)
    assert result.pass_rate == 1.0
    assert result.passed


@pytest.mark.asyncio
async def test_stat_runner_all_fail():
    runner = StatRunner(max_concurrency=5)

    async def always_fail(ctx: EvalContext):
        output = Output(text="bad")
        return output, BehavioralProperty(fn=lambda o, c: False, name="bad")

    result = await runner.run("test_all_fail", always_fail, runs=10, threshold=0.5)
    assert result.pass_rate == 0.0
    assert not result.passed


@pytest.mark.asyncio
async def test_stat_runner_exception_counts_as_failure():
    runner = StatRunner(max_concurrency=5)

    async def always_raise(ctx: EvalContext):
        raise RuntimeError("boom")

    result = await runner.run("test_raises", always_raise, runs=5, threshold=0.1)
    assert result.pass_rate == 0.0
    for run in result.run_results:
        assert run.error is not None


@pytest.mark.asyncio
async def test_stat_runner_threshold_boundary():
    runner = StatRunner(max_concurrency=5)

    async def pass_half(ctx: EvalContext):
        passes = ctx.run_index % 2 == 0
        return Output(text="x"), BehavioralProperty(fn=lambda o, c: passes, name="alternating")

    result = await runner.run("test_half", pass_half, runs=10, threshold=0.5)
    assert result.pass_rate == 0.5
    assert result.passed  # exactly at threshold

    result2 = await runner.run("test_half_strict", pass_half, runs=10, threshold=0.51)
    assert not result2.passed  # just above 50% fails


# --- @stochast.test decorator registration ---

def test_decorator_registers_test():
    from stochast._registry import get_registered, clear
    clear()

    @stochast.test(runs=5, threshold=0.8)
    async def my_ai_test(ctx):
        return BehavioralProperty(fn=lambda o, c: True, name="ok")

    registered = get_registered()
    assert len(registered) == 1
    assert registered[0]["name"] == "my_ai_test"
    assert registered[0]["runs"] == 5
    assert registered[0]["threshold"] == 0.8
    clear()
