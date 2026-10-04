"""
The numbers of a run: pass^k (a scenario counts only when every sample
passed), pass@1 (the share of passed samples), per-criterion pass rates,
judge averages, pass rates per niche and language, list-price cost and
the p50/p95 model latency of the assistant's turns.
"""

import math
from collections import defaultdict
from collections.abc import Sequence

from pydantic import BaseModel, Field

from scripts.eval_harness.run_results import SampleResult, ScenarioResult

MICRO_USD_PER_USD: int = 1_000_000


class CriterionSummary(BaseModel):
    criterion: str
    checked: int
    passed: int
    rate: float


class GroupSummary(BaseModel):
    niche: str
    language: str
    scenarios: int
    passed: int
    pass_rate: float


class RunSummary(BaseModel):
    scenario_count: int
    passed_count: int
    pass_rate: float
    pass_at_1: float
    stale_count: int
    errored_count: int
    cost_usd: float
    latency_p50_ms: int
    latency_p95_ms: int
    criteria: list[CriterionSummary] = Field(default_factory=list[CriterionSummary])
    judge_averages: dict[str, float] = Field(default_factory=dict[str, float])
    groups: list[GroupSummary] = Field(default_factory=list[GroupSummary])


def summarize(scenarios: Sequence[ScenarioResult]) -> RunSummary:
    samples: list[SampleResult] = [
        sample for scenario in scenarios for sample in scenario.samples
    ]
    passed: int = sum(1 for scenario in scenarios if scenario.is_passed)
    latencies: list[int] = [
        latency for sample in samples for latency in sample.turn_latencies_ms
    ]
    return RunSummary(
        scenario_count=len(scenarios),
        passed_count=passed,
        pass_rate=ratio(passed, len(scenarios)),
        pass_at_1=ratio(sum(1 for sample in samples if sample.is_passed), len(samples)),
        stale_count=sum(1 for scenario in scenarios if scenario.is_stale),
        errored_count=sum(
            1 for scenario in scenarios if any(s.error for s in scenario.samples)
        ),
        cost_usd=sum(sample.cost_micro_usd for sample in samples) / MICRO_USD_PER_USD,
        latency_p50_ms=percentile(latencies, 50),
        latency_p95_ms=percentile(latencies, 95),
        criteria=summarize_criteria(samples),
        judge_averages=average_judge_scores(samples),
        groups=summarize_groups(scenarios),
    )


def ratio(part: int, whole: int) -> float:
    return round(part / whole, 4) if whole else 0.0


def percentile(values: Sequence[int], rank: int) -> int:
    """Nearest-rank percentile; 0 for no values."""

    if not values:
        return 0

    ordered: list[int] = sorted(values)
    index: int = max(0, math.ceil(rank / 100 * len(ordered)) - 1)
    return ordered[index]


def summarize_criteria(samples: Sequence[SampleResult]) -> list[CriterionSummary]:
    checked: dict[str, int] = defaultdict(int)
    passed: dict[str, int] = defaultdict(int)
    for sample in samples:
        for result in sample.criteria:
            checked[result.criterion.value] += 1
            passed[result.criterion.value] += int(result.is_passed)

    return [
        CriterionSummary(
            criterion=criterion,
            checked=count,
            passed=passed[criterion],
            rate=ratio(passed[criterion], count),
        )
        for criterion, count in checked.items()
    ]


def average_judge_scores(samples: Sequence[SampleResult]) -> dict[str, float]:
    scores: dict[str, list[int]] = defaultdict(list)
    for sample in samples:
        if sample.judge is None:
            continue

        for criterion, score in sample.judge.scores.items():
            scores[criterion].append(score)

    return {
        criterion: round(sum(values) / len(values), 2)
        for criterion, values in sorted(scores.items())
    }


def summarize_groups(scenarios: Sequence[ScenarioResult]) -> list[GroupSummary]:
    groups: dict[tuple[str, str], list[ScenarioResult]] = defaultdict(list)
    for scenario in scenarios:
        groups[(scenario.niche, scenario.language)].append(scenario)

    return [
        GroupSummary(
            niche=niche,
            language=language,
            scenarios=len(members),
            passed=sum(1 for member in members if member.is_passed),
            pass_rate=ratio(sum(1 for m in members if m.is_passed), len(members)),
        )
        for (niche, language), members in sorted(groups.items())
    ]
