"""
Turning a customer's "yes" to an offered place into the booking of exactly
that place: the resource, the local date and time (or a stay's nights),
the service, the party and the note of their wish, in their conversation.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from app.schemas.constants.bookings import BookingUnit
from app.schemas.domain.resources import ResourceDocument
from app.schemas.domain.waitlist import WaitlistEntryDocument, WaitlistOffer
from app.schemas.dto.bookings import CreateBookingCommand
from app.schemas.dto.conversation_engine import PreparedTurn
from app.schemas.typings.bookings.constrained_integers import (
    BookingDurationMinutes,
    NightCount,
)
from app.schemas.typings.bookings.constrained_strings import LocalTimeOfDay
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.knowledge.strings import ServiceReference
from app.utilities.scheduling.zoned_time import to_local_date, to_local_moment

SECONDS_PER_MINUTE: int = 60


def booking_of_offer(
    turn: PreparedTurn,
    entry: WaitlistEntryDocument,
    offer: WaitlistOffer,
    resource: ResourceDocument,
    zone: ZoneInfo,
) -> CreateBookingCommand | None:
    """The booking of the offered place; None without a name to book under."""

    name: ContactName | None = entry.contact_name or turn.contact.name
    if name is None:
        return None

    starts: datetime = to_local_moment(int(offer.starts_at), zone)
    is_stay: bool = resource.booking_unit is BookingUnit.NIGHT
    ends: datetime = to_local_moment(int(offer.ends_at), zone)
    return CreateBookingCommand(
        business_id=turn.business.id,
        contact_id=turn.contact.id,
        conversation_id=turn.conversation.id,
        contact_name=name,
        resource_id=offer.resource_id,
        service_reference=(
            None
            if offer.service_item_id is None
            else ServiceReference(str(offer.service_item_id))
        ),
        date=to_local_date(starts.date()),
        time=None if is_stay else LocalTimeOfDay(starts.strftime("%H:%M")),
        duration_minutes=(
            None
            if is_stay or offer.service_item_id is not None
            else BookingDurationMinutes(
                (int(offer.ends_at) - int(offer.starts_at)) // SECONDS_PER_MINUTE
            )
        ),
        nights=(
            NightCount(max((ends.date() - starts.date()).days, 1)) if is_stay else None
        ),
        party_size=entry.party_size,
        notes=entry.notes,
        source_channel=turn.conversation.channel,
        language=turn.reply_language,
        is_sandbox=False,
    )
