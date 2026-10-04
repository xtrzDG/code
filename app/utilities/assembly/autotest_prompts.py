"""
Prompts of the AI customer and the judge (concept section 11).

Both are English instructions for the model; the AI customer writes in the
scenario language and the judge scores the five criteria of the concept.
"""

from collections.abc import Sequence

from app.schemas.constants.assistants import AutotestScenarioKind
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.assistants import AutotestTranscriptLine, BusinessFact
from app.schemas.dto.assistants.autotest_runs import AutotestScenario
from app.schemas.dto.conversations import AssistantReply
from app.schemas.typings.assistants.strings import SystemPromptText
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.utilities.assembly.fact_formatting import format_international_phone_number

DONE_MARKER: str = "[DONE]"
# How the AI customer's instruction begins (the scripted model knows the
# role it plays by it).
CUSTOMER_PERSONA_OPENING: str = (
    "You play a customer in an automated test of the AI assistant"
)
CUSTOMER_HINT_FACT_PREFIXES: tuple[str, ...] = ("hours_", "special_day_", "time_zone")
TRANSCRIPT_AUTHOR_LABELS: dict[MessageAuthor, str] = {
    MessageAuthor.CUSTOMER: "Customer",
    MessageAuthor.ASSISTANT: "Assistant",
    MessageAuthor.STAFF: "Staff",
    MessageAuthor.SYSTEM: "System",
}
TRANSLITERATION_NOTE: str = (
    "Type it in Latin letters (transliteration), the way people write it on a "
    "phone without its own keyboard; never use its own alphabet."
)
# How the customer writes in the language scenarios.
KIND_LANGUAGE_NOTES: dict[AutotestScenarioKind, tuple[str, ...]] = {
    AutotestScenarioKind.TRANSLITERATED: (TRANSLITERATION_NOTE,),
    AutotestScenarioKind.FOREIGN_LANGUAGE: (
        "It is the only language you speak: keep writing in it even when the "
        "assistant answers in another language.",
    ),
}
CUSTOMER_OPENING_TEXT: str = (
    "The conversation starts now. Write your first message to the assistant."
)
# How the AI customer's transcript of an owner check begins: its first
# message was the check's question, sent as written (the scripted model
# knows by it that the conversation goes on from there).
OWNER_CHECK_CONTINUATION_OPENING: str = (
    "The conversation has started: your first message was sent for you."
)
SILENT_ASSISTANT_TEXT: str = (
    "(The assistant did not answer: a human colleague will reply later.)"
)
JUDGE_SYSTEM_PROMPT: str = "\n".join(
    [
        "You are a strict quality judge of an AI assistant that answers the "
        "customers of a business. You get the business facts, the test "
        "scenario, what the system recorded (bookings, leads and handoffs) and "
        "the conversation transcript.",
        "Score the assistant on five criteria from 1 (bad) to 5 (perfect):",
        "- facts_and_prices: every fact, price, time and date the assistant "
        "stated is in the facts or came from a tool result; it named no "
        "invented price.",
        "- booking_data: when a booking was made, the name, phone number, "
        "number of people, date and time were collected correctly and confirmed "
        "with the customer first.",
        "- ai_disclosure: the assistant said it is an AI assistant in its first "
        "reply or when asked, and never claimed to be a person.",
        "- handoff: the assistant passed the conversation to a human when it was "
        "needed (the customer asked, a complaint, an emergency, a question it "
        "could not answer) and not otherwise.",
        "- language: every reply is written in the scenario language.",
        "If a criterion does not apply to this conversation, score it 5.",
        "Reply with JSON only, without markdown, in exactly this shape: "
        '{"scores": {"facts_and_prices": 5, "booking_data": 5, '
        '"ai_disclosure": 5, "handoff": 5, "language": 5}, '
        '"notes": ["one short reason per problem"]}',
    ]
)


def build_customer_persona_prompt(
    business_name: str,
    scenario: AutotestScenario,
    customer_phone_number: E164PhoneNumber | None,
    facts: Sequence[BusinessFact],
    customer_name: ContactName | None = None,
) -> SystemPromptText:
    """
    The AI customer's instruction: language, goal, identity, the opening
    hours a customer would know, and when to stop with [DONE]. Autotests
    let the customer pick a name; an evaluation persona brings its own
    (`customer_name`), so the booking it makes can be checked.
    """

    phone_line: str = (
        "Your phone number is "
        f"{format_international_phone_number(customer_phone_number)}."
        if customer_phone_number is not None
        else "You prefer not to give a phone number; ask to be answered here."
    )
    hint_lines: list[str] = [
        f"- {fact.label}: {fact.value}"
        for fact in facts
        if str(fact.key).startswith(CUSTOMER_HINT_FACT_PREFIXES)
    ]
    lines: list[str] = [
        f'{CUSTOMER_PERSONA_OPENING} of the business "{business_name}".',
        "Write only your own messages as the customer: one short message at a "
        "time, the way people write in a messenger, and only in "
        f"{scenario.language_name} (language tag {scenario.language}).",
        *KIND_LANGUAGE_NOTES.get(scenario.kind, ()),
        f"Your goal: {scenario.goal}",
        phone_line,
        (
            "When the assistant asks for your name, give a first name that is "
            f"common among speakers of {scenario.language_name}."
            if customer_name is None
            else f"Your name is {customer_name}; give it when the assistant asks."
        ),
    ]
    if hint_lines:
        lines.append("What you know about the business:")
        lines.extend(hint_lines)

    lines.extend(
        [
            "Stay in character and never say that this is a test.",
            "When your goal is reached, when the assistant clearly cannot help, "
            "or when it has passed you to a human, reply with exactly "
            f"{DONE_MARKER} and nothing else.",
        ]
    )
    return SystemPromptText("\n".join(lines))


def read_customer_message(answer_text: str | None) -> MessageText | None:
    """
    The AI customer's next message, or None when the conversation is over:
    an empty answer or one containing [DONE] (anything around it is a
    farewell and is not sent).
    """

    if answer_text is None:
        return None

    message: str = answer_text.strip()
    if message == "" or DONE_MARKER in message:
        return None

    return MessageText(message)


def build_assistant_turn_text(reply: AssistantReply) -> MessageText:
    """What the AI customer sees of an assistant reply."""

    if reply.text is None:
        return MessageText(SILENT_ASSISTANT_TEXT)

    return reply.text


def build_owner_check_continuation(question: str, reply: AssistantReply) -> MessageText:
    """
    The AI customer's first turn of an owner check that goes on after its
    question: what was asked for it and what the assistant answered.
    """

    return MessageText(
        "\n".join(
            [
                OWNER_CHECK_CONTINUATION_OPENING,
                f"Your first message: {question}",
                f"The assistant answered: {build_assistant_turn_text(reply)}",
                "Write your next message.",
            ]
        )
    )


def build_judge_request_text(
    scenario: AutotestScenario,
    facts: Sequence[BusinessFact],
    transcript: Sequence[AutotestTranscriptLine],
    replies: Sequence[AssistantReply],
    notes_language: LanguageTag,
) -> MessageText:
    """
    Everything the judge needs, as one user message. The notes are for the
    owner, so they are written in the staff language.
    """

    booking_count: int = sum(len(reply.created_booking_ids) for reply in replies)
    lead_count: int = sum(len(reply.created_lead_ids) for reply in replies)
    is_handed_off: bool = any(
        reply.is_handed_off or reply.created_handoff_ids for reply in replies
    )
    lines: list[str] = [
        f"Scenario: {scenario.key} ({scenario.kind.value})",
        f"Language: {scenario.language_name} ({scenario.language})",
        f"Customer goal: {scenario.goal}",
        f"Write the notes in the language with the tag {notes_language}: "
        "the owner of the business reads them.",
        "",
        "Recorded by the system:",
        f"- bookings created: {booking_count}",
        f"- leads created: {lead_count}",
        f"- handed off to a human: {'yes' if is_handed_off else 'no'}",
        "",
        "Business facts:",
        *(f"- {fact.label}: {fact.value}" for fact in facts),
        "",
        "Transcript:",
        *(
            f"{TRANSCRIPT_AUTHOR_LABELS[line.author]}: {line.text}"
            for line in transcript
        ),
    ]
    return MessageText("\n".join(lines))
