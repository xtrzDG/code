"""The customer messages of a WhatsApp Cloud API `messages` change."""

from app.contracts.localization_utilities import PhoneNumberParserContract
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.message_media import InboundAttachment
from app.schemas.dto.channels.channel_webhooks import ChannelInboundMessage
from app.schemas.typings.channels.strings import ChannelExternalId, ProviderMessageId
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.utilities.channels.attachment_reading import has_content
from app.utilities.channels.channel_phone_numbers import (
    parse_messaging_phone_number,
)
from app.utilities.channels.json_values import (
    JsonObject,
    read_identifier,
    read_object,
    read_objects,
    read_text,
)
from app.utilities.channels.whatsapp_attachments import read_whatsapp_attachments
from app.utilities.channels.whatsapp_webhook_parts import (
    read_message_text,
    skipped_message_kind,
)
from app.utilities.sharing.acquisition_sources import (
    read_greeting_code,
    read_referral_source,
)

MAX_CONTACT_NAME_LENGTH: int = 128


def read_change_messages(
    value: JsonObject,
    skipped: list[str],
    phone_number_parser: PhoneNumberParserContract,
) -> list[ChannelInboundMessage]:
    """
    The customer messages of one `messages` change: the typed text, a
    tapped button or list row, the attachments, the profile name and where
    the customer came from; what holds none of them is skipped by kind.
    """

    metadata: JsonObject = read_object(value, "metadata") or {}
    phone_number_id: str | None = read_identifier(metadata, "phone_number_id")
    if phone_number_id is None:
        return []

    profile_names: dict[str, str] = {}
    for contact in read_objects(value, "contacts"):
        wa_id: str | None = read_identifier(contact, "wa_id")
        profile: JsonObject = read_object(contact, "profile") or {}
        name: str | None = read_text(profile, "name")
        if wa_id is not None and name is not None:
            profile_names[wa_id] = name

    messages: list[ChannelInboundMessage] = []
    for message in read_objects(value, "messages"):
        sender: str | None = read_identifier(message, "from")
        # A click-to-WhatsApp ad, else the code of a tagged wa.me link.
        coded, text = read_greeting_code(read_message_text(message) or "")
        source = read_referral_source(read_object(message, "referral")) or coded
        attachments: list[InboundAttachment] = read_whatsapp_attachments(message)
        if sender is None or not has_content(text, attachments):
            skipped.append(skipped_message_kind(message))
            continue

        message_id: str | None = read_text(message, "id")
        contact_name: str | None = profile_names.get(sender)
        messages.append(
            ChannelInboundMessage(
                channel=ChannelKind.WHATSAPP,
                account_id=ChannelExternalId(phone_number_id),
                channel_user_id=ChannelUserId(sender),
                text=MessageText(text),
                contact_name=(
                    None
                    if contact_name is None
                    else ContactName(contact_name[:MAX_CONTACT_NAME_LENGTH])
                ),
                contact_phone_number=parse_messaging_phone_number(
                    phone_number_parser,
                    sender,
                ),
                provider_message_id=(
                    None if message_id is None else ProviderMessageId(message_id)
                ),
                attachments=attachments,
                acquisition_source=source,
            )
        )

    return messages
