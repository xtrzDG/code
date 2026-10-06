"""
Identities of the waitlist: the settings of a business and the outbox
message that carries one offer of a freed place to one entry.
"""

from uuid import UUID, uuid5

from app.schemas.typings.bookings.prefixed_id import BookingId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.deliveries.constrained_strings import OutboundIdempotencyKey
from app.schemas.typings.waitlist.prefixed_id import WaitlistEntryId, WaitlistSettingsId

# A fixed namespace of derived ids (never change it: stored ids depend on it).
WAITLIST_SETTINGS_NAMESPACE: UUID = UUID("5c0e2f7a-91d4-4b3e-a6f8-0d7b3c2e9a14")


def waitlist_settings_id_of(business_id: BusinessId) -> WaitlistSettingsId:
    """One settings document per business."""

    return WaitlistSettingsId(uuid5(WAITLIST_SETTINGS_NAMESPACE, str(business_id)))


def waitlist_offer_idempotency_key(
    entry_id: WaitlistEntryId, freed_booking_id: BookingId
) -> OutboundIdempotencyKey:
    """One outbox message per offer: an entry offered one freed place once."""

    return OutboundIdempotencyKey(f"waitlist:{entry_id}:{freed_booking_id}")
