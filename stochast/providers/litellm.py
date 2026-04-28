from __future__ import annotations

import os

from stochast._core.exceptions import ConfigurationError, ProviderError
from stochast._core.types import Output, TokenUsage


def _build_messages(prompt: str, system: str | None) -> list[dict]:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    return messages


def _openai_usage(usage) -> TokenUsage | None:
    if usage is None:
        return None
    return TokenUsage(
        prompt_tokens=usage.prompt_tokens or 0,
        completion_tokens=usage.completion_tokens or 0,
    )


class LiteLLMAdapter:
    """Provider adapter backed by LiteLLM — supports 100+ models with one interface.

    Examples:
        LiteLLMAdapter("gemini/gemini-2.5-flash")
        LiteLLMAdapter("anthropic/claude-sonnet-4-6")
        LiteLLMAdapter("ollama/llama3")
        LiteLLMAdapter("gpt-4o-mini")

    API keys are read from environment variables per LiteLLM conventions
    (GEMINI_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.) or can be
    passed as extra kwargs: LiteLLMAdapter("gpt-4o", api_key="sk-...").
    """

    def __init__(
        self,
        model: str,
        temperature: float = 0.9,
        **default_kwargs,
    ) -> None:
        self.model = model
        self._default_temperature = temperature
        self._default_kwargs = default_kwargs
        self._litellm = None

    def _get_litellm(self):
        if self._litellm is None:
            try:
                import litellm
                self._litellm = litellm
            except ImportError:
                raise ImportError(
                    "LiteLLMAdapter requires litellm. "
                    "Install with: pip install litellm"
                )
        return self._litellm

    async def __call__(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float | None = None,
        **kwargs,
    ) -> Output:
        litellm = self._get_litellm()
        t = temperature if temperature is not None else self._default_temperature
        try:
            response = await litellm.acompletion(
                model=self.model,
                messages=_build_messages(prompt, system),
                temperature=t,
                **{**self._default_kwargs, **kwargs},
            )
            return Output(
                text=response.choices[0].message.content or "",
                raw=response,
                usage=_openai_usage(response.usage),
            )
        except Exception as exc:
            raise ProviderError(f"LiteLLM call failed ({self.model}): {exc}") from exc
