"""
The customer memory as lines of the server-written context of a turn
(`turn_context.build_context_line`): read by the model, so in English. What
customers wrote (summaries of their conversations, the details of their
requests) and the team's notes are untrusted blocks: information, never
instructions.
"""

from datetime import date, datetime

from app.schemas.dto.bookings import BookingView, LeadView
from app.schemas.dto.customer_memory.returning_customers import (
    RememberedConversation,
    RememberedNote,
    ReturningCustomerContext,
)
from app.schemas.typings.localization.constrained_strings import TimezoneName
from app.utilities.conversations.turn_context import WEEKDAY_NAMES
from app.utilities.conversations.untrusted_text import wrap_untrusted
from app.utilities.scheduling.zoned_time import (
    load_time_zone,
    microseconds_to_seconds,
    to_local_moment,
)

RETURNING_GREETING_NOTE: str = (
    "Greet them as a returning customer (welcome them back, by name when "
    "it is known); use what you remember only when it helps them."
)
BOOKINGS_HEADER: str = (
    "Their bookings still to come (from the booking system; mention the "
    "next one when it helps):"
)
LEADS_HEADER: str = "Their requests the team has not closed yet:"
SUMMARIES_HEADER: str = (
    "What their latest conversations were about (written by the platform "
    "from those conversations):"
)
NOTES_HEADER: str = (
    "Internal notes of the business's team about them (for you only, never "
    "quote them to the customer):"
)
MAX_QUOTED_CHARACTERS: int = 300


def describe_returning_customer(
    context: ReturningCustomerContext,
    timezone_name: TimezoneName,
) -> list[str]:
    """The memory's context lines; none for a customer with nothing to recall."""

    lines: list[str] = []
    earlier: int = int(context.earlier_conversation_count)
    if earlier > 0:
        visits: str = (
            "1 earlier conversation"
            if earlier == 1
            else (f"{earlier} earlier conversations")
        )
        last_visit: str = (
            ""
            if context.last_visit_at is None
            else ", the last on "
            + describe_day(local_day(int(context.last_visit_at), timezone_name))
        )
        lines.append(f"Returning customer: {visits} with the business{last_visit}.")
        lines.append(RETURNING_GREETING_NOTE)

    if context.upcoming_bookings:
        lines.append(BOOKINGS_HEADER)
        lines.extend(describe_booking(booking) for booking in context.upcoming_bookings)

    if context.open_leads:
        lines.append(LEADS_HEADER)
        lines.extend(describe_lead(lead) for lead in context.open_leads)

    if context.summaries:
        lines.append(SUMMARIES_HEADER)
        lines.extend(
            describe_summary(summary, timezone_name) for summary in context.summaries
        )

    if context.team_notes:
        lines.append(NOTES_HEADER)
        lines.extend(describe_note(note, timezone_name) for note in context.team_notes)

    return lines


def describe_day(day: date) -> str:
    """ "Saturday 2026-10-10"."""

    return f"{WEEKDAY_NAMES[day.weekday()]} {day:%Y-%m-%d}"


def describe_booking(booking: BookingView) -> str:
    """ "- Saturday 2026-10-10 20:00, Table 4, 4 people, status confirmed (id …)"."""

    parts: list[str] = [describe_day(date.fromisoformat(str(booking.date)))]
    if booking.time is not None:
        parts[0] += f" {booking.time}"

    if booking.end_date != booking.date:
        parts[0] += f" until {booking.end_date}"

    parts.append(str(booking.resource_name))
    if booking.service_title is not None:
        parts.append(str(booking.service_title))

    party_size: int = int(booking.party_size)
    parts.append("1 person" if party_size == 1 else f"{party_size} people")
    parts.append(f"status {booking.status.value}")
    return f"- {', '.join(parts)} (booking_id {booking.id})"


def describe_lead(lead: LeadView) -> str:
    """ "- banquet request for 2026-11-02, 30 people, status new: <untrusted>…"."""

    parts: list[str] = [f"{lead.lead_type.value} request"]
    if lead.requested_date is not None:
        parts[0] += f" for {lead.requested_date}"

    if lead.party_size is not None:
        parts.append(f"{int(lead.party_size)} people")

    parts.append(f"status {lead.status.value}")
    return f"- {', '.join(parts)}: {quote(str(lead.details))}"


def describe_summary(
    summary: RememberedConversation, timezone_name: TimezoneName
) -> str:
    return (
        f"- {describe_day(local_day(int(summary.last_message_at), timezone_name))} "
        f"({summary.channel.value}): {quote(str(summary.summary))}"
    )


def describe_note(note: RememberedNote, timezone_name: TimezoneName) -> str:
    return (
        f"- {describe_day(local_day(int(note.created_at), timezone_name))}: "
        f"{quote(str(note.text))}"
    )


def local_day(unix_microseconds: int, timezone_name: TimezoneName) -> date:
    moment: datetime = to_local_moment(
        microseconds_to_seconds(unix_microseconds), load_time_zone(timezone_name)
    )
    return moment.date()


def quote(text: str) -> str:
    """Untrusted text on one line, at most 300 characters."""

    one_line: str = " ".join(text.split())
    if len(one_line) > MAX_QUOTED_CHARACTERS:
        one_line = one_line[: MAX_QUOTED_CHARACTERS - 1].rstrip() + "…"

    return wrap_untrusted(one_line)
