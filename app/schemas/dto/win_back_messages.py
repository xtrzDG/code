"""A win-back message on its way to the owners of a business that cancelled."""

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds

from app.schemas.constants.subscription_lifecycle import (
    CancellationReason,
    WinBackStage,
)
from app.schemas.typings.billing.prefixed_id import SubscriptionId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.subscription_lifecycle.constrained_integers import (
    ConversationsSinceCancellation,
)


class WinBackMessage(ImmutableDTO):
    """
    One stage of the win-back for a cancelled subscription: when the owner
    cancelled and why, and how many customers the assistant (taking
    requests only) talked to since.
    """

    business_id: BusinessId
    subscription_id: SubscriptionId
    stage: WinBackStage
    cancelled_at: Microseconds
    reason: CancellationReason | None = None
    conversations_since: ConversationsSinceCancellation
