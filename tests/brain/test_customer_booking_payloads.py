"""The list_my_bookings result the language model reads."""

import json

from typed_time_provider import Microseconds

from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.channels import ChannelKind
from app.schemas.dto.bookings import BookingView
from app.schemas.dto.customer_bookings import CustomerBookingList
from app.schemas.typings.bookings.constrained_integers import (
    BookingValueMinor,
    PartySize,
)
from app.schemas.typings.bookings.constrained_strings import LocalDate, LocalTimeOfDay
from app.schemas.typings.bookings.prefixed_id import BookingId, ResourceId
from app.schemas.typings.bookings.strings import ResourceName
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.knowledge.strings import KnowledgeTitle
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    TimezoneName,
)
from app.utilities.conversations.customer_booking_payloads import (
    NO_BOOKINGS_NOTE,
    render_customer_bookings,
)

TBILISI: TimezoneName = TimezoneName("Asia/Tbilisi")
THURSDAY: Microseconds = Microseconds(1_790_848_800_000_000)


def booking(**changes: object) -> BookingView:
    fields: dict[str, object] = {
        "id": BookingId(),
        "business_id": BusinessId(),
        "resource_id": ResourceId(),
        "resource_name": ResourceName("Chair 1"),
        "contact_id": ContactId(),
        "date": LocalDate("2026-10-09"),
        "end_date": LocalDate("2026-10-09"),
        "timezone": TBILISI,
        "party_size": PartySize(1),
        "status": BookingStatus.CONFIRMED,
        "source_channel": ChannelKind.WHATSAPP,
        "created_at": THURSDAY,
    }
    return BookingView.model_validate({**fields, **changes})


def read(result: CustomerBookingList, today: str | None = None) -> dict[str, object]:
    decoded: dict[str, object] = json.loads(
        str(render_customer_bookings(result, today))
    )
    return decoded


def test_no_bookings_says_what_can_be_looked_up() -> None:
    payload = read(CustomerBookingList(), "2026-10-01 (Thursday)")

    assert payload == {
        "bookings": [],
        "note": NO_BOOKINGS_NOTE,
        "business_today": "2026-10-01 (Thursday)",
    }


def test_a_service_booking_carries_its_time_service_and_price() -> None:
    haircut = booking(
        time=LocalTimeOfDay("15:00"),
        end_time=LocalTimeOfDay("15:45"),
        service_title=KnowledgeTitle("Haircut"),
        value_minor=BookingValueMinor(4500),
        currency_code=CurrencyCode("GEL"),
    )

    payload = read(CustomerBookingList(bookings=[haircut]))

    assert "note" not in payload
    assert "business_today" not in payload
    assert payload["bookings"] == [
        {
            "booking_id": str(haircut.id),
            "status": "confirmed",
            "resource_name": "Chair 1",
            "date": "2026-10-09",
            "end_date": "2026-10-09",
            "party_size": 1,
            "timezone": "Asia/Tbilisi",
            "time": "15:00",
            "end_time": "15:45",
            "service": "Haircut",
            "price": "45.00",
            "currency": "GEL",
        }
    ]


def test_an_all_day_booking_without_a_price_has_no_time_or_price() -> None:
    stay = booking(
        end_date=LocalDate("2026-10-11"),
        value_minor=BookingValueMinor(4500),
        status=BookingStatus.CANCELLED,
    )

    payload = read(CustomerBookingList(bookings=[stay]))
    rendered = payload["bookings"]

    assert isinstance(rendered, list)
    assert rendered[0] == {
        "booking_id": str(stay.id),
        "status": "cancelled",
        "resource_name": "Chair 1",
        "date": "2026-10-09",
        "end_date": "2026-10-11",
        "party_size": 1,
        "timezone": "Asia/Tbilisi",
    }
