"""
The server-written context placed before each customer message.

What changes from turn to turn (local date and time, the next days, the
channel, the known phone, notes) lives in the user turn, never in the frozen
instruction, so the provider's prompt cache keeps the instruction. The text
is English: it is read by the model, not by the customer.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.schemas.constants.channels import ChannelKind

WEEKDAY_NAMES: tuple[str, ...] = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
)
UPCOMING_DAY_COUNT: int = 7
CONTEXT_HEADER: str = "[Context from the platform, not written by the customer]"
CUSTOMER_HEADER: str = "[Customer message]"
LEADS_ONLY_NOTE: str = (
    "Bookings are paused for this business: do not check availability or "
    "book. Take the request with create_lead, or pass the conversation to a "
    "colleague with handoff_to_human."
)
FIRST_REPLY_NOTE: str = (
    "This is your first reply in this conversation. The platform starts it "
    "with the disclosure that you are the AI assistant of the business, so do "
    "not introduce yourself again."
)
AFTER_HOURS_NOTE: str = "The business is closed right now (outside opening hours)."


@dataclass(frozen=True)
class TurnContext:
    """Facts of one turn known to the server (technical record)."""

    business_name: str
    timezone_name: str
    local_now: datetime
    channel: ChannelKind
    customer_name: str | None
    customer_phone_number: str | None
    is_after_hours: bool | None
    is_leads_only: bool
    is_first_reply: bool


def build_context_line(context: TurnContext) -> str:
    """
    Context lines, e.g.:

        [Context from the platform, not written by the customer]
        Business: Sakhli.
        Local time at the business: Thursday 2026-10-01 14:05 (Asia/Tbilisi).
        Next days: Fri 2026-10-02, Sat 2026-10-03, ...
        Channel: whatsapp.
        Customer: Giorgi, phone +995555123456.
    """

    lines: list[str] = [
        CONTEXT_HEADER,
        f"Business: {context.business_name}.",
        "Local time at the business: "
        f"{WEEKDAY_NAMES[context.local_now.weekday()]} "
        f"{context.local_now:%Y-%m-%d %H:%M} ({context.timezone_name}).",
        "Next days: "
        + ", ".join(
            f"{WEEKDAY_NAMES[day.weekday()][:3]} {day:%Y-%m-%d}"
            for day in (
                context.local_now + timedelta(days=offset)
                for offset in range(1, UPCOMING_DAY_COUNT + 1)
            )
        )
        + ".",
    ]
    if context.is_after_hours:
        lines.append(AFTER_HOURS_NOTE)

    lines.append(f"Channel: {context.channel.value}.")
    customer_details: list[str] = []
    if context.customer_name is not None:
        customer_details.append(context.customer_name)

    if context.customer_phone_number is not None:
        customer_details.append(f"phone {context.customer_phone_number}")

    if customer_details:
        lines.append(f"Customer: {', '.join(customer_details)}.")

    if context.is_leads_only:
        lines.append(LEADS_ONLY_NOTE)

    if context.is_first_reply:
        lines.append(FIRST_REPLY_NOTE)

    return "\n".join(lines)


def build_user_turn_text(context_line: str, customer_text: str) -> str:
    """The user turn: the context, then the customer's own words."""

    return f"{context_line}\n{CUSTOMER_HEADER}\n{customer_text}"


def build_rewrite_note(unverified_values: list[str]) -> str:
    """
    The one request to rewrite a reply whose values the guard could not
    find in the facts, the tool results or the customer's messages.
    """

    return (
        "[Check by the platform, not written by the customer]\n"
        "Your last reply mentions values that are not in the fact table, the "
        "tool results or the customer's messages: "
        + "; ".join(unverified_values)
        + ". Write the reply again in the customer's language without these "
        "values: use only values from the facts or tool results, call a tool "
        "to check them, or offer to pass the question to a colleague."
    )
