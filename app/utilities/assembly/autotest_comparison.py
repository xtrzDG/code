"""
Compare an autotest run with the live version's run (the version page's
"against the live version" card).

Scenarios are matched by key ("booking__ka", "price_question__en__2", an
owner check's key): only scenarios both runs played are compared. A new
failure passed on the live version and did not pass now; a fix is the
other way round. A scenario's score change is the move of its average
judge score by at least half a point, worst first; the criteria are
averaged over the shared scenarios both runs scored.
"""

from collections.abc import Sequence

from app.schemas.constants.assistants import AutotestOutcome, JudgeCriterion
from app.schemas.domain.assistants import (
    AssistantVersionDocument,
    AutotestRunDocument,
    AutotestScenarioResult,
)
from app.schemas.dto.assistants.autotest_comparison_views import (
    AutotestCriterionChangeView,
    AutotestOutcomeChangeView,
    AutotestRunComparisonView,
    AutotestScoreChangeView,
)
from app.schemas.typings.assistants.constrained_floats import (
    AverageJudgeScore,
    AverageJudgeScoreChange,
)
from app.schemas.typings.assistants.constrained_integers import AutotestScenarioCount

SCORE_CHANGE_THRESHOLD: float = 0.5
CHANGE_DECIMALS: int = 2

type ResultPair = tuple[AutotestScenarioResult, AutotestScenarioResult]


def compare_runs(
    run: AutotestRunDocument,
    baseline_run: AutotestRunDocument,
    baseline_version: AssistantVersionDocument,
) -> AutotestRunComparisonView:
    """`run` against `baseline_run`, the run of `baseline_version`."""

    baseline_results: dict[str, AutotestScenarioResult] = {
        str(result.scenario_key): result for result in baseline_run.results
    }
    shared: list[ResultPair] = [
        (result, baseline_results[str(result.scenario_key)])
        for result in run.results
        if str(result.scenario_key) in baseline_results
    ]
    return AutotestRunComparisonView(
        baseline_run_id=baseline_run.id,
        baseline_version_id=baseline_version.id,
        baseline_version_number=baseline_version.version_number,
        baseline_average_score=baseline_run.average_score,
        average_score_change=(
            score_change(float(run.average_score), float(baseline_run.average_score))
            if run.average_score is not None and baseline_run.average_score is not None
            else None
        ),
        shared_scenario_count=AutotestScenarioCount(len(shared)),
        new_failures=[
            outcome_change(result, baseline)
            for result, baseline in shared
            if result.outcome is not AutotestOutcome.PASSED
            and baseline.outcome is AutotestOutcome.PASSED
        ],
        fixed=[
            outcome_change(result, baseline)
            for result, baseline in shared
            if result.outcome is AutotestOutcome.PASSED
            and baseline.outcome is not AutotestOutcome.PASSED
        ],
        score_changes=collect_score_changes(shared),
        criterion_changes=collect_criterion_changes(shared),
    )


def outcome_change(
    result: AutotestScenarioResult, baseline: AutotestScenarioResult
) -> AutotestOutcomeChangeView:
    return AutotestOutcomeChangeView(
        scenario_key=result.scenario_key,
        kind=result.kind,
        language=result.language,
        outcome=result.outcome,
        baseline_outcome=baseline.outcome,
        check_codes=list(result.check_codes),
        autotest_case_id=result.autotest_case_id,
    )


def collect_score_changes(
    shared: Sequence[ResultPair],
) -> list[AutotestScoreChangeView]:
    changes: list[AutotestScoreChangeView] = []
    for result, baseline in shared:
        now: float | None = mean_score(result)
        before: float | None = mean_score(baseline)
        if now is None or before is None:
            continue

        if abs(now - before) >= SCORE_CHANGE_THRESHOLD:
            changes.append(
                AutotestScoreChangeView(
                    scenario_key=result.scenario_key,
                    kind=result.kind,
                    language=result.language,
                    average_score=AverageJudgeScore(round(now, CHANGE_DECIMALS)),
                    baseline_average_score=AverageJudgeScore(
                        round(before, CHANGE_DECIMALS)
                    ),
                    change=score_change(now, before),
                )
            )

    return sorted(changes, key=lambda change: float(change.change))


def collect_criterion_changes(
    shared: Sequence[ResultPair],
) -> list[AutotestCriterionChangeView]:
    changes: list[AutotestCriterionChangeView] = []
    for criterion in JudgeCriterion:
        now: list[int] = []
        before: list[int] = []
        for result, baseline in shared:
            now_score: int | None = criterion_score(result, criterion)
            before_score: int | None = criterion_score(baseline, criterion)
            if now_score is not None and before_score is not None:
                now.append(now_score)
                before.append(before_score)

        if now:
            now_mean: float = sum(now) / len(now)
            before_mean: float = sum(before) / len(before)
            changes.append(
                AutotestCriterionChangeView(
                    criterion=criterion,
                    average_score=AverageJudgeScore(round(now_mean, CHANGE_DECIMALS)),
                    baseline_average_score=AverageJudgeScore(
                        round(before_mean, CHANGE_DECIMALS)
                    ),
                    change=score_change(now_mean, before_mean),
                )
            )

    return changes


def mean_score(result: AutotestScenarioResult) -> float | None:
    if not result.scores:
        return None

    return sum(int(score.score) for score in result.scores) / len(result.scores)


def criterion_score(
    result: AutotestScenarioResult, criterion: JudgeCriterion
) -> int | None:
    return next(
        (int(score.score) for score in result.scores if score.criterion is criterion),
        None,
    )


def score_change(now: float, before: float) -> AverageJudgeScoreChange:
    return AverageJudgeScoreChange(round(now - before, CHANGE_DECIMALS))
