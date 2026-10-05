"""
Today at the business, as the scheduling tools state it on every channel.

The chat model reads today's date in the context line; the voice agent
only in the call's opening variables. Both turn "tomorrow" or "this
Friday" into a date themselves, so availability and booking results, and
their errors, also carry `business_today`: a wrong guess is caught where
it matters, and a date that has already passed is refused with today's
date instead of a vague "too soon".
"""

from dataclasses import dataclass
from datetime import date, datetime

from typed_time_provider import Microseconds

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.typings.localization.constrained_strings import TimezoneName
from app.utilities.conversations.turn_context import WEEKDAY_NAMES
from app.utilities.scheduling.zoned_time import load_time_zone

MICROSECONDS_PER_SECOND: int = 1_000_000
SCHEDULING_TOOLS: frozenset[AssistantToolName] = frozenset(
    {
        AssistantToolName.CHECK_AVAILABILITY,
        AssistantToolName.CREATE_BOOKING,
        AssistantToolName.RESCHEDULE_BOOKING,
        AssistantToolName.CANCEL_BOOKING,
        AssistantToolName.LIST_MY_BOOKINGS,
    }
)


@dataclass(frozen=True)
class BusinessToday:
    """The business-local date and how tool results state it (technical record)."""

    day: date
    text: str


def find_business_today(
    now: Microseconds, timezone_name: TimezoneName
) -> BusinessToday:
    """Today in the business time zone: "2026-10-01 (Thursday)"."""

    local_day: date = datetime.fromtimestamp(
        int(now) / MICROSECONDS_PER_SECOND, tz=load_time_zone(timezone_name)
    ).date()
    return BusinessToday(
        day=local_day,
        text=f"{local_day.isoformat()} ({WEEKDAY_NAMES[local_day.weekday()]})",
    )


def describe_past_date(requested_date: str, today: BusinessToday) -> str | None:
    """
    The tool error for a date before today at the business, else None
    (`requested_date` is an ISO date the tool input already validated).
    """

    if date.fromisoformat(requested_date) >= today.day:
        return None

    return (
        f"The date {requested_date} has already passed: today at the business is "
        f"{today.text}. Work out the date again from today and ask the customer "
        "if it is unclear."
    )
