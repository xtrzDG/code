"""A booking's .ics file: valid iCalendar lines a guest's calendar imports."""

from typed_time_provider import Microseconds

from app.schemas.constants.bookings import BookingStatus
from app.schemas.dto.booking_manage import BookingCalendarEvent
from app.schemas.typings.bookings.constrained_integers import (
    BookingEndsAtUnixSeconds,
    BookingStartsAtUnixSeconds,
)
from app.schemas.typings.bookings.constrained_strings import (
    BookingManageLink,
    LocalDate,
)
from app.schemas.typings.bookings.prefixed_id import BookingId
from app.schemas.typings.bookings.strings import (
    CalendarEventDescription,
    CalendarEventTitle,
)
from app.schemas.typings.businesses.strings import AddressText
from app.utilities.bookings.booking_calendar_files import (
    calendar_file_name,
    escape_text,
    fold_line,
    render_calendar_file,
)

STARTS_AT: int = 1_791_298_800  # 2026-10-06 15:00 UTC = 19:00 in Tbilisi
LINK: str = "https://app.workshop.example/r/" + "A" * 71


def event(
    status: BookingStatus = BookingStatus.CONFIRMED,
    changed_at: int = 1_791_200_000,
    title: str = "Salobie Bia",
    description: str = "Guests: 2\nChange or cancel: " + LINK,
    location: str | None = "Тбилиси, проспект Руставели 1",
) -> BookingCalendarEvent:
    return BookingCalendarEvent(
        booking_id=BookingId(),
        starts_at=BookingStartsAtUnixSeconds(STARTS_AT),
        ends_at=BookingEndsAtUnixSeconds(STARTS_AT + 2 * 3600),
        stamped_at=Microseconds(1_791_201_234_000_000),
        changed_at=Microseconds(changed_at * 1_000_000),
        title=CalendarEventTitle(title),
        description=CalendarEventDescription(description),
        location=None if location is None else AddressText(location),
        url=BookingManageLink(LINK),
        status=status,
    )


def unfolded(text: str) -> list[str]:
    return text.replace("\r\n ", "").split("\r\n")


def test_the_file_is_one_event_in_utc_with_crlf_lines() -> None:
    booked = event()

    text = str(render_calendar_file(booked))

    assert text.endswith("\r\n")
    assert "\n" not in text.replace("\r\n", "")
    lines = unfolded(text)
    assert lines[:6] == [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Assistant Workshop//Booking//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
    ]
    assert f"UID:{booked.booking_id}@bookings.assistant-workshop" in lines
    assert "DTSTART:20261006T150000Z" in lines
    assert "DTEND:20261006T170000Z" in lines
    assert "DTSTAMP:20261005T115354Z" in lines
    assert "SUMMARY:Salobie Bia" in lines
    assert "DESCRIPTION:Guests: 2\\nChange or cancel: " + LINK in lines
    assert "LOCATION:Тбилиси\\, проспект Руставели 1" in lines
    assert f"URL:{LINK}" in lines
    assert "STATUS:CONFIRMED" in lines
    assert lines[-3:] == ["END:VEVENT", "END:VCALENDAR", ""]


def test_a_cancelled_booking_says_so_and_a_later_change_wins() -> None:
    first = unfolded(str(render_calendar_file(event(changed_at=1_791_200_000))))
    cancelled = unfolded(
        str(
            render_calendar_file(
                event(status=BookingStatus.CANCELLED, changed_at=1_791_200_060)
            )
        )
    )

    assert "STATUS:CANCELLED" in cancelled
    sequence = {
        int(line.removeprefix("SEQUENCE:"))
        for line in first
        if line.startswith("SEQUENCE:")
    }
    later = {
        int(line.removeprefix("SEQUENCE:"))
        for line in cancelled
        if line.startswith("SEQUENCE:")
    }
    assert later == {next(iter(sequence)) + 60}


def test_without_an_address_there_is_no_location() -> None:
    lines = unfolded(str(render_calendar_file(event(location=None))))

    assert not any(line.startswith("LOCATION") for line in lines)


def test_text_values_escape_what_icalendar_reserves() -> None:
    assert escape_text("a\\b;c,d\ne\r\nf") == "a\\\\b\\;c\\,d\\ne\\nf"

    lines = unfolded(str(render_calendar_file(event(title="Bar; Grill, \\ Co"))))
    assert "SUMMARY:Bar\\; Grill\\, \\\\ Co" in lines


def test_long_lines_fold_at_75_octets_without_splitting_a_letter() -> None:
    georgian = "სალობიე ბია — " * 12
    text = str(render_calendar_file(event(title=georgian)))

    for line in text.split("\r\n"):
        assert len(line.encode("utf-8")) <= 75
    assert f"SUMMARY:{georgian}" in unfolded(text)

    folded = fold_line("X" * 200)
    parts = folded.split("\r\n")
    assert [len(part) for part in parts] == [75, 75, 52]
    assert all(part.startswith(" ") for part in parts[1:])


def test_the_file_name_is_the_local_date() -> None:
    assert str(calendar_file_name(LocalDate("2026-10-06"))) == "booking-2026-10-06.ics"
