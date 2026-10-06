"""
A resource's busy times as an iCalendar feed (RFC 5545) for Airbnb,
Booking.com or any calendar: one opaque event per booking, no guest's
name or detail (anyone with the address reads the feed). Stays are
whole-day events from check-in to check-out date, as rental calendars
expect; other bookings are exact UTC times.
"""

import datetime
from collections.abc import Sequence
from typing import NamedTuple

import icalendar

from app.schemas.dto.localization import LocalizedText
from app.schemas.typings.calendar_sync.strings import IcalFeedText
from app.utilities.localization.localized_texts import build_localized_text

PRODUCT_ID: str = "-//Assistant Workshop//Availability//EN"
UID_DOMAIN: str = "availability.assistant-workshop"
# What each event says, in the owner's language (no guest's details).
BUSY_EVENT_TITLE: LocalizedText = build_localized_text(
    en="Booked", ru="Забронировано", ka="დაჯავშნილია"
)


class ExportedBusyTime(NamedTuple):
    """
    One event of the feed: `dates` [check-in, check-out) for a stay, else
    `times` [start, end) in UTC seconds; `uid_key` stays the same for the
    same booking, so calendars update it instead of adding another.
    """

    uid_key: str
    times: tuple[int, int] | None
    dates: tuple[datetime.date, datetime.date] | None


def render_busy_feed(
    calendar_name: str,
    title: str,
    busy_times: Sequence[ExportedBusyTime],
    stamped_at_seconds: int,
) -> IcalFeedText:
    """The feed's text with CRLF lines, escaped and folded by the library."""

    calendar = icalendar.Calendar()
    calendar.add("prodid", PRODUCT_ID)
    calendar.add("version", "2.0")
    calendar.add("calscale", "GREGORIAN")
    calendar.add("method", "PUBLISH")
    calendar.add("x-wr-calname", calendar_name)
    stamp = datetime.datetime.fromtimestamp(stamped_at_seconds, tz=datetime.UTC)
    for busy_time in busy_times:
        event = icalendar.Event()
        event.add("uid", f"{busy_time.uid_key}@{UID_DOMAIN}")
        event.add("dtstamp", stamp)
        if busy_time.dates is not None:
            event.add("dtstart", busy_time.dates[0])
            event.add("dtend", busy_time.dates[1])
        elif busy_time.times is not None:
            event.add("dtstart", utc_moment(busy_time.times[0]))
            event.add("dtend", utc_moment(busy_time.times[1]))
        else:
            continue
        event.add("summary", title)
        event.add("transp", "OPAQUE")
        event.add("status", "CONFIRMED")
        calendar.add_component(event)

    return IcalFeedText(calendar.to_ical().decode("utf-8"))


def utc_moment(unix_seconds: int) -> datetime.datetime:
    return datetime.datetime.fromtimestamp(unix_seconds, tz=datetime.UTC)
