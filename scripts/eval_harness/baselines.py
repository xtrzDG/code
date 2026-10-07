"""
Baselines (evals/baselines/<model>.json): what a model scored when the
baseline was accepted, scenario by scenario and criterion by criterion, so
a later run of any subset compares against the same scenarios and fails
when its pass rate (pass^k) dropped by more than the tolerance, or any
criterion's pass rate by more than the criterion tolerance (3 points by
default for both: a live model's drift shows before it costs a customer).
"""

from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel, Field

from scripts.eval_harness.run_results import ScenarioResult
from scripts.eval_harness.run_summary import RunSummary, ratio

DEFAULT_TOLERANCE: float = 0.03
DEFAULT_CRITERION_TOLERANCE: float = 0.03


class Baseline(BaseModel):
    assistant_model: str
    judge_model: str | None = None
    samples: int
    pass_rate: float
    pass_at_1: float
    criteria: dict[str, float] = Field(default_factory=dict[str, float])
    scenarios: dict[str, bool] = Field(default_factory=dict[str, bool])
    # Scenario key -> criterion -> share of its samples that passed it.
    scenario_criteria: dict[str, dict[str, float]] = Field(
        default_factory=dict[str, dict[str, float]]
    )


class BaselineDiff(BaseModel):
    baseline_pass_rate: float
    pass_rate: float
    delta: float
    tolerance: float
    is_regression: bool
    compared_scenarios: int
    newly_failing: list[str] = Field(default_factory=list[str])
    newly_passing: list[str] = Field(default_factory=list[str])
    criteria_deltas: dict[str, float] = Field(default_factory=dict[str, float])
    criterion_tolerance: float = DEFAULT_CRITERION_TOLERANCE
    regressed_criteria: list[str] = Field(default_factory=list[str])


def baseline_path(directory: Path, assistant_model: str) -> Path:
    return directory / f"{assistant_model}.json"


def read_baseline(path: Path) -> Baseline | None:
    if not path.exists():
        return None

    return Baseline.model_validate_json(path.read_text(encoding="utf-8"))


def write_baseline(path: Path, baseline: Baseline) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(baseline.model_dump_json(indent=2) + "\n", encoding="utf-8")


def build_baseline(
    summary: RunSummary,
    scenarios: Sequence[ScenarioResult],
    assistant_model: str,
    judge_model: str | None,
    samples: int,
) -> Baseline:
    return Baseline(
        assistant_model=assistant_model,
        judge_model=judge_model,
        samples=samples,
        pass_rate=summary.pass_rate,
        pass_at_1=summary.pass_at_1,
        criteria={item.criterion: item.rate for item in summary.criteria},
        scenarios={scenario.key: scenario.is_passed for scenario in scenarios},
        scenario_criteria={
            scenario.key: criterion_rates(scenario) for scenario in scenarios
        },
    )


def criterion_rates(scenario: ScenarioResult) -> dict[str, float]:
    """Each criterion the scenario checked and the share of samples passing it."""

    checked: dict[str, int] = {}
    passed: dict[str, int] = {}
    for sample in scenario.samples:
        for result in sample.criteria:
            name: str = result.criterion.value
            checked[name] = checked.get(name, 0) + 1
            passed[name] = passed.get(name, 0) + int(result.is_passed)

    return {name: ratio(passed[name], count) for name, count in checked.items()}


def compare_with_baseline(
    baseline: Baseline,
    summary: RunSummary,
    scenarios: Sequence[ScenarioResult],
    tolerance: float = DEFAULT_TOLERANCE,
    criterion_tolerance: float = DEFAULT_CRITERION_TOLERANCE,
) -> BaselineDiff:
    """
    The pass rate over the scenarios both runs have, its change, the
    scenarios that flipped and each criterion's change over the scenarios
    both runs checked it in. A regression is a drop beyond the tolerance
    of the pass rate or of any criterion.
    """

    shared: list[ScenarioResult] = [
        scenario for scenario in scenarios if scenario.key in baseline.scenarios
    ]
    baseline_rate: float = ratio(
        sum(1 for scenario in shared if baseline.scenarios[scenario.key]), len(shared)
    )
    current_rate: float = ratio(
        sum(1 for scenario in shared if scenario.is_passed), len(shared)
    )
    delta: float = round(current_rate - baseline_rate, 4)
    criteria_deltas: dict[str, float] = (
        compare_criteria(baseline, shared)
        if baseline.scenario_criteria
        # An older baseline has whole-run rates only: same set or nothing.
        else {
            item.criterion: round(item.rate - baseline.criteria[item.criterion], 4)
            for item in summary.criteria
            if item.criterion in baseline.criteria
        }
        if len(shared) == len(baseline.scenarios) == len(scenarios)
        else {}
    )
    regressed: list[str] = sorted(
        name
        for name, change in criteria_deltas.items()
        if change < -criterion_tolerance
    )
    return BaselineDiff(
        baseline_pass_rate=baseline_rate,
        pass_rate=current_rate,
        delta=delta,
        tolerance=tolerance,
        is_regression=delta < -tolerance or bool(regressed),
        compared_scenarios=len(shared),
        newly_failing=[
            scenario.key
            for scenario in shared
            if baseline.scenarios[scenario.key] and not scenario.is_passed
        ],
        newly_passing=[
            scenario.key
            for scenario in shared
            if not baseline.scenarios[scenario.key] and scenario.is_passed
        ],
        criteria_deltas=criteria_deltas,
        criterion_tolerance=criterion_tolerance,
        regressed_criteria=regressed,
    )


def compare_criteria(
    baseline: Baseline, shared: Sequence[ScenarioResult]
) -> dict[str, float]:
    """Each criterion's mean rate change over the scenarios both runs checked."""

    before: dict[str, list[float]] = {}
    after: dict[str, list[float]] = {}
    for scenario in shared:
        accepted: dict[str, float] = baseline.scenario_criteria.get(scenario.key, {})
        for name, rate in criterion_rates(scenario).items():
            if name in accepted:
                before.setdefault(name, []).append(accepted[name])
                after.setdefault(name, []).append(rate)

    return {
        name: round(sum(after[name]) / len(after[name]) - sum(rates) / len(rates), 4)
        for name, rates in sorted(before.items())
    }
