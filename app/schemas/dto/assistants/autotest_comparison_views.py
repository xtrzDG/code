"""
How an autotest run compares with the run of the version that was live
when it started: what broke, what got fixed and where the judge's scores
moved (the version page shows it before the owner publishes).
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.assistants import (
    AutotestCheckCode,
    AutotestOutcome,
    AutotestScenarioKind,
    JudgeCriterion,
)
from app.schemas.typings.assistants.constrained_floats import (
    AverageJudgeScore,
    AverageJudgeScoreChange,
)
from app.schemas.typings.assistants.constrained_integers import (
    AssistantVersionNumber,
    AutotestScenarioCount,
)
from app.schemas.typings.assistants.constrained_strings import AutotestScenarioKey
from app.schemas.typings.assistants.prefixed_id import (
    AssistantVersionId,
    AutotestCaseId,
    AutotestRunId,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag


class AutotestOutcomeChangeView(ImmutableDTO):
    """
    A scenario played by both runs whose outcome changed: a new failure
    (passed on the live version, not now) or a fix (the other way round).
    """

    scenario_key: AutotestScenarioKey
    kind: AutotestScenarioKind
    language: LanguageTag
    outcome: AutotestOutcome
    baseline_outcome: AutotestOutcome
    # The deterministic checks this run's play failed (empty for a fix).
    check_codes: list[AutotestCheckCode] = Field(
        default_factory=list[AutotestCheckCode]
    )
    autotest_case_id: AutotestCaseId | None = None


class AutotestScoreChangeView(ImmutableDTO):
    """A scenario whose average judge score moved by half a point or more."""

    scenario_key: AutotestScenarioKey
    kind: AutotestScenarioKind
    language: LanguageTag
    average_score: AverageJudgeScore
    baseline_average_score: AverageJudgeScore
    change: AverageJudgeScoreChange


class AutotestCriterionChangeView(ImmutableDTO):
    """The average score of one judge criterion over the shared scenarios."""

    criterion: JudgeCriterion
    average_score: AverageJudgeScore
    baseline_average_score: AverageJudgeScore
    change: AverageJudgeScoreChange


class AutotestRunComparisonView(ImmutableDTO):
    """
    This run against the live version's run. Only scenarios both runs
    played (`shared_scenario_count`) are compared; scenarios new to this
    run are in the run's own results.
    """

    baseline_run_id: AutotestRunId
    baseline_version_id: AssistantVersionId
    baseline_version_number: AssistantVersionNumber
    baseline_average_score: AverageJudgeScore | None = None
    average_score_change: AverageJudgeScoreChange | None = None
    shared_scenario_count: AutotestScenarioCount
    new_failures: list[AutotestOutcomeChangeView]
    fixed: list[AutotestOutcomeChangeView]
    score_changes: list[AutotestScoreChangeView]
    criterion_changes: list[AutotestCriterionChangeView]
