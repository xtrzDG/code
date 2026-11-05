"""
A customer's own bookings, read by their contacts (list_my_bookings and the
customer memory), in memory and on Postgres: the contacts, statuses and
sandbox mode asked for, not over yet, the soonest first, at most a limit.
"""

import pytest
from typed_time_provider import Microseconds

from app.repositories.booking_repositories import BookingRepository
from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.bookings import BookingDocument
from app.schemas.dto.customer_bookings import ContactBookingLookup
from app.schemas.typings.bookings.constrained_integers import (
    BookingEndsAtUnixSeconds,
    BookingSearchBoundSeconds,
    BookingStartsAtUnixSeconds,
    PartySize,
)
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.booleans import IsSandboxConversation
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from tests.storage.conftest import CollectionFactory

pytestmark = pytest.mark.usefixtures("platform_scope")

NOW = 1_800_000_000
HOUR = 3_600
OPEN_STATUSES: tuple[BookingStatus, ...] = (
    BookingStatus.PENDING,
    BookingStatus.CONFIRMED,
)


def booking(
    business_id: BusinessId,
    contact_id: ContactId,
    hours_from_now: int,
    status: BookingStatus = BookingStatus.CONFIRMED,
    is_sandbox: bool = False,
) -> BookingDocument:
    starts_at = NOW + hours_from_now * HOUR
    return BookingDocument(
        business_id=business_id,
        resource_id=ResourceId(),
        contact_id=contact_id,
        starts_at=BookingStartsAtUnixSeconds(starts_at),
        ends_at=BookingEndsAtUnixSeconds(starts_at + HOUR),
        party_size=PartySize(2),
        status=status,
        source_channel=ChannelKind.WHATSAPP,
        is_sandbox=is_sandbox,
        created_at=Microseconds(1_790_000_000_000_000),
        updated_at=Microseconds(1_790_000_000_000_000),
    )


def lookup(
    contact_ids: tuple[ContactId, ...],
    is_sandbox: bool = False,
    limit: int = 10,
    statuses: tuple[BookingStatus, ...] = OPEN_STATUSES,
) -> ContactBookingLookup:
    return ContactBookingLookup(
        contact_ids=contact_ids,
        statuses=statuses,
        is_sandbox=IsSandboxConversation(is_sandbox),
        ends_after=BookingSearchBoundSeconds(NOW),
        limit=DocumentQueryLimit(limit),
    )


def test_only_the_customers_open_bookings_soonest_first(
    collections: CollectionFactory,
) -> None:
    bookings = BookingRepository(collections(BookingDocument, "bookings"))
    business_id = BusinessId()
    giorgi, by_phone, nino = ContactId(), ContactId(), ContactId()
    later = booking(business_id, giorgi, 48)
    sooner = booking(business_id, by_phone, 5, BookingStatus.PENDING)
    # Under way: started now, ends within the hour.
    under_way = booking(business_id, giorgi, 0)
    bookings.save_many(
        [
            later,
            sooner,
            under_way,
            # Left out: over, cancelled, a test booking, another customer,
            # the same contact id in another business.
            booking(business_id, giorgi, -2),
            booking(business_id, giorgi, 3, BookingStatus.CANCELLED),
            booking(business_id, giorgi, 4, is_sandbox=True),
            booking(business_id, nino, 6),
            booking(BusinessId(), giorgi, 8),
        ]
    )

    found = bookings.list_for_contacts(business_id, lookup((giorgi, by_phone)))

    assert [item.id for item in found] == [under_way.id, sooner.id, later.id]


def test_a_test_chat_sees_only_test_bookings(collections: CollectionFactory) -> None:
    bookings = BookingRepository(collections(BookingDocument, "bookings"))
    business_id = BusinessId()
    owner = ContactId()
    test_booking = booking(business_id, owner, 4, is_sandbox=True)
    bookings.save_many([booking(business_id, owner, 3), test_booking])

    found = bookings.list_for_contacts(business_id, lookup((owner,), is_sandbox=True))

    assert [item.id for item in found] == [test_booking.id]


def test_the_limit_keeps_the_soonest(collections: CollectionFactory) -> None:
    bookings = BookingRepository(collections(BookingDocument, "bookings"))
    business_id = BusinessId()
    regular = ContactId()
    visits = [booking(business_id, regular, hours) for hours in (30, 10, 20, 40)]
    bookings.save_many(visits)

    found = bookings.list_for_contacts(business_id, lookup((regular,), limit=2))

    assert [int(item.starts_at) for item in found] == [NOW + 10 * HOUR, NOW + 20 * HOUR]


def test_nothing_to_look_for_reads_nothing(collections: CollectionFactory) -> None:
    bookings = BookingRepository(collections(BookingDocument, "bookings"))
    business_id = BusinessId()
    regular = ContactId()
    bookings.save(booking(business_id, regular, 3))

    assert bookings.list_for_contacts(business_id, lookup(())) == []
    no_status = lookup((regular,), statuses=())
    assert bookings.list_for_contacts(business_id, no_status) == []
