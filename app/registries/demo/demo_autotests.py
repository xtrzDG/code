"""
The finished autotest run of a demo version: scenario results with short
transcripts, the judge's scores and notes, summarized like a real run.
"""

from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.schemas.constants.assistants import (
    AutotestRunStatus,
    AutotestScenarioKind,
    JudgeCriterion,
)
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.assistants import (
    AutotestRunDocument,
    AutotestScenarioResult,
    AutotestTranscriptLine,
    JudgeCriterionScore,
)
from app.schemas.dto.assistants import AutotestRunSummary
from app.schemas.typings.assistants.constrained_integers import (
    AutotestScenarioCount,
    JudgeScore,
)
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.assistants.strings import JudgeNote
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.assembly.autotest_evaluation import decide_outcome, summarize_run
from app.utilities.assembly.autotest_scenarios import build_scenario_key

# A played scenario costs a few US cents: the customer, the assistant and
# the judge are all model calls.
SCENARIO_COST_MICRO_USD: int = 41000
# Scores in criterion order: facts and prices, booking data, AI
# disclosure, handoff, language.
PERFECT_SCORES: tuple[int, int, int, int, int] = (5, 5, 5, 5, 5)
CRITERIA: tuple[JudgeCriterion, ...] = (
    JudgeCriterion.FACTS_AND_PRICES,
    JudgeCriterion.BOOKING_DATA,
    JudgeCriterion.AI_DISCLOSURE,
    JudgeCriterion.HANDOFF,
    JudgeCriterion.LANGUAGE,
)


def scenario(
    kind: AutotestScenarioKind,
    language: str,
    customer_text: str,
    assistant_text: str,
    scores: tuple[int, int, int, int, int] = PERFECT_SCORES,
    judge_note: str | None = None,
    ordinal: int | None = None,
) -> AutotestScenarioResult:
    """One played scenario: the opening exchange and the judge's verdict."""

    judge_scores: list[JudgeCriterionScore] = [
        JudgeCriterionScore(criterion=criterion, score=JudgeScore(score))
        for criterion, score in zip(CRITERIA, scores, strict=True)
    ]
    return AutotestScenarioResult(
        scenario_key=build_scenario_key(kind, LanguageTag(language), ordinal),
        kind=kind,
        language=LanguageTag(language),
        outcome=decide_outcome(judge_scores, []),
        scores=judge_scores,
        judge_notes=[] if judge_note is None else [JudgeNote(judge_note)],
        transcript=[
            AutotestTranscriptLine(
                author=MessageAuthor.CUSTOMER, text=MessageText(customer_text)
            ),
            AutotestTranscriptLine(
                author=MessageAuthor.ASSISTANT, text=MessageText(assistant_text)
            ),
        ],
        cost_micro_usd=CostMicroUsd(SCENARIO_COST_MICRO_USD),
    )


def finished_run(
    business_id: BusinessId,
    version_id: AssistantVersionId,
    finished_at: Microseconds,
    results: Sequence[AutotestScenarioResult],
) -> AutotestRunDocument:
    """A run over every language and scenario kind, summarized."""

    summary: AutotestRunSummary = summarize_run(results)
    return AutotestRunDocument(
        business_id=business_id,
        assistant_version_id=version_id,
        status=AutotestRunStatus.FINISHED,
        is_full_coverage=True,
        planned_scenario_count=AutotestScenarioCount(len(results)),
        results=list(results),
        pass_rate=summary.pass_rate,
        average_score=summary.average_score,
        is_passed=summary.is_passed,
        created_at=finished_at,
        updated_at=finished_at,
    )
