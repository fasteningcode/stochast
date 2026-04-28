from __future__ import annotations

import json

from stochast._core.types import AssertionResult, EvalContext, Output
from stochast.runner.stat_runner import _DEFAULT_PROVIDER_KEY

_JUDGE_SYSTEM = """You are a strict output quality evaluator.
You will be given an AI-generated output and evaluation criteria.
Score the output from 0.0 to 1.0 based on how well it meets the criteria.
Respond in this exact JSON format:
{"score": <float 0.0-1.0>, "passed": <true|false>, "reason": "<one sentence>"}
"""

_JUDGE_USER = """Criteria:
{criteria}

Output to evaluate:
{output}

Score threshold to pass: {threshold}
Respond with JSON only."""


class LLMJudge:
    def __init__(
        self,
        criteria: str,
        provider: object | None = None,
        score_threshold: float = 0.7,
    ) -> None:
        self.criteria = criteria.strip()
        self.provider = provider
        self.score_threshold = score_threshold

    async def evaluate(self, output: Output, context: EvalContext) -> AssertionResult:
        provider = self.provider or context.metadata.get(_DEFAULT_PROVIDER_KEY)
        if provider is None:
            return AssertionResult(
                passed=False,
                name="llm_judge",
                score=0.0,
                reason="LLMJudge requires a provider. Pass one via @stochast.test(provider=...) or LLMJudge(provider=...)",
            )

        prompt = _JUDGE_USER.format(
            criteria=self.criteria,
            output=output.text[:4000],
            threshold=self.score_threshold,
        )

        try:
            judge_output = await provider(
                prompt=prompt,
                system=_JUDGE_SYSTEM,
                temperature=0.0,
            )
            data = json.loads(judge_output.text)
            score = float(data.get("score", 0.0))
            passed = bool(data.get("passed", score >= self.score_threshold))
            cost = (judge_output.usage.total_tokens * 0.0000015) if judge_output.usage else None
            return AssertionResult(
                passed=passed,
                name="llm_judge",
                score=score,
                reason=str(data.get("reason", "")),
                cost_usd=cost,
            )
        except Exception as exc:
            return AssertionResult(
                passed=False,
                name="llm_judge",
                score=0.0,
                reason=f"Judge call failed: {type(exc).__name__}: {exc}",
            )
