"""
What a customer message refers to, as the model reads it: a line after the
platform's context, marked untrusted (the story itself is the customer's
or the business's content, which the assistant cannot see).
"""

from app.schemas.constants.channels import InboundContextNote
from app.utilities.conversations.untrusted_text import wrap_untrusted

CONTEXT_NOTE_TEXTS: dict[InboundContextNote, str] = {
    InboundContextNote.STORY_REPLY: "a reply to the business's Instagram story",
    InboundContextNote.STORY_MENTION: (
        "a mention of the business in the customer's own Instagram story"
    ),
}
CONTEXT_NOTE_ADVICE: str = (
    "You cannot see the story: thank the customer for a mention, and ask "
    "what they mean when the message depends on the story."
)


def describe_context_note(note: InboundContextNote) -> str:
    """'Message context: <untrusted>a reply to ...</untrusted> ...'."""

    return (
        f"Message context: {wrap_untrusted(CONTEXT_NOTE_TEXTS[note])}. "
        f"{CONTEXT_NOTE_ADVICE}"
    )
