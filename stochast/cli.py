from __future__ import annotations

import asyncio
import importlib.util
import os
import sys
import time
from pathlib import Path

import click

from stochast._core.types import StochasticResult
from stochast._registry import clear as clear_registry, get_registered
from stochast.runner.stat_runner import StatRunner


def _discover_test_files(paths: tuple[str, ...]) -> list[Path]:
    roots = [Path(p) for p in paths] if paths else [Path("tests")]
    files: list[Path] = []
    for root in roots:
        if root.is_file() and root.suffix == ".py":
            files.append(root)
        elif root.is_dir():
            files.extend(
                f for f in sorted(root.rglob("*.py"))
                if f.stem.startswith("test_") or f.stem.endswith("_test")
            )
    return list(dict.fromkeys(files))


def _load_file(path: Path) -> None:
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec and spec.loader:
        module = importlib.util.module_from_spec(spec)
        sys.modules[path.stem] = module
        spec.loader.exec_module(module)  # type: ignore[union-attr]


def _emit_github_annotations(results: list[StochasticResult]) -> None:
    for r in results:
        if not r.passed:
            print(
                f"::error title=Stochast FAIL::{r.test_name}: "
                f"pass rate {r.pass_rate:.1%} < threshold {r.threshold:.0%}"
            )


@click.group()
def main():
    """Stochast — statistical testing for non-deterministic AI systems."""


@main.command()
@click.argument("paths", nargs=-1)
@click.option("--runs", "-n", default=None, type=int, help="Override default run count.")
@click.option("--threshold", "-t", default=None, type=float, help="Override pass-rate threshold.")
@click.option("--concurrency", "-c", default=10, type=int, help="Max parallel LLM calls.")
@click.option("--junit-xml", default=None, help="Write JUnit XML to this path.")
@click.option("--json-out", default=None, help="Write JSON results to this path.")
@click.option("--filter", "name_filter", default=None, help="Only run tests matching this substring.")
@click.option("--fail-fast", is_flag=True, default=False, help="Stop after first failure.")
def run(
    paths: tuple[str, ...],
    runs: int | None,
    threshold: float | None,
    concurrency: int,
    junit_xml: str | None,
    json_out: str | None,
    name_filter: str | None,
    fail_fast: bool,
) -> None:
    """Discover and run stochastic AI tests."""
    clear_registry()
    files = _discover_test_files(paths)

    if not files:
        click.echo("No test files found.", err=True)
        sys.exit(5)

    for f in files:
        _load_file(f)

    registered = get_registered()
    if name_filter:
        registered = [t for t in registered if name_filter in t["name"]]

    if not registered:
        click.echo("No @stochast.test functions found.", err=True)
        sys.exit(5)

    start = time.monotonic()
    results = asyncio.run(_run_all(registered, runs, threshold, concurrency, fail_fast))
    duration_s = time.monotonic() - start

    from stochast.reporters import terminal, junit, json_reporter
    terminal.render(results, duration_s)

    if os.environ.get("GITHUB_ACTIONS"):
        _emit_github_annotations(results)

    if junit_xml:
        junit.write(results, junit_xml, duration_s)

    if json_out:
        json_reporter.write(results, json_out, duration_s)

    sys.exit(1 if any(not r.passed for r in results) else 0)


async def _run_all(
    registered: list[dict],
    runs_override: int | None,
    threshold_override: float | None,
    concurrency: int,
    fail_fast: bool,
) -> list[StochasticResult]:
    runner = StatRunner(max_concurrency=concurrency)

    async def _make_coro(entry: dict) -> StochasticResult:
        async def _test_fn(ctx, _fn=entry["fn"]):
            return await _fn(ctx)

        return await runner.run(
            test_name=entry["name"],
            test_fn=_test_fn,
            runs=runs_override if runs_override is not None else entry["runs"],
            threshold=threshold_override if threshold_override is not None else entry["threshold"],
            default_provider=entry["provider"],
        )

    if fail_fast:
        results: list[StochasticResult] = []
        for entry in registered:
            result = await _make_coro(entry)
            results.append(result)
            if not result.passed:
                break
        return results

    return list(await asyncio.gather(*[_make_coro(e) for e in registered]))


if __name__ == "__main__":
    main()
