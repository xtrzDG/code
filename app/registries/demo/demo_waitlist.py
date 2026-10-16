"""
The waitlist of a demo business: three guests waiting for a full evening
in the days ahead, one who took a freed place (that booking counts as the
waitlist's) and one who let an offered place lapse yesterday.
"""

from collections.abc import Sequence
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from typed_time_provider import Microseconds

from app.schemas.constants.bookings import BookingOrigin, BookingStatus
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.waitlist import WaitlistEndReason, WaitlistStatus
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.waitlist import WaitlistEntryDocument, WaitlistOffer
from app.schemas.typings.bookings.constrained_integers import PartySize
from app.schemas.typings.bookings.constrained_strings import (
    LocalDate,
    LocalTimeOfDay,
)
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.waitlist.constrained_integers import WaitlistOfferCount
from app.utilities.scheduling.zoned_time import load_time_zone

MICROSECONDS_PER_SECOND: int = 1_000_000
MINUTE: int = 60 * MICROSECONDS_PER_SECOND
HOUR: int = 60 * MINUTE
# (days ahead, earliest start, latest start, guests) of the waiting guests.
WISHES: tuple[tuple[int, str | None, str | None, int], ...] = (
    (2, "19:00", "21:00", 4),
    (3, "20:00", "22:00", 2),
    (5, None, None, 6),
)
KEPT_STATUSES: frozenset[BookingStatus] = frozenset(
    {BookingStatus.CONFIRMED, BookingStatus.COMPLETED}
)


def build_demo_waitlist(
    business: BusinessDocument,
    bookings: Sequence[BookingDocument],
    contacts: Sequence[ContactDocument],
    now: Microseconds,
) -> list[WaitlistEntryDocument]:
    """The entries; the booking the waitlist filled is marked as its own."""

    guests: list[ContactDocument] = [
        contact
        for contact in contacts
        if contact.name is not None
        and contact.erased_at is None
        and not contact.is_test_only
        and not contact.opted_out_channels
    ]
    if len(guests) < len(WISHES) + 1:
        return []

    zone: ZoneInfo = load_time_zone(business.timezone)
    today: date = datetime.fromtimestamp(
        int(now) / MICROSECONDS_PER_SECOND, zone
    ).date()
    entries: list[WaitlistEntryDocument] = []
    for index, (days, earliest, latest, guests_count) in enumerate(WISHES):
        guest: ContactDocument = guests[index]
        day: date = today + timedelta(days=days)
        joined = Microseconds(int(now) - (index + 1) * 3 * HOUR)
        entries.append(
            WaitlistEntryDocument(
                business_id=business.id,
                contact_id=guest.id,
                contact_name=guest.name,
                source_channel=channel_of(guest),
                language=guest.language or business.default_language,
                date=LocalDate(day.isoformat()),
                time_from=None if earliest is None else LocalTimeOfDay(earliest),
                time_to=None if latest is None else LocalTimeOfDay(latest),
                party_size=PartySize(guests_count),
                waits_until=day_end(day, zone),
                created_at=joined,
                updated_at=joined,
            )
        )

    by_id = {contact.id: contact for contact in contacts}
    taken: BookingDocument | None = latest_kept_booking(bookings, by_id, now)
    if taken is not None:
        entries.append(filled_entry(business, taken, by_id[taken.contact_id], now))

    lapsed_guest: ContactDocument = guests[len(WISHES)]
    entries.append(lapsed_entry(business, lapsed_guest, today, now))
    return entries


def filled_entry(
    business: BusinessDocument,
    booking: BookingDocument,
    guest: ContactDocument,
    now: Microseconds,
) -> WaitlistEntryDocument:
    """A guest who took a freed place; the booking is the waitlist's."""

    booking.origin = BookingOrigin.WAITLIST
    zone: ZoneInfo = load_time_zone(business.timezone)
    starts: datetime = datetime.fromtimestamp(int(booking.starts_at), zone)
    offered = Microseconds(min(int(booking.created_at), int(now)) - 10 * MINUTE)
    joined = Microseconds(int(offered) - 26 * HOUR)
    return WaitlistEntryDocument(
        business_id=business.id,
        contact_id=guest.id,
        contact_name=guest.name,
        source_channel=channel_of(guest),
        language=booking.language or guest.language or business.default_language,
        date=LocalDate(starts.date().isoformat()),
        party_size=booking.party_size,
        waits_until=day_end(starts.date(), zone),
        status=WaitlistStatus.BOOKED,
        offer=WaitlistOffer(
            freed_booking_id=booking.id,
            resource_id=booking.resource_id,
            starts_at=booking.starts_at,
            ends_at=booking.ends_at,
            offered_at=offered,
            channel=channel_of(guest),
        ),
        offer_count=WaitlistOfferCount(1),
        booking_id=booking.id,
        booked_at=booking.created_at,
        created_at=joined,
        updated_at=booking.created_at,
    )


def lapsed_entry(
    business: BusinessDocument,
    guest: ContactDocument,
    today: date,
    now: Microseconds,
) -> WaitlistEntryDocument:
    """A guest who waited for yesterday and let the offered place lapse."""

    zone: ZoneInfo = load_time_zone(business.timezone)
    day: date = today - timedelta(days=1)
    ended = Microseconds(int(now) - 20 * HOUR)
    return WaitlistEntryDocument(
        business_id=business.id,
        contact_id=guest.id,
        contact_name=guest.name,
        source_channel=channel_of(guest),
        language=guest.language or business.default_language,
        date=LocalDate(day.isoformat()),
        time_from=LocalTimeOfDay("18:00"),
        time_to=LocalTimeOfDay("20:00"),
        party_size=PartySize(3),
        waits_until=day_end(day, zone),
        status=WaitlistStatus.EXPIRED,
        offer_count=WaitlistOfferCount(1),
        end_reason=WaitlistEndReason.NO_ANSWER,
        ended_at=ended,
        created_at=Microseconds(int(ended) - 30 * HOUR),
        updated_at=ended,
    )


def latest_kept_booking(
    bookings: Sequence[BookingDocument],
    contacts: dict[ContactId, ContactDocument],
    now: Microseconds,
) -> BookingDocument | None:
    """The latest kept booking of a known guest, made before now."""

    kept: list[BookingDocument] = [
        booking
        for booking in bookings
        if booking.status in KEPT_STATUSES
        and not booking.is_sandbox
        and booking.origin is None
        and booking.contact_id in contacts
        and int(booking.created_at) < int(now)
    ]
    return max(kept, key=lambda booking: int(booking.created_at), default=None)


def channel_of(contact: ContactDocument) -> ChannelKind:
    """The guest's first messenger (the demo guests all have one)."""

    for identity in contact.channel_identities:
        if identity.channel is not ChannelKind.PHONE:
            return identity.channel

    return ChannelKind.WHATSAPP


def day_end(day: date, zone: ZoneInfo) -> Microseconds:
    """The end of a local day: a guest waits for it until then."""

    end = datetime.combine(day + timedelta(days=1), datetime.min.time(), zone)
    return Microseconds(int(end.timestamp()) * MICROSECONDS_PER_SECOND)
