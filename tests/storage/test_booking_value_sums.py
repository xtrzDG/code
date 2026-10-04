"""What the bookings made in a period are worth, in memory and on Postgres."""

import pytest
from typed_time_provider import Microseconds

from app.repositories.booking_repositories import BookingRepository
from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.bookings import BookingDocument
from app.schemas.dto.operations.activity_counts import ActivityPeriod
from app.schemas.typings.bookings.constrained_integers import (
    BookingEndsAtUnixSeconds,
    BookingStartsAtUnixSeconds,
    BookingValueMinor,
    PartySize,
)
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from tests.storage.conftest import CollectionFactory

pytestmark = pytest.mark.usefixtures("platform_scope")

HOUR = 3_600_000_000
START = 1_790_000_000_000_000
PERIOD = ActivityPeriod(
    start=Microseconds(START),
    end=Microseconds(START + 48 * HOUR),
    segment_starts=(Microseconds(START), Microseconds(START + 24 * HOUR)),
)


def booking(
    business_id: BusinessId,
    hours_in: int,
    value: tuple[int, str] | None,
    status: BookingStatus = BookingStatus.CONFIRMED,
    by_assistant: bool = True,
    is_sandbox: bool = False,
) -> BookingDocument:
    moment = Microseconds(START + hours_in * HOUR)
    return BookingDocument(
        business_id=business_id,
        resource_id=ResourceId(),
        contact_id=ContactId(),
        conversation_id=ConversationId() if by_assistant else None,
        starts_at=BookingStartsAtUnixSeconds(1_800_000_000),
        ends_at=BookingEndsAtUnixSeconds(1_800_003_600),
        party_size=PartySize(1),
        status=status,
        source_channel=ChannelKind.WHATSAPP,
        is_sandbox=is_sandbox,
        value_minor=None if value is None else BookingValueMinor(value[0]),
        currency_code=None if value is None else CurrencyCode(value[1]),
        created_at=moment,
        updated_at=moment,
    )


def test_values_are_summed_per_status_currency_and_segment(
    collections: CollectionFactory,
) -> None:
    bookings = BookingRepository(collections(BookingDocument, "bookings"))
    business_id = BusinessId()
    bookings.save_many(
        [
            booking(business_id, 1, (4_500, "GEL")),
            booking(business_id, 2, (3_000, "GEL")),
            booking(business_id, 3, (2_000, "USD")),
            booking(business_id, 4, None),
            booking(business_id, 30, (80_000, "GEL")),
            booking(business_id, 31, (7_000, "GEL"), BookingStatus.CANCELLED),
            booking(business_id, 32, (5_000, "GEL"), by_assistant=False),
            # Left out: a test booking, one after the period, another business.
            booking(business_id, 5, (9_999, "GEL"), is_sandbox=True),
            booking(business_id, 60, (9_999, "GEL")),
            booking(BusinessId(), 5, (9_999, "GEL")),
        ]
    )

    every = bookings.sum_value_made(business_id, PERIOD)
    by_staff = bookings.sum_value_made(business_id, PERIOD, by_staff_only=True)

    assert {
        (
            group.status,
            None if group.currency_code is None else str(group.currency_code),
            int(group.segment),
            int(group.count),
            int(group.value_minor),
        )
        for group in every
    } == {
        (BookingStatus.CONFIRMED, "GEL", 0, 2, 7_500),
        (BookingStatus.CONFIRMED, "USD", 0, 1, 2_000),
        (BookingStatus.CONFIRMED, None, 0, 1, 0),
        (BookingStatus.CONFIRMED, "GEL", 1, 2, 85_000),
        (BookingStatus.CANCELLED, "GEL", 1, 1, 7_000),
    }
    assert [(int(group.count), int(group.value_minor)) for group in by_staff] == [
        (1, 5_000)
    ]
