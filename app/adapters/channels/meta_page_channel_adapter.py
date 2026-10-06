import logging
from functools import partial
from typing import ClassVar

from app.contracts.channel_clients import (
    MetaGraphApiClientContract,
    MetaTypingClientContract,
)
from app.contracts.channels import ChannelAdapterContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.channels import ChannelKind, InboundContextNote
from app.schemas.domain.message_media import InboundAttachment
from app.schemas.domain.reply_choices import ReplyChoices
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
from app.utilities.channels.choice_delivery import send_with_choices, split_reply
from app.utilities.channels.choice_payloads import page_quick_replies
from app.utilities.channels.json_values import (
    JsonObject,
    parse_json_object,
    read_flag,
    read_identifier,
    read_object,
    read_objects,
    read_text,
)
from app.utilities.channels.meta_page_attachments import read_meta_attachments
from app.utilities.channels.meta_page_events import (
    ROUTINE_KINDS,
    other_entry_kinds,
    skipped_event_kind,
)
from app.utilities.channels.meta_story_context import read_story_note
from app.utilities.channels.skipped_webhook_parts import log_skipped_parts
from app.utilities.channels.webhook_signatures import is_valid_sha256_signature
from app.utilities.sharing.acquisition_sources import read_referral_source

LOGGER: logging.Logger = logging.getLogger(__name__)


class MetaPageChannelAdapter(ChannelAdapterContract):
    """
    Messaging of a Facebook page or an Instagram professional account
    (Graph API webhooks with `messaging` events, Send API with the page
    token). Subclasses name the webhook object, the channel and the length
    limit.

    Echoes of the business's own messages, delivery and read receipts and
    reactions are skipped; a tapped button (postback) counts as the customer
    typing its title, and a tapped quick reply arrives as its text. Voice
    clips, photos, places and other files are attachments
    (`meta_page_attachments`); a reply to the business's Instagram story or
    a mention in the customer's story is the message's context note
    (`meta_story_context`). Options of a reply go out as quick replies.
    The `referral` of a tagged link
    or an ad that came with the message is where the customer came from; a
    referral to an open thread without a message has nothing to answer
    and is skipped.
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
        skipped: list[str] = []
        for entry in read_objects(root, "entry"):
            account_id: str | None = read_identifier(entry, "id")
            if account_id is None:
                skipped.append("entry:without account")
                continue

            skipped.extend(other_entry_kinds(entry))
            for event in read_objects(entry, "messaging"):
                message: ChannelInboundMessage | None = self._read_event(
                    account_id,
                    event,
                )
                if message is None:
                    skipped.append(skipped_event_kind(event, account_id))
                else:
                    messages.append(message)

        log_skipped_parts(LOGGER, self.channel_kind.value, skipped, ROUTINE_KINDS)
        return messages

    def split(
        self, text: MessageText, choices: ReplyChoices | None = None
    ) -> list[MessageText]:
        return [
            MessageText(part)
            for part in split_reply(str(text), self.message_limit, choices)
        ]

    def send(
        self,
        target: ChannelDeliveryTarget,
        text: MessageText,
        choices: ReplyChoices | None = None,
    ) -> ChannelSendReceipt:
        """Options go as quick replies under the last part."""

        credential: ChannelSecret | None = target.credential
        if credential is None:
            raise ExternalServiceError(
                f"The {self.channel_kind.value} account of this business is not "
                "connected."
            )

        def send_part(
            part: str, quick_replies: list[JsonObject] | None = None
        ) -> ProviderMessageId | None:
            return self._meta_client.send_page_message(
                credential,
                target.channel_user_id,
                OutboundMessagePart(part),
                quick_replies,
            )

        parts: list[MessageText] = self.split(text, choices)
        provider_message_id: ProviderMessageId | None = None
        for index, part in enumerate(parts):
            if choices is not None and index == len(parts) - 1:
                provider_message_id = send_with_choices(
                    self.channel_kind.value,
                    str(part),
                    choices,
                    partial(send_part, quick_replies=page_quick_replies(choices)),
                    send_part,
                )
            else:
                provider_message_id = send_part(str(part))

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
        context_note: InboundContextNote | None = None
        message_id: str | None = None
        message: JsonObject | None = read_object(event, "message")
        postback: JsonObject | None = read_object(event, "postback")
        # m.me / ig.me `?ref=` and ads: on the event, the message or the
        # "Get started" postback of a new thread.
        referral: JsonObject | None = read_object(event, "referral")
        if message is not None:
            if read_flag(message, "is_echo"):
                return None

            text = read_text(message, "text") or ""
            attachments = read_meta_attachments(message)
            context_note = read_story_note(message)
            message_id = read_text(message, "mid")
            referral = referral or read_object(message, "referral")
        elif postback is not None:
            text = read_text(postback, "title") or ""
            message_id = read_text(postback, "mid")
            referral = referral or read_object(postback, "referral")

        if not has_content(text, attachments) and context_note is None:
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
            acquisition_source=read_referral_source(referral),
            context_note=context_note,
        )
