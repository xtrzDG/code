"""
Webhooks of messaging platforms: inbound messages, reply delivery and
what a webhook call did.
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.message_media import InboundAttachment
from app.schemas.typings.channels.constrained_integers import (
    DeliveredMessageCount,
    WebhookMessageCount,
)
from app.schemas.typings.channels.prefixed_id import ChannelId
from app.schemas.typings.channels.strings import (
    ChannelExternalId,
    ChannelSecret,
    MetaWebhookChallenge,
    MetaWebhookMode,
    PresentedWebhookSecret,
    ProviderMessageId,
    WebhookSignatureHeader,
)
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.sharing.constrained_strings import AcquisitionSourceTag


class ChannelWebhookPayload(ImmutableDTO):
    """
    One webhook delivery exactly as it arrived: the raw body bytes (signatures
    are computed over them) and the platform's authentication header
    (Meta X-Hub-Signature-256, Telegram X-Telegram-Bot-Api-Secret-Token).
    """

    body: bytes
    signature_header: WebhookSignatureHeader | None = None


class TelegramWebhookRequest(ImmutableDTO):
    """Webhook of one business's Telegram bot; the URL names the channel."""

    channel_id: ChannelId
    payload: ChannelWebhookPayload


class MetaWebhookRequest(ImmutableDTO):
    """Webhook of the Meta app: WhatsApp, Messenger and Instagram in one."""

    payload: ChannelWebhookPayload


class MetaWebhookVerificationRequest(ImmutableDTO):
    """GET verification of the Meta webhook (hub.mode, hub.verify_token, ...)."""

    mode: MetaWebhookMode | None = None
    verify_token: PresentedWebhookSecret | None = Field(default=None, repr=False)
    challenge: MetaWebhookChallenge | None = None


class ChannelInboundMessage(ImmutableDTO):
    """
    A customer message as a channel adapter reads it (the concept's
    InboundMessage before the business is resolved).

    `account_id` is the business account inside the channel (WhatsApp phone
    number id, Facebook page id, Instagram account id); it is None when the
    webhook address already names the channel (Telegram). `text` is what
    the customer typed (empty for a photo or a voice note without words);
    `attachments` are the voice notes, photos, places and other files, with
    their captions. `acquisition_source` is where the customer came from
    when the message carried it (`acquisition_sources.py`).
    """

    channel: ChannelKind
    account_id: ChannelExternalId | None = None
    channel_user_id: ChannelUserId
    text: MessageText
    contact_name: ContactName | None = None
    contact_phone_number: E164PhoneNumber | None = None
    provider_message_id: ProviderMessageId | None = None
    attachments: list[InboundAttachment] = Field(
        default_factory=list[InboundAttachment]
    )
    acquisition_source: AcquisitionSourceTag | None = None


class ChannelDeliveryTarget(ImmutableDTO):
    """
    Where a message to a customer goes: the business's account in a channel
    and the customer inside it.

    `credential` is the decrypted bot or page token (None for WhatsApp, which
    uses the platform token). It is excluded from the representation so it
    never reaches logs.
    """

    channel: ChannelKind
    account_id: ChannelExternalId | None = None
    channel_user_id: ChannelUserId
    credential: ChannelSecret | None = Field(default=None, repr=False)


class ChannelSendReceipt(ImmutableDTO):
    """
    What one send through a channel did: how many platform messages went
    out (long texts are split) and the platform's id of the last one, when
    it named one.
    """

    delivered: DeliveredMessageCount
    provider_message_id: ProviderMessageId | None = None


class ChannelWebhookOutcome(ImmutableDTO):
    """
    What happened to the customer messages of one webhook delivery.

    Messages are stored in the inbox and answered by the background worker,
    so the platform gets its 200 at once: `queued` counts new messages,
    `duplicates` messages the platform delivered before. `answered` and
    `silenced` stay 0 (replies are sent later, not in this request);
    `failed` counts messages that could not be stored.
    """

    received: WebhookMessageCount = WebhookMessageCount(0)
    answered: WebhookMessageCount = WebhookMessageCount(0)
    silenced: WebhookMessageCount = WebhookMessageCount(0)
    failed: WebhookMessageCount = WebhookMessageCount(0)
    queued: WebhookMessageCount = WebhookMessageCount(0)
    duplicates: WebhookMessageCount = WebhookMessageCount(0)
