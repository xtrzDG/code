"""The booking a customer's create_booking makes, before it is saved."""

from typed_time_provider import Microseconds

from app.schemas.constants.bookings import BookingStatus
from app.schemas.domain.bookings import BookingDocument
from app.schemas.dto.bookings import CreateBookingCommand
from app.schemas.typings.bookings.constrained_integers import (
    BookingEndsAtUnixSeconds,
    BookingStartsAtUnixSeconds,
)
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.knowledge.constrained_integers import BufferMinutes
from app.use_cases.bookings.offer_selection import BookedOffer
from app.utilities.scheduling.placement import Placement


def build_new_booking(
    command: CreateBookingCommand,
    placement: Placement,
    contact_id: ContactId,
    buffer_minutes: BufferMinutes | None,
    booked: BookedOffer,
    now: Microseconds,
) -> BookingDocument:
    """
    A CONFIRMED booking of the placement for the contact, with the booked
    service, its value and the buffer that follows it.
    """

    return BookingDocument(
        business_id=command.business_id,
        resource_id=placement.resource.id,
        contact_id=contact_id,
        conversation_id=command.conversation_id,
        starts_at=BookingStartsAtUnixSeconds(placement.starts_at),
        ends_at=BookingEndsAtUnixSeconds(placement.ends_at),
        party_size=command.party_size,
        status=BookingStatus.CONFIRMED,
        source_channel=command.source_channel,
        notes=command.notes,
        is_sandbox=command.is_sandbox,
        language=command.language,
        service_item_id=booked.service_item_id,
        buffer_minutes=buffer_minutes,
        value_minor=booked.value_minor,
        currency_code=booked.currency_code,
        created_at=now,
        updated_at=now,
    )
