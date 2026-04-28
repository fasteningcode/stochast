from __future__ import annotations

import json
from typing import Type

from pydantic import BaseModel, ValidationError

from stochast._core.types import AssertionResult, EvalContext, Output


class SchemaValidator:
    def __init__(self, model: Type[BaseModel]) -> None:
        self.model = model

    async def evaluate(self, output: Output, context: EvalContext) -> AssertionResult:
        try:
            data = output.raw if isinstance(output.raw, dict) else json.loads(output.text)
            self.model.model_validate(data)
            return AssertionResult(passed=True, name="schema_validator", score=1.0)
        except ValidationError as exc:
            errors = "; ".join(
                f"{'.'.join(str(l) for l in e['loc'])}: {e['msg']}"
                for e in exc.errors()
            )
            return AssertionResult(
                passed=False,
                name="schema_validator",
                score=0.0,
                reason=f"Schema validation failed: {errors}",
            )
        except (json.JSONDecodeError, TypeError) as exc:
            return AssertionResult(
                passed=False,
                name="schema_validator",
                score=0.0,
                reason=f"Could not parse output as JSON: {exc}",
            )
