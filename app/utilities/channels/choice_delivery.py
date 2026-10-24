"""
Sending a reply's last part with its options: the platform's own buttons,
or, when the platform refuses them, the same text with the options as a
numbered list (the customer answers with the option or its number).
"""

import logging
from collections.abc import Callable

from app.schemas.domain.reply_choices import ReplyChoices
from app.schemas.exceptions.application_errors import ProviderRejectedMessageError
from app.schemas.typings.channels.strings import ProviderMessageId
from app.utilities.channels.choice_payloads import fallback_room
from app.utilities.channels.message_chunks import split_message_text
from app.utilities.conversations.reply_choices_text import number_the_options

LOGGER: logging.Logger = logging.getLogger(__name__)

type PartSend = Callable[[str], ProviderMessageId | None]


def split_reply(
    text: str,
    limit: int,
    choices: ReplyChoices | None,
    choice_limit: int | None = None,
) -> list[str]:
    """
    The parts of a reply at the channel's `limit`; with options, every part
    also fits the platform's limit for a message with buttons
    (`choice_limit`) and leaves room for their numbered list.
    """

    if choices is None:
        return split_message_text(text, limit)

    part_limit: int = min(limit - fallback_room(choices), choice_limit or limit)
    return split_message_text(text, part_limit)


def send_with_choices(
    platform: str,
    text: str,
    choices: ReplyChoices,
    send_buttons: PartSend,
    send_text: PartSend,
) -> ProviderMessageId | None:
    """
    The part with the platform's buttons; a refusal of the buttons (a 4xx
    that sending again cannot help) sends the text with a numbered list.
    Other failures are raised for the outbox to retry.
    """

    try:
        return send_buttons(text)
    except ProviderRejectedMessageError as error:
        LOGGER.warning(
            "%s refused the reply's buttons, sending them as a list: %s",
            platform,
            error,
        )
        return send_text(number_the_options(text, choices))
