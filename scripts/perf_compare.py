"""
Compare a perf report (tests/perf with PERF_REPORT) with the stored
baseline, as the weekly perf run does (.github/workflows/perf.yml):

    uv run python -m scripts.perf_compare perf/results/latest.json \\
        perf/baseline.json
    uv run python -m scripts.perf_compare REPORT BASELINE --update

A request kind regresses when its p95 is more than 20% above the
baseline's (and more than 1 ms, below which timer noise dominates). Exit
codes: 0 within the baseline, 1 a regression or a measured kind missing
from the report, 2 the files do not fit (unreadable, another scale).
`--update` stores the report's p95s as the new baseline instead (review
the change like code: a slower baseline needs a reason). The comparison
is printed as a Markdown table for the job summary.
"""

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ALLOWED_REGRESSION: float = 0.20
NOISE_FLOOR_MS: float = 1.0
EXIT_OK: int = 0
EXIT_REGRESSED: int = 1
EXIT_UNUSABLE: int = 2


@dataclass(frozen=True)
class Comparison:
    """One request kind: its baseline and measured p95 in ms."""

    name: str
    baseline_ms: float | None
    measured_ms: float | None

    @property
    def is_regression(self) -> bool:
        if self.baseline_ms is None:
            return False

        if self.measured_ms is None:
            return True

        limit: float = self.baseline_ms * (1 + ALLOWED_REGRESSION)
        return (
            self.measured_ms > limit
            and self.measured_ms - self.baseline_ms > NOISE_FLOOR_MS
        )

    def describe(self) -> str:
        baseline: str = "new" if self.baseline_ms is None else f"{self.baseline_ms:.1f}"
        measured: str = "missing" if self.measured_ms is None else (
            f"{self.measured_ms:.1f}"
        )
        change: str = ""
        if self.baseline_ms and self.measured_ms is not None:
            change = f"{(self.measured_ms / self.baseline_ms - 1) * 100:+.0f}%"

        verdict: str = "regression" if self.is_regression else "ok"
        return f"| {self.name} | {baseline} | {measured} | {change} | {verdict} |"


def compare(report: dict[str, Any], baseline: dict[str, Any]) -> list[Comparison]:
    measured: dict[str, float] = {
        name: float(result["p95_ms"]) for name, result in report["results"].items()
    }
    stored: dict[str, float] = {
        name: float(value) for name, value in baseline["p95_ms"].items()
    }
    return [
        Comparison(name, stored.get(name), measured.get(name))
        for name in sorted(set(measured) | set(stored))
    ]


def build_baseline(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "scale": report["scale"]["name"],
        "p95_ms": {
            name: round(float(result["p95_ms"]), 1)
            for name, result in sorted(report["results"].items())
        },
    }


def render(comparisons: list[Comparison], scale: str) -> str:
    lines: list[str] = [
        f"### Perf: p95 against the baseline ({scale} scale)",
        "",
        "| request | baseline ms | measured ms | change | verdict |",
        "| --- | ---: | ---: | ---: | --- |",
        *(comparison.describe() for comparison in comparisons),
    ]
    return "\n".join(lines)


def main(arguments: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="perf_compare")
    parser.add_argument("report", type=Path)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("--update", action="store_true")
    parsed: argparse.Namespace = parser.parse_args(arguments)
    try:
        report: dict[str, Any] = json.loads(parsed.report.read_text())
        if parsed.update:
            baseline_text = json.dumps(build_baseline(report), indent=2) + "\n"
            parsed.baseline.write_text(baseline_text)
            print(f"Baseline written to {parsed.baseline}.")
            return EXIT_OK

        baseline: dict[str, Any] = json.loads(parsed.baseline.read_text())
        scale: str = str(report["scale"]["name"])
        if scale != baseline["scale"]:
            print(
                f"The report is of the {scale} scale, the baseline of "
                f"{baseline['scale']}: run the same scale or --update.",
                file=sys.stderr,
            )
            return EXIT_UNUSABLE

        comparisons: list[Comparison] = compare(report, baseline)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"Cannot compare: {error!r}", file=sys.stderr)
        return EXIT_UNUSABLE

    print(render(comparisons, scale))
    if any(comparison.is_regression for comparison in comparisons):
        return EXIT_REGRESSED

    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
