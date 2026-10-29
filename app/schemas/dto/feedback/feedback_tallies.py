"""The counts of a business's feedback requests over a period (storage)."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.feedback import FeedbackRequestStatus
from app.schemas.dto.feedback.review_stats import VisitScoreCount
from app.schemas.typings.feedback.constrained_integers import (
    FeedbackRequestCount,
    FeedbackScoreTotal,
)


class FeedbackTally(ImmutableDTO):
    """
    The requests created in a period, counted in the database: per status,
    the sum and the count of each rating of the answered ones, and how
    many customers opened their review link.
    """

    status_counts: dict[FeedbackRequestStatus, FeedbackRequestCount] = Field(
        default_factory=dict[FeedbackRequestStatus, FeedbackRequestCount]
    )
    score_total: FeedbackScoreTotal = FeedbackScoreTotal(0)
    score_counts: list[VisitScoreCount] = Field(default_factory=list[VisitScoreCount])
    opened_count: FeedbackRequestCount = FeedbackRequestCount(0)
