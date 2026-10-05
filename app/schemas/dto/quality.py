"""Production quality: the judge's scores of real conversations, read back."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.conversation_quality import ConversationQualityScoreDocument
from app.schemas.dto.assistants.assistant_views import JudgeCriterionScoreView
from app.schemas.dto.conversations import LlmRequest
from app.schemas.typings.assistants.constrained_floats import AverageJudgeScore
from app.schemas.typings.assistants.strings import JudgeNote
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.quality.booleans import IsQualityDropping
from app.schemas.typings.quality.constrained_integers import (
    QualityDropPercent,
    QualitySampleCount,
    QualityScoreHundredthsTotal,
)
from app.schemas.typings.users.prefixed_id import UserId


class QualityTotals(ImmutableDTO):
    """
    The scores of a stretch of time (summed by the database): how many
    conversations were scored, their average scores added up in hundredths,
    and what judging them cost.
    """

    sample_count: QualitySampleCount = QualitySampleCount(0)
    score_hundredths_total: QualityScoreHundredthsTotal = QualityScoreHundredthsTotal(0)
    cost_micro_usd: CostMicroUsd = CostMicroUsd(0)


class QualityJudgeRequest(ImmutableDTO):
    """
    The judge's request for one conversation and the most it can cost
    (every output token used), checked against the night's budget first.
    """

    request: LlmRequest
    worst_case_cost: CostMicroUsd


class QualityJudgement(ImmutableDTO):
    """
    What judging one conversation gave: its score (None when the judge's
    answer could not be read) and what the call cost either way.
    """

    score: ConversationQualityScoreDocument | None = None
    cost_micro_usd: CostMicroUsd


class QualityDayView(ImmutableDTO):
    """One day of a business's trend (its own time zone): samples, average."""

    day_start: Microseconds
    sample_count: QualitySampleCount
    average_score: AverageJudgeScore | None = None


class QualitySampleView(ImmutableDTO):
    """One scored conversation in the admin's list (scores only, no text)."""

    conversation_id: ConversationId
    channel: ChannelKind
    language: LanguageTag | None = None
    average_score: AverageJudgeScore
    scores: list[JudgeCriterionScoreView]
    judged_at: Microseconds


class ClientQualityView(ImmutableDTO):
    """
    A client's production quality for the platform admin: the last 30 days
    of the business's time zone, oldest first, the average of the last 7
    days against the 7 before (`is_dropping` when it fell by more than
    the QUALITY_DROP alert's threshold), and the lowest-scored
    conversations of the 30 days. Scores only: no customer text.
    """

    business_id: BusinessId
    sample_count: QualitySampleCount
    average_score: AverageJudgeScore | None = None
    last_week_average: AverageJudgeScore | None = None
    previous_week_average: AverageJudgeScore | None = None
    drop_percent: QualityDropPercent = QualityDropPercent(0)
    is_dropping: IsQualityDropping = False
    days: list[QualityDayView]
    lowest: list[QualitySampleView] = Field(default_factory=list[QualitySampleView])


class ConversationQualityQuery(ImmutableDTO):
    """A member of the business reads one conversation's quality score."""

    user_id: UserId
    business_id: BusinessId
    conversation_id: ConversationId


class ConversationQualityScoreView(ImmutableDTO):
    """The judge's score of a conversation, its notes in the owner's language."""

    average_score: AverageJudgeScore
    scores: list[JudgeCriterionScoreView]
    judge_notes: list[JudgeNote] = Field(default_factory=list[JudgeNote])
    judged_at: Microseconds


class ConversationQualityView(ImmutableDTO):
    """
    A conversation's quality score on its card; `score` is None for the
    conversations the nightly sample did not pick (most of them).
    """

    conversation_id: ConversationId
    score: ConversationQualityScoreView | None = None
