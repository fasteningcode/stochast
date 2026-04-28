from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from stochast._core.types import StochasticResult
from stochast.reporters._utils import ensure_parent


def write(results: list[StochasticResult], path: str | Path, duration_s: float) -> None:
    passed = sum(1 for r in results if r.passed)
    root = ET.Element("testsuites")
    root.set("name", "Stochast")
    root.set("tests", str(len(results)))
    root.set("failures", str(len(results) - passed))
    root.set("time", f"{duration_s:.3f}")

    for result in results:
        suite = ET.SubElement(root, "testsuite")
        suite.set("name", result.test_name)
        suite.set("tests", "1")
        suite.set("failures", "0" if result.passed else "1")
        suite.set("time", f"{result.mean_latency_ms / 1000:.3f}")

        testcase = ET.SubElement(suite, "testcase")
        testcase.set("name", result.test_name)
        testcase.set("classname", result.test_name)
        testcase.set("time", f"{result.mean_latency_ms / 1000:.3f}")

        if not result.passed:
            failure = ET.SubElement(testcase, "failure")
            failure.set(
                "message",
                f"Pass rate {result.pass_rate:.1%} below threshold {result.threshold:.0%}",
            )
            reasons = []
            for run in [r for r in result.run_results if not r.passed][:3]:
                if run.error:
                    reasons.append(f"run {run.run_index}: {run.error}")
                elif run.assertion_results:
                    for ar in run.assertion_results:
                        if not ar.passed and ar.reason:
                            reasons.append(f"run {run.run_index} [{ar.name}]: {ar.reason}")
                            break
            failure.text = "\n".join(reasons) if reasons else "No reason captured"

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    output_path = ensure_parent(path)
    tree.write(output_path, encoding="unicode", xml_declaration=True)
