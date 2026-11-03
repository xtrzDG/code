"""
Sections that differ in the phone instruction (concept section 7).

On the phone the platform's greeting carries the AI disclosure (and the
recording notice while the business records calls), facts are written as
they are said, links are never read aloud, answers are short spoken
sentences, and a caller's existing bookings are not touched: the caller id
proves nobody's identity, so the voice agent has no tool that reads or
changes them (`CALLER_ID_BOUND_TOOLS`). Everything else is shared with the
chat instruction.
"""

from collections.abc import Sequence

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.domain.assistants import BusinessFact
from app.utilities.assembly.instruction_sections import (
    build_booking_section,
    build_fact_section_from_rows,
    build_role_section,
)
from app.utilities.assembly.spoken_facts import SpokenFactTable, speak_facts

PHONE_DISCLOSURE: str = (
    "The greeting of every call already says that you are the AI assistant of "
    "the business, so do not repeat it."
)
# What replaces cancel_booking, reschedule_booking and list_my_bookings on
# the phone (the tool webhook refuses them with the same advice).
PHONE_EXISTING_BOOKING_RULES: tuple[str, ...] = (
    "- On a call the caller's number does not prove who is calling, so you "
    "cannot look up, cancel or move an existing booking. Never say whether a "
    "booking exists: offer to pass the request to a colleague with "
    "handoff_to_human, who calls back the number on the booking.",
)
# Nothing reaches a caller in writing unless a tool result says so.
NO_TEXT_PROMISE_RULE: str = (
    "Never promise a text message, an SMS or a written confirmation unless a "
    "tool result says that one is sent."
)


# ACC-03: a caller who did not catch an answer, or hears badly, asks again.
REPEAT_AND_SLOWER_RULE: str = (
    "When the caller asks you to repeat, say your last answer again in the "
    "same words. When they ask you to speak slower or more clearly, use "
    "shorter sentences, pause between details and say each date, time, "
    "price and number on its own, and keep doing so for the rest of the call."
)


def build_phone_role_section(
    business_name: str,
    business_type: str,
    location: str,
) -> list[str]:
    """Who the assistant is on the phone, and the AI disclosure rule."""

    return build_role_section(
        business_name,
        business_type,
        location,
        medium="on the phone",
        disclosure=PHONE_DISCLOSURE,
    )


def build_spoken_fact_section(
    facts: Sequence[BusinessFact],
    tools: Sequence[AssistantToolName],
) -> list[str]:
    """
    The fact table as it is said on the phone. Rows that are only a link are
    named instead, as links send_link can offer when the version can send
    links (whether one is texted is the tool result's to say).
    """

    table: SpokenFactTable = speak_facts(facts)
    lines: list[str] = build_fact_section_from_rows(table.rows, tools)
    if table.link_labels and AssistantToolName.SEND_LINK in tools:
        lines.append(
            "- Links you can offer with send_link: " + ", ".join(table.link_labels)
        )

    return lines


def build_phone_answer_format_section(
    tools: Sequence[AssistantToolName],
) -> list[str]:
    """How answers sound on the phone, and what to do instead of reading links."""

    lines: list[str] = [
        "# Answer format",
        "You are speaking on the phone: use short, plain sentences and ask one "
        "question at a time. Never use lists, emojis, symbols or markdown.",
        "Say prices with the name of the currency, the way people say amounts "
        "aloud in the caller's language; never say a currency code.",
        "Say dates with the day and the month and times the way people say "
        "them. Say phone numbers slowly, digit by digit, and repeat the digits "
        "back for confirmation.",
        REPEAT_AND_SLOWER_RULE,
        "Never read a link or a web address aloud.",
        NO_TEXT_PROMISE_RULE,
    ]
    if AssistantToolName.SEND_LINK in tools:
        lines.append(
            "When a link would help (the menu, a booking page, the map, a "
            'payment), call send_link. When its result has "texted_after_call": '
            'true, say "I will text you the link": the platform texts it right '
            "after the call. Otherwise never promise a message: say where the "
            "caller can find it or offer to pass the request to a colleague."
        )

    return lines


def build_phone_booking_section(
    tools: Sequence[AssistantToolName],
    country_name: str,
    timezone_name: str,
    has_sister_locations: bool,
) -> list[str]:
    """
    The booking section of the voice agent's tools (`tools` without
    CALLER_ID_BOUND_TOOLS): new bookings as in the chat, existing ones
    passed to a colleague.
    """

    return build_booking_section(
        tools,
        country_name,
        timezone_name,
        has_sister_locations=has_sister_locations,
        existing_booking_rules=PHONE_EXISTING_BOOKING_RULES,
    )
