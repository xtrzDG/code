"""
The derived ids of the subscription lifecycle: a win-back stage of a
subscription is recorded once, and a business gets the save-offer credit
once.
"""

from uuid import UUID, uuid5

from app.schemas.constants.subscription_lifecycle import WinBackStage
from app.schemas.typings.billing.prefixed_id import BillingCreditId, SubscriptionId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.subscription_lifecycle.prefixed_id import (
    SubscriptionEventId,
)

# Fixed namespaces of the derived ids (never change them: stored ids depend
# on them).
WIN_BACK_NAMESPACE: UUID = UUID("d5b50f64-a5bd-4c9e-9325-5ea72ce8f92a")
SAVE_CREDIT_NAMESPACE: UUID = UUID("e9d956e3-ac2a-4f2c-9474-3d012966d72a")


def derive_win_back_event_id(
    subscription_id: SubscriptionId, stage: WinBackStage
) -> SubscriptionEventId:
    """The id of a win-back step: one per subscription and stage."""

    return SubscriptionEventId(
        uuid5(WIN_BACK_NAMESPACE, f"{subscription_id}:{stage.value}")
    )


def derive_save_credit_id(business_id: BusinessId) -> BillingCreditId:
    """The id of the credit taken instead of cancelling: one per business."""

    return BillingCreditId(uuid5(SAVE_CREDIT_NAMESPACE, str(business_id)))
