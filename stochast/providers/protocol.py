from __future__ import annotations

from typing import Protocol, runtime_checkable

from stochast._core.types import Output


@runtime_checkable
class ProviderAdapter(Protocol):
    async def __call__(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float = 0.9,
        **kwargs,
    ) -> Output:
        ...
