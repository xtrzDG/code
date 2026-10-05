"""
A booking as an iCalendar file (RFC 5545) the guest adds to their calendar:
one event in UTC, its place, a short description and the manage link.
"""

import datetime

from app.schemas.constants.bookings import BookingStatus
from app.schemas.dto.booking_manage import BookingCalendarEvent
from app.schemas.typings.bookings.constrained_strings import (
    BookingCalendarFileName,
    LocalDate,
)
from app.schemas.typings.bookings.strings import BookingCalendarText

PRODUCT_ID: str = "-//Assistant Workshop//Booking//EN"
UID_DOMAIN: str = "bookings.assistant-workshop"
LINE_BREAK: str = "\r\n"
# Content lines are folded at 75 octets (RFC 5545, 3.1).
MAX_LINE_OCTETS: int = 75
MICROSECONDS_PER_SECOND: int = 1_000_000
# SEQUENCE counts seconds from this moment (2023-11-14), so it stays a small
# 32-bit number that calendars compare safely.
SEQUENCE_EPOCH_SECONDS: int = 1_700_000_000
CANCELLED_STATUSES: frozenset[BookingStatus] = frozenset({BookingStatus.CANCELLED})


def render_calendar_file(event: BookingCalendarEvent) -> BookingCalendarText:
    """The file's text with CRLF line ends, escaped and folded lines."""

    lines: list[str] = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:{PRODUCT_ID}",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:{event.booking_id}@{UID_DOMAIN}",
        f"DTSTAMP:{utc_stamp(int(event.stamped_at) // MICROSECONDS_PER_SECOND)}",
        f"DTSTART:{utc_stamp(int(event.starts_at))}",
        f"DTEND:{utc_stamp(int(event.ends_at))}",
        f"SEQUENCE:{sequence_of(event)}",
        f"SUMMARY:{escape_text(str(event.title))}",
        f"DESCRIPTION:{escape_text(str(event.description))}",
    ]
    if event.location is not None:
        lines.append(f"LOCATION:{escape_text(str(event.location))}")
    if event.url is not None:
        lines.append(f"URL:{event.url}")
    lines.append(
        "STATUS:CANCELLED" if event.status in CANCELLED_STATUSES else "STATUS:CONFIRMED"
    )
    lines.extend(["END:VEVENT", "END:VCALENDAR"])
    return BookingCalendarText("".join(fold_line(line) + LINE_BREAK for line in lines))


def calendar_file_name(date: LocalDate) -> BookingCalendarFileName:
    """`booking-2026-10-06.ics`: ASCII, the local date of the booking."""

    return BookingCalendarFileName(f"booking-{date}.ics")


def sequence_of(event: BookingCalendarEvent) -> int:
    """
    The event's revision: calendars replace an imported event only by a
    higher SEQUENCE, and every change of the booking moves `changed_at`.
    """

    changed_seconds: int = int(event.changed_at) // MICROSECONDS_PER_SECOND
    return max(0, changed_seconds - SEQUENCE_EPOCH_SECONDS)


def utc_stamp(unix_seconds: int) -> str:
    moment = datetime.datetime.fromtimestamp(unix_seconds, tz=datetime.UTC)
    return moment.strftime("%Y%m%dT%H%M%SZ")


def escape_text(value: str) -> str:
    """TEXT escaping: backslash, semicolon, comma and line breaks."""

    return (
        value.replace("\\", "\\\\")
        .replace(";", "\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
        .replace("\r", "\\n")
    )


def fold_line(line: str) -> str:
    """Split a line longer than 75 octets, never inside a UTF-8 character."""

    parts: list[str] = []
    current: str = ""
    limit: int = MAX_LINE_OCTETS
    for character in line:
        if len((current + character).encode("utf-8")) > limit:
            parts.append(current)
            current = character
            # Continuation lines start with a space, which counts.
            limit = MAX_LINE_OCTETS - 1
            continue
        current += character
    parts.append(current)
    return (LINE_BREAK + " ").join(parts)
