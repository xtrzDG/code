"""Seams of the channels module: messaging adapters, voice webhooks, storage."""

from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.adapter_contract import AdapterContract
from app.contracts.repo_contract import RepoContract
from app.schemas.domain.manager_links import ManagerTelegramLinkDocument
from app.schemas.dto.calls.missed_calls import MissedCallReport
from app.schemas.dto.channels.channel_webhooks import (
    ChannelDeliveryTarget,
    ChannelInboundMessage,
    ChannelSendReceipt,
    ChannelWebhookPayload,
)
from app.schemas.dto.voice_webhooks import (
    FinishedCallReport,
    PostCallWebhookRequest,
    VoiceToolCallArguments,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_strings import (
    MetaObjectId,
    WhatsAppTemplateLanguageCode,
    WhatsAppTemplateName,
)
from app.schemas.typings.channels.strings import (
    ChannelSecret,
    ManagerLinkCodeHash,
    ProviderMessageId,
)
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.storage.constrained_integers import DocumentCount


class ChannelAdapterContract(AdapterContract, Protocol):
    """
    One messaging channel (concept section 6: every channel implements
    parseWebhook, send and verifySignature; a new channel is a new adapter).
    """

    def verify_signature(
        self,
        payload: ChannelWebhookPayload,
        channel_secret: ChannelSecret | None,
    ) -> None:
        """
        Raise AuthenticationRequiredError unless the platform sent the
        delivery. `channel_secret` is the decrypted credential of the channel
        when the webhook secret is derived from it (Telegram); channels signed
        with an app-wide secret ignore it.
        """
        raise NotImplementedError

    def parse_webhook(
        self,
        payload: ChannelWebhookPayload,
    ) -> list[ChannelInboundMessage]:
        """
        Customer messages of a verified delivery, in order: the typed text
        and the attachments (voice notes, photos, places and every other
        file, with captions), so no customer message goes unanswered.
        Echoes of the business's own messages, delivery statuses and
        reactions are skipped; malformed content yields no messages.
        """
        raise NotImplementedError

    def split(self, text: MessageText) -> list[MessageText]:
        """
        The platform messages `send` sends for `text`: one per part at the
        channel's length limit, in order (each part goes out as one message).
        """
        raise NotImplementedError

    def send(
        self,
        target: ChannelDeliveryTarget,
        text: MessageText,
    ) -> ChannelSendReceipt:
        """
        Send a text, split at the channel's length limit: how many platform
        messages were sent and the id of the last. Raises
        ProviderRateLimitedError, ChannelCredentialRejectedError,
        ProviderRejectedMessageError (a 4xx: sending again cannot help) or
        ExternalServiceError (a temporary failure).
        """
        raise NotImplementedError

    def signal_typing(
        self,
        target: ChannelDeliveryTarget,
        replying_to: ProviderMessageId | None,
    ) -> None:
        """
        Show the customer "typing…" while the reply is being written; the
        platform hides it after a few seconds or when the reply arrives.
        `replying_to` is the platform's id of the customer's message (the
        WhatsApp indicator goes with its read receipt). A channel that
        cannot show typing does nothing (this default). Raises like `send`.
        """
        del target, replying_to


class WhatsAppTemplateAdapterContract(AdapterContract, Protocol):
    """
    Template messages of the WhatsApp Cloud API.

    Free-form text may be sent only within 24 hours of the customer's last
    message; confirmations and reminders outside that window, and staff
    notifications, need templates approved by Meta.
    """

    def send_template(
        self,
        phone_number_id: MetaObjectId,
        recipient: ChannelUserId,
        template_name: WhatsAppTemplateName,
        language_code: WhatsAppTemplateLanguageCode,
        body_parameters: list[MessageText],
    ) -> ProviderMessageId | None:
        """
        The sent message's id. Raises ExternalServiceError (unknown template,
        closed number, ...).
        """
        raise NotImplementedError


class VoiceWebhookAdapterContract(AdapterContract, Protocol):
    """Payloads and signatures of the voice platform (ElevenLabs Agents)."""

    def verify_post_call_signature(
        self,
        request: PostCallWebhookRequest,
        now: Microseconds,
    ) -> None:
        """
        Raise AuthenticationRequiredError for a missing, wrong or stale
        signature of a post-call webhook.
        """
        raise NotImplementedError

    def parse_post_call(self, body: bytes) -> FinishedCallReport | None:
        """
        The finished call of a verified post-call webhook; None for other
        events (audio, failed call initiation). Raises ValidationFailedError
        for a malformed call report.
        """
        raise NotImplementedError

    def parse_call_start_failure(self, body: bytes) -> MissedCallReport | None:
        """
        The caller of a verified post-call webhook about a call the platform
        could not start; None for other events. Raises ValidationFailedError
        for a malformed failure report.
        """
        raise NotImplementedError

    def parse_tool_call(self, body: bytes) -> VoiceToolCallArguments:
        """Raises ValidationFailedError for a malformed tool call body."""
        raise NotImplementedError

    def parse_call_initiation(self, body: bytes) -> RawPhoneNumberInput | None:
        """
        The caller number of a call-initiation request (None when withheld).
        Raises ValidationFailedError for a malformed body.
        """
        raise NotImplementedError


class ChannelMessageReceiptRepoContract(RepoContract, Protocol):
    """
    Webhook receipts of earlier releases (the inbox replaced them); kept
    only until the daily purge has removed the last ones.
    """

    def delete_created_before(self, created_before: Microseconds) -> DocumentCount:
        """Purge receipts created before a moment; returns how many."""
        raise NotImplementedError


class ManagerTelegramLinkRepoContract(RepoContract, Protocol):
    def save(self, link: ManagerTelegramLinkDocument) -> None:
        raise NotImplementedError

    def find_by_code_hash(
        self,
        code_hash: ManagerLinkCodeHash,
    ) -> ManagerTelegramLinkDocument | None:
        """Look a link up by its code (the bot does not know the business)."""
        raise NotImplementedError

    def list_by_business(
        self,
        business_id: BusinessId,
    ) -> list[ManagerTelegramLinkDocument]:
        """Return links ordered by created_at ascending."""
        raise NotImplementedError
