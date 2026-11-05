"""Timing requests and keeping the results the weekly run compares."""

import json
import statistics
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path

from tests.perf.perf_scale import PerfScale

WARM_UP_RUNS: int = 20
MEASURED_RUNS: int = 200


@dataclass(frozen=True)
class LatencyResult:
    """One measured request kind: its p50 and p95 and its budget, in ms."""

    runs: int
    p50_ms: float
    p95_ms: float
    budget_ms: float


@dataclass
class PerfReport:
    """Everything one perf session measured (written to PERF_REPORT)."""

    scale: PerfScale
    seed_seconds: float = 0.0
    results: dict[str, LatencyResult] = field(default_factory=dict[str, LatencyResult])

    def record(
        self, name: str, durations_ms: list[float], budget_ms: float
    ) -> LatencyResult:
        result = LatencyResult(
            runs=len(durations_ms),
            p50_ms=round(statistics.median(durations_ms), 3),
            p95_ms=round(percentile(durations_ms, 95), 3),
            budget_ms=budget_ms,
        )
        self.results[name] = result
        return result

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        document = {
            "scale": asdict(self.scale),
            "seed_seconds": round(self.seed_seconds, 1),
            "results": {name: asdict(result) for name, result in self.results.items()},
        }
        path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n")


def percentile(values: list[float], rank: int) -> float:
    """The `rank`-th percentile, interpolated between the measured values."""

    if len(values) == 1:
        return values[0]

    return statistics.quantiles(values, n=100, method="inclusive")[rank - 1]


def measure(
    send: Callable[[int], int],
    runs: int = MEASURED_RUNS,
    warm_up: int = WARM_UP_RUNS,
) -> list[float]:
    """
    Durations in ms of `runs` calls of `send(i)` after `warm_up` untimed
    ones; every call must answer 200 (`send` returns the status code).
    """

    for index in range(warm_up):
        status: int = send(index)
        assert status == 200, f"warm-up request {index} answered {status}"

    durations: list[float] = []
    for index in range(warm_up, warm_up + runs):
        started: float = time.perf_counter()
        status = send(index)
        durations.append((time.perf_counter() - started) * 1000)
        assert status == 200, f"request {index} answered {status}"

    return durations
