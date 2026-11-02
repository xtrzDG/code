"""The customer message an inbox event keeps."""

from collections.abc import Sequence

from app.schemas.constants.channels import InboundContextNote
from app.schemas.domain.inbound_events import InboundCustomerMessage
from app.schemas.domain.message_media import InboundAttachment
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.media.strings import AttachmentCaption
from app.schemas.typings.sharing.constrained_strings import AcquisitionSourceTag
from app.utilities.privacy.sensitive_numbers import mask_sensitive_numbers

NUL_CHARACTER: str = "\x00"


def build_inbound_customer_message(
    channel_user_id: ChannelUserId,
    text: MessageText,
    contact_name: ContactName | None,
    contact_phone_number: E164PhoneNumber | None,
    attachments: Sequence[InboundAttachment] = (),
    acquisition_source: AcquisitionSourceTag | None = None,
    context_note: InboundContextNote | None = None,
    client_ip_address: ClientIpAddress | None = None,
) -> InboundCustomerMessage:
    """
    The message without NUL characters in its text and name: no customer
    means them, and Postgres JSONB cannot store them, so the inbox would
    refuse the message (the engine strips them the same way). Card,
    security code, IBAN and ID numbers in the text and the captions are
    masked before the inbox keeps them (`mask_sensitive_numbers`).
    """

    name: str | None = (
        None
        if contact_name is None
        else str(contact_name).replace(NUL_CHARACTER, "").strip()
    )
    return InboundCustomerMessage(
        channel_user_id=channel_user_id,
        text=MessageText(mask_sensitive_numbers(str(text).replace(NUL_CHARACTER, ""))),
        contact_name=None if not name else ContactName(name),
        contact_phone_number=contact_phone_number,
        attachments=[masked_caption(attachment) for attachment in attachments],
        acquisition_source=acquisition_source,
        context_note=context_note,
        client_ip_address=client_ip_address,
    )


def masked_caption(attachment: InboundAttachment) -> InboundAttachment:
    """The attachment with the sensitive numbers of its caption masked."""

    if attachment.caption is None:
        return attachment

    caption: str = str(attachment.caption)
    masked: str = mask_sensitive_numbers(caption)
    if masked == caption:
        return attachment

    return attachment.model_copy(update={"caption": AttachmentCaption(masked)})


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
