"""The options a reply offers the customer to tap (model tool offer_choices)."""

from base_pydantic_schemas import PersistentDocument
from pydantic import Field

from app.schemas.typings.conversations.constrained_strings import (
    ChoiceLabel,
    ChoicePromptText,
)

MIN_CHOICES: int = 2
MAX_CHOICES: int = 10


class ReplyChoices(PersistentDocument):
    """
    What the assistant asked and the options it offered with a reply: the
    reply ends with `prompt`, and each option becomes a WhatsApp reply
    button or list row, a Telegram inline button, a Messenger or Instagram
    quick reply or a website chat chip (a numbered list where a channel
    cannot show them). A tap comes back as the option's label.
    """

    prompt: ChoicePromptText
    options: list[ChoiceLabel] = Field(min_length=MIN_CHOICES, max_length=MAX_CHOICES)
