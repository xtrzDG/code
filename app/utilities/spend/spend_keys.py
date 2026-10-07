"""
The derived ids of the spend guard: one limits document per business and
one mark per business, day and spend level.
"""

from uuid import UUID, uuid5

from app.schemas.constants.spend import SpendLevel
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.spend.constrained_strings import SpendDay
from app.schemas.typings.spend.prefixed_id import BusinessLimitsId, SpendLimitMarkId

# Fixed namespaces of derived ids (never change them: stored ids depend on
# them).
BUSINESS_LIMITS_NAMESPACE: UUID = UUID("5b0f3c62-8e1a-4b9d-a7c4-2f6d0e9b1a37")
SPEND_LIMIT_MARK_NAMESPACE: UUID = UUID("c3e8a1d4-6f2b-4e7a-9d05-8b1f4c2e7a90")


def business_limits_id_of(business_id: BusinessId) -> BusinessLimitsId:
    """One limits document per business."""

    return BusinessLimitsId(uuid5(BUSINESS_LIMITS_NAMESPACE, str(business_id)))


def spend_limit_mark_id_of(
    business_id: BusinessId, day: SpendDay, level: SpendLevel
) -> SpendLimitMarkId:
    """One mark per business, day and spend level."""

    return SpendLimitMarkId(
        uuid5(SPEND_LIMIT_MARK_NAMESPACE, f"{business_id}:{day}:{level.value}")
    )
