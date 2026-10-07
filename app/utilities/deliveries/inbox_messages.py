"""The customer message an inbox event keeps."""

from collections.abc import Sequence

from app.schemas.constants.channels import InboundContextNote
from app.schemas.domain.inbound_events import InboundCustomerMessage
from app.schemas.domain.message_media import InboundAttachment
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.sharing.constrained_strings import AcquisitionSourceTag

NUL_CHARACTER: str = "\x00"


def build_inbound_customer_message(
    channel_user_id: ChannelUserId,
    text: MessageText,
    contact_name: ContactName | None,
    contact_phone_number: E164PhoneNumber | None,
    attachments: Sequence[InboundAttachment] = (),
    acquisition_source: AcquisitionSourceTag | None = None,
    context_note: InboundContextNote | None = None,
) -> InboundCustomerMessage:
    """
    The message without NUL characters in its text and name: no customer
    means them, and Postgres JSONB cannot store them, so the inbox would
    refuse the message (the engine strips them the same way).
    """

    name: str | None = (
        None
        if contact_name is None
        else str(contact_name).replace(NUL_CHARACTER, "").strip()
    )
    return InboundCustomerMessage(
        channel_user_id=channel_user_id,
        text=MessageText(str(text).replace(NUL_CHARACTER, "")),
        contact_name=None if not name else ContactName(name),
        contact_phone_number=contact_phone_number,
        attachments=list(attachments),
        acquisition_source=acquisition_source,
        context_note=context_note,
    )


def customer_written_text(customer: InboundCustomerMessage) -> MessageText:
    """
    What the customer wrote: the typed text and the captions of their
    photos and files, each once, in order.
    """

    parts: list[str] = [str(customer.text).strip()]
    parts.extend(
        str(attachment.caption).strip()
        for attachment in customer.attachments
        if attachment.caption is not None
    )
    return MessageText("\n\n".join(dict.fromkeys(part for part in parts if part)))
