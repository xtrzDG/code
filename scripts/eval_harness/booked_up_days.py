"""
Days a dataset's business has no free place on (`business.booked_up`):
every unit of every active resource is taken the whole local day, so a
scenario can ask for that day and be offered the waitlist.
"""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from typed_time_provider import Microseconds

from app.containers.app import AppContainer
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.typings.bookings.constrained_integers import (
    BookingEndsAtUnixSeconds,
    BookingStartsAtUnixSeconds,
    PartySize,
)
from app.schemas.typings.contacts.prefixed_id import ContactId


def book_up(
    container: AppContainer,
    business: BusinessDocument,
    days: list[str],
    now: Microseconds,
) -> None:
    """One whole-day booking per unit of each active resource on each day."""

    if not days:
        return

    zone = ZoneInfo(str(business.timezone))
    resources = [
        resource
        for resource in container.repositories.resource_repo().list_by_business(
            business.id
        )
        if resource.is_active
    ]
    regular = ContactId()
    bookings: list[BookingDocument] = []
    for day in days:
        start = datetime.combine(date.fromisoformat(day), datetime.min.time(), zone)
        end = start + timedelta(days=1)
        for resource in resources:
            for _ in range(int(resource.unit_count)):
                bookings.append(
                    BookingDocument(
                        business_id=business.id,
                        resource_id=resource.id,
                        contact_id=regular,
                        starts_at=BookingStartsAtUnixSeconds(int(start.timestamp())),
                        ends_at=BookingEndsAtUnixSeconds(int(end.timestamp())),
                        party_size=PartySize(1),
                        source_channel=ChannelKind.PHONE,
                        created_at=now,
                        updated_at=now,
                    )
                )

    container.repositories.booking_repo().save_many(bookings)
