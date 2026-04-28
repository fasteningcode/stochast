# Contributing to stochast

Thanks for your interest. This document covers how to add things to the project.

## Setup

```bash
git clone https://github.com/fasteningcode/stochast.git
cd stochast
pip install -e ".[dev]"
```

Run the tests:

```bash
pytest tests/
```

All 21 unit tests run without any API keys. They use no mocks and make no LLM calls.

---

## Adding a provider

Create a new file in `stochast/providers/`. The only contract is:

```python
class MyProviderAdapter:
    async def __call__(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float | None = None,
        **kwargs,
    ) -> Output:
        ...
```

Return an `Output(text=..., raw=..., usage=TokenUsage(...))`. Raise `ProviderError` on failure.

Then export it from `stochast/providers/__init__.py` and add the optional dependency to `pyproject.toml`.

---

## Adding an assertion strategy

Create a new file in `stochast/assertions/`. The contract:

```python
class MyAssertion:
    async def evaluate(self, output: Output, context: EvalContext) -> AssertionResult:
        ...
```

Return `AssertionResult(passed=bool, name=str, score=float, reason=str)`. Do not raise — catch exceptions internally and return a failed result with the error in `reason`.

Export from `stochast/assertions/__init__.py`.

---

## What belongs here

- New LLM providers
- New assertion strategies
- Bug fixes in the runner, reporter, or CLI
- Better statistical methods (alternatives to Wilson CI)

## What doesn't belong here

- Dashboards, UIs, or persistent backends — the framework is intentionally local-first
- Wrappers around existing tools (Langfuse, LangSmith, etc.)
- Breaking changes to the `(output, assertion)` return contract

---

## Submitting a PR

- Keep it focused. One change per PR.
- Add a test for anything new.
- Don't change `_core/types.py` without a clear reason — everything depends on it.
