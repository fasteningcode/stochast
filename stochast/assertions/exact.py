from __future__ import annotations

import re

from stochast._core.types import AssertionResult, EvalContext, Output


def _normalize(s: str, case_sensitive: bool) -> str:
    return s if case_sensitive else s.lower()


class ExactMatcher:
    def __init__(self, expected: str, case_sensitive: bool = True) -> None:
        self.expected = expected
        self.case_sensitive = case_sensitive

    async def evaluate(self, output: Output, context: EvalContext) -> AssertionResult:
        text = _normalize(output.text, self.case_sensitive)
        expected = _normalize(self.expected, self.case_sensitive)
        passed = text == expected
        return AssertionResult(
            passed=passed,
            name="exact_match",
            score=float(passed),
            reason="" if passed else f"Expected '{self.expected}', got '{output.text}'",
        )


class ContainsMatcher:
    def __init__(self, substring: str, case_sensitive: bool = False) -> None:
        self.substring = substring
        self.case_sensitive = case_sensitive

    async def evaluate(self, output: Output, context: EvalContext) -> AssertionResult:
        passed = _normalize(self.substring, self.case_sensitive) in _normalize(output.text, self.case_sensitive)
        return AssertionResult(
            passed=passed,
            name="contains",
            score=float(passed),
            reason="" if passed else f"Expected output to contain '{self.substring}'",
        )


class RegexMatcher:
    def __init__(self, pattern: str, flags: int = 0) -> None:
        self.pattern = pattern
        self._compiled = re.compile(pattern, flags)

    async def evaluate(self, output: Output, context: EvalContext) -> AssertionResult:
        passed = bool(self._compiled.search(output.text))
        return AssertionResult(
            passed=passed,
            name="regex_match",
            score=float(passed),
            reason="" if passed else f"Pattern '{self.pattern}' not found in output",
        )
