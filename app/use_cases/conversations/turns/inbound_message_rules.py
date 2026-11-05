"""What an inbound message is before the turn uses it."""

from app.schemas.constants.channels import ChannelKind
from app.schemas.dto.conversations import InboundMessage
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.strings import MessageText
from app.utilities.privacy.sensitive_numbers import mask_sensitive_numbers

NUL_CHARACTER: str = "\x00"


def clean_inbound_message(message: InboundMessage) -> InboundMessage:
    """
    The message as the turn stores and the model reads it: without NUL
    characters, and with card, security code, IBAN and ID numbers masked
    (the inbox masked those of channel messages already; the owner's test
    chat and the API's messages come here directly).
    """

    cleaned: InboundMessage = remove_nul_characters(message)
    text: str = str(cleaned.text)
    masked: str = mask_sensitive_numbers(text)
    if masked == text:
        return cleaned

    return cleaned.model_copy(update={"text": MessageText(masked)})


def remove_nul_characters(message: InboundMessage) -> InboundMessage:
    """
    The message without NUL characters in its text and name: no customer
    means them, and Postgres JSONB cannot store them, so keeping them would
    answer a message in memory and silently drop it on Postgres.
    """

    text: str = str(message.text)
    name: str | None = (
        None if message.contact_name is None else str(message.contact_name)
    )
    if NUL_CHARACTER not in text and (name is None or NUL_CHARACTER not in name):
        return message

    return message.model_copy(
        update={
            "text": MessageText(text.replace(NUL_CHARACTER, "")),
            "contact_name": (
                None
                if name is None or name.replace(NUL_CHARACTER, "").strip() == ""
                else ContactName(name.replace(NUL_CHARACTER, ""))
            ),
        }
    )


def is_sandbox_message(message: InboundMessage) -> bool:
    """Owner test chat and autotests never reach real customers or billing."""

    return message.is_sandbox or message.channel is ChannelKind.OWNER_TEST
