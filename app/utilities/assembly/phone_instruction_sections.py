"""
Sections that differ in the phone instruction (concept section 7).

On the phone the platform's greeting carries the AI disclosure and the
recording notice, facts are written as they are said, links are never read
aloud, and answers are short spoken sentences. Everything else is shared
with the chat instruction.
"""

from collections.abc import Sequence

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.domain.assistants import BusinessFact
from app.utilities.assembly.instruction_sections import (
    build_fact_section_from_rows,
    build_role_section,
)
from app.utilities.assembly.spoken_facts import SpokenFactTable, speak_facts

PHONE_DISCLOSURE: str = (
    "The greeting of every call already says that you are the AI assistant of "
    "the business and that the call is recorded, so do not repeat it."
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
    named instead, as links the caller can get by text message when the
    version can send links.
    """

    table: SpokenFactTable = speak_facts(facts)
    lines: list[str] = build_fact_section_from_rows(table.rows, tools)
    if table.link_labels and AssistantToolName.SEND_LINK in tools:
        lines.append(
            "- Links the caller can get as a text message with send_link: "
            + ", ".join(table.link_labels)
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
        "Never read a link or a web address aloud.",
    ]
    if AssistantToolName.SEND_LINK in tools:
        lines.append(
            "When a link would help (the menu, a booking page, the map, a "
            "payment), call send_link. When its result says the link will be "
            'texted, say "I will text you the link". Otherwise never promise a '
            "message: say where the caller can find it or offer to pass the "
            "request to a colleague."
        )

    return lines
