from __future__ import annotations

from stochast._core.types import StochasticResult


def render(results: list[StochasticResult], duration_s: float) -> None:
    try:
        import rich  # noqa: F401 — presence check only; Console imported inside _render_rich
        _render_rich(results, duration_s)
    except ImportError:
        _render_plain(results, duration_s)


def _bar(passed: int, total: int, width: int = 28) -> str:
    filled = int((passed / total) * width) if total else 0
    return "█" * filled + "░" * (width - filled)


def _render_rich(results: list[StochasticResult], duration_s: float) -> None:
    from rich.console import Console

    console = Console()
    console.print()

    for r in results:
        status = "[bold green]✓ PASS[/]" if r.passed else "[bold red]✗ FAIL[/]"
        console.print(f" [dim]Running[/] [bold]{r.test_name}[/]  {r.runs}/{r.runs} runs")
        console.print(
            f"   [cyan]{_bar(r.passed_count, r.runs)}[/]  {r.passed_count}/{r.runs} passed  "
            f"([bold]{r.pass_rate:.1%}[/])  threshold: {r.threshold:.0%}  {status}"
        )
        if not r.passed:
            errors = [run for run in r.run_results if run.error]
            failures = [run for run in r.run_results if not run.passed and not run.error]
            if errors:
                console.print(f"   [red]Errors in runs: {[e.run_index for e in errors[:3]]}[/]")
                console.print(f"   [red dim]{errors[0].error}[/]")
            elif failures and failures[0].assertion_results:
                for ar in failures[0].assertion_results:
                    if not ar.passed and ar.reason:
                        console.print(f"   [yellow]↳ {ar.reason}[/]")
                        break
        console.print()

    total_calls = sum(r.runs for r in results)
    total_cost = sum(r.total_cost_usd for r in results)
    failed = [r for r in results if not r.passed]

    console.rule()
    cost_str = f"  •  ~${total_cost:.3f} estimated" if total_cost > 0 else ""
    console.print(
        f" [bold]{len(results)} tests[/]  •  {total_calls} LLM calls"
        f"  •  {duration_s:.1f}s{cost_str}"
    )

    if failed:
        console.print(f"\n [bold red]FAIL {len(failed)}[/]")
        for r in failed:
            console.print(
                f"   [red]{r.test_name}[/]  [dim]{r.pass_rate:.1%} < {r.threshold:.0%}[/]"
            )
    else:
        console.print(f"\n [bold green]All {len(results)} tests passed[/]")
    console.print()


def _render_plain(results: list[StochasticResult], duration_s: float) -> None:
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        print(
            f"{r.test_name}: {r.passed_count}/{r.runs} passed "
            f"({r.pass_rate:.1%}) threshold={r.threshold:.0%} [{status}]"
        )
    passed = sum(1 for r in results if r.passed)
    print(f"\n{passed}/{len(results)} tests passed in {duration_s:.1f}s")
