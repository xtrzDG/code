"""
Baselines (evals/baselines/<model>.json): what a model scored when the
baseline was accepted, scenario by scenario, so a later run of any subset
compares against the same scenarios and fails when its pass rate dropped
by more than the tolerance.
"""

from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel, Field

from scripts.eval_harness.run_results import ScenarioResult
from scripts.eval_harness.run_summary import RunSummary, ratio

DEFAULT_TOLERANCE: float = 0.05


class Baseline(BaseModel):
    assistant_model: str
    judge_model: str | None = None
    samples: int
    pass_rate: float
    pass_at_1: float
    criteria: dict[str, float] = Field(default_factory=dict[str, float])
    scenarios: dict[str, bool] = Field(default_factory=dict[str, bool])


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
    )


def compare_with_baseline(
    baseline: Baseline,
    summary: RunSummary,
    scenarios: Sequence[ScenarioResult],
    tolerance: float = DEFAULT_TOLERANCE,
) -> BaselineDiff:
    """
    The pass rate over the scenarios both runs have, its change, and the
    scenarios that flipped. A regression is a drop beyond the tolerance.
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
    return BaselineDiff(
        baseline_pass_rate=baseline_rate,
        pass_rate=current_rate,
        delta=delta,
        tolerance=tolerance,
        is_regression=delta < -tolerance,
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
        # Criterion rates are whole-run numbers: compared only over the same set.
        criteria_deltas=(
            {
                item.criterion: round(item.rate - baseline.criteria[item.criterion], 4)
                for item in summary.criteria
                if item.criterion in baseline.criteria
            }
            if len(shared) == len(baseline.scenarios) == len(scenarios)
            else {}
        ),
    )
