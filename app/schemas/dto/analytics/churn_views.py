"""Why owners cancel, and what kept or brought them back (admin Metrics)."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.subscription_lifecycle import (
    CancellationReason,
    RetentionOfferKind,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.subscription_lifecycle.constrained_integers import (
    CancellationCount,
    SubscriptionStepCount,
)
from app.schemas.typings.subscription_lifecycle.constrained_strings import (
    CancellationDetails,
)


class ChurnReasonRow(ImmutableDTO):
    """
    One reason of the period: how many cancelled with it and how many took
    the offer it brought instead (`saved`). `reason` None: cancelled
    without saying why (a cabinet from before the question).
    """

    reason: CancellationReason | None = None
    cancellations: CancellationCount
    saved: SubscriptionStepCount


class RetentionOfferRow(ImmutableDTO):
    """How many owners took one kind of offer instead of cancelling."""

    kind: RetentionOfferKind
    accepted: SubscriptionStepCount


class ChurnComment(ImmutableDTO):
    """What one owner wrote when cancelling, newest first."""

    business_id: BusinessId
    reason: CancellationReason | None = None
    details: CancellationDetails
    occurred_at: Microseconds


class ChurnView(ImmutableDTO):
    """
    The period's cancellations by reason (most first) with the owners'
    own words, the offers taken instead, the seasonal pauses scheduled and
    ended, the win-back messages sent, and the businesses that subscribed
    again after one (`returned_after_win_back`).
    """

    cancellations: CancellationCount = CancellationCount(0)
    reasons: list[ChurnReasonRow] = Field(default_factory=list[ChurnReasonRow])
    offers: list[RetentionOfferRow] = Field(default_factory=list[RetentionOfferRow])
    pauses_scheduled: SubscriptionStepCount = SubscriptionStepCount(0)
    pauses_ended: SubscriptionStepCount = SubscriptionStepCount(0)
    win_back_sent: SubscriptionStepCount = SubscriptionStepCount(0)
    returned_after_win_back: SubscriptionStepCount = SubscriptionStepCount(0)
    comments: list[ChurnComment] = Field(default_factory=list[ChurnComment])
