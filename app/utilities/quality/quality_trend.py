"""
Averages and drops of production quality, the same for the admin's client
page and the QUALITY_DROP platform alert, and the views of stored scores.
"""

from collections.abc import Sequence

from app.schemas.domain.conversation_quality import ConversationQualityScoreDocument
from app.schemas.dto.assistants.assistant_views import JudgeCriterionScoreView
from app.schemas.dto.quality import (
    ConversationQualityScoreView,
    QualitySampleView,
    QualityTotals,
)
from app.schemas.typings.assistants.constrained_floats import AverageJudgeScore
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.quality.constrained_integers import (
    QualityDropPercent,
    QualitySampleCount,
    QualityScoreHundredthsTotal,
)

HUNDREDTHS: int = 100
SCORE_DECIMALS: int = 2
# A drop of production quality: the recent average below the earlier one by
# more than this many percent, once both hold this many scored
# conversations (the QUALITY_DROP alert, ops/alerts/quality_drop.yaml, and
# a client's page for the admin).
QUALITY_DROP_PERCENT: int = 10
QUALITY_DROP_FLOOR: int = 10


def add_totals(totals: Sequence[QualityTotals]) -> QualityTotals:
    return QualityTotals(
        sample_count=QualitySampleCount(sum(int(item.sample_count) for item in totals)),
        score_hundredths_total=QualityScoreHundredthsTotal(
            sum(int(item.score_hundredths_total) for item in totals)
        ),
        cost_micro_usd=CostMicroUsd(sum(int(item.cost_micro_usd) for item in totals)),
    )


def average_of(totals: QualityTotals) -> AverageJudgeScore | None:
    """The average score of the stretch; None when nothing was scored."""

    if int(totals.sample_count) == 0:
        return None

    return AverageJudgeScore(
        round(
            int(totals.score_hundredths_total) / int(totals.sample_count) / HUNDREDTHS,
            SCORE_DECIMALS,
        )
    )


def describe_average(totals: QualityTotals) -> str:
    """The stretch's average as text ("4.6"); "-" when nothing was scored."""

    average: AverageJudgeScore | None = average_of(totals)
    return "-" if average is None else f"{float(average):.1f}"


def drop_percent(recent: QualityTotals, earlier: QualityTotals) -> QualityDropPercent:
    """
    How many percent the recent average is below the earlier one, rounded
    down (0 when it did not fall or a stretch has no score). Compared in
    whole numbers: recent_total * earlier_count against earlier_total *
    recent_count.
    """

    recent_count: int = int(recent.sample_count)
    earlier_count: int = int(earlier.sample_count)
    if recent_count == 0 or earlier_count == 0:
        return QualityDropPercent(0)

    recent_scaled: int = int(recent.score_hundredths_total) * earlier_count
    earlier_scaled: int = int(earlier.score_hundredths_total) * recent_count
    if recent_scaled >= earlier_scaled:
        return QualityDropPercent(0)

    return QualityDropPercent((earlier_scaled - recent_scaled) * 100 // earlier_scaled)


def to_criterion_views(
    score: ConversationQualityScoreDocument,
) -> list[JudgeCriterionScoreView]:
    return [
        JudgeCriterionScoreView(criterion=item.criterion, score=item.score)
        for item in score.scores
    ]


def to_average(score: ConversationQualityScoreDocument) -> AverageJudgeScore:
    return AverageJudgeScore(int(score.score_hundredths) / HUNDREDTHS)


def to_sample_view(score: ConversationQualityScoreDocument) -> QualitySampleView:
    """A score in the admin's list: numbers only, no notes."""

    return QualitySampleView(
        conversation_id=score.conversation_id,
        channel=score.channel,
        language=score.language,
        average_score=to_average(score),
        scores=to_criterion_views(score),
        judged_at=score.judged_at,
    )


def to_score_view(
    score: ConversationQualityScoreDocument,
) -> ConversationQualityScoreView:
    """A score on its conversation's card, with the judge's notes."""

    return ConversationQualityScoreView(
        average_score=to_average(score),
        scores=to_criterion_views(score),
        judge_notes=list(score.judge_notes),
        judged_at=score.judged_at,
    )
