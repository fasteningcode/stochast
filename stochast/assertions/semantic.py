from __future__ import annotations

import asyncio

from stochast._core.types import AssertionResult, EvalContext, Output


class SemanticSimilarity:
    """Cosine similarity between output and reference using sentence-transformers."""

    def __init__(
        self,
        reference: str,
        threshold: float = 0.80,
        model: str = "all-MiniLM-L6-v2",
    ) -> None:
        self.reference = reference
        self.threshold = threshold
        self.model_name = model
        self._encoder = None
        self._ref_embedding = None

    def _get_encoder(self):
        if self._encoder is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._encoder = SentenceTransformer(self.model_name)
            except ImportError:
                raise ImportError(
                    "SemanticSimilarity requires sentence-transformers. "
                    "Install with: pip install stochast[semantic]"
                )
        return self._encoder

    async def evaluate(self, output: Output, context: EvalContext) -> AssertionResult:
        import numpy as np

        encoder = self._get_encoder()
        loop = asyncio.get_running_loop()

        if self._ref_embedding is None:
            self._ref_embedding = await loop.run_in_executor(
                None, lambda: encoder.encode([self.reference])[0]
            )

        ref = self._ref_embedding

        def _compute() -> float:
            a = encoder.encode([output.text])[0]
            return float(np.dot(a, ref) / (np.linalg.norm(a) * np.linalg.norm(ref)))

        score = await loop.run_in_executor(None, _compute)
        passed = score >= self.threshold
        return AssertionResult(
            passed=passed,
            name="semantic_similarity",
            score=score,
            reason="" if passed else f"Similarity {score:.3f} below threshold {self.threshold}",
        )
