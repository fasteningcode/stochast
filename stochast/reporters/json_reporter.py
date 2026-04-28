from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from stochast._core.types import StochasticResult
from stochast.reporters._utils import ensure_parent


def write(results: list[StochasticResult], path: str | Path, duration_s: float) -> None:
    passed = sum(1 for r in results if r.passed)
    data = {
        "schema_version": "1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total": len(results),
            "passed": passed,
            "failed": len(results) - passed,
            "duration_seconds": round(duration_s, 3),
            "total_cost_usd": round(sum(r.total_cost_usd for r in results), 6),
        },
        "tests": [_serialize(r) for r in results],
    }
    ensure_parent(path).write_text(json.dumps(data, indent=2))


def _serialize(r: StochasticResult) -> dict:
    return {
        "name": r.test_name,
        "status": "PASS" if r.passed else "FAIL",
        "pass_rate": round(r.pass_rate, 4),
        "threshold": r.threshold,
        "runs": r.runs,
        "passed_count": r.passed_count,
        "mean_latency_ms": round(r.mean_latency_ms, 1),
        "total_cost_usd": round(r.total_cost_usd, 6),
        "run_details": [
            {
                "run_index": run.run_index,
                "passed": run.passed,
                "latency_ms": round(run.latency_ms, 1),
                "error": run.error,
                "assertions": [
                    {
                        "name": ar.name,
                        "passed": ar.passed,
                        "score": round(ar.score, 4),
                        "reason": ar.reason,
                    }
                    for ar in run.assertion_results
                ],
            }
            for run in r.run_results
        ],
    }
