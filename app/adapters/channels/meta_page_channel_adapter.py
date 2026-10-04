from typing import ClassVar

from app.contracts.channel_clients import (
    MetaGraphApiClientContract,
    MetaTypingClientContract,
)
from app.contracts.channels import ChannelAdapterContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.message_media import InboundAttachment
from app.schemas.dto.channels.channel_webhooks import (
    ChannelDeliveryTarget,
    ChannelInboundMessage,
    ChannelSendReceipt,
    ChannelWebhookPayload,
)
from app.schemas.exceptions.application_errors import (
    AuthenticationRequiredError,
    ExternalServiceError,
)
from app.schemas.typings.channels.constrained_integers import DeliveredMessageCount
from app.schemas.typings.channels.strings import (
    ChannelExternalId,
    ChannelSecret,
    OutboundMessagePart,
    ProviderMessageId,
)
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.channels.attachment_reading import has_content
from app.utilities.channels.json_values import (
    JsonObject,
    parse_json_object,
    read_flag,
    read_identifier,
    read_object,
    read_objects,
    read_text,
)
from app.utilities.channels.message_chunks import split_message_text
from app.utilities.channels.meta_page_attachments import read_meta_attachments
from app.utilities.channels.webhook_signatures import is_valid_sha256_signature


class MetaPageChannelAdapter(ChannelAdapterContract):
    """
    Messaging of a Facebook page or an Instagram professional account
    (Graph API webhooks with `messaging` events, Send API with the page
    token). Subclasses name the webhook object, the channel and the length
    limit.

    Echoes of the business's own messages, delivery and read receipts and
    reactions are skipped; a tapped button (postback) counts as the customer
    typing its title. Voice clips, photos, places and other files are
    attachments (`meta_page_attachments`).
    """

    webhook_object: ClassVar[str]
    channel_kind: ClassVar[ChannelKind]
    message_limit: ClassVar[int]

    def __init__(
        self,
        meta_client: MetaGraphApiClientContract,
        app_settings: AppSettings,
        typing_client: MetaTypingClientContract | None = None,
    ) -> None:
        self._meta_client: MetaGraphApiClientContract = meta_client
        self._app_settings: AppSettings = app_settings
        self._typing_client: MetaTypingClientContract | None = typing_client

    def verify_signature(
        self,
        payload: ChannelWebhookPayload,
        channel_secret: ChannelSecret | None,
    ) -> None:
        del channel_secret
        app_secret: PlatformSecret | None = self._app_settings.meta_app_secret
        if app_secret is None or not is_valid_sha256_signature(
            str(app_secret),
            payload.body,
            payload.signature_header,
        ):
            raise AuthenticationRequiredError(
                "The Meta webhook signature is missing or wrong."
            )

    def parse_webhook(
        self,
        payload: ChannelWebhookPayload,
    ) -> list[ChannelInboundMessage]:
        root: JsonObject | None = parse_json_object(payload.body)
        if root is None or read_text(root, "object") != self.webhook_object:
            return []

        messages: list[ChannelInboundMessage] = []
        for entry in read_objects(root, "entry"):
            account_id: str | None = read_identifier(entry, "id")
            if account_id is None:
                continue

            for event in read_objects(entry, "messaging"):
                message: ChannelInboundMessage | None = self._read_event(
                    account_id,
                    event,
                )
                if message is not None:
                    messages.append(message)

        return messages

    def split(self, text: MessageText) -> list[MessageText]:
        return [
            MessageText(part)
            for part in split_message_text(str(text), self.message_limit)
        ]

    def send(
        self,
        target: ChannelDeliveryTarget,
        text: MessageText,
    ) -> ChannelSendReceipt:
        if target.credential is None:
            raise ExternalServiceError(
                f"The {self.channel_kind.value} account of this business is not "
                "connected."
            )

        parts: list[MessageText] = self.split(text)
        provider_message_id: ProviderMessageId | None = None
        for part in parts:
            provider_message_id = self._meta_client.send_page_message(
                target.credential,
                target.channel_user_id,
                OutboundMessagePart(str(part)),
            )

        return ChannelSendReceipt(
            delivered=DeliveredMessageCount(len(parts)),
            provider_message_id=provider_message_id,
        )

    def signal_typing(
        self,
        target: ChannelDeliveryTarget,
        replying_to: ProviderMessageId | None,
    ) -> None:
        """`sender_action` "typing_on" through the page token."""

        del replying_to
        if self._typing_client is None or target.credential is None:
            return

        self._typing_client.show_page_typing(target.credential, target.channel_user_id)

    def _read_event(
        self,
        account_id: str,
        event: JsonObject,
    ) -> ChannelInboundMessage | None:
        sender: JsonObject = read_object(event, "sender") or {}
        sender_id: str | None = read_identifier(sender, "id")
        if sender_id is None or sender_id == account_id:
            return None

        text: str = ""
        attachments: list[InboundAttachment] = []
        message_id: str | None = None
        message: JsonObject | None = read_object(event, "message")
        postback: JsonObject | None = read_object(event, "postback")
        if message is not None:
            if read_flag(message, "is_echo"):
                return None

            text = read_text(message, "text") or ""
            attachments = read_meta_attachments(message)
            message_id = read_text(message, "mid")
        elif postback is not None:
            text = read_text(postback, "title") or ""
            message_id = read_text(postback, "mid")

        if not has_content(text, attachments):
            return None

        return ChannelInboundMessage(
            channel=self.channel_kind,
            account_id=ChannelExternalId(account_id),
            channel_user_id=ChannelUserId(sender_id),
            text=MessageText(text),
            provider_message_id=(
                None if message_id is None else ProviderMessageId(message_id)
            ),
            attachments=attachments,
        )
