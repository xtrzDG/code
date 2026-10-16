"""Which scenarios the comparison with the live run lists, and how."""

from typed_time_provider import Microseconds

from app.schemas.constants.assistants import (
    AssistantToolName,
    AssistantVersionStatus,
    AutotestOutcome,
    AutotestRunStatus,
    AutotestScenarioKind,
)
from app.schemas.constants.niches import NicheKey
from app.schemas.domain.assistants import (
    AssistantVersionDocument,
    AutotestRunDocument,
    AutotestScenarioResult,
)
from app.schemas.typings.assistants.constrained_floats import AverageJudgeScore
from app.schemas.typings.assistants.constrained_integers import AssistantVersionNumber
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.assistants.strings import SystemPromptText
from app.schemas.typings.businesses.booleans import IsVoiceEnabled
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.assembly.autotest_comparison import compare_runs
from tests.assembly.judge_helpers import result, scores

BUSINESS_ID: BusinessId = BusinessId()


def run_of(
    results: list[AutotestScenarioResult], average: float | None
) -> AutotestRunDocument:
    version = live_version()
    return AutotestRunDocument(
        business_id=BUSINESS_ID,
        assistant_version_id=version.id,
        status=AutotestRunStatus.FINISHED,
        results=results,
        average_score=AverageJudgeScore(average) if average is not None else None,
        previous_version_status=AssistantVersionStatus.DRAFT,
        created_at=Microseconds(1),
        updated_at=Microseconds(1),
    )


def live_version() -> AssistantVersionDocument:
    return AssistantVersionDocument(
        business_id=BUSINESS_ID,
        version_number=AssistantVersionNumber(3),
        status=AssistantVersionStatus.PUBLISHED,
        niche_key=NicheKey.RESTAURANT,
        model_id=LlmModelId("gpt-5-mini"),
        prompt_text=SystemPromptText("You answer customers."),
        tools=[AssistantToolName.GET_PRICE],
        languages=[LanguageTag("en")],
        default_language=LanguageTag("en"),
        is_voice_enabled=IsVoiceEnabled(False),
        facts=[],
        profile_revision=Microseconds(1),
    )


def test_errored_scenarios_count_as_new_failures_and_unshared_ones_are_skipped() -> (
    None
):
    errored = result(AutotestScenarioKind.BOOKING, AutotestOutcome.ERRORED, [])
    now = run_of(
        [
            errored,
            result(AutotestScenarioKind.EMERGENCY, AutotestOutcome.FAILED),
            result(
                AutotestScenarioKind.PRICE_QUESTION,
                AutotestOutcome.PASSED,
                scores(handoff=3),
            ),
        ],
        average=None,
    )
    before = run_of(
        [
            result(AutotestScenarioKind.BOOKING, AutotestOutcome.PASSED),
            result(
                AutotestScenarioKind.PRICE_QUESTION,
                AutotestOutcome.PASSED,
                scores(handoff=4),
            ),
        ],
        average=5.0,
    )
    version = live_version()

    comparison = compare_runs(now, before, version)

    assert comparison.shared_scenario_count == 2
    assert [change.outcome for change in comparison.new_failures] == [
        AutotestOutcome.ERRORED
    ]
    assert comparison.fixed == []
    # 4.6 against 4.8 moved less than half a point; the errored play has
    # no score to compare.
    assert comparison.score_changes == []
    assert comparison.average_score_change is None
    assert comparison.baseline_average_score == AverageJudgeScore(5.0)
    assert comparison.baseline_version_number == version.version_number
    handoff = [
        change
        for change in comparison.criterion_changes
        if change.criterion == "handoff"
    ]
    assert [float(change.change) for change in handoff] == [-1.0]
