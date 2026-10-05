"""
End to end over HTTP: the assistant books a table in the website chat, the
widget shows the written confirmation, and its link opens the booking's
page and calendar file. Nothing about the guest is on the page, and a link
the platform did not sign, or signed for another booking, opens nothing.
"""

import base64

from typed_time_provider import Microseconds

from app.schemas.dto.booking_manage import BookingManageClaims
from app.schemas.typings.bookings.constrained_integers import (
    BookingStartsAtUnixSeconds,
)
from app.schemas.typings.bookings.constrained_strings import BookingManageToken
from app.schemas.typings.bookings.prefixed_id import BookingId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from tests.bookings.conftest import CABINET_BASE_URL
from tests.bookings.manage_journey import (
    BOOKINGS_PATH,
    BookedTable,
    book_a_table,
    widget_messages_after,
)
from tests.e2e.harness import Workshop
from tests.e2e.journeys import JsonObject

PRIVATE_HEADERS: dict[str, str] = {
    "cache-control": "no-store",
    "x-robots-tag": "noindex",
    "referrer-policy": "no-referrer",
}
GUEST_PHONE: str = "+995555123456"


def refusal_codes(response: object) -> list[str]:
    body: JsonObject = response.json()  # type: ignore[attr-defined]
    return [str(reason["code"]) for reason in body["reasons"]]


def test_the_widget_shows_the_confirmation_with_its_link(workshop: Workshop) -> None:
    booked = book_a_table(workshop)

    lines = booked.confirmation.split("\n")
    assert lines[0] == "Salobie Bia: ваша бронь подтверждена."
    assert lines[1].startswith("Когда: ") and "19:00" in lines[1]
    assert lines[2:5] == [
        "Гостей: 2",
        "Адрес: Тбилиси, проспект Руставели 1",
        "Карта: https://maps.example/salobie",
    ]
    assert lines[5] == f"Изменить или отменить: {CABINET_BASE_URL}/r/{booked.token}"
    # Shown once: the next poll has nothing new.
    again = widget_messages_after(workshop, booked.restaurant, booked.cursor)
    assert again["items"] == []


def test_the_page_shows_the_booking_and_nothing_about_the_guest(
    workshop: Workshop,
) -> None:
    booked = book_a_table(workshop)

    page = workshop.client.get(booked.page)

    assert page.status_code == 200, page.text
    for header, value in PRIVATE_HEADERS.items():
        assert page.headers[header] == value
    view: JsonObject = page.json()
    assert view["token"] == booked.token
    assert {
        key: view[key]
        for key in (
            "business_name",
            "status",
            "booking_unit",
            "date",
            "time",
            "timezone",
            "party_size",
            "address",
            "maps_url",
            "phone_number",
            "cancellation_policy",
            "language",
            "can_cancel",
            "can_reschedule",
            "is_over",
        )
    } == {
        "business_name": "Salobie Bia",
        "status": "confirmed",
        "booking_unit": "time_slot",
        "date": "2026-10-06",
        "time": "19:00",
        "timezone": "Asia/Tbilisi",
        "party_size": 2,
        "address": "Тбилиси, проспект Руставели 1",
        "maps_url": "https://maps.example/salobie",
        "phone_number": "+995322123456",
        "cancellation_policy": "Бесплатная отмена за 2 часа.",
        "language": "ru",
        "can_cancel": True,
        "can_reschedule": True,
        "is_over": False,
    }
    # The chat the booking was made in comes first: the hosted chat page.
    first_link: JsonObject = view["chat_links"][0]
    assert first_link["kind"] == "hosted_chat"
    assert first_link["url"] == (
        f"{CABINET_BASE_URL}/c/{booked.restaurant.business_id}"
    )
    assert GUEST_PHONE not in page.text
    assert "Нино" not in page.text
    assert "У окна" not in page.text


def test_the_calendar_file_is_the_booking_in_utc(workshop: Workshop) -> None:
    booked = book_a_table(workshop)

    calendar = workshop.client.get(f"{booked.page}/calendar.ics")

    assert calendar.status_code == 200, calendar.text
    assert calendar.headers["content-type"] == "text/calendar; charset=utf-8"
    assert calendar.headers["content-disposition"] == (
        'attachment; filename="booking-2026-10-06.ics"; '
        "filename*=UTF-8''booking-2026-10-06.ics"
    )
    assert calendar.headers["cache-control"] == "no-store"
    lines = calendar.text.replace("\r\n ", "").split("\r\n")
    assert "DTSTART:20261006T150000Z" in lines
    assert "SUMMARY:Salobie Bia" in lines
    assert "LOCATION:Тбилиси\\, проспект Руставели 1" in lines
    assert "STATUS:CONFIRMED" in lines
    [url] = [line for line in lines if line.startswith("URL:")]
    assert url.startswith(f"URL:{CABINET_BASE_URL}/r/")
    [description] = [line for line in lines if line.startswith("DESCRIPTION:")]
    assert description.startswith("DESCRIPTION:Гостей: 2\\nИзменить или отменить: ")
    assert GUEST_PHONE not in calendar.text


def altered(token: str) -> str:
    middle = len(token) // 2
    return token[:middle] + ("A" if token[middle] != "A" else "B") + token[middle + 1 :]


def test_links_the_platform_did_not_sign_open_nothing(workshop: Workshop) -> None:
    booked = book_a_table(workshop)

    for token in (altered(booked.token), "A" * 71, "not-a-token", "x" * 200):
        for path in ("", "/calendar.ics", "/slots?date=2026-10-07"):
            refused = workshop.client.get(f"{BOOKINGS_PATH}/{token}{path}")
            assert refused.status_code == 404, (token, path, refused.text)
            assert refusal_codes(refused) == ["link_invalid"]
        cancelled = workshop.client.post(f"{BOOKINGS_PATH}/{token}/cancel")
        assert cancelled.status_code == 404
    still = workshop.client.get(booked.page).json()
    assert still["status"] == "confirmed"


def test_a_signed_link_cannot_reach_a_booking_of_another_business(
    workshop: Workshop,
) -> None:
    booked = book_a_table(workshop)
    signer = workshop.container.utilities.booking_manage_token_signer()
    claims = signer.read(BookingManageToken(booked.token))
    assert claims is not None

    for forged in (
        claims.model_copy(update={"business_id": BusinessId()}),
        claims.model_copy(update={"booking_id": BookingId()}),
        claims.model_copy(
            update={"booking_version": BookingStartsAtUnixSeconds(1_791_302_400)}
        ),
    ):
        refused = workshop.client.post(f"{BOOKINGS_PATH}/{signer.sign(forged)}/cancel")
        assert refused.status_code == 404, refused.text
        assert refusal_codes(refused) == ["booking_changed"]

    assert workshop.client.get(booked.page).json()["status"] == "confirmed"


def test_a_link_stops_opening_a_month_after_the_visit(workshop: Workshop) -> None:
    booked = book_a_table(workshop)
    signer = workshop.container.utilities.booking_manage_token_signer()
    claims = signer.read(BookingManageToken(booked.token))
    assert claims is not None
    expires_seconds = int(claims.expires_at) // 1_000_000

    now_seconds = int(workshop.clock.wall_clock.now_unix()) // 1_000_000
    workshop.clock.advance(expires_seconds - now_seconds - 60)
    over = workshop.client.get(booked.page)
    assert over.status_code == 200, over.text
    assert over.json()["is_over"] is True
    assert over.json()["can_cancel"] is False

    workshop.clock.advance(120)
    expired = workshop.client.get(booked.page)
    assert expired.status_code == 404
    assert refusal_codes(expired) == ["link_expired"]


def test_the_token_carries_only_ids_and_times(workshop: Workshop) -> None:
    booked: BookedTable = book_a_table(workshop)

    raw = base64.urlsafe_b64decode(booked.token + "=")

    assert len(raw) == 53
    assert b"Salobie" not in raw
    claims = workshop.container.utilities.booking_manage_token_signer().read(
        BookingManageToken(booked.token)
    )
    assert isinstance(claims, BookingManageClaims)
    assert claims.expires_at > Microseconds(0)
