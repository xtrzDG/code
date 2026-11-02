"""
Sections of the assistant instruction (concept section 4), composed by code:
English lines that depend only on their arguments (no date, no random value),
so a version's instruction is byte-stable and the provider's prompt cache warm.
Who the assistant is, its languages, style, facts and bookings are here; the
rule sections are in `instruction_rule_sections`.
"""

from collections.abc import Sequence

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.domain.assistants import BusinessFact
from app.utilities.conversations.owner_text_fencing import (
    OWNER_TEXT_RULE,
    fence_owner_text,
)
from app.utilities.conversations.untrusted_text import UNTRUSTED_RULE, wrap_untrusted

DEFAULT_TONE: str = "friendly, polite and brief"
SECTION_SEPARATOR: str = "\n\n"
LINE_SEPARATOR: str = "\n"


def join_sections(sections: Sequence[Sequence[str]]) -> str:
    """Lines of a section joined by newlines, sections by blank lines."""

    return SECTION_SEPARATOR.join(
        LINE_SEPARATOR.join(section) for section in sections if section
    )


CHAT_DISCLOSURE: str = (
    "The first reply of every conversation already starts with an AI "
    "disclosure that is added automatically, so do not repeat it."
)


def build_role_section(
    business_name: str,
    business_type: str,
    location: str,
    medium: str = "in chat",
    disclosure: str = CHAT_DISCLOSURE,
) -> list[str]:
    """
    Who the assistant is, where it talks (`medium`) and the AI disclosure
    rule: the platform adds the disclosure (`disclosure` says where), and
    the assistant answers honestly whenever it is asked, offering a person
    or a message for the team (EU AI Act Art. 50(1)).
    """

    return [
        "# Role",
        f'You are the AI assistant of "{business_name}" '
        f"(type of business: {business_type}; location: {location}). "
        f"You answer the customers of this business {medium}, on behalf of the "
        "business.",
        f"You are an AI, not a person. {disclosure} Whenever someone asks "
        'whether they are talking to a real person or a bot ("are you a real '
        'person?", "sei una persona vera?"), say honestly that you are an AI '
        "assistant, in their language, and offer to pass them to a colleague "
        "(handoff_to_human) or to take a message for the team.",
    ]


def build_language_section(
    language_names: str,
    default_language_name: str,
) -> list[str]:
    """Answer in the customer's language among the business languages."""

    return [
        "# Languages",
        f"The business serves customers in: {language_names}. "
        f"Its default language is {default_language_name}.",
        "Always reply in the language of the customer's latest message when it "
        "is one of these languages. If the customer writes or speaks another "
        "language, reply in that language if you can; otherwise reply in "
        f"{default_language_name}.",
        "Keep names, prices, dates, times and phone numbers exactly as in the "
        "facts and tool results; never convert currencies.",
    ]


def build_style_section(tone: str | None) -> list[str]:
    """
    The tone the owner asked for (fenced as their text), or a neutral
    default, and how the owner's texts of the instruction are read.
    """

    chosen_tone: str = tone.strip() if tone is not None and tone.strip() else ""
    return [
        "# Style",
        f"Tone: {fence_owner_text(chosen_tone) if chosen_tone else DEFAULT_TONE}.",
        "Be helpful and polite, keep replies short and ask one question at a time.",
        OWNER_TEXT_RULE,
    ]


def build_fact_section(
    facts: Sequence[BusinessFact],
    tools: Sequence[AssistantToolName],
) -> list[str]:
    """The fact table and the rule to answer only from it."""

    return build_fact_section_from_rows(
        [(fact_label_text(fact), fact_value_text(fact)) for fact in facts], tools
    )


def fact_label_text(fact: BusinessFact) -> str:
    """A fact's label; an imported one (its title) as an untrusted block."""

    return wrap_untrusted(str(fact.label)) if fact.is_imported else str(fact.label)


def fact_value_text(fact: BusinessFact) -> str:
    """A fact's value; an imported one as an untrusted block."""

    return wrap_untrusted(str(fact.value)) if fact.is_imported else str(fact.value)


def build_fact_section_from_rows(
    rows: Sequence[tuple[str, str]],
    tools: Sequence[AssistantToolName],
) -> list[str]:
    """The fact table from (label, value) rows, and the rule to answer from it."""

    unknown_answer_rule: str = (
        "If the answer is not there, say that you do not know"
        + (
            ", record the question with record_unanswered_question"
            if AssistantToolName.RECORD_UNANSWERED_QUESTION in tools
            else ""
        )
        + " and offer to pass it to a colleague."
    )
    return [
        "# Facts",
        "Answer only from the facts below, the knowledge base (search_knowledge) "
        "and tool results. Never invent prices, opening hours, dates, "
        "availability, people or policies.",
        unknown_answer_rule,
        UNTRUSTED_RULE,
        *(f"- {label}: {value}" for label, value in rows),
    ]


# Rules of booking tools a version assembled before them lacks.
OPTIONAL_BOOKING_RULES: tuple[tuple[AssistantToolName, str], ...] = (
    (
        AssistantToolName.LIST_MY_BOOKINGS,
        "- When customers ask about their own bookings, call list_my_bookings.",
    ),
    (
        AssistantToolName.JOIN_WAITLIST,
        "- When no time is free and check_availability says waitlist_open, offer "
        "the waitlist; call join_waitlist only after the customer agrees.",
    ),
)


SISTER_LOCATION_RULE: str = (
    "- When nothing is free and check_availability lists sister_locations, "
    "offer the brand's other location: its name, address and free times, and "
    "its chat link or phone. You cannot book there yourself."
)


def build_booking_section(
    tools: Sequence[AssistantToolName],
    country_name: str,
    timezone_name: str,
    has_sister_locations: bool = False,
) -> list[str]:
    """
    Booking procedure, or how a request is taken when the version cannot
    book; a brand's location also offers its sister locations.
    """

    phone_rule: str = (
        "- Accept phone numbers of any country; a number without a country "
        f"code is a number of {country_name}."
    )
    time_rule: str = (
        "- All dates and times are local to the business time zone "
        f"({timezone_name}); understand and state them in that time zone."
    )
    if AssistantToolName.CREATE_BOOKING not in tools:
        return [
            "# Requests",
            "- You cannot book directly. When a customer wants to book or order, "
            "collect their name, phone number and what they need with "
            "create_lead and say that a colleague will confirm.",
            phone_rule,
            time_rule,
        ]

    return [
        "# Bookings",
        "- Always call check_availability before create_booking.",
        "- Collect the customer's name, phone number, number of people, date and time.",
        phone_rule,
        "- Before you create, move or cancel a booking, repeat the date, time, "
        "number of people and name back to the customer and wait for a clear "
        "confirmation.",
        "- Follow the booking rules in the facts: maximum party size, minimum "
        "notice, deposit and cancellation policy.",
        "- Use cancel_booking and reschedule_booking to change existing bookings.",
        *(rule for tool, rule in OPTIONAL_BOOKING_RULES if tool in tools),
        *([SISTER_LOCATION_RULE] if has_sister_locations else []),
        time_rule,
        "- For larger groups, banquets, corporate events and other non-standard "
        "requests, collect the details with create_lead.",
    ]
