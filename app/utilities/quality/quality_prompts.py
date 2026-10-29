"""
The judge of real conversations (production quality): its instruction and
the one message it gets per conversation.

The same five criteria as the autotest judge; the transcript is the
conversation as stored, its newest MAX_JUDGED_MESSAGES messages, with
phone numbers and e-mail addresses blanked out before they leave the
platform. The notes are for the owner, in the owner's language, and must
not quote the customer.
"""

from collections.abc import Sequence

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.assistants import BusinessFact
from app.schemas.domain.conversations import MessageDocument, ToolCallRecord
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    LanguageTag,
)
from app.utilities.assembly.autotest_prompts import (
    JUDGE_ANSWER_SHAPE,
    JUDGE_PROMPT_OPENING,
    JUDGE_SHARED_CRITERIA,
    TRANSCRIPT_AUTHOR_LABELS,
)
from app.utilities.reply_guard.contact_details import (
    find_email_addresses,
    find_phone_numbers,
)

MAX_JUDGED_MESSAGES: int = 40
MAX_MESSAGE_CHARACTERS: int = 1_000
PHONE_PLACEHOLDER: str = "[phone]"
EMAIL_PLACEHOLDER: str = "[e-mail]"
QUALITY_JUDGE_SYSTEM_PROMPT: str = "\n".join(
    [
        f"{JUDGE_PROMPT_OPENING} You get the business facts, what the system "
        "recorded (bookings, requests and handoffs) and the transcript of a "
        "real conversation with a customer; phone numbers and e-mail "
        "addresses in it are blanked out.",
        *JUDGE_SHARED_CRITERIA,
        "- language: every reply is written in the language the customer wrote in.",
        "The notes are read by the owner of the business: describe each "
        "problem in general terms; never quote the customer and never repeat "
        "a name, phone number, address or other personal detail.",
        *JUDGE_ANSWER_SHAPE,
    ]
)


def build_quality_request_text(
    facts: Sequence[BusinessFact],
    messages: Sequence[MessageDocument],
    country: CountryCode,
    notes_language: LanguageTag,
) -> MessageText:
    """Everything the judge needs about one real conversation."""

    judged: Sequence[MessageDocument] = messages[-MAX_JUDGED_MESSAGES:]
    calls: list[ToolCallRecord] = [
        call for message in messages for call in message.tool_calls if not call.is_error
    ]
    lines: list[str] = [
        f"Write the notes in the language with the tag {notes_language}: "
        "the owner of the business reads them.",
        "",
        "Recorded by the system:",
        f"- bookings created: {count_calls(calls, AssistantToolName.CREATE_BOOKING)}",
        f"- requests created: {count_calls(calls, AssistantToolName.CREATE_LEAD)}",
        "- handed off to a human: "
        f"{'yes' if count_calls(calls, AssistantToolName.HANDOFF_TO_HUMAN) else 'no'}",
        "",
        "Business facts:",
        *(f"- {fact.label}: {fact.value}" for fact in facts),
        "",
        "Transcript:",
        *(
            f"{TRANSCRIPT_AUTHOR_LABELS[message.author]}: "
            f"{blank_contacts(str(message.text)[:MAX_MESSAGE_CHARACTERS], country)}"
            for message in judged
            if message.author is not MessageAuthor.SYSTEM
        ),
    ]
    return MessageText("\n".join(lines))


def count_calls(calls: Sequence[ToolCallRecord], tool_name: AssistantToolName) -> int:
    return sum(1 for call in calls if call.tool_name is tool_name)


def blank_contacts(text: str, country: CountryCode) -> str:
    """The text with its phone numbers and e-mail addresses blanked out."""

    blanked: str = text
    for phone in find_phone_numbers(text, country):
        blanked = blanked.replace(phone.text, PHONE_PLACEHOLDER)

    for address in find_email_addresses(blanked):
        blanked = replace_ignoring_case(blanked, address, EMAIL_PLACEHOLDER)

    return blanked


def replace_ignoring_case(text: str, needle: str, replacement: str) -> str:
    lowered: str = text.lower()
    pieces: list[str] = []
    start: int = 0
    position: int = lowered.find(needle, start)
    while position != -1:
        pieces.extend([text[start:position], replacement])
        start = position + len(needle)
        position = lowered.find(needle, start)

    pieces.append(text[start:])
    return "".join(pieces)
