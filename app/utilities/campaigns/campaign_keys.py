"""
Identities of the rebooking campaigns: the settings of a business, one
message per rule and booking, and the outbox message that carries it.
"""

from uuid import UUID, uuid5

from app.schemas.constants.campaigns import RebookingRuleKind
from app.schemas.typings.bookings.prefixed_id import BookingId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.campaigns.prefixed_id import (
    CampaignMessageId,
    CampaignSettingsId,
)
from app.schemas.typings.deliveries.constrained_strings import OutboundIdempotencyKey

# Fixed namespaces of derived ids (never change them: stored ids depend on
# them).
CAMPAIGN_SETTINGS_NAMESPACE: UUID = UUID("e3a9b1c5-2d6f-4e80-9b7a-4c1d8f2e6b35")
CAMPAIGN_MESSAGE_NAMESPACE: UUID = UUID("7f4d2b8e-6a13-4c95-8e0b-b2a5d9c1f347")


def campaign_settings_id_of(business_id: BusinessId) -> CampaignSettingsId:
    """One settings document per business."""

    return CampaignSettingsId(uuid5(CAMPAIGN_SETTINGS_NAMESPACE, str(business_id)))


def campaign_message_id_of(
    business_id: BusinessId,
    rule_kind: RebookingRuleKind,
    anchor_booking_id: BookingId,
) -> CampaignMessageId:
    """A booking leads to one message of a rule, however often the job looks."""

    return CampaignMessageId(
        uuid5(
            CAMPAIGN_MESSAGE_NAMESPACE,
            f"{business_id}|{rule_kind.value}|{anchor_booking_id}",
        )
    )


def campaign_idempotency_key(message_id: CampaignMessageId) -> OutboundIdempotencyKey:
    """One outbox message per campaign message."""

    return OutboundIdempotencyKey(f"campaign:{message_id}")
