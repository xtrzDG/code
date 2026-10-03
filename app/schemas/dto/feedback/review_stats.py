"""Settings → Reviews: how the feedback after visits went lately."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.feedback.constrained_floats import AverageVisitScore
from app.schemas.typings.feedback.constrained_integers import (
    FeedbackRequestCount,
    ReviewStatsPeriodDays,
    VisitScore,
)
from app.schemas.typings.users.prefixed_id import UserId


class ReviewStatsQuery(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId


class VisitScoreCount(ImmutableDTO):
    """How many customers rated their visit with one score."""

    score: VisitScore
    count: FeedbackRequestCount


class ReviewStatsView(ImmutableDTO):
    """
    The requests of the last `period_days`: how many customers were asked
    (sent, answered or not), how many answered and their average rating
    with the count of each score (1 to 5), how many of them opened the
    review link, and how many visits were not asked (skipped) or whose
    request could not be delivered (failed).
    """

    period_days: ReviewStatsPeriodDays
    asked_count: FeedbackRequestCount
    answered_count: FeedbackRequestCount
    average_score: AverageVisitScore | None = None
    score_counts: list[VisitScoreCount] = Field(default_factory=list[VisitScoreCount])
    review_opened_count: FeedbackRequestCount
    skipped_count: FeedbackRequestCount
    failed_count: FeedbackRequestCount
