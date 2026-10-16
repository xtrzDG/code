"""
The places held for waiting customers as a placement sees them: each
offer whose hold has not run out is an unsaved booking of its resource and
time, so no other booking (and no other offer) can take its unit.
"""

from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.waitlist import WaitlistStatus
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.waitlist import WaitlistEntryDocument, WaitlistOffer
from app.schemas.typings.bookings.constrained_integers import BookingSearchBoundSeconds
from app.schemas.typings.contacts.prefixed_id import ContactId


def is_hold_live(entry: WaitlistEntryDocument, now: Microseconds) -> bool:
    """An offered place still held for its customer at `now`."""

    return (
        entry.status is WaitlistStatus.OFFERED
        and entry.offer is not None
        and entry.offer_expires_at is not None
        and int(entry.offer_expires_at) > int(now)
    )


def held_place_bookings(
    entries: Sequence[WaitlistEntryDocument],
    ends_after: BookingSearchBoundSeconds,
    now: Microseconds,
    holder: ContactId | None,
) -> list[BookingDocument]:
    """
    The live holds that end after `ends_after`, except the ones held for
    `holder` (the customer may take their own place), as bookings.
    """

    return [
        held_place_booking(entry, entry.offer)
        for entry in entries
        if entry.offer is not None
        and is_hold_live(entry, now)
        and entry.contact_id != holder
        and int(entry.offer.ends_at) > int(ends_after)
    ]


def held_place_booking(
    entry: WaitlistEntryDocument, offer: WaitlistOffer
) -> BookingDocument:
    """One held place as a booking: never saved, it only takes its unit."""

    return BookingDocument(
        business_id=entry.business_id,
        resource_id=offer.resource_id,
        contact_id=entry.contact_id,
        conversation_id=entry.conversation_id,
        starts_at=offer.starts_at,
        ends_at=offer.ends_at,
        party_size=entry.party_size,
        status=BookingStatus.CONFIRMED,
        source_channel=entry.source_channel,
        buffer_minutes=offer.buffer_minutes,
        created_at=offer.offered_at,
        updated_at=offer.offered_at,
    )
