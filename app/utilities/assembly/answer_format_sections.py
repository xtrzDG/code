"""How the assistant's chat answers look (the phone has its own instruction)."""

from collections.abc import Sequence

from app.schemas.constants.assistants import AssistantToolName

CHAT_FORMAT_RULE: str = (
    "Write concise plain text without markdown, usually no more than three "
    "short sentences."
)
LINK_RULE: str = " Send links only through send_link."
# offer_choices is offered in every chat channel (the phone has none), so
# the rule depends on the version's tools only for its examples.
CHOICES_RULE: str = (
    "When the customer has to pick one of a few answers, call offer_choices "
    "with your question and the options so they can tap one: {examples}. "
    "Keep each option to a few words (at most 20 characters, such as "
    '"18:00" or "Yes"), and do not repeat the question or the options in '
    "your text. A tapped option comes back as the customer's message."
)
BOOKING_CHOICES: str = (
    "the free times check_availability returned, the services to choose "
    "from, or yes and no when you repeat a booking back for confirmation"
)
REQUEST_CHOICES: str = (
    "the services to choose from, or yes and no when you repeat a request "
    "back for confirmation"
)


def build_answer_format_section(tools: Sequence[AssistantToolName]) -> list[str]:
    """Plain short text, links through send_link, choices through offer_choices."""

    chat_format: str = CHAT_FORMAT_RULE
    if AssistantToolName.SEND_LINK in tools:
        chat_format += LINK_RULE

    examples: str = (
        BOOKING_CHOICES
        if AssistantToolName.CHECK_AVAILABILITY in tools
        else REQUEST_CHOICES
    )
    return ["# Answer format", chat_format, CHOICES_RULE.format(examples=examples)]
