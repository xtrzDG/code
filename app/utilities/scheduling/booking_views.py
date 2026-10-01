"""Bookings rendered in the business time zone."""

from datetime import datetime
from zoneinfo import ZoneInfo

from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.bookings import BookingView
from app.schemas.typings.bookings.strings import ResourceName
from app.schemas.typings.localization.constrained_strings import TimezoneName
from app.utilities.scheduling.zoned_time import (
    minute_of_day,
    to_local_date,
    to_local_moment,
    to_time_of_day,
)


def build_booking_view(
    booking: BookingDocument,
    timezone: TimezoneName,
    zone: ZoneInfo,
    resource: ResourceDocument | None,
    contact: ContactDocument | None,
) -> BookingView:
    """
    Local start and end of a booking with its resource and contact.

    A resource deleted after the booking is shown by its id.
    """

    starts: datetime = to_local_moment(int(booking.starts_at), zone)
    ends: datetime = to_local_moment(int(booking.ends_at), zone)
    resource_name: ResourceName = (
        ResourceName(str(booking.resource_id)) if resource is None else resource.name
    )
    return BookingView(
        id=booking.id,
        business_id=booking.business_id,
        resource_id=booking.resource_id,
        resource_name=resource_name,
        contact_id=booking.contact_id,
        contact_name=None if contact is None else contact.name,
        contact_phone_number=None if contact is None else contact.phone_number,
        date=to_local_date(starts.date()),
        time=to_time_of_day(minute_of_day(starts)),
        end_date=to_local_date(ends.date()),
        end_time=to_time_of_day(minute_of_day(ends)),
        timezone=timezone,
        party_size=booking.party_size,
        status=booking.status,
        source_channel=booking.source_channel,
        notes=booking.notes,
        is_sandbox=booking.is_sandbox,
        conversation_id=booking.conversation_id,
        language=booking.language,
        reminder_sent_at=booking.reminder_sent_at,
        created_at=booking.created_at,
    )
